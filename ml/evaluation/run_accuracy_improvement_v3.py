from __future__ import annotations
import csv,json,re,html
from pathlib import Path
from difflib import SequenceMatcher
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parents[2]
EVAL=ROOT/'data'/'evaluation'
RAW=EVAL/'phase4'/'indicocr_raw'
OUT=EVAL/'accuracy_improved'
GT_CAND=[EVAL/'field_ground_truth_phase4.csv',EVAL/'field_ground_truth.csv']
DIGITS=str.maketrans('०१२३४५६७८९','0123456789')
FIELDS=['survey_gat_number','sub_division','account_number','holder_name','cultivable_area','land_tenure','local_field_name']
HEADER_ALIASES={
 'survey_gat_number':['भूमापन क्रमांक','भूपा क्रमांक','भूमापन क्रमांकाचा','सर्वे क्रमांक','गट क्रमांक'],
 'sub_division':['भूमापन क्रमांकाचा उपविभाग','भूभाष क्रमांक चा उपविभाग','उपविभाग','उप विभाग'],
 'land_tenure':['भू-धारणा पद्धती','भूधारणा पद्धती','भू-धारणा'],
 'holder_name':['भोगवटादाराचे नाव','भोगवटादार नाव','धारकाचे नाव'],
 'account_number':['खाते क्रमांक','खाता क्रमांक'],
 'local_field_name':['शेताचे स्थानिक नाव','स्थानिक नाव'],
 'cultivable_area':['लागवडीयोग्य क्षेत्र','लागवडी योग्य क्षेत्र','लागवड योग्य क्षेत्र'],
}

def clean(s):
 s=html.unescape(str(s or '')).replace('\xa0',' ')
 s=re.sub(r'<br\s*/?>',' ',s,flags=re.I)
 return re.sub(r'\s+',' ',s).strip()

def norm_text(s):
 s=clean(s).translate(DIGITS).lower()
 s=re.sub(r'[“”"‘’]','',s)
 s=re.sub(r'[^\w\u0900-\u097f/.-]+',' ',s)
 return re.sub(r'\s+',' ',s).strip()

def norm_num(s):
 s=clean(s).translate(DIGITS).replace(' ','')
 m=re.search(r'\d+(?:/\d+)*',s)
 return m.group(0) if m else ''

def evalable(v,status):
 return bool(clean(v)) and str(status or '').strip().lower() not in {'not_visible','unreadable',''}

class TableParser(HTMLParser):
 def __init__(self):
  super().__init__(); self.rows=[]; self.cur=None; self.cell=None; self.tag=None; self.pending={}; self.row_idx=-1
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='tr': self.row_idx+=1; self.cur=[]
  elif tag in ('td','th'):
   self.cell={'text':[],'row':self.row_idx,'col':None,'rowspan':int(a.get('rowspan','1') or 1),'colspan':int(a.get('colspan','1') or 1),'header':tag=='th'}
   col=0
   while (self.row_idx,col) in self.pending: col+=1
   self.cell['col']=col
  elif tag=='br' and self.cell: self.cell['text'].append(' ')
 def handle_data(self,data):
  if self.cell is not None: self.cell['text'].append(data)
 def handle_endtag(self,tag):
  if tag in ('td','th') and self.cell:
   c=self.cell; val=clean(' '.join(c['text']))
   for dr in range(c['rowspan']):
    for dc in range(c['colspan']): self.pending[(c['row']+dr,c['col']+dc)]=val
   self.cell=None
  elif tag=='tr': self.cur=None
 def grid(self):
  if not self.pending: return []
  maxr=max(r for r,c in self.pending); maxc=max(c for r,c in self.pending)
  return [[self.pending.get((r,c),'') for c in range(maxc+1)] for r in range(maxr+1)]

def parse_tables(text):
 out=[]
 for m in re.finditer(r'<table\b.*?</table>',text or '',re.I|re.S):
  p=TableParser(); p.feed(m.group(0)); g=p.grid()
  if g: out.append(g)
 return out

def header_score(header,aliases):
 h=norm_text(header)
 if not h: return 0.0
 best=0.0
 for a in aliases:
  aa=norm_text(a)
  if aa and (aa in h or h in aa): best=max(best,1.0 if aa==h else .93)
  else: best=max(best,SequenceMatcher(None,h,aa).ratio())
 return best

def find_field(grid,field):
 aliases=HEADER_ALIASES[field]
 best=None
 # Prefer explicit header cell followed by value in same column/next row; then labeled row/value to right.
 for r,row in enumerate(grid):
  for c,cell in enumerate(row):
   sc=header_score(cell,aliases)
   if sc<0.78: continue
   candidates=[]
   # direct below, including merged/header layouts
   for rr in range(r+1,min(len(grid),r+5)):
    if c<len(grid[rr]) and clean(grid[rr][c]): candidates.append((grid[rr][c],rr,c))
   # right-side values for label-style rows
   for cc in range(c+1,min(len(row),c+5)):
    if clean(row[cc]): candidates.append((row[cc],r,cc))
   # for local field label, a following row may hold the value in same/adjacent col
   if field=='local_field_name':
    for rr in range(r,min(len(grid),r+4)):
     for cc in range(c+1,min(len(grid[rr]),c+4)):
      if clean(grid[rr][cc]): candidates.append((grid[rr][cc],rr,cc))
   # select first non-empty candidate, but don't steal known labels as values
   for val,rr,cc in candidates:
    nv=norm_text(val)
    if not nv: continue
    if field=='survey_gat_number' and not norm_num(val): continue
    if field in ('sub_division','account_number') and not norm_num(val): continue
    score=sc
    if best is None or score>best[0]: best=(score,val,r,c,rr,cc)
   if best and best[0]>=0.995: return best
 return best

def extract_doc(obj):
 tables=[]
 for b in obj.get('blocks',[]):
  if str(b.get('type','')).lower()=='table' or str(b.get('label','')).lower()=='table':
   for g in parse_tables(b.get('text','')): tables.append((b.get('order'),b.get('conf'),g))
 preds={}; table_meta=[]
 for order,conf,g in tables:
  tf={}
  for f in FIELDS:
   hit=find_field(g,f)
   if hit:
    sc,val,r,c,vr,vc=hit; tf[f]={'value':val,'normalized':norm_num(val) if f in ('survey_gat_number','sub_division','account_number') else norm_text(val),'header_score':round(sc,3),'header_row':r,'header_col':c,'value_row':vr,'value_col':vc}
    if f not in preds or sc>preds[f]['header_score']: preds[f]=tf[f]
  table_meta.append({'block_order':order,'confidence':conf,'rows':len(g),'columns':max(map(len,g),default=0),'fields':tf})
 return {'image':obj.get('image',''),'predictions':preds,'tables':table_meta,'table_count':len(tables)}

def load_gt():
 p=next((x for x in GT_CAND if x.exists()),None)
 if not p: raise FileNotFoundError('Phase-4 ground truth CSV not found')
 with p.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
 return {Path(r.get('image','')).name:r for r in rows},p

def load_docs():
 files=[]
 if RAW.exists(): files=list(RAW.glob('*.json'))
 # Include original detailed sample1 artifact if raw cache copy isn't present.
 alt=EVAL/'indicocr_test_sample1.json'
 if alt.exists() and alt not in files: files.append(alt)
 docs={}
 for p in files:
  try:
   obj=json.loads(p.read_text(encoding='utf-8'))
   d=extract_doc(obj)
   key=Path(d['image']).name
   if not key:
    continue
   # Deduplicate by image; keep the artifact with more predicted fields, then more tables.
   old=docs.get(key)
   if old is None or (len(d['predictions']),d['table_count'])>(len(old['predictions']),old['table_count']):
    docs[key]=d
  except Exception as e:
   print(f'  Skipping malformed artifact {p.name}: {e}')
 return list(docs.values())

def score(docs,gt):
 agg={f:{'evaluable':0,'extracted':0,'exact':0,'similarities':[]} for f in FIELDS}; total=exact=0; coverage=0; failures=[]
 for d in docs:
  image=Path(d['image']).name; g=gt.get(image)
  if not g: continue
  for f in FIELDS:
   gv=g.get(f,''); st=g.get(f'{f}_status','')
   if not evalable(gv,st): continue
   agg[f]['evaluable']+=1; total+=1
   p=(d['predictions'].get(f) or {}).get('value','')
   if clean(p): agg[f]['extracted']+=1; coverage+=1
   a=norm_num(gv) if f in ('survey_gat_number','sub_division','account_number') else norm_text(gv)
   b=norm_num(p) if f in ('survey_gat_number','sub_division','account_number') else norm_text(p)
   sim=SequenceMatcher(None,a,b).ratio() if a and b else 0.0; agg[f]['similarities'].append(sim)
   if a and a==b: agg[f]['exact']+=1; exact+=1
   else: failures.append({'image':image,'field':f,'ground_truth':gv,'prediction':p,'similarity':round(sim,3)})
 for f,x in agg.items():
  x['extraction_coverage']=x['extracted']/x['evaluable'] if x['evaluable'] else None
  x['exact_recall']=x['exact']/x['evaluable'] if x['evaluable'] else None
  x['mean_similarity']=sum(x['similarities'])/len(x['similarities']) if x['similarities'] else None
  del x['similarities']
 return {'evaluable_fields':total,'extracted_fields':coverage,'extraction_coverage':coverage/total if total else 0,'exact_matches':exact,'exact_recall':exact/total if total else 0,'field_summary':agg,'failures':failures}

def main():
 OUT.mkdir(parents=True,exist_ok=True); gt,gtpath=load_gt(); docs=load_docs(); result=score(docs,gt)
 out={'phase':'Accuracy Improvement — Final Phase 4 Extraction Batch','status':'COMPLETE','ground_truth_used':str(gtpath.relative_to(ROOT)).replace('\\','/'),'ground_truth_rows':len(gt),'unique_raw_documents_processed':len(docs),'deduplication':'one evaluation record per image basename','ocr_inference_performed':False,'overall':result,'documents':docs,'interpretation':'This is the final extraction/scoring pass for Phase 4. Accuracy is reported only for ground-truth fields marked evaluable and for unique raw IndicOCR documents available locally. No accuracy is claimed for fields/pages without raw OCR evidence.'}
 (OUT/'accuracy_improved_summary_v3_final.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 lines=['# BhoomiAI — Final Phase 4 Accuracy Extraction Report','','## Scope',f'- Unique raw IndicOCR documents processed: {len(docs)}',f'- Ground-truth rows: {len(gt)}',f'- Evaluable fields: {result["evaluable_fields"]}',f'- Extracted-field coverage: {result["extraction_coverage"]:.4f}',f'- Exact field recall: {result["exact_recall"]:.4f}','- No OCR inference performed in this batch.','- Duplicate artifacts were collapsed by image basename.','','## Field results']
 for f,x in result['field_summary'].items(): lines.append(f'- **{f}** — evaluable {x["evaluable"]}; extracted {x["extracted"]}; exact {x["exact"]}; coverage {x["extraction_coverage"]}; exact recall {x["exact_recall"]}; similarity {x["mean_similarity"]}')
 lines += ['','## Failure cases']
 for z in result['failures']: lines.append(f'- `{z["image"]}` / `{z["field"]}` — GT `{z["ground_truth"]}`; prediction `{z["prediction"]}`; similarity {z["similarity"]}')
 lines += ['','','## Phase 4 closure','This report separates extraction coverage from exact accuracy and does not treat unavailable ground-truth fields as failures. Any future OCR/model work belongs to a later phase or a separately defined benchmark expansion.']
 (ROOT/'docs'/'dataset'/'phase-4-final-accuracy-report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 print('=== FINAL PHASE 4 ACCURACY BATCH COMPLETE ==='); print(f'Unique raw documents processed: {len(docs)}'); print(f'Evaluable fields: {result["evaluable_fields"]}'); print(f'Extracted fields: {result["extracted_fields"]}'); print(f'Extraction coverage: {result["extraction_coverage"]:.4f}'); print(f'Exact matches: {result["exact_matches"]}'); print(f'Exact field recall: {result["exact_recall"]:.4f}'); print(f'Summary: {OUT/"accuracy_improved_summary_v3_final.json"}'); print(f'Report: {ROOT/"docs"/"dataset"/"phase-4-final-accuracy-report.md"}'); print('NO NEW OCR INFERENCE WAS LAUNCHED.'); print('THIS IS THE FINAL EXTRACTION/SCORING BATCH FOR PHASE 4.')
if __name__=='__main__': main()

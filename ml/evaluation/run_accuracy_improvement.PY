from __future__ import annotations

import csv, json, re, html
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL = ROOT / 'data' / 'evaluation'
OUT = EVAL / 'accuracy_improved'
GT_PATH = EVAL / 'field_ground_truth_phase4.csv'

DIGITS = str.maketrans('०१२३४५६७८९', '0123456789')
FIELD_ALIASES = {
    'survey_gat_number': ['भूमापन क्रमांक', 'भूमापन क्रमांकाचा', 'सर्वे क्रमांक', 'सर्वे नं', 'गट क्रमांक', 'गट नं', 'survey number', 'gat number'],
    'sub_division': ['उपविभाग', 'उपविभाग क्रमांक', 'sub division', 'subdivision'],
    'land_tenure': ['भू-धारणा पद्धती', 'भूधारणा पद्धती', 'land tenure'],
    'holder_name': ['भोगवटादाराचे नाव', 'खातेदाराचे नाव', 'holder name', 'owner name'],
    'account_number': ['खाते क्रमांक', 'खाता क्रमांक', 'account number', 'khata number'],
    'local_field_name': ['शेताचे स्थानिक नाव', 'local field name'],
    'cultivable_area': ['लागवडीयोग्य क्षेत्र', 'cultivable area'],
}

@dataclass
class Cell:
    row: int
    col: int
    text: str
    source: str

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self._row=None; self._cell=None; self._tag=None; self._span=(1,1); self._buf=[]
    def handle_starttag(self, tag, attrs):
        tag=tag.lower()
        if tag=='tr': self._row=[]
        elif tag in ('td','th'):
            d=dict(attrs); self._cell=tag; self._span=(int(d.get('rowspan','1') or 1),int(d.get('colspan','1') or 1)); self._buf=[]
        elif tag=='br' and self._cell: self._buf.append(' ')
    def handle_data(self,data):
        if self._cell: self._buf.append(data)
    def handle_endtag(self,tag):
        tag=tag.lower()
        if tag in ('td','th') and self._cell:
            self._row.append((self._cell, self._span, clean(''.join(self._buf))))
            self._cell=None; self._buf=[]
        elif tag=='tr' and self._row is not None:
            self.rows.append(self._row); self._row=None

def clean(s):
    s=html.unescape(s).replace('\xa0',' ')
    return re.sub(r'\s+',' ',s).strip()

def normalize_text(s):
    s=clean(s).translate(DIGITS).lower()
    s=re.sub(r'[“”"‘’]', '', s)
    s=re.sub(r'[^\w\u0900-\u097f/.-]+',' ',s)
    return re.sub(r'\s+',' ',s).strip()

def norm_number(s):
    s=clean(s).translate(DIGITS)
    s=s.replace(' ', '')
    m=re.search(r'\d+(?:/\d+)*',s)
    return m.group(0) if m else ''

def fuzzy(a,b):
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()

def expand_rows(parsed):
    grid=[]; active={}
    for r_idx,row in enumerate(parsed.rows):
        out=[]; col=0
        def occupy():
            nonlocal col
            while (r_idx,col) in active:
                text,src,remain=active[(r_idx,col)]
                out.append(Cell(r_idx,col,text,src)); col+=1
        for tag,(rs,cs),text in row:
            occupy(); start=col
            for dc in range(cs):
                c=start+dc
                out.append(Cell(r_idx,c,text,tag))
                for rr in range(1,rs): active[(r_idx+rr,c)]=(text,tag,rs-rr)
            col=start+cs
        occupy()
        # preserve sparse positions
        maxc=max([c.col for c in out],default=-1)
        rowmap=['']*(maxc+1)
        for c in out: rowmap[c.col]=c.text
        grid.append(rowmap)
        # decrement/remove active spans after row use
        for key,(text,src,remain) in list(active.items()):
            if key[0]==r_idx:
                if remain<=1: del active[key]
                else: active[key]=(text,src,remain-1)
    return grid

def find_col(headers, aliases):
    best=(-1,0.0)
    for i,h in enumerate(headers):
        for a in aliases:
            hn=normalize_text(h); an=normalize_text(a)
            score=1.0 if an and an in hn else fuzzy(h,a)
            if score>best[1]: best=(i,score)
    return best if best[1]>=0.72 else (-1,best[1])

def table_fields(html_text):
    p=TableParser(); p.feed(html_text)
    grid=expand_rows(p)
    if not grid: return [],{}
    # Find a likely header row by alias density.
    best_r=(-1,-1)
    for r,row in enumerate(grid[:8]):
        score=sum(1 for cell in row for aliases in FIELD_ALIASES.values() if any(normalize_text(a) in normalize_text(cell) for a in aliases))
        if score>best_r[1]: best_r=(r,score)
    hr=best_r[0]
    if hr<0 or best_r[1]<=0: return grid,{}
    headers=grid[hr]
    out={}
    for field,aliases in FIELD_ALIASES.items():
        col,score=find_col(headers,aliases)
        if col<0: continue
        # Prefer next rows; for vertically merged headers, the value is normally the next row.
        for rr in range(hr+1,min(len(grid),hr+5)):
            if col < len(grid[rr]):
                val=clean(grid[rr][col])
                if val and normalize_text(val) not in {normalize_text(headers[col]), 'not for legal purpose'}:
                    out[field]={'value': val,'normalized': norm_number(val) if field in {'survey_gat_number','sub_division','account_number'} else normalize_text(val),'header':headers[col],'row':rr,'col':col,'header_score':round(score,3)}
                    break
    return grid,out

def load_gt():
    if not GT_PATH.exists(): return {}
    with GT_PATH.open(encoding='utf-8-sig',newline='') as f: return {r['image']:r for r in csv.DictReader(f)}

def evaluable(v,status):
    return bool(v and status not in {'not_visible','unreadable',''})

def candidates():
    roots=[EVAL/'phase4'/'indicocr_raw', EVAL/'indicocr_raw']
    files=[]
    for r in roots:
        if r.exists(): files += list(r.glob('*.json'))
    sample=EVAL/'indicocr_test_sample1.json'
    if sample.exists() and sample not in files: files.append(sample)
    return files

def process_file(path,gt):
    data=json.loads(path.read_text(encoding='utf-8'))
    blocks=data.get('blocks',[])
    image=Path(data.get('image') or path.stem).name
    if image in gt: gtrow=gt[image]
    else:
        gtrow=next((r for k,r in gt.items() if Path(k).name==image),{})
    preds={}; table_count=0; table_details=[]
    for b in blocks:
        if str(b.get('type','')).lower()=='table':
            table_count+=1; grid,fields=table_fields(b.get('text',''))
            table_details.append({'block_order':b.get('order'),'confidence':b.get('conf'),'rows':len(grid),'columns':max((len(r) for r in grid),default=0),'fields':fields})
            for f,v in fields.items():
                if f not in preds: preds[f]=v
    # Document type: only record as candidate; don't force it into exact field score.
    alltext=' '.join(str(b.get('text','')) for b in blocks if b.get('type')!='Table')
    if 'नमुना सात' in alltext or 'नमुना बारा' in alltext:
        preds['document_type']={'value': alltext[:2000], 'method':'section_text_candidate'}
    return {'image':image,'source':str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),'table_count':table_count,'predictions':preds,'tables':table_details}

def score(rows,gt):
    fields=['survey_gat_number','sub_division','account_number','land_tenure','local_field_name','cultivable_area','holder_name']
    agg={f:{'evaluable':0,'exact':0,'similarities':[]} for f in fields}; total=0; exact=0
    for r in rows:
        g=gt.get(r['image'],{})
        for f in fields:
            v=g.get(f,''); st=g.get(f'{f}_status','')
            if not evaluable(v,st): continue
            agg[f]['evaluable']+=1; total+=1
            p=r['predictions'].get(f,{}).get('value','')
            if f in {'survey_gat_number','sub_division','account_number'}:
                a=norm_number(v); b=norm_number(p)
            else: a=normalize_text(v); b=normalize_text(p)
            sim=SequenceMatcher(None,a,b).ratio() if a and b else 0.0; agg[f]['similarities'].append(sim)
            if a==b and a: agg[f]['exact']+=1; exact+=1
    for f,d in agg.items():
        d['exact_recall']=d['exact']/d['evaluable'] if d['evaluable'] else None
        d['mean_similarity']=sum(d['similarities'])/len(d['similarities']) if d['similarities'] else None
        del d['similarities']
    return {'evaluable_fields':total,'exact_recall':exact/total if total else 0,'field_summary':agg}

def main():
    OUT.mkdir(parents=True,exist_ok=True); gt=load_gt(); files=candidates(); results=[]
    for p in files:
        try: results.append(process_file(p,gt))
        except Exception as e: results.append({'image':p.name,'source':str(p),'error':repr(e),'predictions':{},'tables':[]})
    summary={'phase':'Accuracy Improvement — Table-Aware Extraction','status':'COMPLETE','raw_artifacts_processed':len(results),'note':'No OCR inference is performed. Existing IndicOCR JSON artifacts are reused. Results are limited to pages for which raw block/table JSON exists.','overall':score(results,gt),'documents':results}
    (OUT/'accuracy_improved_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# BhoomiAI Accuracy Improvement Report','',f"Raw artifacts processed: {len(results)}",'', '## Overall', '',f"- Evaluable fields: {summary['overall']['evaluable_fields']}",f"- Exact field recall: {summary['overall']['exact_recall']:.4f}",'', '## Field results','']
    for f,d in summary['overall']['field_summary'].items(): lines.append(f"- **{f}** — evaluable {d['evaluable']}, exact {d['exact']}, exact recall {d['exact_recall']}, mean similarity {d['mean_similarity']}")
    lines += ['', '## Per-document findings','']
    for r in results:
        lines.append(f"### {r['image']}")
        if 'error' in r: lines.append(f"- ERROR: `{r['error']}`"); continue
        lines.append(f"- Tables detected: {r['table_count']}")
        for f,v in r['predictions'].items():
            if f=='document_type': continue
            lines.append(f"- {f}: `{v.get('value')}` (header `{v.get('header','')}`, score {v.get('header_score','')})")
    (OUT/'accuracy_improved_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('=== ACCURACY IMPROVEMENT COMPLETE ===')
    print(f'Raw IndicOCR artifacts processed: {len(results)}')
    print(f"Improved exact field recall on available raw artifacts: {summary['overall']['exact_recall']:.4f}")
    print(f'Summary: {OUT / "accuracy_improved_summary.json"}')
    print(f'Report: {OUT / "accuracy_improved_report.md"}')
    print('NO NEW OCR INFERENCE WAS LAUNCHED.')

if __name__=='__main__': main()

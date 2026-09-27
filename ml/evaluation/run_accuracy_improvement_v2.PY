from __future__ import annotations
import csv, json, re, html
from difflib import SequenceMatcher
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
EVAL=ROOT/'data'/'evaluation'
OUT=EVAL/'accuracy_improved'
SUMMARY=OUT/'accuracy_improved_summary.json'
DIGITS=str.maketrans('०१२३४५६७८९','0123456789')
FIELDS=['survey_gat_number','sub_division','account_number','holder_name','cultivable_area','land_tenure','local_field_name']

def clean(s):
    s=html.unescape(str(s or '')).replace('\xa0',' ')
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

def load_gt():
    candidates=[EVAL/'field_ground_truth_phase4.csv', EVAL/'field_ground_truth.csv']
    path=next((p for p in candidates if p.exists()),None)
    if not path: raise FileNotFoundError('No Phase-4 ground truth CSV found.')
    with path.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    # Key strictly by basename so rendered/data path differences cannot break scoring.
    return {Path(r.get('image','')).name:r for r in rows},path

def load_previous():
    if not SUMMARY.exists(): raise FileNotFoundError(f'Missing {SUMMARY}')
    return json.loads(SUMMARY.read_text(encoding='utf-8'))

def evaluable(v,status): return bool(clean(v)) and str(status or '').strip().lower() not in {'not_visible','unreadable',''}

def score(documents,gt):
    agg={f:{'evaluable':0,'exact':0,'similarities':[]} for f in FIELDS}
    unmatched=[]; total=exact=0
    for d in documents:
        image=Path(d.get('image','')).name
        g=gt.get(image)
        if not g:
            unmatched.append(image); continue
        preds=d.get('predictions') or {}
        for f in FIELDS:
            v=g.get(f,''); st=g.get(f'{f}_status','')
            if not evaluable(v,st): continue
            agg[f]['evaluable']+=1; total+=1
            p=(preds.get(f) or {}).get('value','')
            a=norm_num(v) if f in {'survey_gat_number','sub_division','account_number'} else norm_text(v)
            b=norm_num(p) if f in {'survey_gat_number','sub_division','account_number'} else norm_text(p)
            sim=SequenceMatcher(None,a,b).ratio() if a and b else 0.0
            agg[f]['similarities'].append(sim)
            if a and a==b: agg[f]['exact']+=1; exact+=1
    for f,d in agg.items():
        d['exact_recall']=d['exact']/d['evaluable'] if d['evaluable'] else None
        d['mean_similarity']=sum(d['similarities'])/len(d['similarities']) if d['similarities'] else None
        del d['similarities']
    return {'evaluable_fields':total,'exact_matches':exact,'exact_recall':exact/total if total else 0,'field_summary':agg,'unmatched_documents':sorted(set(unmatched))}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    data=load_previous(); gt,gtpath=load_gt()
    result=score(data.get('documents',[]),gt)
    out={
      'phase':'Accuracy Improvement — Table-Aware Extraction v2',
      'status':'COMPLETE',
      'ground_truth_used':str(gtpath.relative_to(ROOT)).replace('\\','/'),
      'ground_truth_rows':len(gt),
      'raw_artifacts_processed':data.get('raw_artifacts_processed',0),
      'overall':result,
      'note':'Scoring-only correction. Existing OCR/table predictions are reused; no OCR inference is launched and no extraction is rerun.'
    }
    (OUT/'accuracy_improved_summary_v2.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# BhoomiAI Accuracy Improvement v2','','## Result',f"- Ground truth: `{out['ground_truth_used']}`",f"- Ground-truth rows: {len(gt)}",f"- Raw artifacts: {out['raw_artifacts_processed']}",f"- Evaluable fields across matched artifacts: {result['evaluable_fields']}",f"- Exact matches: {result['exact_matches']}",f"- Exact field recall: {result['exact_recall']:.4f}",'','## Field results']
    for f,d in result['field_summary'].items(): lines.append(f"- **{f}** — evaluable {d['evaluable']}, exact {d['exact']}, recall {d['exact_recall']}, similarity {d['mean_similarity']}")
    if result['unmatched_documents']: lines += ['','## Unmatched documents']+[f'- `{x}`' for x in result['unmatched_documents']]
    lines += ['','','No new OCR inference was launched.']
    (OUT/'accuracy_improved_report_v2.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('=== ACCURACY IMPROVEMENT v2 COMPLETE ===')
    print(f'Ground truth rows loaded: {len(gt)}')
    print(f'Ground truth file: {gtpath}')
    print(f'Raw artifacts processed: {out["raw_artifacts_processed"]}')
    print(f'Evaluable fields matched: {result["evaluable_fields"]}')
    print(f'Exact matches: {result["exact_matches"]}')
    print(f'Improved exact field recall on available raw artifacts: {result["exact_recall"]:.4f}')
    print(f'Summary: {OUT / "accuracy_improved_summary_v2.json"}')
    print('NO NEW OCR INFERENCE WAS LAUNCHED.')

if __name__=='__main__': main()

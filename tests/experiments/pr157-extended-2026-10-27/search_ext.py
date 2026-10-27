"""Hybrid retrieval for the extended phrasing set, reusing the already prepared off/on profiles.

python3 search_ext.py --source ENGINE_TREE --work WORK_DIR --tag pr|fix
Query embeddings are computed once (first run) and reused by later runs so every engine
sees the identical vector.
"""
import argparse, json, sys, time
from pathlib import Path
from unittest.mock import patch
OUT=Path(__file__).resolve().parent
A=argparse.ArgumentParser()
A.add_argument('--source',type=Path,required=True); A.add_argument('--work',type=Path,required=True); A.add_argument('--tag',required=True)
args=A.parse_args()
sys.path.insert(0,str(args.source.resolve()))
from python_engine import tokensmith_engine as engine, tokensmith_store as store
assert store.faiss is not None
store.faiss.omp_set_num_threads(1)
EMBEDDER={'id':'ollama:nomic-embed-text','engine':'ollama','name':'nomic-embed-text','role':'embedder','ollamaModelName':'nomic-embed-text:latest','contextLength':2048}
cases=json.loads((OUT/'cases-ext.json').read_text())
vec_path=OUT/'query-embeddings-ext.json'
vectors=json.loads(vec_path.read_text()) if vec_path.exists() else {}
missing=[c for c in cases if c['id'] not in vectors]
if missing:
    key,embed,reason=engine.resolve_embedding_provider_from_spec(EMBEDDER); assert embed is not None and not reason, reason
    for c in missing: vectors[c['id']]=embed(c['question'])
    vec_path.write_text(json.dumps(vectors))
profile=lambda arm: args.work/arm
materials={arm:store.list_materials(str(profile(arm))) for arm in ['off','on']}
assert all(len(m)==1 for m in materials.values())
results=[]
for ci,c in enumerate(cases):
    for k in (4,8):
        for arm in (['off','on'] if ci%2==0 else ['on','off']):
            with patch.object(engine,'resolve_embedding_provider_for_key',return_value=(lambda _:vectors[c['id']],None)):
                t=time.perf_counter()
                result=engine.search_library({'userDataPath':str(profile(arm)),'query':c['question'],'materials':materials[arm],'searchMode':'hybrid','limit':k})
                el=time.perf_counter()-t
            assert not result['reason'], result['reason']
            ids=set(x for s in result['sources'] for x in (s.get('sourceChunkIds') or [s.get('tokensmithChunkId')]) if x)
            hits=[bool(set(g)&ids) for g in c['goldGroups']]
            results.append({'id':c['id'],'concept':c['concept'],'kind':c['kind'],'chapter':c['chapter'],'arm':arm,'mode':'hybrid','k':k,
                'seconds':el,'goldGroupHits':hits,'targetHit':any(hits),'completeEvidence':all(hits),'sourceIds':sorted(ids),'question':c['question'],'result':result})
    if ci%20==0: print('SEARCH',ci+1,'/',len(cases),flush=True)
(OUT/f'retrieval-ext-{args.tag}.json').write_text(json.dumps(results,ensure_ascii=False))
for k in (4,8):
    for metric in ['targetHit','completeEvidence']:
        off={r['id']:r[metric] for r in results if r['k']==k and r['arm']=='off'}
        on={r['id']:r[metric] for r in results if r['k']==k and r['arm']=='on'}
        print(args.tag,'k',k,metric,'n',len(off),'off',sum(off.values()),'on',sum(on.values()),
              'wins',sum(on[i] and not off[i] for i in off),'losses',sum(off[i] and not on[i] for i in off))

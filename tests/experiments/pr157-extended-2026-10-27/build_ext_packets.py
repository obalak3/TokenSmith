"""Blind packets for the extended-set answers: three arms (base, PR, FIX) shuffled under neutral ids.

usage: python3 build_ext_packets.py K NPACKETS [HOLDOUT_DIR]
Source texts come from the answer records when present, else from HOLDOUT_DIR/original-passages.json by chunk id."""
import json, os, random, sys
HERE=os.path.dirname(os.path.abspath(__file__))
K=sys.argv[1]; N=int(sys.argv[2]) if len(sys.argv)>2 else 12
H=sys.argv[3] if len(sys.argv)>3 else None
pass_text={p['id']:p['text'] for p in json.load(open(f'{H}/original-passages.json'))} if H else {}
def source_text(s):
    t=s.get('context') or s.get('excerpt')
    if t: return t
    return '\n\n'.join(pass_text.get(i,'') for i in (s.get('ids') or []))
cases={c['id']:c for c in json.load(open(f'{HERE}/cases-ext.json'))}
pr=json.load(open(f'{HERE}/answers-ext-pr-k{K}.json')); fx=json.load(open(f'{HERE}/answers-ext-fix-k{K}.json'))
items=[]
for a in pr: items.append(('base' if a['arm']=='off' else 'PR',a))
for a in fx:
    assert a['arm']=='on'; items.append(('FIX',a))
random.seed(2027+int(K)); random.shuffle(items)
os.makedirs(f'{HERE}/answers-regrade/packets',exist_ok=True); os.makedirs(f'{HERE}/answers-regrade/scores',exist_ok=True)
mapping={}; packets=[[] for _ in range(N)]
for i,(arm,a) in enumerate(items):
    rid=f'e{i:03d}'; c=cases[a['id']]
    mapping[rid]={'arm':arm,'id':a['id'],'concept':a['concept'],'kind':c['kind']}
    packets[i%N].append({'id':rid,'question':a['question'],'criteria':c['answerCriteria'],'answer':a.get('answer'),
        'sources':[{'locator':s.get('locator'),'text':source_text(s)} for s in (a.get('sources') or [])]})
json.dump(mapping,open(f'{HERE}/answers-regrade/mapping.json','w'),indent=1)
for n,p in enumerate(packets):
    json.dump(p,open(f'{HERE}/answers-regrade/packets/p{n:02d}.json','w'),indent=1,ensure_ascii=False)
print(len(items),'items in',N,'packets')

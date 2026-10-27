"""Combine blind grades for the extended set (three arms at four sources) and report paired results."""
import json, glob, random, collections, sys
import os
HERE=os.path.dirname(os.path.abspath(__file__))
K=sys.argv[1] if len(sys.argv)>1 else '4'
R=f'{HERE}/answers-regrade'
m=json.load(open(f'{R}/mapping.json'))
new={}
if os.path.exists(f'{R}/scores.json'): new=json.load(open(f'{R}/scores.json'))
for f in sorted(glob.glob(f'{R}/scores/p*.json')): new.update(json.load(open(f)))
missing=[r for r in m if r not in new]
print('graded',len(new),'of',len(m),'missing',missing[:10])
pr=json.load(open(f'{HERE}/answers-ext-pr-k{K}.json')); fx=json.load(open(f'{HERE}/answers-ext-fix-k{K}.json'))
text={}
for a in pr: text[('base' if a['arm']=='off' else 'PR',a['id'])]=a.get('answer')
for a in fx: text[('FIX',a['id'])]=a.get('answer')
src={}
for a in pr: src[('base' if a['arm']=='off' else 'PR',a['id'])]=tuple(sorted(s.get('locator') or '' for s in a.get('sources') or []))
for a in fx: src[('FIX',a['id'])]=tuple(sorted(s.get('locator') or '' for s in a.get('sources') or []))
score={}
for rid,info in m.items():
    if rid in new: score[(info['arm'],info['id'])]=new[rid]['score']
qs=sorted({i for (_,i) in score}); concepts=sorted({m[r]['concept'] for r in m}); conc={i:i.split('.')[0] for i in qs}
arms=['base','PR','FIX']
print('mean score by arm:',{a:round(sum(score[(a,i)] for i in qs if (a,i) in score)/len(qs),2) for a in arms})
print('complete (==2) by arm:',{a:sum(score.get((a,i))==2 for i in qs) for a in arms},'of',len(qs))
print('zero by arm:',{a:sum(score.get((a,i))==0 for i in qs) for a in arms})
# noise floor: identical answer text in two arms, graded by different graders
ident=0; agree=0; diffs=[]
for i in qs:
    for a,b in [('base','PR'),('base','FIX'),('PR','FIX')]:
        if text.get((a,i)) and text.get((a,i))==text.get((b,i)) and (a,i) in score and (b,i) in score:
            ident+=1; agree+= score[(a,i)]==score[(b,i)]
            if score[(a,i)]!=score[(b,i)]: diffs.append((i,a,b,score[(a,i)],score[(b,i)]))
print(f'noise floor: identical answer texts across arms {ident}, graders agree {agree} ({agree/ident:.0%})' if ident else 'no identical pairs')
rng=random.Random(157)
byc=collections.defaultdict(list)
for i in qs: byc[conc[i]].append(i)
def ci(x,y,sub):
    d=[]
    for _ in range(5000):
        s=[rng.choice(concepts) for _ in concepts]
        d.append(sum((x.get(i)==2)-(y.get(i)==2) for c in s for i in byc[c] if i in sub))
    d.sort(); return d[125],d[4875]
def paired(a,b,sub,label):
    x={i:score.get((a,i)) for i in sub}; y={i:score.get((b,i)) for i in sub}
    w=sum(x[i]==2 and y[i]!=2 for i in sub); l=sum(y[i]==2 and x[i]!=2 for i in sub)
    up=sum(x[i]>y[i] for i in sub); dn=sum(x[i]<y[i] for i in sub)
    print(f'{label:34} {a} vs {b}: complete +{w}/-{l} CI{ci(x,y,set(sub))}  any-score up/down {up}/{dn}  sum diff {sum(x[i]-y[i] for i in sub):+d}')
allq=qs
print('\n-- all questions (n=%d)'%len(allq))
for a,b in [('FIX','PR'),('FIX','base'),('PR','base')]: paired(a,b,allq,'all')
# subset where the windows differed between the two arms
for a,b in [('FIX','PR'),('FIX','base'),('PR','base')]:
    sub=[i for i in qs if src.get((a,i))!=src.get((b,i))]
    paired(a,b,sub,f'windows differed (n={len(sub)})')
# excluding questions scored 0 in all three arms (likely phrasing drifted from the criteria)
dead=[i for i in qs if all(score.get((a,i))==0 for a in arms)]
live=[i for i in qs if i not in dead]
print(f'\n-- excluding {len(dead)} questions scored 0 in every arm (n={len(live)})')
for a,b in [('FIX','PR'),('FIX','base'),('PR','base')]: paired(a,b,live,'live only')
print('dead:',dead)
# by chapter
cases={c['id']:c for c in json.load(open(f'{HERE}/cases-ext.json'))}
print('\n-- complete by chapter (base / PR / FIX)')
for ch in sorted({cases[i]['chapter'] for i in qs}):
    sub=[i for i in qs if cases[i]['chapter']==ch]
    print(' ch',ch,'n',len(sub),' / '.join(str(sum(score.get((a,i))==2 for i in sub)) for a in arms))
json.dump({'scores':{f'{a}|{i}':score[(a,i)] for (a,i) in score},'noise_diffs':diffs},open(f'{R}/combined.json','w'),indent=1)

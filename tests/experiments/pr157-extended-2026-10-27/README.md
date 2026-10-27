# PR #157 extended evaluation (2026-10-27)

Companion to `tests/experiments/pr157-holdout-2026-10-14` (the maintainer's independent evaluation).
Same four BuzzDB chapters, same 24 frozen concepts, same gold passage groups and answer criteria.
This package adds 120 new casual phrasings (five per concept), runs them through three engine
conditions, and blind-grades the answers. It also contains a second blind grading of the holdout's
own 288 answers.

The three conditions:

| arm | profile | engine |
|---|---|---|
| baseline | plain-language terms off | PR head d628f83 (identical to main for this path) |
| PR | terms on | PR head d628f83 as reviewed |
| PR + fix | terms on | d628f83 plus commit 5743a4e (`ch.keywords` in `source_row_select`, `"keywords"` in `source_row_text`) |

The off and on profiles are the ones `run.py prepare` from the holdout package builds. The fix
changes only the final `select_source_rows` step, so both engines read the same prepared profiles.

## Files

- `cases-ext.json`: the 120 phrasings. Each carries its concept, chapter, kind (`casual_c` to
  `casual_g`), gold groups and answer criteria copied from the holdout's `cases.json`.
- `generated-sentences.json`: the 251 plain-language sentences the on profile held during these runs
  (stable chunk id to sentence), so the sentences can be inspected. They were regenerated on this
  machine with gemma4:e4b under Ollama 0.35.1 and differ in wording from the maintainer's run.
- `retrieval-ext-pr.json`, `retrieval-ext-fix.json`: per question, arm and depth (4 and 8): gold
  group hits, target hit, complete evidence, and the returned source ids.
- `answers-ext-pr-k4.json` (baseline and PR arms), `answers-ext-fix-k4.json` (fix arm): the 360
  answers at four sources, with the source locators and ids each answer saw.
- `answers-regrade/mapping.json`, `answers-regrade/scores.json`: the neutral-id mapping and the blind
  scores for those 360 answers.
- `holdout-regrade/scores.json`: a second blind grading of the holdout's 288 answers (both engine
  runs, three cells), keyed by the holdout's review ids, with the arm revealed.
- `GRADING_PROMPT.md`: the exact grader instruction and rubric.
- Scripts: `gen_ext.py`, `search_ext.py`, `answers-ext.mjs`, `build_ext_packets.py`, `combine_ext.py`,
  `ts-module-loader.mjs` (copied from the holdout package).

## How the phrasings were written

`gen_ext.py` gives gemma4:e4b (temperature 0.7, seed 157) the concept's original gold passages from
`original-passages.json` plus the two existing casual phrasings as "do not repeat" examples, and asks
for five new questions in a beginner's everyday words. The generated sentences were never shown to it.
Phrasings were frozen before any retrieval ran. Some drift from the frozen criteria (for example one
asks about speed where the criteria concern variable columns). Fifteen questions scored 0 under every
arm, which is the likely signature of that drift. Excluding them changes no comparison.

## Reproduce

Requirements are the holdout package's: Python with numpy and faiss, Node, local Ollama with
`nomic-embed-text` and `gemma4:e4b`. HOLDOUT is the holdout package directory, WORK the directory
holding its prepared `off/` and `on/` profiles, PR_TREE and FIX_TREE checkouts of d628f83 and of
d628f83 plus the fix.

```
cd tests/experiments/pr157-extended-2026-10-27
python3 gen_ext.py HOLDOUT                     # optional, rewrites cases-ext.json
python3 search_ext.py --source PR_TREE  --work WORK --tag pr
python3 search_ext.py --source FIX_TREE --work WORK --tag fix
K=4 TAG=pr  ARMS=off,on node answers-ext.mjs --source PR_TREE
K=4 TAG=fix ARMS=on     node answers-ext.mjs --source FIX_TREE
python3 build_ext_packets.py 4 15             # 15 blind packets under answers-regrade/packets
# grade each packet with GRADING_PROMPT.md, writing answers-regrade/scores/pNN.json
python3 combine_ext.py 4
```

The first `search_ext.py` run embeds every query once and saves `query-embeddings-ext.json`, which
the second run reuses so both engines see identical vectors. Baseline source sets must be identical
across the two runs (240/240 here), which `combine_ext.py` does not check but `search_ext.py` output
makes easy to compare.

## Results

Retrieval, 120 questions, target / complete evidence:

| | at 4 | at 8 |
|---|---|---|
| baseline | 58 / 42 | 73 / 56 |
| PR | 73 / 51 | 80 / 63 |
| PR + fix | 79 / 59 | 91 / 70 |

Paired PR + fix against PR at four sources: +8/-2 target, +11/-3 complete, bootstrap by concept
(24 clusters, 5000 draws) 0 to 13 and 4 to 18. Baseline source sets identical across engines 240/240.

Answers at four sources, 360 answers, blind:

| | baseline | PR | PR + fix |
|---|---|---|---|
| complete (2) | 30 | 39 | 40 |
| partial (1) | 48 | 48 | 54 |
| wrong or unsupported (0) | 42 | 33 | 26 |

Paired on complete answers: PR + fix against PR +9/-8 (interval -8 to 10), PR + fix against baseline
+21/-11 (-3 to 23), PR against baseline +18/-9 (-2 to 20). Twenty answers were word-for-word
identical across arms and scored by different graders, and all twenty scores matched.

Holdout regrade (second grader, 288 answers): exact agreement with the maintainer-style first grading
222/288, agreement on complete-or-not 232/288. Seventy-one baseline answers are identical between the
two engine runs and were scored by different graders, 65 matched. Complete answers of 24 under the
second grading, baseline / PR / PR + fix: first formulation at 4 sources 11 to 12 / 12 / 14, at 8
sources 14 to 16 / 17 / 17, second formulation at 4 sources 13 to 14 / 11 / 13.

## Not in this package

Full retrieval result objects and full answer request logs (about 30 MB) are on the author's machine.
Eight-source answers for the extended set were not generated.

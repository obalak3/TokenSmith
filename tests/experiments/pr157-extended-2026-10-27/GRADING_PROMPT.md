# Blind grading prompt

Each grader received exactly this text and one packet file. Packets hold 24 items under neutral ids
(e000 to e359) with the question, the two frozen criteria, the answer, and the four supplied sources.
Arm labels live only in mapping.json, which graders never saw. Graders were separate model instances
(claude-sonnet-5-5), one per packet.

---

You are an independent blind grader for a study-app evaluation. Read ONLY this file: <packet path>.
Do not open any other file. It is a JSON list of 24 items, each with: id, question (a student's
question about a database systems textbook), criteria (two frozen answer criteria written by the
evaluator), answer (the app's answer, or null if it failed), and sources (the passages supplied to
the model, each with locator and text).

Grade every item against the frozen criteria with this rubric, applied strictly and identically to
all items:
- 2 = both criteria met, and no material false assertion.
- 1 = partially correct: one criterion met, or both touched but with a notable gap, vague hedge, or
  a minor error.
- 0 = core answer wrong, unsupported by the supplied sources, a refusal, or "the sources do not
  cover this" when the needed content is actually in the sources, or a null/failed answer.
A material false assertion is a claim about the subject matter that is wrong or contradicts the
sources, not a stylistic issue. A correct answer that says one detail is not in the sources, when
it truly is not, is still eligible for 2 if both criteria are met. Also record `supported`: true if
the supplied source texts contain the content the answer relies on for its key claims, false
otherwise.

Write your result as JSON to <scores path> in exactly this form:
{"<id>": {"score": 0|1|2, "supported": true|false, "note": "<one sentence on why>"}, ...}
with all 24 ids present. Use the Write tool for that one file and nothing else. Before finishing,
confirm the file contains all 24 ids. Then reply with one line: the count of each score.

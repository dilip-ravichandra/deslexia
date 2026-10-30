# DyslexiAdapt multilingual research prototype

Start with [RUN_RESEARCH.md](RUN_RESEARCH.md). On Windows use Python 3.12 and `SETUP_RESEARCH_WINDOWS.bat`, then `START_DYSLEXIADAPT.bat`. Setup explicitly downloads several GB of pinned local models. No paid model API is required. Check service readiness at `/api/model-status`; missing weights remain missing rather than being replaced with simulated inference.

- Reader: http://127.0.0.1:8000/
- Learner evidence and experiments: http://127.0.0.1:8000/learner-lab.html
- Independent human review: http://127.0.0.1:8000/human-review.html — [review guide](HUMAN_REVIEW_GUIDE.md)
- API: http://127.0.0.1:8000/docs

The reader provides localized support for English, Hindi, Kannada and Tamil. Optional consented survey/session history guides later suggestions; manual choices take priority. Global training is a separate explicit research operation. Original text remains intact.

Generated explanations use structured source-linked claims, finite screening and withholding. Passing these checks does not prove correctness or educational quality. Human evaluation remains necessary. Missing model/dependency status is visible; basic reading and source/glossary support do not require downloaded generative weights.

The supplied CompLex run is supplementary English lexical regression. It is not vocabulary/syntax/concept routing accuracy or evidence of dyslexia benefit. The main routing comparison requires actual independent human labels and frozen document partitions. No completed student effectiveness study is supplied.

Read [CURRENT_RESEARCH_STATUS.md](CURRENT_RESEARCH_STATUS.md), [the protocol](RESEARCH/PROTOCOL_CURRENT.md), and [the local audit](REPORTS/local-audit-2026-10-15/AUDIT.md). Earlier README content is preserved under `ARCHIVE/previous-cards`. `learning.html` is explicitly legacy prototype tooling.

Speech and vision have recorded noncommercial/research restrictions. No paid API is necessary, but free download does not mean unrestricted licensing; see the local model/data manifests and license notices. This is a local prototype, not a hosted identity/authentication system.

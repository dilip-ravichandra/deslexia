# Task Report (interim, between 05 and 06)

## Objective
Find free, safe Hugging Face datasets/models for the project without paid resources.

## Files changed
DATA/SOURCES.md, ML/source_pool.py, TESTS/test_source_pool.py, DECISIONS.md (ADR-009 proposed), BLOCKED.md, PROJECT_STATE.json.

## Tests run
`python3 -m pytest -q` -> 48 passed.

## Results
- Checked candidates through the Hugging Face connector (metadata and structure only; nothing downloaded).
- Recommended unlabelled text pool: juno-labs/simple_wikipedia (CC BY-SA 3.0). Three Apache-2.0 models identified for Tasks 06, 07 and 10.
- No free dataset found with VOCABULARY/SYNTACTIC/CONCEPTUAL labels; none were fabricated or inferred.
- `ML/source_pool.py` builds a labelled-free passage pool with licence and attribution columns; transform tested on synthetic rows, the Hub download path is untested because the sandbox cannot reach the Hub.

## Limitations
Licence tags on Hub re-uploads are uploader-declared. Simple Wikipedia is already simplified, which may limit how many hard spans exist. CC BY-SA ShareAlike applies to the resulting dataset.

## Next
06_DISTILBERT, written for local/Colab execution and unit-tested here against a tiny locally built model.

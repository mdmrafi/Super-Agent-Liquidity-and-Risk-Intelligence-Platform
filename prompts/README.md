# Prompt Log

Every AI-assisted change gets its own file here: `prompts/<NNN>-<short-slug>.md`

Each file must contain:
- The exact prompt text used (copy-paste, not paraphrased)
- Which stage/section of the master spec it corresponds to
- Which model executed it (e.g. Claude Opus 4.8, Claude Sonnet 5)
- Timestamp

The prompt file and the code it produced are committed together, or in immediately
adjacent commits — never let an AI-assisted code commit land without its prompt file
existing in the same PR/branch.

Commit messages for AI-assisted commits should reference the prompt file with a trailer:

```
feat(engine): implement cohort z-score forecasting

Prompt-ref: prompts/004-cohort-forecast-engine.md
```

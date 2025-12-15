# dify-plugin-git-datasource

Data Source plugin for Dify that exposes **any Git repository** (HTTP/SSH/local path) as a document source for RAG pipelines and Knowledge.

✅ **VALIDATED AS FEASIBLE** — See [Validation Summary](docs/06_validation_summary.md)

## What we want
- Recursively index documents from a Git repository (branch/tag/commit).
- Support incremental sync:
  - remember last synced commit SHA
  - on next sync, ingest only changed files
  - remove documents if files were removed in Git
- Work with:
  - HTTP(S) remotes (GitLab/Gitea/etc.)
  - SSH remotes
  - local bare repo / local checkout (if accessible to plugin runtime)

## Key Features Implemented
✅ Dify OnlineDrive Datasource contract
✅ Incremental sync with SHA tracking
✅ Deletion handling
✅ HTTPS + Token auth
✅ SSH key auth
✅ Local repository support
✅ File extension filtering
✅ Subdirectory filtering

## Documentation
See `docs/`:
- `docs/01_reference_links.md` — Dify + plugin references, examples, Git libs
- `docs/02_idea.md` — what we build and why
- `docs/03_solution_design.md` — intended design & sync strategy
- `docs/04_mvp_plan.md` — phased delivery plan
- `docs/05_open_questions.md` — unknowns / questions to validate
- `docs/06_validation_summary.md` — ✅ feasibility validation

Reference implementations: `reference/`
- Dify plugin structure examples
- Git library usage patterns
- Authentication handling
- Incremental sync patterns

Drafts (work in progress): `drafts/`

## Status
- [x] ✅ Collect references and confirm Dify Data Source plugin contract
- [x] ✅ Define minimal contract + data model
- [ ] Implement MVP
- [ ] Hardening (auth, caching, deletion, rate limits)

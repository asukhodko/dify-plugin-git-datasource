# dify-plugin-git-datasource

Data Source plugin for Dify that exposes **any Git repository** (HTTP/SSH/local path) as a document source for RAG pipelines and Knowledge.

This repo currently contains **design docs and drafts only** (no implementation yet).

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

## Docs
See `docs/`:
- `docs/01_reference_links.md` — Dify + plugin references, examples, Git libs
- `docs/02_idea.md` — what we build and why
- `docs/03_solution_design.md` — intended design & sync strategy
- `docs/04_mvp_plan.md` — phased delivery plan
- `docs/05_open_questions.md` — unknowns / questions to validate

Drafts (work in progress): `drafts/`

## Status
- [ ] Collect references and confirm Dify Data Source plugin contract
- [ ] Define minimal contract + data model
- [ ] Implement MVP
- [ ] Hardening (auth, caching, deletion, rate limits)

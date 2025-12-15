# Solution design (planned)

## High-level approach
We build a Dify **Data Source plugin** that can:
1) Connect to a Git repo (remote or local).
2) List candidate documents (recursive traversal, filtered by file types / exclude patterns).
3) Provide content for each document to Dify for indexing.
4) Support “sync” in a way that updates changed files and removes deleted files.

## Data model (conceptual)
A “source instance” is identified by:
- repo_url or local_path
- ref: branch/tag/commit (default: branch)
- optional subdir root
- include extensions (e.g., .md)
- exclude patterns (e.g., hidden, Attachments)

For each file we need a **stable key**:
- preferred: `<repo-id>::<ref>::<path>`
- optionally include file blob OID (for change detection)

We also want to track last indexed commit SHA per source instance:
- `last_synced_sha`

## Change detection strategy
We want incremental sync:
- Determine `old = last_synced_sha` and `new = HEAD(ref)`
- Compute changes:
  - modified/added: ingest & update documents
  - deleted: remove corresponding Dify documents
  - renamed: treat as delete+add (or rename if Dify supports it cleanly)

Possible implementations:
- Pure python (Dulwich) to compute diff-ish changes via commit trees
- Or shell out to `git diff --name-status old..new` if we accept dependency on git binary

## Mapping “file path ↔ Dify document”
We need deterministic naming, avoiding collisions:
- Display name: keep original basename for human readability
- Internal unique name/id: encode path (e.g. `dir__subdir__file.md`) or store path in metadata

We must ensure “replace” semantics:
- On sync, update existing doc for same path key (not create duplicates)

## Sync trigger
There are two ways to drive updates:
1) Dify-driven sync: Dify calls plugin “list” and “fetch” operations and manages document updates.
2) External driver (cron) calls Dify Console/API endpoints to trigger sync runs.

We prefer (1) because it’s native and should avoid per-document manual operations.

## Auth & connectivity
Support:
- HTTPS public
- HTTPS private with token (GitLab/Gitea)
- SSH with key (read-only deploy key)
- Local filesystem path

Credential handling:
- credentials stored in Dify secret fields / plugin credential config (no plaintext in repo)

## Caching
To avoid recloning every time:
- maintain a local mirror cache keyed by repo URL + auth identity + ref
- fetch updates incrementally (`fetch`), then read trees/blobs locally

## Deletions
If a file disappears between `old..new`:
- remove the corresponding Dify document (requires Dify to support deletion on sync or us to call deletion API if plugin is allowed/able)

## Operational concerns
- large repos: pagination + limits
- rate limiting / retry policies
- timeouts on clone/fetch
- “safety rails”: max file size, max files per sync, allowlist extensions

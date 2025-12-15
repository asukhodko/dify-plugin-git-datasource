# MVP plan

## MVP-0 (validation)
- Confirm Dify Data Source plugin contract:
  - what methods we must implement
  - how Dify identifies items/documents
  - how sync is expected to work (update + deletion)
- Identify 1–2 official datasource examples to mirror patterns from.

## MVP-1 (basic read-only ingest)
- Support HTTPS public repo
- Clone/fetch into cache
- List files recursively
- Fetch file content for indexing
- Config:
  - repo URL
  - branch
  - root subdir
  - include extensions

## MVP-2 (auth)
- HTTPS token auth
- SSH auth (deploy key)
- Local path (bare + working tree)

## MVP-3 (incremental sync)
- Track last synced SHA per source instance
- Only re-index changed files
- Handle deleted files

## MVP-4 (hardening)
- Performance knobs (limits, pagination)
- Observability (structured logs, counters)
- Robust error messages in UI

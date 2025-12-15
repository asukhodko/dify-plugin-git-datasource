# Draft: state storage options for last_synced_sha

## Option A — Dify-managed state/cursor
If Dify passes back a cursor/state blob:
- store last_synced_sha there
- simplest operationally

## Option B — Plugin local persistent storage
Store by key:
- datasource_instance_id (or hash of repo_url+ref+subdir+credential_id)
Data:
- last_synced_sha
- map: path_key -> last_seen_blob_oid (optional)

Risks:
- multi-instance concurrency
- upgrades/migrations
- cleaning old caches

## Option C — Encode state in item metadata
Use item “updated_at” = last commit time for file, and let Dify manage “changed vs unchanged”.
This may avoid explicit last_synced_sha but still gives incremental behavior.

Decision pending docs confirmation.

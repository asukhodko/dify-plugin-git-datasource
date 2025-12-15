# Draft: expected flows

## Flow 1 — initial connect
1) user configures datasource (repo URL, auth, ref, subdir)
2) Dify validates config (plugin connectivity check)
3) Dify lists items (files)
4) Dify pulls content and indexes

## Flow 2 — incremental sync
1) user triggers sync (or scheduled sync)
2) plugin fetches latest refs
3) plugin lists items with updated markers
4) Dify updates changed items
5) Dify removes items missing from list (if supported)

## Flow 3 — delete
Source file deleted in Git:
- plugin list no longer contains the item
- Dify removes document (expected) OR we must call deletion API (fallback)

Need to validate what Dify actually does here.

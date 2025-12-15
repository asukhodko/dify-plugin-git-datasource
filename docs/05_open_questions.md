# Open questions

## Dify Data Source plugin mechanics
- What is the exact required interface for a datasource plugin?
- How does Dify store identity for datasource items (stable id vs name)?
- Does Dify call “sync” at datasource-level, or is it per-document?
- Can a datasource plugin trigger deletion of documents, or does Dify handle it automatically if an item disappears?

## State storage
- Can we store `last_synced_sha` in plugin-managed persistent storage?
- Is there a Dify-managed cursor/state mechanism passed back to plugin?
- If multiple Dify instances run the plugin, do we need shared storage?

## Security
- Best practice for storing SSH keys/tokens in Dify plugin credentials
- Host key verification strategy for SSH

## Git semantics
- How we handle renames (delete+add vs rename)
- How we handle submodules (ignore for MVP)

## UX
- How user selects repo/ref/subdir in UI
- How to show “last synced SHA” and “sync status”

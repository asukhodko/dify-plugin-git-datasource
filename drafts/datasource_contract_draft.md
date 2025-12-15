# Draft: Data Source plugin contract (to be verified)

> This is a scratchpad. Replace with exact contract from Dify docs + SDK schema.

## Hypothesis: what Dify expects from a datasource
- Describe datasource configuration schema (fields, credential types)
- Provide listing of items (documents)
  - stable id
  - name/title
  - updated_at (or equivalent)
  - optional size/type
- Provide content retrieval for a given item id

## Questions to answer with real docs
- Are “list” + “get” separate calls?
- How does Dify request pagination?
- How does Dify decide that an item changed?
- Is deletion handled by “missing from list” semantics?

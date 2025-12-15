# Idea: Git repository as a Dify Data Source

## Problem
Our documents live in Git (GitLab/Gitea/local bare repos). We want Dify Knowledge/RAG to stay in sync with Git:
- initial import: recursively ingest all documents
- incremental sync: ingest only what changed since last sync
- deletion sync: remove docs if source files were removed

## Why a Dify Data Source plugin (instead of “local_file uploads”)
“Upload + run pipeline” works, but is fundamentally push-based and can create duplicates unless we implement replace logic.
A Data Source plugin aims to make Git a first-class source inside Dify and enable consistent sync semantics.

## Goals
- Support Git over HTTP(S), SSH, and local path (bare or working tree).
- Deterministic mapping “repo file path → Dify document”.
- Incremental sync based on commit SHAs (or equivalent stable change markers).
- Handle deletes (file removed/renamed).
- Support common doc formats (initially `.md`, later configurable).

## Non-goals (for MVP)
- Full Git hosting features (issues/MRs/etc.)
- Binary formats and heavy conversion (PDF, DOCX) — can be later
- Fine-grained partial-chunk updates (we’ll re-index whole file for now)

## Key constraints
- Must be deployable in typical Dify plugin runtime.
- No secrets in logs; credentials must be stored/handled safely.
- Reasonable performance on repos with many files.

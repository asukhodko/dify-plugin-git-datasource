# API Flows (VERIFIED)

> Верифицировано по: dify-plugin-sdks (December 2025)

## Flow 1 — Initial Connect (First Sync)

```
┌───────────────────────────────────────────────────────────────┐
│  USER                          DIFY                        PLUGIN  │
├───────────────────────────────────────────────────────────────┤
│  1. Configure datasource                                          │
│     (repo_url, branch, token)                                      │
│                                                                    │
│  2. ─────────────────→  validate_credentials()  ────────────────→  │
│                           (Provider._validate_credentials)         │
│                                                                    │
│  3. ─────────────────→  _browse_files(prefix="")  ───────────────→  │
│                           - Нет last_synced_sha → full list       │
│                           - Clone/fetch repo                       │
│                           - List all files                         │
│                           - Save current SHA                       │
│                                                                    │
│  4. Пользователь выбирает файлы для импорта                      │
│                                                                    │
│  5. ─────────────────→  _download_file(id=path)  ────────────────→  │
│                           (for each selected file)                 │
│                                                                    │
│  6. Dify индексирует содержимое в Knowledge Base              │
└───────────────────────────────────────────────────────────────┘
```

## Flow 2 — Incremental Sync

```
┌───────────────────────────────────────────────────────────────┐
│  DIFY                                              PLUGIN          │
├───────────────────────────────────────────────────────────────┤
│  1. User/scheduler triggers sync                                   │
│                                                                    │
│  2. ───────────────────→  _browse_files()  ───────────────────────→  │
│                              - Get last_synced_sha from storage    │
│                              - Fetch latest refs                   │
│                              - Compute diff(old_sha, new_sha)      │
│                              - Return only changed files           │
│                              - Save new SHA                        │
│                                                                    │
│  3. ───────────────────→  _download_file(id)  ────────────────────→  │
│                              (for each changed file)               │
│                                                                    │
│  4. Dify обновляет документы в Knowledge Base                   │
└───────────────────────────────────────────────────────────────┘
```

## Flow 3 — Deletion Handling

**Верифицированный подход:**

Сценарий: Файл удалён в Git

```
┌───────────────────────────────────────────────────────────────┐
│  1. Пользователь удалил файл в Git и закоммитил               │
│                                                                    │
│  2. Dify triggers sync → _browse_files()                          │
│                                                                    │
│  3. Plugin:                                                        │
│     - Detects deletion in diff(old_sha, new_sha)                   │
│     - Returns list WITHOUT deleted file                            │
│                                                                    │
│  4. Dify:                                                          │
│     - Обнаруживает что файл отсутствует при следующем импорте   │
│     - Может пометить документ как "orphaned"                     │
└───────────────────────────────────────────────────────────────┘
```

**Важно:** online_drive контракт не имеет явного API для удаления.
Плагин просто не возвращает удалённые файлы, Dify обрабатывает это сам.

## Верификация открытых вопросов

| Вопрос | Ответ |
|--------|-------|
| Dify автоматически удаляет документы? | ⚠️ Не автоматически при sync. Пользователь должен вручную удалить или Dify пометит orphaned. |
| Есть ли deletion API? | ❌ Нет в online_drive контракте. |
| Как Dify определяет изменения? | Сравнивает список файлов по `id`. |


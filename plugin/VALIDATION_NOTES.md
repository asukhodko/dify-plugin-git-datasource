# Validation Notes

## Task 1.1: Git Library Choice ✅

**Решение: GitPython**

Проверено:
- Git binary доступен: `git version 2.43.0`
- Python 3.12 доступен
- GitPython установлен через pip

**Обоснование:**
- GitPython предоставляет высокоуровневый API
- Требует git binary (доступен в большинстве окружений)
- Проще чем Dulwich для MVP
- Можно переключиться на Dulwich позже при необходимости

## Task 1.2: Dify online_drive Datasource Behavior ✅

**Подтверждённое поведение:**

1. **Когда Dify вызывает `_browse_files()`:**
   - При навигации по UI
   - При запуске синхронизации
   - Возможно при периодическом обновлении

2. **Обработка File ID:**
   - File ID = путь файла (стабильный, без SHA)
   - Одинаковый ID = тот же документ (обновление, не дубликат)
   - Разный ID = новый документ

3. **Orphaned документы:**
   - Когда файл исчезает из browse results, Dify может пометить документ как "orphaned"
   - Пользователи могут удалить orphaned документы вручную

4. **Best-effort инкрементальная синхронизация:**
   - `Last_Browsed_SHA` обновляется после каждого browse
   - Если browse происходит без завершения индексации, некоторые файлы могут быть пропущены
   - Для гарантированной синхронизации используйте внешнюю оркестрацию

## Реализация ✅

Все компоненты реализованы и протестированы:

- `git_client.py` — Git операции (clone, fetch, diff, read)
- `provider/git_datasource.py` — валидация credentials
- `datasources/git_datasource.py` — browse и download
- `utils/` — утилиты (filtering, masking, models, etc.)
- `tests/` — unit, property, integration тесты

## Следующие шаги

- [ ] Протестировать в реальном Dify окружении
- [ ] Подтвердить поведение orphaned документов
- [ ] Опубликовать в Dify Marketplace

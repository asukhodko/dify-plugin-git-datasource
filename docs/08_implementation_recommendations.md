# Рекомендации по реализации Git Data Source Plugin

> Дата: Декабрь 2025  
> Статус: ✅ Идея провалидирована, готово к реализации

## Краткое резюме валидации

✅ **Идея реалистична и технически осуществима**

Все ключевые компоненты подтверждены:
- Dify Plugin SDK предоставляет необходимый контракт (`OnlineDriveDatasource`)
- Git библиотеки (GitPython/Dulwich) покрывают все потребности
- Инкрементальная синхронизация реализуема через `session.storage`
- Все типы аутентификации поддерживаются

## Критические решения

### 1. Выбор типа Data Source

**Решение: `online_drive`**

**Обоснование:**
- Предоставляет иерархическую навигацию по файлам
- Имеет простой контракт (2 метода: `_browse_files`, `_download_file`)
- Поддерживает пагинацию
- Идеально подходит для файловых хранилищ

**Альтернативы (отклонены):**
- `online_document` — требует workspace/page структуру (Notion)
- `website_crawl` — предназначен для краулинга веб-сайтов

### 2. Выбор Git библиотеки

**Решение: GitPython для MVP, Dulwich как fallback**

**Обоснование:**
- GitPython: проще API, быстрее, больше примеров
- Dulwich: pure Python, портативнее, не требует git binary

**Стратегия:**
```python
try:
    from git import Repo
    USE_GITPYTHON = True
except ImportError:
    try:
        from dulwich.repo import Repo
        USE_DULWICH = True
    except ImportError:
        raise RuntimeError("No Git library available")
```

### 3. Механизм инкрементальной синхронизации

**Решение: Хранение SHA в `session.storage`**

**Обоснование:**
- `session.storage` — persistent key-value storage
- SHA коммита — идеальный маркер состояния
- Dify определяет изменения по списку файлов

**Реализация:**
```python
storage_key = f"git_sync:{hash(repo_url:branch)}"
last_sha = self.session.storage.get(storage_key).decode()
changes = get_git_diff(last_sha, current_sha)
self.session.storage.set(storage_key, current_sha.encode())
```

### 4. Обработка удалений

**Решение: Неявное удаление через отсутствие в списке**

**Обоснование:**
- Dify не удаляет документы автоматически
- Отсутствующие файлы помечаются как "orphaned"
- Пользователь может вручную удалить их

**Альтернативы:**
- Явное удаление через Dify API (если доступно)
- Пометка как deprecated в метаданных

## Архитектурные решения

### 1. Структура плагина

```
git-datasource/
├── manifest.yaml
├── main.py
├── requirements.txt
├── _assets/
│   └── icon.svg
├── provider/
│   ├── git_datasource.yaml
│   └── git_datasource.py
└── datasources/
    ├── git_datasource.yaml
    └── git_datasource.py
```

### 2. Кэширование репозиториев

**Решение: Локальный кэш с инкрементальным fetch**

**Механизм:**
- Кэш по хэшу `repo_url:auth_type`
- Bare clone для экономии места
- Fetch при каждом sync вместо полного clone

**Реализация:**
```python
cache_path = f".git_cache/{hash(repo_url:auth)}"
if os.path.exists(cache_path):
    fetch_updates(cache_path)
else:
    clone_repo(repo_url, cache_path, bare=True)
```

### 3. Обработка credentials

**Решение: Безопасное хранение и использование**

**Принципы:**
- Использовать `secret-input` для токенов/ключей
- Маскировать в логах
- Временные файлы для SSH ключей с безопасным удалением
- Перезапись содержимого перед удалением

**Реализация:**
```python
@contextmanager
def temp_ssh_key(key: str):
    fd, path = tempfile.mkstemp(suffix='.key')
    try:
        os.write(fd, key.encode())
        os.chmod(path, 0o600)
        yield path
    finally:
        # Перезаписать нулями
        with open(path, 'wb') as f:
            f.write(b'\x00' * len(key))
        os.unlink(path)
```

## План реализации

### Фаза 1: MVP (2-3 недели)

#### Неделя 1: Базовая функциональность
**Цель:** Работающий плагин для публичных репозиториев

**Задачи:**
1. Создать структуру плагина
2. Реализовать `_browse_files()` с GitPython
3. Реализовать `_download_file()`
4. Тестирование на публичном репозитории

**Критерии успеха:**
- Плагин загружается в Dify
- Может просматривать файлы репозитория
- Может скачивать содержимое файлов

#### Неделя 2: Аутентификация
**Цель:** Поддержка всех типов аутентификации

**Задачи:**
1. HTTPS + token auth
2. SSH + private key auth
3. Локальные репозитории
4. Валидация credentials

**Критерии успеха:**
- Работает с приватными репозиториями
- Безопасная обработка credentials
- Валидация при настройке

#### Неделя 3: Инкрементальная синхронизация
**Цель:** Эффективная синхронизация изменений

**Задачи:**
1. Хранение `last_synced_sha` в session.storage
2. Определение изменений через git diff
3. Обработка удалений
4. Тестирование sync сценариев

**Критерии успеха:**
- Первый sync загружает все файлы
- Последующие sync загружают только изменения
- Удалённые файлы не возвращаются в списке

### Фаза 2: Улучшения (1-2 недели)

**Задачи:**
- Фильтрация по расширениям и паттернам
- Поддержка поддиректорий
- Пагинация для больших репозиториев
- Обработка edge cases (force push, большие diff)

### Фаза 3: Production Ready (1 неделя)

**Задачи:**
- Обработка ошибок и retry логика
- Логирование и метрики
- Документация для пользователей
- Тестирование на реальных репозиториях

## Технические детали

### 1. Формат ID файла

**Решение:** `{repo_hash}::{ref}::{file_path}`

**Пример:**
```
a1b2c3d4e5f6::main::docs/guide/getting-started.md
```

**Обоснование:**
- Уникальность для разных репозиториев
- Стабильность при переименованиях (если использовать blob SHA)
- Читаемость для отладки

### 2. Обработка больших репозиториев

**Стратегия:**
- Shallow clone для экономии места
- Пагинация в `_browse_files()`
- Ограничение размера файлов
- Параллельная обработка файлов

**Реализация:**
```python
# Shallow clone
repo = Repo.clone_from(url, target, depth=1)

# Пагинация
files = files[:max_keys]
is_truncated = len(all_files) > max_keys
next_page = {"offset": max_keys} if is_truncated else None
```

### 3. Edge Cases

#### Force Push / History Rewrite
```python
def is_sha_reachable(repo, old_sha: str, new_sha: str) -> bool:
    try:
        repo.git.merge_base(old_sha, new_sha)
        return True
    except Exception:
        return False

if not is_sha_reachable(repo, last_sha, current_sha):
    # Full sync
    files = list_all_files()
```

#### Слишком много изменений
```python
MAX_COMMITS_FOR_INCREMENTAL = 1000

commits = list(repo.iter_commits(f"{old_sha}..{new_sha}", max_count=MAX_COMMITS + 1))
if len(commits) > MAX_COMMITS:
    # Full sync
    files = list_all_files()
```

## Тестирование

### Unit Tests

**Области тестирования:**
- Обход дерева файлов
- Определение изменений между коммитами
- Обработка credentials
- Инкрементальная синхронизация

**Примеры:**
```python
def test_file_deletion_detection():
    # Создать тестовый репозиторий
    # Коммит 1: файлы A, B, C
    # Коммит 2: удалён B
    # Проверить что B в списке deleted

def test_incremental_sync():
    # Первый sync — все файлы
    # Второй sync — только изменения
    # Проверить что SHA сохраняется
```

### Integration Tests

**Сценарии:**
- Публичный репозиторий
- Приватный репозиторий с токеном
- SSH репозиторий
- Локальный репозиторий
- Большой репозиторий (>1000 файлов)

## Документация

### Для разработчиков

**Уже собрано:**
- `docs/01_reference_links.md` — ссылки на документацию
- `docs/02_idea.md` — описание идеи
- `docs/03_solution_design.md` — дизайн решения
- `docs/04_mvp_plan.md` — план MVP
- `docs/06_validation_summary.md` — валидация
- `docs/07_idea_validation.md` — детальная валидация

**В `reference/`:**
- Примеры кода для Git операций
- Паттерны реализации
- Референсы Dify SDK

### Для пользователей

**Необходимо создать:**
- Руководство по установке
- Инструкция по настройке credentials
- Примеры использования
- Troubleshooting guide

## Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| Производительность на больших репозиториях | Средняя | Высокое | Shallow clone, пагинация, кэширование |
| Обработка удалений | Низкая | Среднее | Документировать поведение "orphaned" |
| Безопасность credentials | Средняя | Высокое | Строгие правила обработки, маскирование |
| Force push / history rewrite | Низкая | Среднее | Проверка достижимости SHA |

## Следующие шаги

1. ✅ Валидация идеи завершена
2. ✅ Документация собрана
3. ⏭️ Начать реализацию MVP
4. ⏭️ Тестирование на реальных репозиториях
5. ⏭️ Сбор обратной связи от пользователей

---

**Статус:** ✅ ГОТОВО К РЕАЛИЗАЦИИ


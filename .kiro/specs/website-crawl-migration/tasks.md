# Implementation Plan: Website Crawl Migration

## Overview

Миграция Git Datasource плагина с `OnlineDriveDatasource` на `WebsiteCrawlDatasource`. Переиспользуем существующий GitClient и утилиты, создаём новый класс datasource с streaming батчингом.

## Tasks

- [-] 0. Валидация Dify semantics (GATE)
  - [x] 0.1 Минимальные изменения YAML для запуска плагина
    - Изменить provider_type на website_crawl
    - Создать заглушку _get_website_crawl (возвращает 1 тестовый файл)
    - _Requirements: R1.AC1_
  - [-] 0.2 Интеграционный тест Dify semantics
    - Full sync → получить документы
    - Delta sync (только 1 файл) → проверить что остальные документы НЕ стали orphaned
    - Если orphaned — нужно переключиться на snapshot-модель
    - _Requirements: DD1 validation_

- [x] 1. Обновить конфигурационные файлы
  - [x] 1.1 Обновить provider/git_datasource.yaml
    - Изменить `provider_type: online_drive` на `provider_type: website_crawl`
    - Оставить только access_token и ssh_private_key в credentials_schema
    - _Requirements: R1.AC1, R4.AC6_
  - [x] 1.2 Обновить datasources/git_datasource.yaml
    - Добавить parameters секцию с repo_url, branch, subdir, extensions
    - Обновить output_schema для website_crawl (title, content, description, source_url)
    - _Requirements: R1.AC1, R6.AC1, R6.AC2_
  - [x] 1.3 Обновить manifest.yaml
    - Изменить `minimum_dify_version: 1.11.1`
    - _Requirements: R1.AC4_
  - [x] 1.4 Проверить что параметры приходят в datasource_parameters
    - Добавить логирование в _get_website_crawl
    - Убедиться что repo_url, branch, subdir, extensions доступны
    - _Requirements: R4.AC6_

- [x] 2. Создать новый класс GitWebsiteCrawlDatasource
  - [x] 2.1 Создать файл datasources/git_website_crawl.py с базовой структурой
    - Наследование от WebsiteCrawlDatasource
    - Константы BATCH_SIZE=50, MAX_FILE_SIZE=5MB
    - Заглушки для всех методов
    - _Requirements: R1.AC2, R1.AC3_
  - [x] 2.2 Реализовать _get_config_hash()
    - config_hash: `sha256(repo_url:branch:subdir:canonicalized_extensions)[:16]`
    - Канонизация extensions: sorted, lowercase, trimmed, joined with `,`
    - SHA storage key: `git_sha:{config_hash}`
    - Failed paths key: `git_failed:{config_hash}`
    - _Requirements: R3.AC2_
  - [x] 2.3 Реализовать _normalize_path()
    - Конвертация в POSIX формат (/ вместо \)
    - Удаление ./ и ведущего /
    - Отклонение путей с .. как компонентом пути (raise ValueError)
    - НЕ блокировать .. в именах файлов (например, `notes..md` — OK)
    - _Requirements: R2.AC8, R6.AC2_
  - [x] 2.4 Реализовать _make_source_url()
    - Формат: `git:{config_hash}:{normalized_path}` (без вложенных префиксов)
    - _Requirements: R2.AC8, R6.AC2_
  - [x] 2.5 Написать unit test для path normalization
    - Test POSIX conversion
    - Test "./" removal
    - Test ".." rejection (as path component only)
    - Test ".." allowed in filenames (e.g., `notes..md`)
    - Test leading "/" removal
    - _Requirements: R2.AC8, R6.AC2_
  - [x] 2.6 Написать unit test для config_hash
    - Test extensions canonicalization (sort, lowercase, trim)
    - Test deterministic hash generation
    - _Requirements: R3.AC2_

- [x] 3. Реализовать получение списка файлов
  - [x] 3.1 Реализовать _get_file_paths() для full sync
    - Использовать GitClient.list_all_files()
    - Применить фильтры (subdir, extensions)
    - Вернуть (paths, total)
    - _Requirements: R2.AC3, R5.AC1, R5.AC2_
  - [x] 3.2 Реализовать _get_file_paths() для incremental sync
    - Использовать GitClient.get_changed_files()
    - Добавить failed_paths к списку (только transient errors)
    - Вернуть (paths, total)
    - _Requirements: R3.AC3_
  - [x] 3.3 Реализовать загрузку/сохранение SHA
    - Методы _get_last_sha(), _save_sha()
    - _Requirements: R3.AC2, R3.AC6_
  - [x] 3.4 Реализовать загрузку/сохранение failed_paths
    - Методы _get_failed_paths(), _save_failed_paths()
    - Только transient errors (IOError, network)
    - НЕ добавлять: non-UTF-8, binary, >MAX_SIZE, symlink
    - Удалять путь если успешно прочитан или не существует
    - Ограничить размер (max 10000 путей)
    - _Requirements: R3.AC3, R7.AC4_
  - [x] 3.5 Написать unit test для SHA storage round-trip
    - Generate random SHAs
    - Verify storage and retrieval
    - _Requirements: R3.AC2, R3.AC6_

- [x] 4. Реализовать streaming обработку файлов
  - [x] 4.1 Реализовать _should_skip_file()
    - Проверка размера < MAX_FILE_SIZE → skip, НЕ добавлять в failed
    - Проверка не symlink → skip, НЕ добавлять в failed
    - Исключение .git директории → skip, НЕ добавлять в failed
    - _Requirements: R5.AC3, R5.AC4, R5.AC5, R5.AC6_
  - [x] 4.2 Реализовать _is_binary_content()
    - Проверка первых N байт на наличие null bytes
    - Проверка magic bytes для известных бинарных форматов
    - Binary → skip, НЕ добавлять в failed (permanent)
    - _Requirements: R5.AC3_
  - [x] 4.3 Реализовать _read_file_content()
    - Чтение через GitClient.read_file()
    - Декодирование UTF-8
    - При UnicodeDecodeError → skip, НЕ добавлять в failed (permanent)
    - При IOError/другие → skip, ДОБАВИТЬ в failed (transient)
    - _Requirements: R5.AC7, R7.AC4, R7.AC5_
  - [x] 4.4 Реализовать _process_files_streaming()
    - Generator, yield батчи по BATCH_SIZE
    - Создание WebSiteInfoDetail для каждого файла
    - title = normalized path
    - source_url = git:{config_hash}:{path}
    - description = "Git: {repo_url} @ {branch}"
    - Сбор transient failed_paths (только IOError)
    - _Requirements: R2.AC4, R2.AC5, R6.AC2_
  - [ ]* 4.5 Написать property test для file filtering
    - **Property 4: File Filtering Correctness**
    - **Validates: R5.AC3, R5.AC4, R5.AC5, R5.AC6, R5.AC7**

- [-] 5. Реализовать главный метод _get_website_crawl
  - [x] 5.1 Реализовать основной flow
    - Получение credentials из self.runtime.credentials (access_token, ssh_private_key)
    - Получение parameters из datasource_parameters (repo_url, branch, subdir, extensions)
    - Инициализация GitClient
    - Clone/fetch репозитория
    - _Requirements: R2.AC1, R2.AC2, R4.AC1, R4.AC2, R4.AC3_
  - [x] 5.2 Реализовать определение режима sync
    - Проверка наличия last_sha
    - Проверка is_sha_reachable (force push detection)
    - Выбор full или incremental sync
    - _Requirements: R3.AC4, R3.AC5_
  - [x] 5.3 Реализовать streaming yield батчей
    - total = len(paths) после фильтров (attempted paths)
    - completed = количество attempted (включая skipped и failed)
    - Обработка пустого результата (total=0) → yield completed с пустым списком
    - Yield с status="processing" для промежуточных
    - Yield с status="completed" для последнего
    - Использование self.create_crawl_message()
    - _Requirements: R2.AC5, R2.AC6, R2.AC7, R6.AC3, R6.AC4, R6.AC5, R6.AC6_
  - [x] 5.4 Реализовать сохранение состояния после sync
    - Сохранение SHA только при успехе (нет fatal errors)
    - Сохранение/очистка failed_paths
    - _Requirements: R3.AC6_
  - [x] 5.5 Написать unit test для batching
    - Test batch sizes <= BATCH_SIZE
    - Test status values (processing/completed)
    - Test monotonic completed counter
    - _Requirements: R2.AC5, R2.AC6, R2.AC7, R6.AC3, R6.AC4, R6.AC5, R6.AC6_
  - [x] 5.6 Написать unit test для empty result
    - Test with 0 files
    - Verify single completed message with empty list
    - _Requirements: R2.AC7, R6.AC4_

- [x] 6. Checkpoint - Базовая функциональность
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Обновить Provider
  - [x] 7.1 Обновить GitDatasourceProvider._validate_credentials()
    - Валидация URL формата
    - Проверка соответствия auth method и credentials
    - Для local path: проверить что это git repo (открыть HEAD), НЕ ls-remote
    - Для SSH: подготовка ключа + ls-remote
    - Для HTTPS: токен (если есть) + ls-remote
    - Никогда не логировать URL с встроенным токеном
    - _Requirements: R4.AC1, R4.AC2, R4.AC3, R4.AC5, R7.AC5_
  - [x] 7.2 Написать unit tests для валидации credentials
    - Test invalid URL → error message
    - Test SSH URL without key → error message
    - Test HTTPS URL with token → success
    - Test local path → success
    - _Requirements: R7.AC1, R7.AC2, R7.AC3_

- [x] 8. Интеграция и очистка
  - [x] 8.1 Обновить datasources/git_datasource.yaml extra.python.source
    - Указать на новый файл git_website_crawl.py
    - _Requirements: R1.AC3_
  - [x] 8.2 Отключить старый OnlineDriveDatasource код (мягко)
    - НЕ удалять файл datasources/git_datasource.py
    - Переименовать в git_datasource_old.py (backup)
    - Убедиться что main.py не импортирует старый класс
    - _Requirements: R8.AC5_
  - [x] 8.3 Обновить main.py если необходимо
    - Проверить регистрацию плагина
    - _Requirements: R1.AC3_

- [x] 9. Checkpoint - Интеграция (72 tests passing)
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Интеграционные тесты
  - [ ]* 10.1 Написать интеграционный тест full sync flow (SKIPPED - optional)
  - [ ]* 10.2 Написать интеграционный тест incremental sync flow (SKIPPED - optional)

- [x] 11. Документация
  - [x] 11.1 Обновить plugin/README.md
    - Документировать delta-model limitations (удаления не отслеживаются)
    - Документировать что orphaned документы нужно удалять вручную в Dify UI
    - Документировать supported auth methods (HTTPS+token, SSH, local)
    - Документировать file size/type limitations (5MB, text only, no symlinks)
    - _Requirements: R9.AC1, R9.AC2, R9.AC3, R9.AC4_
  - [x] 11.2 Проверить manifest.yaml
    - Убедиться что есть `resource.permission.storage`
    - _Requirements: R9.AC5_

- [x] 12. Final checkpoint
  - 135 tests passing
  - Package built: dist/git_datasource.difypkg (26.9 KB)
  - Ensure all tests pass, ask the user if questions arise.
  - Build package with `make package`

## Notes

- Task 0.2 is a GATE — if Dify uses snapshot semantics, need to switch to snapshot-model
- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements (R{num}.AC{num} format)
- Checkpoints ensure incremental validation
- Existing GitClient and utilities are reused without modification
- Old OnlineDriveDatasource code is kept as backup, not deleted
- failed_paths only for transient errors (IOError, network), NOT for permanent skips (binary, non-UTF-8, too large, symlink)
- config_hash uses canonicalized extensions (sorted, lowercase, trimmed)
- completed/total count attempted paths, not successful documents

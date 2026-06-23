# Graph Report - research-ux-jobs  (2026-06-23)

## Corpus Check
- 106 files · ~77,502 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 850 nodes · 1372 edges · 84 communities (68 shown, 16 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 24 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `938e4dc1`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 83|Community 83]]

## God Nodes (most connected - your core abstractions)
1. `_get_connection()` - 37 edges
2. `BaseParser` - 30 edges
3. `score_vacancy()` - 26 edges
4. `validate_llm_output()` - 17 edges
5. `ScoringResult` - 15 edges
6. `ScoringInput` - 14 edges
7. `_parse_sections()` - 12 edges
8. `send_alert()` - 11 edges
9. `handle_edit_reply()` - 11 edges
10. `_get_or_score()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `AdzunaParser` --uses--> `BaseParser`  [INFERRED]
  parsers/adzuna.py → research-ux-jobs/parsers/base.py
- `ArbeitnowParser` --uses--> `BaseParser`  [INFERRED]
  parsers/arbeitnow.py → research-ux-jobs/parsers/base.py
- `AshbyParser` --uses--> `BaseParser`  [INFERRED]
  parsers/ashby.py → research-ux-jobs/parsers/base.py
- `BebeeParser` --uses--> `BaseParser`  [INFERRED]
  parsers/bebee.py → research-ux-jobs/parsers/base.py
- `DesignprojectParser` --uses--> `BaseParser`  [INFERRED]
  parsers/designproject.py → research-ux-jobs/parsers/base.py

## Import Cycles
- None detected.

## Communities (84 total, 16 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (53): night_probe_cycle(), Ночной авто-харвест ATS-токенов по именам компаний из свежих вакансий., all_companies(), AshbyParser, _extract_salary(), _extract_work_format(), _is_relevant(), Парсер Ashby Job Board API. Публичный, без авторизации. Итерируется по списку ко (+45 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (42): _build_post(), _clean(), _expand_bullets(), _first_sentence(), _fmt_bullets(), _fmt_conditions(), _normalize(), _parse_sections() (+34 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (36): _export(), export_rejected_to_sheets(), _gc(), _ensure_headers(), export_to_sheets(), _get_sheet(), Экспорт вакансий в Google Sheets., _to_row() (+28 more)

### Community 3 - "Community 3"
Cohesion: 0.07
Nodes (39): Еженедельный харвест ATS-токенов из globalwork.ai., weekly_globalwork_cycle(), DesignprojectParser, _enrich_from_detail(), _is_relevant(), _parse_card(), _parse_salary(), Парсер designproject.io/jobs. Публичного API нет — парсим SSR HTML листинга и де (+31 more)

### Community 4 - "Community 4"
Cohesion: 0.11
Nodes (26): map_tier(), _enrich_val(), - Нормализует None/не-dict входные данные в safe dict     - Заполняет отсутствую, _to_bool(), validate_llm_output(), Smoke-тесты модуля scoring. Без сети — LLM замокан. Запуск: poetry run pytest te, Булевы поля (research_maturity, vague_jd) приходят     в разных форматах от LLM, JSON без обязательных полей — все заполняются дефолтами. (+18 more)

### Community 5 - "Community 5"
Cohesion: 0.13
Nodes (25): _apply_cookies(), _authenticate(), _company_from_linkedin(), _fetch_description(), HirifyParser, _is_authed(), _location(), _login_password() (+17 more)

### Community 6 - "Community 6"
Cohesion: 0.13
Nodes (21): _build_report(), check_balances(), daily_report(), _fmt_delta(), money_report(), _openrouter_status(), _railway_status(), Алерты в Telegram-группу мониторинга. (+13 more)

### Community 7 - "Community 7"
Cohesion: 0.08
Nodes (23): Adzuna HTML scraping per vacancy, APScheduler `max_instances=1`, `bot/templates.py` section parser, Concerns, `data/vacancies.db`, Duplicate Code: `handlers.py` vs `moderator.py`, Fragile Areas, `google_credentials.json` in repo root (+15 more)

### Community 8 - "Community 8"
Cohesion: 0.13
Nodes (18): BaseModel, run_eval(), _clean_company(), enable_brand_cache(), _make_inp(), _neutral_brand(), Подключает БД-кэш бренда. get(company)->dict|None, put(company, data)->None., Отсекает hirify-плейсхолдер ('%hirify_global%') и любую утечку 'hirify',     что (+10 more)

### Community 9 - "Community 9"
Cohesion: 0.16
Nodes (17): BebeeParser, _format_location(), _format_one_location(), _is_fresh(), _is_relevant(), _normalize_salary(), _parse_detail(), _parse_listing() (+9 more)

### Community 10 - "Community 10"
Cohesion: 0.18
Nodes (17): _format(), _get_channel_id(), handle_edit_reply(), handle_moderation(), _is_authorized_chat(), Обработчики Telegram-бота. handle_moderation — реагирует на нажатия кнопок в чат, Обрабатывает ответ на запрос редактирования описания., Принимает чат как численный id, так и @username — env может содержать любой форм (+9 more)

### Community 11 - "Community 11"
Cohesion: 0.17
Nodes (10): _get_token(), _headers(), HHParser, Парсер вакансий с hh.ru через публичный API. Документация: https://api.hh.ru/ope, Забирает вакансии по запросу и добавляет новые в result., Один поисковый запрос к API hh.ru., Запрашивает полную карточку вакансии по ID., Преобразует элемент из списка в наш формат. (+2 more)

### Community 12 - "Community 12"
Cohesion: 0.24
Nodes (15): _build_user_message(), call_llm(), call_llm_enrich_only(), call_with_fallback(), _get_client(), _make_system_prompt(), Ленивый module-level OpenAI клиент. Один httpx-pool на процесс., ScoringInput (+7 more)

### Community 13 - "Community 13"
Cohesion: 0.16
Nodes (16): connection, _get_connection(), get_pending_vacancies(), init_db(), insert_vacancy(), mark_posted(), mark_rejected(), Работа с базой данных PostgreSQL. Создаёт таблицу vacancies, умеет вставлять/чит (+8 more)

### Community 14 - "Community 14"
Cohesion: 0.12
Nodes (17): get_brand_cache(), get_vacancy_by_id(), load_ats_tokens(), mark_pending(), _get_connection(), Создаёт подключение к PostgreSQL из DATABASE_URL., Возвращает закэшированный brand_data по компании, если запись свежее TTL.     Пр, Upsert brand_data по компании. Обновляет updated_at (сбрасывает TTL). (+9 more)

### Community 15 - "Community 15"
Cohesion: 0.17
Nodes (9): ABC, BaseParser, Базовый класс для всех парсеров. Каждый новый источник наследуется от BaseParser, Общий интерфейс парсера вакансий., Получает список сырых вакансий из источника.         Каждая вакансия — dict с по, Генерирует хэш для дедупликации.         Если есть external_id — используем sour, Дополняет сырую вакансию служебными полями перед сохранением., Полный цикл: забрать → подготовить. Возвращает список готовых dict'ов. (+1 more)

### Community 16 - "Community 16"
Cohesion: 0.25
Nodes (12): _format(), _get_enrichment(), Отправка вакансий в чат модерации и публикация одобренных в каналы. Использует T, Восстанавливает ScoringResult из строки vacancy_scores., Сигналы зарубежной вакансии: одна строка статусов + цитаты-обоснования., _row_to_scoring_result(), _scoring_footer(), _signals_block() (+4 more)

### Community 17 - "Community 17"
Cohesion: 0.14
Nodes (13): get_latest_vacancy_score(), get_probed_pairs(), insert_vacancy(), mark_posted(), Работа с базой данных PostgreSQL. Создаёт таблицу vacancies, умеет вставлять/чит, Множество уже опробованных (lower(name), ats) — для пропуска повторов., Проверяет наличие вакансии по external_id + source., Вставляет вакансию в БД. Возвращает id или None при дубликате. (+5 more)

### Community 18 - "Community 18"
Cohesion: 0.14
Nodes (13): Common Skill Categories, Find Skills, How to Help Users Find Skills, Step 1: Understand What They Need, Step 2: Check the Leaderboard First, Step 3: Search for Skills, Step 4: Verify Quality Before Recommending, Step 5: Present Options to the User (+5 more)

### Community 19 - "Community 19"
Cohesion: 0.20
Nodes (7): Один поисковый запрос к API hh.ru., Запрашивает полную карточку вакансии по ID., Преобразует элемент из списка в наш формат., Определяет формат работы: Удалёнка / Офис / Гибрид / None.          Приоритет: н, Забирает вакансии по запросу и добавляет новые в result., HHParser, Парсер вакансий с hh.ru через публичный API. Документация: https://api.hh.ru/ope

### Community 20 - "Community 20"
Cohesion: 0.15
Nodes (12): check_post_completeness, Framework, map_tier, Mocking Strategy, pre_filter (blacklist), Running Tests, score_vacancy (integration, LLM mocked), Test Coverage Areas (`test_scoring.py`) (+4 more)

### Community 21 - "Community 21"
Cohesion: 0.15
Nodes (13): get_discovered_counts(), get_discovered_tokens(), get_parser_stats(), get_recent_companies(), mark_scheduled(), Уникальные непустые названия компаний из vacancies за период [start, end)., Токены, добавленные за период [start, end), сгруппированные по ATS., Сколько токенов добавлено за период [start, end) в разрезе способа.     Возвраща (+5 more)

### Community 22 - "Community 22"
Cohesion: 0.18
Nodes (10): Alert Chat, Bot API (python-telegram-bot, async), Bot API (requests, sync), External Job APIs, Google Sheets, Integrations, OpenRouter (LLM), PostgreSQL (+2 more)

### Community 23 - "Community 23"
Cohesion: 0.25
Nodes (10): OpenAI, _build_user_message(), call_brand_scorer(), _extract_json(), _get_client(), Возвращает dict с brand_boost и качественным анализом бренда.     При ошибке воз, Ленивый module-level OpenAI клиент. Один httpx-pool на процесс., Вытаскивает JSON-объект из ответа модели. Толерантен к markdown-fence,     текст (+2 more)

### Community 24 - "Community 24"
Cohesion: 0.29
Nodes (9): Bot, _format(), _get_bot(), _get_channel_id(), post_all(), _post_vacancies(), Отправка вакансий в Telegram-каналы. Использует python-telegram-bot (async)., Публикует все новые вакансии для канала. Возвращает кол-во опубликованных. (+1 more)

### Community 25 - "Community 25"
Cohesion: 0.22
Nodes (9): Публикует вакансии у которых наступило scheduled_at., scheduled_publish_cycle(), publish_due_scheduled(), Публикует все вакансии у которых scheduled_at уже наступил., call(), _mask(), Общий low-level хелпер для Telegram Bot API через requests. Маскирует токен в UR, Заменяет /bot<TOKEN>/ на /bot***/. (+1 more)

### Community 26 - "Community 26"
Cohesion: 0.20
Nodes (9): Async vs Sync Boundary, Code Style, Config Access Pattern, Conventions, Database Pattern, Error Handling, Logging, Parser Pattern (+1 more)

### Community 27 - "Community 27"
Cohesion: 0.20
Nodes (10): init_ats_tables(), init_brand_cache(), init_parser_runs(), init_vacancy_scores(), init_db(), Создаёт таблицу parser_runs — посуточная статистика парсеров и фильтров., Хранилище авто-найденных ATS-токенов и реестр опробованных имён.     На Railway, Кэш брендового скоринга по компании. Hit (если запись свежая по TTL)     пропуск (+2 more)

### Community 28 - "Community 28"
Cohesion: 0.27
Nodes (6): Получает список сырых вакансий из источника.         Каждая вакансия — dict с по, Генерирует хэш для дедупликации по title+company.         URL намеренно исключён, Дополняет сырую вакансию служебными полями перед сохранением., Полный цикл: забрать → подготовить. Возвращает список готовых dict'ов., BaseParser, Общий интерфейс парсера вакансий.

### Community 29 - "Community 29"
Cohesion: 0.31
Nodes (6): _detect_work_format(), _first_line(), _parse_salary(), Парсер вакансий из Telegram-каналов через Telethon.  Требует переменных окружени, TelegramChannelParser, Возвращает первую непустую строку текста.

### Community 30 - "Community 30"
Cohesion: 0.20
Nodes (9): Запуск локально, Стек, VacancyFinder — UX/CX Research Jobs Bot, Источники, Как это работает, Модерация, Переменные окружения, Скоринг (+1 more)

### Community 31 - "Community 31"
Cohesion: 0.31
Nodes (7): $(), initChat(), initFlow(), positionTooltip(), showTooltip(), updateNavDots(), updateProgress()

### Community 32 - "Community 32"
Cohesion: 0.22
Nodes (8): check_post_completeness(), pre_filter(), Проверяет текст вакансии на blacklist-паттерны.     text — конкатенация title +, Считает насколько хорошо существующий шаблон сможет собрать пост.     Использует, test_completeness_full_vacancy(), test_completeness_no_location_no_salary(), test_completeness_sparse_vacancy(), test_pre_filter_blacklist()

### Community 33 - "Community 33"
Cohesion: 0.25
Nodes (5): BaseParser, # TODO: реализовать на этапе 2, ArbeitnowParser, Парсер Arbeitnow.com — будет реализован на этапе 2. API: https://www.arbeitnow.c, _DummyParser

### Community 34 - "Community 34"
Cohesion: 0.32
Nodes (7): Красиво форматирует зарплатную вилку., Шаблон поста для РФ-канала (русский язык)., Шаблон поста для глобального канала (английский)., format_global(), format_ru(), _format_salary(), Шаблоны постов для Telegram-каналов. Формат: HTML (Telegram parse_mode="HTML").

### Community 35 - "Community 35"
Cohesion: 0.25
Nodes (7): Architecture, Concurrency Model, Data Flow, Entry Points, Key Abstractions, Layers, Pattern

### Community 36 - "Community 36"
Cohesion: 0.25
Nodes (7): build, builder, deploy, restartPolicyMaxRetries, restartPolicyType, startCommand, $schema

### Community 37 - "Community 37"
Cohesion: 0.25
Nodes (7): Запуск локально, Стек, Research UX Jobs — Парсер вакансий, Переменные окружения (.env), Структура, Что делает, Что планируется

### Community 38 - "Community 38"
Cohesion: 0.29
Nodes (7): _balance_html_tags(), Урезает text+footer под лимит Telegram (UTF-16 units). Сохраняет ссылку 'Откликн, Длина в UTF-16 code units — так Telegram считает лимит 4096., Усекает строку до max_units UTF-16 code units., _tg_len(), _tg_truncate(), _truncate_for_telegram()

### Community 39 - "Community 39"
Cohesion: 0.29
Nodes (6): Configuration, Core Frameworks & Libraries, Deployment, Dev Dependencies, Language & Runtime, Stack

### Community 40 - "Community 40"
Cohesion: 0.47
Nodes (3): _is_relevant(), ArbeitnowParser, Парсер Arbeitnow.com. API: https://www.arbeitnow.com/api/job-board-api Публичный

### Community 41 - "Community 41"
Cohesion: 0.53
Nodes (5): _ensure_headers(), export_to_sheets(), _get_sheet(), Экспорт вакансий в Google Sheets., _to_row()

### Community 42 - "Community 42"
Cohesion: 0.47
Nodes (5): _access_points(), _brand_points(), combine_score(), Доступ — максимум, не сумма. Виза/релок и ремоут взаимозаменяемы.     Возвращает, Собирает итоговый score 0-10 и breakdown.      Логика:     - Доступ берётся макс

### Community 43 - "Community 43"
Cohesion: 0.40
Nodes (3): Конфигурация проекта. Читает переменные окружения из .env и предоставляет их как, validate(), Проверяет, что все обязательные настройки заполнены.     Возвращает список ошибо

### Community 44 - "Community 44"
Cohesion: 0.40
Nodes (4): Directory Layout, Key Locations, Naming Conventions, Structure

### Community 45 - "Community 45"
Cohesion: 0.40
Nodes (3): Полная выгрузка вакансий за 7 дней со ВСЕХ страниц. Сохраняет в CSV: и прошедшие, Забирает ВСЕ страницы по одному запросу., search_all_pages()

### Community 46 - "Community 46"
Cohesion: 0.50
Nodes (4): _is_allowed_language(), apply_filters(), Фильтрация вакансий.  Подход: БЕЛЫЙ СПИСОК — вакансия проходит, только если в за, True = вакансия прошла фильтр.

### Community 47 - "Community 47"
Cohesion: 0.50
Nodes (3): _is_relevant(), HimalayasParser, Парсер RemoteOK.com (замена Himalayas — у него нет публичного API). API: https:/

### Community 48 - "Community 48"
Cohesion: 0.40
Nodes (3): # TODO: реализовать на этапе 2, HimalayasParser, Парсер Himalayas.app — будет реализован на этапе 2. API: https://himalayas.app/a

### Community 49 - "Community 49"
Cohesion: 0.50
Nodes (3): _is_relevant(), Парсер Remotive.com. API: https://remotive.com/api/remote-jobs Публичный, без кл, RemotiveParser

### Community 50 - "Community 50"
Cohesion: 0.40
Nodes (3): # TODO: реализовать на этапе 2, Парсер Remotive.com — будет реализован на этапе 2. API: https://remotive.com/api, RemotiveParser

### Community 51 - "Community 51"
Cohesion: 0.40
Nodes (3): # TODO: реализовать на этапе 3 (Telethon), Парсер Telegram-каналов через Telethon — будет реализован на этапе 3. Требует от, TelegramChannelParser

### Community 52 - "Community 52"
Cohesion: 0.50
Nodes (3): print_post(), Скоринг реальных вакансий из БД + превью поста до и после AI. Запуск: poetry run, strip_html()

### Community 53 - "Community 53"
Cohesion: 0.40
Nodes (3): Полная выгрузка вакансий за 7 дней со ВСЕХ страниц. Сохраняет в CSV: и прошедшие, Забирает ВСЕ страницы по одному запросу., search_all_pages()

### Community 54 - "Community 54"
Cohesion: 0.40
Nodes (5): _mock_llm_response(), Запускает score_vacancy с замоканным LLM возвращающим content., score_vacancy не падает при любом плохом ответе LLM — возвращает None или Scorin, _score_vacancy_with_mock_content(), test_score_vacancy_bad_llm_response_no_crash()

### Community 55 - "Community 55"
Cohesion: 0.50
Nodes (3): is_duplicate(), Дедупликация вакансий. Проверяет по хэшу, а также по external_id+source (для пер, Возвращает True, если вакансия уже есть в базе.

### Community 56 - "Community 56"
Cohesion: 0.50
Nodes (3): Возвращает True, если вакансия уже есть в базе., is_duplicate(), Дедупликация вакансий. Проверяет хэш (title+company+url) по базе. Если уже есть

### Community 57 - "Community 57"
Cohesion: 0.50
Nodes (3): True = вакансия прошла фильтр., apply_filters(), Фильтрация вакансий.  Подход: БЕЛЫЙ СПИСОК — вакансия проходит, только если в за

### Community 58 - "Community 58"
Cohesion: 0.50
Nodes (3): Конфигурация проекта. Читает переменные окружения из .env и предоставляет их как, validate(), Проверяет, что все обязательные настройки заполнены.     Возвращает список ошибо

### Community 59 - "Community 59"
Cohesion: 0.67
Nodes (3): Планировщик: парсинг, фильтрация, БД, Google Sheets. Постинг в Telegram пока отк, run_cycle(), start_scheduler()

## Knowledge Gaps
- **90 isolated node(s):** `vacancy-parser`, `$schema`, `builder`, `startCommand`, `restartPolicyType` (+85 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `score_vacancy()` connect `Community 8` to `Community 32`, `Community 2`, `Community 4`, `Community 10`, `Community 42`, `Community 12`, `Community 16`, `Community 52`, `Community 23`?**
  _High betweenness centrality (0.102) - this node is a cross-community bridge._
- **Why does `BaseParser` connect `Community 28` to `Community 0`, `Community 33`, `Community 2`, `Community 3`, `Community 5`, `Community 40`, `Community 9`, `Community 11`, `Community 47`, `Community 15`, `Community 49`, `Community 48`, `Community 19`, `Community 50`, `Community 51`, `Community 29`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Why does `_parse_sections()` connect `Community 1` to `Community 32`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Are the 23 inferred relationships involving `BaseParser` (e.g. with `AdzunaParser` and `ArbeitnowParser`) actually correct?**
  _`BaseParser` has 23 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Алерты в Telegram-группу мониторинга.`, `Возвращает {usage, limit, remaining} или None. remaining=None если лимит не зада`, `Возвращает {remaining} в USD или None.` to the rest of the system?**
  _321 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.05182443151771549 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.05844155844155844 - nodes in this community are weakly interconnected._
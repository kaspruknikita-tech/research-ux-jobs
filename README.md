# Research UX Jobs — Парсер вакансий

Автоматический парсер вакансий для исследователей (UX, CX, Market Research).
Собирает вакансии с hh.ru, фильтрует, дедуплицирует и выгружает в Google Sheets.

## Что делает

- Каждые 30 минут парсит hh.ru по 29 поисковым запросам
- Фильтрует по белому списку слов (researcher, ux, cx, insight и др.)
- Отсеивает мусор по чёрному списку
- Дедуплицирует по хэшу (title + company + url)
- Сохраняет в SQLite
- Выгружает новые вакансии в Google Sheets
- Работает на Railway (сервер, 24/7)

## Стек

- Python 3.12, Poetry
- SQLite — хранение вакансий
- APScheduler — планировщик
- gspread — экспорт в Google Sheets
- Railway — хостинг

## Структура
research-ux-jobs/
├── parsers/
│   └── hh.py           # Парсер hh.ru (двухшаговый: список + карточка)
├── filters/
│   ├── stopwords.py    # Белый и чёрный список слов
│   └── dedup.py        # Дедупликация по хэшу
├── exporters/
│   └── sheets.py       # Экспорт в Google Sheets
├── bot/
│   ├── poster.py       # Постинг в Telegram (не подключён)
│   └── templates.py    # Шаблоны постов
├── data/
│   └── vacancies.db    # SQLite база
├── database.py         # Работа с БД
├── scheduler.py        # Главный цикл
├── config.py           # Конфигурация из .env
└── Procfile            # Для Railway

## Запуск локально
```bash
poetry install
poetry run python scheduler.py
```

## Переменные окружения (.env)
GOOGLE_SHEET_ID=id_таблицы
GOOGLE_CREDENTIALS_JSON=содержимое_json_ключа  # на Railway
HH_USER_AGENT=VacancyParser/0.1 (email)
PARSE_INTERVAL_MINUTES=30
DATABASE_PATH=data/vacancies.db
LOG_LEVEL=INFO

## Что планируется

- Постинг в Telegram-каналы (РФ и глобальный)
- Парсеры англоязычных сайтов (Remotive, Himalayas, Arbeitnow)
- Ручная модерация через Google Sheets

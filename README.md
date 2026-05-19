# VacancyFinder — UX/CX Research Jobs Bot

Телеграм-бот, который автоматически собирает вакансии для UX и CX-исследователей, скорит их через LLM и отправляет на модерацию перед публикацией в каналы.

**Зачем:** вакансий для исследователей много, но они разбросаны по десяткам сайтов и большинство — мусор (нет визы, только офис, нерелевантная роль). Бот фильтрует, оценивает и оставляет только стоящее.

---

## Как это работает

```
Парсеры (11 источников)
    ↓
Дедупликация + стоп-слова
    ↓
LLM-скоринг (0–10) + тир (S/A/B/C)
    ↓
Чат модерации (RU / Global)
    ↓  [✅ / ❌ / ⏰ / ✏️]
Telegram-каналы
```

### Источники

| Источник | Канал |
|----------|-------|
| hh.ru | RU |
| Adzuna | Global |
| Himalayas | Global |
| Remotive | Global |
| WeWorkRemotely | Global |
| WorkingNomads | Global |
| Arbeitnow | Global |
| Greenhouse | Global |
| WantApply | Global |
| Hirify | Global |
| Telegram-каналы | RU/Global |

### Скоринг

LLM (OpenRouter: Gemini Flash Lite → Mistral Small → Llama 3.3) извлекает из описания:

- Визовая поддержка / релокация / формат работы
- Уровень (junior/mid/senior/lead)
- Зарплата

И выдаёт **числовой score 0–10** на основе сигналов (+4 за визу, +3 за global remote, -4 за офис и т.д.).

Score + наличие визы/релокации → **тир**:

| Тир | Смысл |
|-----|-------|
| S ⭐ | Виза + релокация + score ≥ 8 |
| A 🔵 | Виза или релокация, хороший score |
| B 🟡 | Без визы/релокации, но норм |
| C 🔴 | Офис / заблокировано / мусор |

### Модерация

Каждая вакансия приходит в закрытый чат с кнопками:

- **✅ Опубликовать** — сразу в канал
- **❌ Отклонить** — в архив
- **✏️ Описание** — отредактировать текст прямо в чате
- **⏰ +30м / +1ч / ... / +24ч** — запланировать публикацию

---

## Стек

- **Python 3.12**, Poetry
- **PostgreSQL** (Railway) — хранение вакансий и скоров
- **python-telegram-bot** — бот модерации
- **APScheduler** — цикл парсинга каждые 2 часа
- **OpenRouter** — LLM-скоринг (multi-model fallback)
- **Playwright** — скрапинг Hirify
- **gspread** — экспорт в Google Sheets
- **Railway** — хостинг

---

## Структура проекта

```
├── parsers/          # 11 парсеров (hh, adzuna, hirify, ...)
├── filters/          # Дедупликация, стоп-слова
├── scoring/          # LLM-скоринг, тир-маппер, pre-filter
│   ├── llm_scorer.py
│   ├── tier_mapper.py
│   └── pre_filter.py
├── bot/
│   ├── moderator.py  # Отправка в чат модерации
│   ├── handlers.py   # Обработка кнопок
│   └── templates.py  # Форматирование постов (RU / EN)
├── exporters/        # Google Sheets
├── database.py       # PostgreSQL
├── scheduler.py      # Цикл парсинга
├── bot_app.py        # Точка входа (планировщик + бот)
└── config.py         # Переменные окружения
```

---

## Запуск локально

```bash
poetry install
playwright install chromium

cp .env.example .env
# заполни .env

poetry run python bot_app.py
```

## Переменные окружения

```env
# Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHANNEL_RU=
TELEGRAM_CHANNEL_GLOBAL=
TELEGRAM_MODERATION_CHAT_RU=
TELEGRAM_MODERATION_CHAT_GLOBAL=
TELEGRAM_ALERT_CHAT=

# hh.ru OAuth
HH_CLIENT_ID=
HH_CLIENT_SECRET=
HH_USER_AGENT=VacancyFinder/1.0 (your@email.com)

# Adzuna
ADZUNA_APP_ID=
ADZUNA_APP_KEY=

# Telethon (парсер Telegram-каналов)
TG_API_ID=
TG_API_HASH=
TG_SESSION_STRING=
TG_SOURCE_CHANNELS=@channel1,@channel2

# LLM
OPENROUTER_API_KEY=

# БД
DATABASE_URL=postgresql://...

# Google Sheets
GOOGLE_SHEET_ID=
```

"""
Работа с базой данных PostgreSQL.
Создаёт таблицу vacancies, умеет вставлять/читать/обновлять записи.
"""

import json
import logging
import os
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)


def _get_connection() -> psycopg2.extensions.connection:
    """Создаёт подключение к PostgreSQL из DATABASE_URL."""
    url = os.environ["DATABASE_URL"]
    # Railway иногда отдаёт postgres://, psycopg2 требует postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(url)


def init_db() -> None:
    """Создаёт таблицы, если их нет."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS vacancies (
                    id              SERIAL PRIMARY KEY,
                    external_id     TEXT,
                    source          TEXT NOT NULL,
                    title           TEXT NOT NULL,
                    company         TEXT,
                    salary_min      INTEGER,
                    salary_max      INTEGER,
                    currency        TEXT,
                    location        TEXT,
                    work_format     TEXT,
                    url             TEXT,
                    description     TEXT,
                    snippet         TEXT,
                    hash            TEXT NOT NULL UNIQUE,
                    status          TEXT NOT NULL DEFAULT 'new',
                    channel         TEXT NOT NULL,
                    parsed_at       TEXT NOT NULL,
                    posted_at       TEXT,
                    scheduled_at    TIMESTAMP WITH TIME ZONE
                )
            """)
            cur.execute("""
                ALTER TABLE vacancies
                ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMP WITH TIME ZONE
            """)
            cur.execute("""
                ALTER TABLE vacancies
                ADD COLUMN IF NOT EXISTS moderation_message_id INTEGER
            """)
        conn.commit()
        logger.info("База данных инициализирована (PostgreSQL)")
    finally:
        conn.close()
    init_vacancy_scores()


def init_vacancy_scores() -> None:
    """Создаёт таблицу vacancy_scores, если её нет."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS vacancy_scores (
                    id               SERIAL PRIMARY KEY,
                    vacancy_id       INTEGER NOT NULL REFERENCES vacancies(id),
                    scored_at        TIMESTAMP DEFAULT NOW(),
                    prompt_version   TEXT NOT NULL,
                    tier             VARCHAR(1) NOT NULL,
                    action           TEXT NOT NULL,
                    score            INTEGER NOT NULL,
                    score_breakdown  JSONB,
                    visa_sponsorship TEXT,
                    relocation_support TEXT,
                    remote_policy    TEXT,
                    salary_min       INTEGER,
                    salary_max       INTEGER,
                    salary_currency  TEXT,
                    experience_level TEXT,
                    verbatim_evidence JSONB,
                    pre_filter_blocked BOOLEAN DEFAULT FALSE,
                    reason           TEXT
                )
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS vacancy_scores_vacancy_id_idx ON vacancy_scores(vacancy_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS vacancy_scores_tier_idx ON vacancy_scores(tier)")
            cur.execute("CREATE INDEX IF NOT EXISTS vacancy_scores_scored_at_idx ON vacancy_scores(scored_at)")
            cur.execute("ALTER TABLE vacancy_scores ADD COLUMN IF NOT EXISTS brand_data JSONB")
        conn.commit()
    finally:
        conn.close()


def save_vacancy_score(result, prompt_version: str) -> None:
    """Сохраняет ScoringResult в vacancy_scores. Каждый вызов — новая строка."""
    conn = _get_connection()
    try:
        enrichment_json = (
            json.dumps(result.post_enrichment.model_dump()) if result.post_enrichment else None
        )
        base_args = (
            result.vacancy_id, prompt_version,
            result.tier, result.action, result.score,
            json.dumps(result.score_breakdown),
            result.visa_sponsorship, result.relocation_support, result.remote_policy,
            result.salary_min, result.salary_max, result.salary_currency,
            result.experience_level,
            json.dumps(result.verbatim_evidence),
            result.pre_filter_blocked, result.reason,
            result.model_used or None, result.latency_ms or None,
        )
        brand_json = json.dumps(result.brand_data) if result.brand_data else None
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO vacancy_scores
                        (vacancy_id, prompt_version, tier, action, score, score_breakdown,
                         visa_sponsorship, relocation_support, remote_policy,
                         salary_min, salary_max, salary_currency, experience_level,
                         verbatim_evidence, pre_filter_blocked, reason,
                         model_used, latency_ms, post_enrichment, brand_data)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    base_args + (enrichment_json, brand_json),
                )
            conn.commit()
        except psycopg2.errors.UndefinedColumn:
            # Колонки post_enrichment/brand_data ещё не добавлены — fallback без них.
            # Другие ошибки (сериализация, FK, сеть) пробрасываем, чтобы не терять данные молча.
            conn.rollback()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO vacancy_scores
                        (vacancy_id, prompt_version, tier, action, score, score_breakdown,
                         visa_sponsorship, relocation_support, remote_policy,
                         salary_min, salary_max, salary_currency, experience_level,
                         verbatim_evidence, pre_filter_blocked, reason,
                         model_used, latency_ms)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    base_args,
                )
            conn.commit()
            logger.warning("save_vacancy_score: brand_data/post_enrichment не сохранены — примените миграции 003-004")
    finally:
        conn.close()


def get_setting(key: str) -> str | None:
    """Читает значение из таблицы settings."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM settings WHERE key = %s", (key,))
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()


def set_setting(key: str, value: str) -> None:
    """Сохраняет или обновляет значение в таблице settings."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO settings (key, value) VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                """,
                (key, value),
            )
        conn.commit()
    finally:
        conn.close()


def vacancy_exists(hash_value: str) -> bool:
    """Проверяет, есть ли вакансия с таким хэшем в базе."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM vacancies WHERE hash = %s", (hash_value,))
            return cur.fetchone() is not None
    finally:
        conn.close()


def vacancy_exists_by_external(external_id: str, source: str) -> bool:
    """Проверяет наличие вакансии по external_id + source."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM vacancies WHERE external_id = %s AND source = %s",
                (external_id, source),
            )
            return cur.fetchone() is not None
    finally:
        conn.close()


def vacancy_exists_by_title_company(title: str, company: str) -> bool:
    """Проверяет, есть ли вакансия с таким же заголовком и компанией."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM vacancies WHERE lower(title) = lower(%s) AND lower(company) = lower(%s) LIMIT 1",
                (title, company),
            )
            return cur.fetchone() is not None
    finally:
        conn.close()


def insert_vacancy(vacancy: dict) -> int | None:
    """Вставляет вакансию в БД. Возвращает id или None при дубликате."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO vacancies
                    (external_id, source, title, company,
                     salary_min, salary_max, currency,
                     location, work_format, url, description, snippet,
                     hash, status, channel, parsed_at)
                VALUES
                    (%(external_id)s, %(source)s, %(title)s, %(company)s,
                     %(salary_min)s, %(salary_max)s, %(currency)s,
                     %(location)s, %(work_format)s, %(url)s, %(description)s, %(snippet)s,
                     %(hash)s, %(status)s, %(channel)s, %(parsed_at)s)
                RETURNING id
                """,
                vacancy,
            )
            new_id = cur.fetchone()[0]
        conn.commit()
        logger.debug("Вакансия сохранена: id=%s, %s", new_id, vacancy.get("title"))
        return new_id
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        logger.debug("Дубликат, пропускаем: %s", vacancy.get("title"))
        return None
    finally:
        conn.close()


def get_pending_vacancies(channel: str) -> list[dict]:
    """Возвращает вакансии со статусом 'new' для указанного канала."""
    conn = _get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM vacancies WHERE status = 'new' AND channel = %s ORDER BY parsed_at",
                (channel,),
            )
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_new_vacancies() -> list[dict]:
    """Возвращает все вакансии со статусом 'new' (ещё не отправлены на модерацию)."""
    conn = _get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM vacancies WHERE status = 'new' ORDER BY parsed_at",
            )
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def get_vacancy_by_id(vacancy_id: int) -> dict | None:
    """Возвращает вакансию по ID."""
    conn = _get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM vacancies WHERE id = %s", (vacancy_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def mark_pending(vacancy_id: int) -> None:
    """Ставит статус 'pending' — вакансия отправлена в чат модерации."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE vacancies SET status = 'pending' WHERE id = %s",
                (vacancy_id,),
            )
        conn.commit()
    finally:
        conn.close()


def mark_posted(vacancy_id: int) -> None:
    """Ставит статус 'posted' и фиксирует время публикации."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            now = datetime.now(timezone.utc).isoformat()
            cur.execute(
                "UPDATE vacancies SET status = 'posted', posted_at = %s WHERE id = %s",
                (now, vacancy_id),
            )
        conn.commit()
    finally:
        conn.close()


def get_latest_vacancy_score(vacancy_id: int) -> dict | None:
    """Возвращает последний скор вакансии из vacancy_scores или None."""
    conn = _get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM vacancy_scores WHERE vacancy_id = %s ORDER BY scored_at DESC LIMIT 1",
                (vacancy_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def save_moderation_message_id(vacancy_id: int, message_id: int) -> None:
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE vacancies SET moderation_message_id = %s WHERE id = %s",
                (message_id, vacancy_id),
            )
        conn.commit()
    finally:
        conn.close()


def update_vacancy_description(vacancy_id: int, description: str) -> None:
    """Обновляет описание вакансии."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE vacancies SET description = %s WHERE id = %s",
                (description, vacancy_id),
            )
        conn.commit()
    finally:
        conn.close()


def mark_scheduled(vacancy_id: int, publish_at: datetime) -> None:
    """Планирует публикацию вакансии на указанное время."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE vacancies SET status = 'scheduled', scheduled_at = %s WHERE id = %s",
                (publish_at, vacancy_id),
            )
        conn.commit()
    finally:
        conn.close()


def get_due_scheduled() -> list[dict]:
    """Возвращает запланированные вакансии, у которых scheduled_at <= now."""
    conn = _get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT * FROM vacancies
                WHERE status = 'scheduled' AND scheduled_at <= NOW()
                ORDER BY scheduled_at
                """,
            )
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def mark_rejected(vacancy_id: int) -> None:
    """Ставит статус 'rejected' (не прошла фильтр)."""
    conn = _get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE vacancies SET status = 'rejected' WHERE id = %s",
                (vacancy_id,),
            )
        conn.commit()
    finally:
        conn.close()

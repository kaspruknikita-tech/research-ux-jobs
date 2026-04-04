"""
Работа с базой данных SQLite.
Создаёт таблицу vacancies, умеет вставлять/читать/обновлять записи.
"""

import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path

import config

logger = logging.getLogger(__name__)


def _get_connection() -> sqlite3.Connection:
    """Создаёт подключение к БД. Если папки нет — создаёт."""
    db_path: Path = config.DATABASE_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row  # чтобы обращаться к колонкам по имени
    return conn


def init_db() -> None:
    """Создаёт таблицу vacancies, если её нет."""
    conn = _get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vacancies (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
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
            hash            TEXT NOT NULL UNIQUE,
            status          TEXT NOT NULL DEFAULT 'new',
            channel         TEXT NOT NULL,
            parsed_at       TEXT NOT NULL,
            posted_at       TEXT
        )
    """)
    conn.commit()
    conn.close()
    logger.info("База данных инициализирована: %s", config.DATABASE_PATH)


def vacancy_exists(hash_value: str) -> bool:
    """Проверяет, есть ли вакансия с таким хэшем в базе."""
    conn = _get_connection()
    row = conn.execute(
        "SELECT 1 FROM vacancies WHERE hash = ?", (hash_value,)
    ).fetchone()
    conn.close()
    return row is not None


def insert_vacancy(vacancy: dict) -> int | None:
    """Вставляет вакансию в БД. Возвращает id или None при дубликате."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO vacancies
                (external_id, source, title, company,
                 salary_min, salary_max, currency,
                 location, work_format, url, description,
                 hash, status, channel, parsed_at)
            VALUES
                (:external_id, :source, :title, :company,
                 :salary_min, :salary_max, :currency,
                 :location, :work_format, :url, :description,
                 :hash, :status, :channel, :parsed_at)
            """,
            vacancy,
        )
        conn.commit()
        new_id = cursor.lastrowid
        logger.debug("Вакансия сохранена: id=%s, %s", new_id, vacancy.get("title"))
        return new_id
    except sqlite3.IntegrityError:
        logger.debug("Дубликат, пропускаем: %s", vacancy.get("title"))
        return None
    finally:
        conn.close()


def get_pending_vacancies(channel: str) -> list[dict]:
    """Возвращает вакансии со статусом 'new' для указанного канала."""
    conn = _get_connection()
    rows = conn.execute(
        "SELECT * FROM vacancies WHERE status = 'new' AND channel = ? ORDER BY parsed_at",
        (channel,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def mark_posted(vacancy_id: int) -> None:
    """Ставит статус 'posted' и фиксирует время публикации."""
    conn = _get_connection()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE vacancies SET status = 'posted', posted_at = ? WHERE id = ?",
        (now, vacancy_id),
    )
    conn.commit()
    conn.close()


def mark_rejected(vacancy_id: int) -> None:
    """Ставит статус 'rejected' (не прошла фильтр)."""
    conn = _get_connection()
    conn.execute(
        "UPDATE vacancies SET status = 'rejected' WHERE id = ?",
        (vacancy_id,),
    )
    conn.commit()
    conn.close()

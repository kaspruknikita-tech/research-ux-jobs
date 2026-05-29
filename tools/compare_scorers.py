"""
Shadow-сравнение моделей-скореров.

Берёт N последних вакансий из БД и прогоняет каждую через все модели
из MODELS параллельно. Выводит таблицу: vacancy | score по каждой модели
+ медиану и расхождение. Помогает увидеть кто строже, кто щедрее,
кто промахивается.

Usage:
    python -m tools.compare_scorers --limit 10
    python -m tools.compare_scorers --vacancy-ids 19100,19124,19128
    python -m tools.compare_scorers --limit 20 --csv out.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

import database
from scoring.llm_scorer import MODELS, _make_system_prompt, _build_user_message
from scoring.models import ScoringInput


def _score_one(model: dict, messages: list[dict], vacancy_id: int) -> dict:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )
    try:
        resp = client.chat.completions.create(
            model=model["id"],
            messages=messages,
            max_tokens=model["max_tokens"],
            temperature=0,
            response_format={"type": "json_object"},
            timeout=30.0,
        )
        raw = resp.choices[0].message.content
        parsed = json.loads(raw)
        return {
            "model": model["id"],
            "ok": True,
            "score": parsed.get("score"),
            "remote_policy": parsed.get("remote_policy"),
            "visa": parsed.get("visa_sponsorship"),
            "reason": (parsed.get("reason") or "")[:120],
        }
    except Exception as e:
        return {"model": model["id"], "ok": False, "error": str(e)[:120]}


def _fetch_vacancies(limit: int | None, ids: list[int] | None) -> list[dict]:
    conn = database._get_connection()
    try:
        with conn.cursor() as cur:
            if ids:
                cur.execute(
                    "SELECT id, title, company, description, location, work_format, "
                    "salary_min, salary_max, currency, channel "
                    "FROM vacancies WHERE id = ANY(%s)",
                    (ids,),
                )
            else:
                cur.execute(
                    "SELECT id, title, company, description, location, work_format, "
                    "salary_min, salary_max, currency, channel "
                    "FROM vacancies WHERE description IS NOT NULL "
                    "ORDER BY id DESC LIMIT %s",
                    (limit,),
                )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()


def _make_inp(v: dict) -> ScoringInput:
    return ScoringInput(
        vacancy_id=v["id"],
        title=v.get("title", ""),
        company=v.get("company", "") or "",
        description=v.get("description", "") or "",
        location=v.get("location"),
        work_format=v.get("work_format"),
        salary_min=v.get("salary_min"),
        salary_max=v.get("salary_max"),
        currency=v.get("currency"),
        is_ru=v.get("channel") == "ru",
    )


def compare_one(v: dict) -> dict:
    inp = _make_inp(v)
    messages = [
        {"role": "system", "content": _make_system_prompt(enrich=False, is_ru=inp.is_ru)},
        {"role": "user", "content": _build_user_message(inp)},
    ]
    results = {}
    with ThreadPoolExecutor(max_workers=len(MODELS)) as pool:
        futures = {pool.submit(_score_one, m, messages, v["id"]): m["id"] for m in MODELS}
        for fut in as_completed(futures):
            r = fut.result()
            results[r["model"]] = r
    return {"vacancy_id": v["id"], "title": v.get("title", ""), "results": results}


def _print_table(rows: list[dict]) -> None:
    model_ids = [m["id"] for m in MODELS]
    print()
    header = f"{'id':>6}  {'title':40}  " + "  ".join(f"{m.split('/')[-1][:18]:>18}" for m in model_ids)
    print(header)
    print("-" * len(header))
    for row in rows:
        title = (row["title"] or "")[:38]
        cells = []
        for m in model_ids:
            r = row["results"].get(m, {})
            if not r.get("ok"):
                cells.append(f"{'FAIL':>18}")
            else:
                cells.append(f"{str(r.get('score')):>18}")
        print(f"{row['vacancy_id']:>6}  {title:40}  " + "  ".join(cells))

    print()
    print("=== Сводка по моделям ===")
    for m in model_ids:
        scores = [row["results"][m].get("score") for row in rows
                  if row["results"].get(m, {}).get("ok") and row["results"][m].get("score") is not None]
        fails = sum(1 for row in rows if not row["results"].get(m, {}).get("ok"))
        if scores:
            avg = sum(scores) / len(scores)
            mn, mx = min(scores), max(scores)
            print(f"  {m:50}  n={len(scores)}  avg={avg:.1f}  range=[{mn},{mx}]  fails={fails}")
        else:
            print(f"  {m:50}  все упали (fails={fails})")


def _write_csv(rows: list[dict], path: str) -> None:
    model_ids = [m["id"] for m in MODELS]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        header = ["vacancy_id", "title"]
        for m in model_ids:
            header += [f"{m}__score", f"{m}__remote", f"{m}__visa", f"{m}__reason", f"{m}__error"]
        w.writerow(header)
        for row in rows:
            line = [row["vacancy_id"], row["title"]]
            for m in model_ids:
                r = row["results"].get(m, {})
                if r.get("ok"):
                    line += [r.get("score"), r.get("remote_policy"), r.get("visa"), r.get("reason"), ""]
                else:
                    line += ["", "", "", "", r.get("error", "")]
            w.writerow(line)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=10, help="сколько последних вакансий")
    ap.add_argument("--vacancy-ids", type=str, default="", help="конкретные id через запятую")
    ap.add_argument("--csv", type=str, default="", help="путь для CSV-выгрузки")
    args = ap.parse_args()

    ids = [int(x) for x in args.vacancy_ids.split(",") if x.strip()] if args.vacancy_ids else None
    vacancies = _fetch_vacancies(args.limit if not ids else None, ids)
    if not vacancies:
        print("Нет вакансий по фильтру", file=sys.stderr)
        sys.exit(1)

    print(f"Сравниваю {len(vacancies)} вакансий × {len(MODELS)} моделей...")
    rows = []
    for i, v in enumerate(vacancies, 1):
        print(f"  [{i}/{len(vacancies)}] id={v['id']} {(v.get('title') or '')[:50]}")
        rows.append(compare_one(v))

    _print_table(rows)
    if args.csv:
        _write_csv(rows, args.csv)
        print(f"\nCSV: {args.csv}")


if __name__ == "__main__":
    main()

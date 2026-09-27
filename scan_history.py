"""Local scan history. Raw uploads and API credentials are never stored."""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any


def database_path() -> Path:
    # Render Free has an ephemeral filesystem; local history is retained only as
    # long as that instance's filesystem survives. Set METERTRUTH_DB_PATH to opt in.
    return Path(os.getenv("METERTRUTH_DB_PATH", "/tmp/metertruth_scans.sqlite3"))


def _connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("""CREATE TABLE IF NOT EXISTS scans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        source_name TEXT NOT NULL,
        metered_name TEXT NOT NULL,
        findings INTEGER NOT NULL,
        underbilling REAL NOT NULL,
        overbilling REAL NOT NULL,
        report_json TEXT NOT NULL
    )""")
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return db


def save(report: dict[str, Any], source_name: str, metered_name: str) -> int:
    # Only sanitized filenames, the computed report and summary are retained.
    source_name = Path(source_name or "source").name[:180]
    metered_name = Path(metered_name or "metered").name[:180]
    with _connect() as db:
        cur = db.execute(
            "INSERT INTO scans(created_at,source_name,metered_name,findings,underbilling,overbilling,report_json) VALUES(?,?,?,?,?,?,?)",
            (report["created_at"], source_name, metered_name,
             report["summary"]["findings"], report["summary"]["potential_underbilling_eur"],
             report["summary"]["potential_overbilling_eur"], json.dumps(report, ensure_ascii=False)),
        )
        return int(cur.lastrowid)


def list_scans(limit: int = 50) -> list[dict[str, Any]]:
    with _connect() as db:
        return [dict(row) for row in db.execute(
            "SELECT id,created_at,source_name,metered_name,findings,underbilling,overbilling FROM scans ORDER BY id DESC LIMIT ?",
            (max(1, min(limit, 200)),),
        )]


def get_scan(scan_id: int) -> dict[str, Any] | None:
    with _connect() as db:
        row = db.execute("SELECT report_json FROM scans WHERE id=?", (scan_id,)).fetchone()
        return json.loads(row[0]) if row else None

"""Bounded CSV/JSON import helpers shared by upload routes."""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

MAX_UPLOAD = 5 * 1024 * 1024
_WRAPPERS = ("data", "events", "rows", "records", "items", "usage")


def parse_data_bytes(data: bytes, filename: str = "upload.csv") -> list[dict[str, str]]:
    if len(data) > MAX_UPLOAD:
        raise ValueError("File exceeds 5 MB MVP limit")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("File must be UTF-8 encoded") from exc
    text = text.strip()
    if not text:
        raise ValueError("File is empty")

    suffix = Path(filename or "").suffix.lower()
    if suffix in {".json", ".jsonl", ".ndjson"} or text.startswith(("{", "[")):
        try:
            value: Any = json.loads(text)
        except json.JSONDecodeError:
            # JSON Lines is parsed line by line; malformed lines fail the import.
            try:
                value = [json.loads(line) for line in text.splitlines() if line.strip()]
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {exc.lineno}: {exc.msg}") from exc
        if isinstance(value, dict):
            for key in _WRAPPERS:
                if isinstance(value.get(key), list):
                    value = value[key]
                    break
            else:
                value = [value]
        if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
            raise ValueError("JSON must be an object, an array of objects, JSON Lines, or a data/events/rows wrapper")
        if not value:
            raise ValueError("File needs at least one data row")
        return [{str(k): "" if v is None else str(v) for k, v in row.items()} for row in value]

    reader = csv.DictReader(io.StringIO(text, newline=""))
    if not reader.fieldnames:
        raise ValueError("CSV needs a header row")
    rows = list(reader)
    if not rows:
        raise ValueError("CSV needs at least one data row")
    if any(None in row for row in rows):
        raise ValueError("CSV contains rows with more values than headers")
    return [{str(k): "" if v is None else str(v) for k, v in row.items()} for row in rows]

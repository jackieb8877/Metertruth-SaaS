from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

STRIPE_API_BASE = "https://api.stripe.com/v1"


class StripeReadError(RuntimeError):
    pass


def validate_secret_key(key: str) -> str:
    key = (key or "").strip()
    if not key:
        raise ValueError("Stripe API key is required")
    # Accept standard and restricted secret keys only. Publishable keys cannot read summaries.
    if not key.startswith(("sk_test_", "sk_live_", "rk_test_", "rk_live_")):
        raise ValueError("Use a Stripe secret or restricted key (sk_* or rk_*), not a publishable key")
    return key


def _default_get(url: str, headers: dict[str, str], timeout: float) -> dict[str, Any]:
    req = Request(url, method="GET", headers=headers)
    try:
        with urlopen(req, timeout=timeout) as resp:  # nosec B310: fixed Stripe HTTPS base URL
            data = resp.read()
            return json.loads(data.decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        message = f"Stripe returned HTTP {exc.code}"
        try:
            payload = json.loads(body)
            detail = payload.get("error", {}).get("message")
            if detail:
                message += f": {detail}"
        except Exception:
            pass
        raise StripeReadError(message) from exc
    except URLError as exc:
        raise StripeReadError(f"Could not reach Stripe: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise StripeReadError("Stripe returned invalid JSON") from exc


@dataclass
class StripeReadClient:
    api_key: str
    timeout: float = 15.0
    get_json: Callable[[str, dict[str, str], float], dict[str, Any]] = _default_get

    def __post_init__(self) -> None:
        self.api_key = validate_secret_key(self.api_key)

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "MeterTruth-MVP/0.3",
        }

    def list_meter_event_summaries(
        self,
        *,
        meter_id: str,
        customer_id: str,
        start_time: int,
        end_time: int,
        grouping: str = "hour",
        max_pages: int = 100,
    ) -> list[dict[str, Any]]:
        meter_id = (meter_id or "").strip()
        customer_id = (customer_id or "").strip()
        if not meter_id.startswith("mtr_"):
            raise ValueError("Stripe meter ID must start with mtr_")
        if not customer_id.startswith("cus_"):
            raise ValueError("Stripe customer ID must start with cus_")
        if grouping not in {"hour", "day"}:
            raise ValueError("Grouping must be hour or day")
        if int(end_time) <= int(start_time):
            raise ValueError("end_time must be after start_time")
        start_dt = __import__("datetime").datetime.fromtimestamp(int(start_time), tz=__import__("datetime").timezone.utc)
        end_dt = __import__("datetime").datetime.fromtimestamp(int(end_time), tz=__import__("datetime").timezone.utc)
        if grouping == "hour" and (start_dt.minute or start_dt.second or end_dt.minute or end_dt.second):
            raise ValueError("Hourly Stripe summaries require start/end aligned to exact UTC hours")
        if grouping == "day" and (start_dt.hour or start_dt.minute or start_dt.second or end_dt.hour or end_dt.minute or end_dt.second):
            raise ValueError("Daily Stripe summaries require start/end aligned to 00:00 UTC")
        if max_pages < 1:
            raise ValueError("max_pages must be positive")

        base = f"{STRIPE_API_BASE}/billing/meters/{meter_id}/event_summaries"
        params: dict[str, Any] = {
            "customer": customer_id,
            "start_time": int(start_time),
            "end_time": int(end_time),
            "value_grouping_window": grouping,
            "limit": 100,
        }
        out: list[dict[str, Any]] = []
        pages = 0
        while True:
            pages += 1
            if pages > max_pages:
                raise StripeReadError("Stripe pagination exceeded safety limit")
            url = base + "?" + urlencode(params)
            payload = self.get_json(url, self.headers, self.timeout)
            data = payload.get("data")
            if not isinstance(data, list):
                raise StripeReadError("Stripe response is missing a data list")
            for row in data:
                if not isinstance(row, dict):
                    raise StripeReadError("Stripe response contains an invalid summary row")
                item = dict(row)
                item["customer_id"] = customer_id
                out.append(item)
            if not payload.get("has_more"):
                break
            if not data or not data[-1].get("id"):
                raise StripeReadError("Stripe pagination response has no cursor")
            params["starting_after"] = data[-1]["id"]
        return out

"""Reproducible in-memory throughput check: python benchmark_recoverycore.py [count]."""
from __future__ import annotations

import json
import sys
import time

from recoverycore_v02 import DEFAULT_CONFIG, reconcile


def make_rows(count: int, adversarial: bool = False):
    raw = [{"event_id": f"evt-{i}", "customer_id": f"customer-{i % 1000}",
            "timestamp": "2026-09-27T00:00:00Z", "quantity": "100", "metric": "tokens"}
           for i in range(count)]
    metered = [dict(row) for row in raw]
    if adversarial and count >= 100:
        step = max(1, count // 100)
        metered = metered[:count-step]
        for i in range(0, len(metered), step):
            metered[i]["quantity"] = "99"
        for i in range(1, len(metered), step):
            metered.append(dict(metered[i]))
        for i in range(count, count+step):
            metered.append({"event_id": f"orphan-{i}", "customer_id": "customer-orphan",
                            "timestamp": "2026-09-27T00:00:00Z", "quantity": "1", "metric": "tokens"})
    return raw, metered


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1_000_000
    raw, metered = make_rows(count, adversarial=count <= 100_000)
    started = time.perf_counter()
    report = reconcile(raw, metered, {**DEFAULT_CONFIG, "price_per_unit": 0.001})
    elapsed = time.perf_counter() - started
    print(json.dumps({"raw_events": len(raw), "metered_rows": len(metered),
                      "elapsed_seconds": round(elapsed, 3), "findings": report["summary"]["findings"],
                      "underbilling_eur": report["summary"]["potential_underbilling_eur"],
                      "overbilling_eur": report["summary"]["potential_overbilling_eur"]}, indent=2))


if __name__ == "__main__":
    main()

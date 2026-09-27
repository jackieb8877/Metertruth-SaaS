from __future__ import annotations

import base64
import csv
import hmac
import io
import json
import os
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from recoverycore_v02 import DEFAULT_CONFIG, infer, reconcile
from stripe_bridge import reconcile_stripe_summaries
from multi_scan import scan_stripe_customers
from identity_mapping import parse_identity_mapping_rows, apply_identity_mapping
from stripe_client import StripeReadClient, StripeReadError
from beta_readiness import build_preflight, executive_summary
from data_import import MAX_UPLOAD as IMPORT_MAX_UPLOAD, parse_data_bytes
import scan_history

app = FastAPI(title="MeterTruth MVP", version="0.7.0")
app.mount("/static", StaticFiles(directory=str(Path(__file__).with_name("static"))), name="static")

MAX_UPLOAD = IMPORT_MAX_UPLOAD


def _basic_auth_ok(header: str | None) -> bool:
    username = os.getenv("BETA_USERNAME", "").strip()
    password = os.getenv("BETA_PASSWORD", "")
    if not username and not password:
        return True
    if not username or not password or not header or not header.startswith("Basic "):
        return False
    try:
        raw = base64.b64decode(header[6:], validate=True).decode("utf-8")
        supplied_user, supplied_password = raw.split(":", 1)
    except (ValueError, UnicodeDecodeError):
        return False
    return hmac.compare_digest(supplied_user, username) and hmac.compare_digest(supplied_password, password)


@app.middleware("http")
async def private_beta_guard(request: Request, call_next):
    if request.url.path not in {"/health", "/robots.txt"} and not _basic_auth_ok(request.headers.get("authorization")):
        return Response(status_code=401, headers={"WWW-Authenticate": 'Basic realm="MeterTruth private beta"'})
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
    return response


def parse_csv_bytes(data: bytes) -> list[dict[str, str]]:
    if len(data) > MAX_UPLOAD:
        raise ValueError("File exceeds 5 MB MVP limit")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be UTF-8 encoded") from exc
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV needs a header row")
    rows = list(reader)
    if not rows:
        raise ValueError("CSV needs at least one data row")
    return rows



def parse_iso_epoch(value: str) -> int:
    value = (value or "").strip()
    if not value:
        raise ValueError("Start and end date/time are required")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid date/time") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.astimezone(timezone.utc).timestamp())


def normalize_raw_for_stripe(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    mapping = infer(rows[0].keys())
    required = {"customer_id", "timestamp", "quantity"}
    missing = required - set(mapping)
    if missing:
        raise ValueError(f"Could not infer raw usage columns: missing {sorted(missing)}")
    return [{
        "customer_id": str(row[mapping["customer_id"]]),
        "timestamp": row[mapping["timestamp"]],
        "timestamp_epoch": parse_iso_epoch(row[mapping["timestamp"]]),
        "quantity": float(row[mapping["quantity"]]),
        "metric": str(row[mapping["metric"]]) if "metric" in mapping else "default",
    } for row in rows]


def config_from_form(price_per_unit: str, late_hours: str, quantity_tolerance: str,
                     annualization_periods: str, pricing_json: str) -> dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    try:
        cfg["price_per_unit"] = float(price_per_unit)
        cfg["late_hours"] = float(late_hours)
        cfg["quantity_tolerance"] = float(quantity_tolerance)
        cfg["annualization_periods"] = int(annualization_periods)
    except ValueError as exc:
        raise ValueError("Numeric configuration contains an invalid value") from exc
    if cfg["price_per_unit"] < 0 or cfg["late_hours"] < 0 or cfg["quantity_tolerance"] < 0:
        raise ValueError("Price, late-hours and tolerance must be non-negative")
    if not 1 <= cfg["annualization_periods"] <= 365:
        raise ValueError("Annualization periods must be between 1 and 365")
    pricing_json = pricing_json.strip()
    if pricing_json:
        try:
            pricing = json.loads(pricing_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Pricing JSON is invalid: {exc.msg}") from exc
        if not isinstance(pricing, dict):
            raise ValueError("Pricing JSON must be an object")
        cfg["pricing"] = pricing
    return cfg


def money(v: float) -> str:
    return f"€{v:,.2f}"


def badge(status: str) -> str:
    cls = {"CONFIRMED": "danger", "SUSPECTED": "warn", "UNVERIFIABLE": "neutral"}.get(status, "neutral")
    return f'<span class="badge {cls}">{escape(status)}</span>'


def layout(body: str, title: str = "MeterTruth") -> str:
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title><link rel="stylesheet" href="/static/app.css"></head>
<body><header><div class="brand">MeterTruth <span>MVP</span></div><div class="tag">Independent usage → billing reconciliation · <a href="/history">Scan history</a></div></header>
<main>{body}</main><footer>MeterTruth private beta v0.7 · RecoveryCore v0.2 · uploads are processed in memory</footer></body></html>'''


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    body = '''
<section class="hero"><div><p class="eyebrow">REVENUE ASSURANCE FOR USAGE-BASED SAAS</p><h1>Find usage that never became revenue.</h1>
<p class="lede">Compare raw product usage against metered or billing usage. MeterTruth flags missing, duplicate, mismatched, late and orphan events and estimates the economic exposure.</p></div>
<div class="privacy"><b>MVP privacy model</b><br>Original uploads and API keys are not stored. Reports and finding evidence are saved to local SQLite scan history.</div></section>
<section class="panel beta"><div><p class="eyebrow">PRIVATE BETA FLOW</p><h2>First time here?</h2><p>Use the guided preflight before connecting Stripe, or inspect a synthetic portfolio report.</p></div><div class="beta-actions"><a class="buttonlink" href="/start">Start guided scan</a><a class="buttonlink secondary" href="/demo">View demo</a></div></section>
<section class="panel"><h2>Run a reconciliation</h2>
<form action="/analyze" method="post" enctype="multipart/form-data">
<div class="grid2"><label>Source / raw usage CSV or JSON<input type="file" name="raw_file" accept=".csv,.json,.jsonl,.ndjson,text/csv,application/json" required></label>
<label>Metered / billing usage CSV or JSON<input type="file" name="metered_file" accept=".csv,.json,.jsonl,.ndjson,text/csv,application/json" required></label></div>
<details><summary>Pricing & detection settings</summary><div class="settings grid2">
<label>Fallback price per unit (€)<input name="price_per_unit" value="0.01" inputmode="decimal"></label>
<label>Late threshold (hours)<input name="late_hours" value="24" inputmode="decimal"></label>
<label>Quantity tolerance<input name="quantity_tolerance" value="0" inputmode="decimal"></label>
<label>Annualization periods<input name="annualization_periods" value="12" inputmode="numeric"></label>
<label class="wide">Optional pricing JSON<textarea name="pricing_json" rows="5" placeholder='{"api_calls":{"unit_price":0.02}}'></textarea></label>
</div></details>
<button type="submit">Analyze leakage</button></form>
<div class="hint"><b>Expected minimum fields:</b> event/request ID, customer/account ID, timestamp, quantity. Metric and idempotency key are optional. CSV headers and JSON object keys use common aliases. <a href="/history">View scan history</a>.</div>
</section>
<section class="panel compact"><h2>Stripe read-only connector</h2><p>Compare raw usage with official Stripe meter summaries without changing Stripe data.</p><a class="buttonlink" href="/stripe">Open Stripe connector</a></section>
<section class="how"><h2>What it checks</h2><div class="chips"><span>Missing usage</span><span>Duplicates</span><span>Wrong quantity</span><span>Customer mismatch</span><span>Metric mismatch</span><span>Late events</span><span>Orphans</span><span>Idempotency collisions</span></div></section>'''
    return layout(body)


@app.post("/analyze", response_class=HTMLResponse)
async def analyze(
    raw_file: UploadFile = File(...),
    metered_file: UploadFile = File(...),
    price_per_unit: str = Form("0.01"),
    late_hours: str = Form("24"),
    quantity_tolerance: str = Form("0"),
    annualization_periods: str = Form("12"),
    pricing_json: str = Form(""),
) -> str:
    try:
        raw = parse_data_bytes(await raw_file.read(), raw_file.filename or "raw.csv")
        metered = parse_data_bytes(await metered_file.read(), metered_file.filename or "metered.csv")
        cfg = config_from_form(price_per_unit, late_hours, quantity_tolerance, annualization_periods, pricing_json)
        report = reconcile(raw, metered, cfg)
        report["created_at"] = datetime.now(timezone.utc).isoformat()
        scan_id = scan_history.save(report, raw_file.filename or "raw.csv", metered_file.filename or "metered.csv")
    except (ValueError, KeyError) as exc:
        return HTMLResponse(layout(f'<section class="panel error"><h2>Could not analyze files</h2><p>{escape(str(exc))}</p><a class="buttonlink" href="/">Try again</a></section>', "MeterTruth · Error"), status_code=400)

    s = report["summary"]
    mapping = report["input_mapping"]
    findings = report["findings"]
    rows = []
    for i, f in enumerate(findings):
        rows.append(f'''<tr><td>{escape(str(f["event_id"]))}</td><td>{escape(str(f.get("customer") or "—"))}</td>
<td><b>{escape(f.get("code", f["type"]))}</b><div class="detail">{escape(f["detail"])}</div></td><td>{badge(f["status"])}</td>
<td class="money">{money(float(f["impact_eur"]))}</td><td>{escape(f["action"])}</td></tr>''')
    table = "".join(rows) or '<tr><td colspan="6" class="empty">No discrepancies found in this scan.</td></tr>'
    report_json = escape(json.dumps(report, ensure_ascii=False))
    map_raw = ", ".join(f"{escape(k)} → {escape(v)}" for k,v in mapping["raw"].items())
    map_meter = ", ".join(f"{escape(k)} → {escape(v)}" for k,v in mapping["metered"].items())
    body = f'''
<section class="results-head"><div><p class="eyebrow">SCAN COMPLETE · #{scan_id}</p><h1>{s["confirmed_findings"]} confirmed findings</h1><p class="lede">{s["raw_events"]} source events compared with {s["metered_rows"]} metered rows.</p></div><div><a class="buttonlink secondary" href="/">New scan</a> <a class="buttonlink" href="/history/{scan_id}">Open saved report</a></div></section>
<section class="cards"><div class="card"><span>Underbilling</span><strong>{money(s["potential_underbilling_eur"])}</strong></div>
<div class="card"><span>Overbilling</span><strong>{money(s["potential_overbilling_eur"])}</strong></div>
<div class="card"><span>Period exposure</span><strong>{money(s["period_exposure_eur"])}</strong></div>
<div class="card"><span>Annualized*</span><strong>{money(s["annualized_exposure_eur"])}</strong></div></section>
<section class="panel compact"><h2>Detected schema</h2><p><b>Source:</b> {map_raw}</p><p><b>Metered:</b> {map_meter}</p></section>
<section class="panel tablepanel"><div class="tabletitle"><div><h2>Findings</h2><p>{s["suspected_findings"]} suspected · {s["unverifiable_findings"]} unverifiable</p></div>
<form action="/export" method="post"><input type="hidden" name="report_json" value="{report_json}"><button class="small" type="submit">Export JSON</button></form></div>
<div class="scroll"><table><thead><tr><th>Event</th><th>Customer</th><th>Finding</th><th>Status</th><th>Impact</th><th>Suggested action</th></tr></thead><tbody>{table}</tbody></table></div></section>
<p class="footnote">*Simple extrapolation using the configured number of periods. It is not a forecast. Suggested actions require human review.</p>'''
    return layout(body, "MeterTruth · Results")


@app.post("/export")
def export(report_json: str = Form(...)) -> Response:
    try:
        payload = json.loads(report_json)
    except json.JSONDecodeError:
        return JSONResponse({"error": "Invalid report"}, status_code=400)
    return Response(json.dumps(payload, indent=2, ensure_ascii=False), media_type="application/json",
                    headers={"Content-Disposition": "attachment; filename=metertruth-report.json"})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": "MeterTruth 0.7.0", "kernel": "RecoveryCore 0.2.0"}


def _report_document(report: dict[str, Any], scan_id: int) -> str:
    s = report["summary"]
    def cash(value: Any) -> str:
        return f"€{float(value):,.2f}"
    if report.get("customers") is not None:
        rows = "".join(
            f"<tr><td>{escape(str(item.get('source_customer_id') or item.get('customer_id','—')))}</td>"
            f"<td>{escape(str(item.get('customer_id','—')))}</td><td>{escape(str(item.get('status','—')))}</td>"
            f"<td>{int(item.get('findings',0))}</td><td>{cash(item.get('potential_underbilling_eur',0))}</td>"
            f"<td>{cash(item.get('potential_overbilling_eur',0))}</td><td>{cash(item.get('period_exposure_eur',0))}</td></tr>"
            for item in report.get("customers", [])
        ) or '<tr><td colspan="7">No customers scanned.</td></tr>'
        table = f"<table><thead><tr><th>Source customer</th><th>Billing customer</th><th>Status</th><th>Findings</th><th>Underbilling</th><th>Overbilling</th><th>Exposure</th></tr></thead><tbody>{rows}</tbody></table>"
        detail = f"{s.get('customers_scanned',0):,} Stripe customers scanned; {s.get('customers_failed',0):,} failed."
    elif report.get("mode") == "stripe_meter_summary":
        rows = "".join(
            f"<tr><td>{escape(str(item.get('customer_id','—')))}</td><td>{escape(str(item.get('metric','—')))}</td>"
            f"<td>{escape(str(item.get('bucket_start','—')))}</td><td>{float(item.get('expected_usage',0)):,.4g}</td>"
            f"<td>{float(item.get('stripe_usage',0)):,.4g}</td><td>{escape(str(item.get('type','—')))}</td>"
            f"<td>{cash(item.get('impact_eur',0))}</td></tr>" for item in report.get("findings", [])
        ) or '<tr><td colspan="7">No aggregate discrepancies found.</td></tr>'
        table = f"<table><thead><tr><th>Customer</th><th>Metric</th><th>Bucket</th><th>Expected</th><th>Stripe</th><th>Finding</th><th>Impact</th></tr></thead><tbody>{rows}</tbody></table>"
        detail = f"{s.get('buckets_compared',0):,} usage buckets compared from Stripe meter summaries."
    else:
        rows = []
        for item in report.get("findings", []):
            evidence_html = escape(json.dumps(item.get("evidence", {}), ensure_ascii=False, indent=2))
            rows.append(
                "<tr>"
                f"<td><b>{escape(str(item.get('code') or item['type']))}</b><br>{escape(str(item['status']))}</td>"
                f"<td>{escape(str(item.get('customer') or '—'))}</td>"
                f"<td>{escape(str(item.get('event_id') or '—'))}</td>"
                f"<td>{cash(item.get('impact_eur', 0))}</td>"
                f"<td>{escape(str(item.get('detail') or ''))}</td>"
                f"<td>{escape(str(item.get('action') or 'Review source data'))}</td>"
                f"<td><details><summary>Evidence</summary><pre>{evidence_html}</pre></details></td>"
                "</tr>"
            )
        table = f"<table><thead><tr><th>Type / status</th><th>Customer</th><th>Event</th><th>Estimated impact</th><th>Evidence summary</th><th>Recommended action</th><th>Source evidence</th></tr></thead><tbody>{''.join(rows) or '<tr><td colspan=\"7\">No discrepancies found.</td></tr>'}</tbody></table>"
        detail = f"{s.get('raw_events',0):,} product events compared with {s.get('metered_rows',0):,} metered rows."
    body = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MeterTruth report #{scan_id}</title><link rel="stylesheet" href="/static/app.css"></head><body><header><div class="brand">MeterTruth <span>REPORT</span></div><div class="tag">Scan #{scan_id} · <a href="/history">History</a></div></header><main class="report"><p class="eyebrow">REVENUE ASSURANCE · {escape(str(report.get('created_at','')))}</p><h1>Revenue Leak Report</h1><p class="lede">{detail}</p><section class="cards"><div class="card"><span>Potential underbilling</span><strong>{cash(s.get('potential_underbilling_eur',0))}</strong></div><div class="card"><span>Potential overbilling</span><strong>{cash(s.get('potential_overbilling_eur',0))}</strong></div><div class="card"><span>Period exposure</span><strong>{cash(s.get('period_exposure_eur',0))}</strong></div><div class="card"><span>Findings</span><strong>{s.get('findings',0)}</strong></div></section><section class="panel"><h2>Findings and evidence</h2><div class="scroll">{table}</div><p class="hint">Amounts are potential exposure estimates. Review pricing, credits, adjustments and period rules before taking billing action.</p></section><p><a class="buttonlink secondary" href="/history">Back to history</a></p></main></body></html>'''
    return body


@app.get("/history", response_class=HTMLResponse)
def history_page() -> str:
    scans = scan_history.list_scans()
    rows = "".join(
        f'<tr><td>#{x["id"]}</td><td>{escape(x["created_at"][:19].replace("T", " "))}</td>'
        f'<td>{escape(x["source_name"])}</td><td>{escape(x["metered_name"])}</td>'
        f'<td>{x["findings"]}</td><td>{money(x["underbilling"])}</td><td>{money(x["overbilling"])}</td>'
        f'<td><a href="/history/{x["id"]}">Open report</a></td></tr>' for x in scans
    ) or '<tr><td colspan="8" class="empty">No saved scans yet. Uploaded source files are not retained.</td></tr>'
    body = f'''<section class="results-head"><div><p class="eyebrow">LOCAL SCAN HISTORY</p><h1>Previous reconciliations</h1><p class="lede">Reports and summary metadata are saved. Original uploads and API keys are not.</p></div><a class="buttonlink" href="/">Run a scan</a></section><section class="panel tablepanel"><div class="scroll"><table><thead><tr><th>Scan</th><th>Date UTC</th><th>Product file</th><th>Metered file</th><th>Findings</th><th>Underbilling</th><th>Overbilling</th><th>Report</th></tr></thead><tbody>{rows}</tbody></table></div></section><p class="footnote">On serverless hosting (including Vercel), this history uses temporary local storage and may disappear after a restart or run in a separate instance.</p>'''
    return layout(body, "MeterTruth · Scan History")


@app.get("/history/{scan_id}", response_class=HTMLResponse)
def history_report(scan_id: int) -> Response:
    report = scan_history.get_scan(scan_id)
    if report is None:
        return HTMLResponse(layout('<section class="panel error"><h2>Report not found</h2><a href="/history">Back to history</a></section>'), status_code=404)
    return HTMLResponse(_report_document(report, scan_id))


@app.get("/robots.txt")
def robots() -> Response:
    return Response("User-agent: *\nDisallow: /\n", media_type="text/plain")

@app.get("/start", response_class=HTMLResponse)
def onboarding() -> str:
    body = '''
<section class="results-head"><div><p class="eyebrow">PRIVATE BETA · FIRST SCAN</p><h1>Get to a trustworthy billing check in four steps.</h1>
<p class="lede">Start with a local preflight. MeterTruth checks your files and identity coverage before any Stripe request is made.</p></div><a class="buttonlink secondary" href="/demo">View demo first</a></section>
<section class="steps"><div class="step"><span>1</span><div><b>Export product usage</b><p>CSV with customer/account, timestamp, quantity and optional metric.</p></div></div>
<div class="step"><span>2</span><div><b>Map customer identities</b><p>If your CSV uses workspace/account IDs, add a two-column internal → Stripe mapping.</p></div></div>
<div class="step"><span>3</span><div><b>Run preflight</b><p>Confirm schema, customer coverage, metric and time window without calling Stripe.</p></div></div>
<div class="step"><span>4</span><div><b>Run read-only scan</b><p>Use a restricted Stripe key and review the ranked exposure report.</p></div></div></section>
<section class="panel"><h2>Preflight your files</h2><form action="/preflight" method="post" enctype="multipart/form-data">
<div class="grid2"><label>Raw product usage CSV<input type="file" name="raw_file" accept=".csv,text/csv" required></label>
<label>Optional identity mapping CSV<input type="file" name="mapping_file" accept=".csv,text/csv"><small>internal_customer_id → stripe_customer_id</small></label></div>
<button type="submit">Check readiness</button></form><div class="hint">No Stripe key is needed for preflight and no external API call is made.</div></section>
<section class="panel compact"><h2>Need sample files?</h2><p>The packaged beta includes <code>demo_internal_usage.csv</code> and <code>demo_identity_mapping.csv</code>. You can also open the built-in portfolio demo without credentials.</p><a class="buttonlink" href="/demo">Open portfolio demo</a></section>'''
    return layout(body, "MeterTruth · First scan")


@app.post("/preflight", response_class=HTMLResponse)
async def preflight(raw_file: UploadFile = File(...), mapping_file: UploadFile | None = File(None)) -> str:
    try:
        raw = normalize_raw_for_stripe(parse_csv_bytes(await raw_file.read()))
        identity_map = None
        if mapping_file is not None and mapping_file.filename:
            mapping_rows = parse_csv_bytes(await mapping_file.read())
            identity_map = parse_identity_mapping_rows(mapping_rows)
        report = build_preflight(raw, identity_map=identity_map)
    except (ValueError, KeyError) as exc:
        return HTMLResponse(layout(f'<section class="panel error"><h2>Preflight failed</h2><p>{escape(str(exc))}</p><a class="buttonlink" href="/start">Try again</a></section>', "MeterTruth · Preflight Error"), status_code=400)

    metrics = "".join(f'<span>{escape(m["name"])} · {m["rows"]} rows</span>' for m in report["metrics"])
    warnings = "".join(f'<li>{escape(x)}</li>' for x in report["warnings"]) or "<li>None.</li>"
    blockers = "".join(f'<li>{escape(x)}</li>' for x in report["blockers"]) or "<li>None.</li>"
    cls = "ok" if report["readiness"] == "READY" else "error"
    next_link = '<a class="buttonlink" href="/stripe">Continue to Stripe scan</a>' if report["readiness"] == "READY" else '<a class="buttonlink secondary" href="/start">Fix files and re-run</a>'
    ident = report["identity_mapping"]
    body = f'''<section class="results-head"><div><p class="eyebrow">PREFLIGHT COMPLETE</p><h1>{report["readiness"]}</h1><p class="lede">{report["rows"]} usage rows · {report["source_customers"]} source customers · {report["stripe_customers_ready"]} Stripe customers ready.</p></div>{next_link}</section>
<section class="cards"><div class="card"><span>Rows</span><strong>{report["rows"]}</strong></div><div class="card"><span>Source customers</span><strong>{report["source_customers"]}</strong></div><div class="card"><span>Stripe-ready</span><strong>{report["stripe_customers_ready"]}</strong></div><div class="card"><span>Unmapped</span><strong>{ident["unmapped_internal_customers"]}</strong></div></section>
<section class="panel"><h2>Dataset coverage</h2><p><b>First event:</b> {escape(report["window"]["first_event"])}</p><p><b>Last event:</b> {escape(report["window"]["last_event"])}</p><div class="chips">{metrics}</div><p class="hint"><b>Suggested metric:</b> {escape(report["recommended"]["metric"])}</p></section>
<section class="grid2"><div class="panel {cls}"><h2>Warnings</h2><ul>{warnings}</ul></div><div class="panel {cls}"><h2>Blockers</h2><ul>{blockers}</ul></div></section>
<p class="footnote">Preflight is network-free. No Stripe API request was made.</p>'''
    return layout(body, "MeterTruth · Preflight")


@app.get("/demo", response_class=HTMLResponse)
def portfolio_demo() -> str:
    demo_path = Path(__file__).with_name("demo_stripe_portfolio_report.json")
    report = json.loads(demo_path.read_text(encoding="utf-8"))
    summary = executive_summary(report)
    rows = []
    for item in report["customers"]:
        rows.append(f'<tr><td><b>{escape(item["customer_id"])}</b></td><td>{escape(item["status"])}</td><td>{item["findings"]}</td><td class="money">{money(item["potential_underbilling_eur"])}</td><td class="money">{money(item["potential_overbilling_eur"])}</td><td class="money">{money(item["period_exposure_eur"])}</td></tr>')
    actions = "".join(f'<li>{escape(a)}</li>' for a in summary["recommended_actions"])
    body = f'''<section class="results-head"><div><p class="eyebrow">INTERACTIVE SAMPLE · NO CREDENTIALS</p><h1>{escape(summary["headline"])}</h1><p class="lede">This is a synthetic portfolio report showing the private-beta output before you connect your own files.</p></div><a class="buttonlink" href="/start">Start your preflight</a></section>
<section class="cards"><div class="card"><span>Underbilling</span><strong>{money(summary["potential_underbilling_eur"])}</strong></div><div class="card"><span>Overbilling</span><strong>{money(summary["potential_overbilling_eur"])}</strong></div><div class="card"><span>Customers flagged</span><strong>{summary["customers_with_findings"]}</strong></div><div class="card"><span>Customers scanned</span><strong>{summary["customers_scanned"]}</strong></div></section>
<section class="panel tablepanel"><div class="tabletitle"><div><h2>Customers ranked by exposure</h2><p>Synthetic demonstration data</p></div></div><div class="scroll"><table><thead><tr><th>Stripe customer</th><th>Status</th><th>Findings</th><th>Underbilling</th><th>Overbilling</th><th>Exposure</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></section>
<section class="panel"><h2>Recommended review actions</h2><ul>{actions}</ul><p class="hint">{escape(summary["scope_note"])}</p></section>'''
    return layout(body, "MeterTruth · Demo")


@app.get("/stripe", response_class=HTMLResponse)
def stripe_home() -> str:
    body = '''
<section class="results-head"><div><p class="eyebrow">STRIPE · READ ONLY</p><h1>Compare product usage with Stripe meter summaries.</h1>
<p class="lede">MeterTruth sends GET requests only. The API key is used for this request and is not persisted by the app.</p></div><a class="buttonlink secondary" href="/">CSV mode</a></section>
<section class="panel"><h2>Portfolio scan · recommended</h2><p class="lede smalllede">Detect Stripe customer IDs from the raw usage file and reconcile every matching customer for one meter.</p><form action="/stripe/scan" method="post" enctype="multipart/form-data">
<div class="grid2"><label>Raw product usage CSV<input type="file" name="raw_file" accept=".csv,text/csv" required></label>
<label>Optional identity mapping CSV<input type="file" name="mapping_file" accept=".csv,text/csv"><small>internal_customer_id → stripe_customer_id</small></label>
<label>Stripe restricted/secret key<input type="password" name="api_key" autocomplete="off" placeholder="rk_test_…" required></label>
<label>Meter ID<input name="meter_id" placeholder="mtr_…" required></label>
<label>Metric name in raw CSV<input name="metric" value="default" required></label>
<label>Unit price (€)<input name="unit_price" value="0.01" inputmode="decimal" required></label>
<label>Usage tolerance<input name="tolerance" value="0" inputmode="decimal"></label>
<label>Start UTC<input type="datetime-local" name="start_time" required></label>
<label>End UTC<input type="datetime-local" name="end_time" required></label>
<label>Grouping<select name="grouping"><option value="hour">Hour</option><option value="day">Day</option></select></label></div>
<button type="submit">Scan all Stripe customers</button></form>
<div class="hint"><b>Identity mapping:</b> raw IDs may be internal account/workspace IDs when you provide a mapping CSV. Rows already using <code>cus_*</code> pass through. Unmapped internal IDs are reported and excluded from Stripe calls. Up to 250 mapped Stripe customers per scan.</div></section>
<section class="panel"><details><summary>Single-customer diagnostic</summary><form action="/stripe/analyze" method="post" enctype="multipart/form-data">
<div class="grid2 settings"><label>Raw product usage CSV<input type="file" name="raw_file" accept=".csv,text/csv" required></label>
<label>Stripe restricted/secret key<input type="password" name="api_key" autocomplete="off" placeholder="rk_test_…" required></label>
<label>Meter ID<input name="meter_id" placeholder="mtr_…" required></label>
<label>Customer ID<input name="customer_id" placeholder="cus_…" required></label>
<label>Metric name in raw CSV<input name="metric" value="default" required></label>
<label>Unit price (€)<input name="unit_price" value="0.01" inputmode="decimal" required></label>
<label>Start UTC<input type="datetime-local" name="start_time" required></label>
<label>End UTC<input type="datetime-local" name="end_time" required></label>
<label>Grouping<select name="grouping"><option value="hour">Hour</option><option value="day">Day</option></select></label>
<label>Usage tolerance<input name="tolerance" value="0" inputmode="decimal"></label></div>
<button type="submit">Fetch one customer</button></form></details>
<div class="hint"><b>Safer key choice:</b> use a restricted Stripe key with only the read permissions required for Billing Meters / event summaries. Never use a publishable key.</div></section>'''
    return layout(body, "MeterTruth · Stripe")


@app.post("/stripe/scan", response_class=HTMLResponse)
async def stripe_multi_scan(
    raw_file: UploadFile = File(...), mapping_file: UploadFile | None = File(None), api_key: str = Form(...), meter_id: str = Form(...),
    metric: str = Form("default"), unit_price: str = Form("0.01"),
    start_time: str = Form(...), end_time: str = Form(...), grouping: str = Form("hour"), tolerance: str = Form("0")
) -> str:
    try:
        raw = normalize_raw_for_stripe(parse_csv_bytes(await raw_file.read()))
        identity_map = None
        if mapping_file is not None and mapping_file.filename:
            mapping_rows = parse_csv_bytes(await mapping_file.read())
            identity_map = parse_identity_mapping_rows(mapping_rows)
        raw, identity_meta = apply_identity_mapping(raw, identity_map, strict=False)
        start_epoch, end_epoch = parse_iso_epoch(start_time), parse_iso_epoch(end_time)
        price, tol = float(unit_price), float(tolerance)
        if price < 0 or tol < 0:
            raise ValueError("Unit price and tolerance must be non-negative")
        if grouping not in {"hour", "day"}:
            raise ValueError("Grouping must be hour or day")
        client = StripeReadClient(api_key)
        report = scan_stripe_customers(
            raw, client=client, meter_id=meter_id, metric=metric, start_time=start_epoch, end_time=end_epoch,
            grouping=grouping, tolerance=tol, unit_price=price, max_customers=250)
        report["identity_mapping"] = identity_meta
        report["created_at"] = datetime.now(timezone.utc).isoformat()
        scan_id = scan_history.save(report, raw_file.filename or "raw.csv", f"stripe-meter-{meter_id}")
    except (ValueError, KeyError, StripeReadError) as exc:
        return HTMLResponse(layout(f'<section class="panel error"><h2>Stripe portfolio scan failed</h2><p>{escape(str(exc))}</p><a class="buttonlink" href="/stripe">Try again</a></section>', "MeterTruth · Stripe Error"), status_code=400)

    s = report["summary"]
    customer_rows = []
    for item in report["customers"]:
        customer_rows.append(f'<tr><td>{escape(item.get("source_customer_id") or item["customer_id"])}</td><td><b>{escape(item["customer_id"])}</b></td><td>{escape(item["status"])}</td><td>{item["findings"]}</td><td>{item["buckets_compared"]}</td><td class="money">{money(item["potential_underbilling_eur"])}</td><td class="money">{money(item["potential_overbilling_eur"])}</td><td class="money">{money(item["period_exposure_eur"])}</td></tr>')
    customer_table = ''.join(customer_rows) or '<tr><td colspan="8" class="empty">No customers completed successfully.</td></tr>'

    errors = ''.join(f'<li><b>{escape(e["customer_id"])}</b>: {escape(e["error"])}</li>' for e in report["errors"])
    error_block = f'<section class="panel error"><h2>{s["customers_failed"]} customers could not be scanned</h2><ul>{errors}</ul></section>' if errors else ''
    identity = report.get("identity_mapping", {})
    unmapped = identity.get("unmapped_ids", [])
    unmapped_preview = ", ".join(escape(x) for x in unmapped[:10])
    if len(unmapped) > 10:
        unmapped_preview += "…"
    identity_block = f'<section class="panel error"><h2>{len(unmapped)} internal customers were not mapped</h2><p>{unmapped_preview}</p><p>They were excluded from Stripe API calls and economic totals.</p></section>' if unmapped else ''
    report_json = escape(json.dumps(report, ensure_ascii=False))
    executive = executive_summary(report)
    actions_html = "".join(f"<li>{escape(a)}</li>" for a in executive["recommended_actions"])
    executive_block = f'<section class="panel executive"><p class="eyebrow">EXECUTIVE SUMMARY</p><h2>{escape(executive["headline"])}</h2><ul>{actions_html}</ul><p class="hint">{escape(executive["scope_note"])}</p></section>'
    body = f"""<section class="results-head"><div><p class="eyebrow">STRIPE PORTFOLIO SCAN COMPLETE</p><h1>{s["customers_with_findings"]} customers with leakage signals</h1>
<p class="lede">Scanned {s["customers_scanned"]} of {s["customers_discovered"]} Stripe customers across one meter. {s["customers_clean"]} were clean in the selected window.</p></div><a class="buttonlink secondary" href="/stripe">New Stripe scan</a></section>
<section class="cards"><div class="card"><span>Underbilling</span><strong>{money(s["potential_underbilling_eur"])}</strong></div><div class="card"><span>Overbilling</span><strong>{money(s["potential_overbilling_eur"])}</strong></div><div class="card"><span>Period exposure</span><strong>{money(s["period_exposure_eur"])}</strong></div><div class="card"><span>Findings</span><strong>{s["findings"]}</strong></div></section>
{executive_block}<p><a class="buttonlink secondary" href="/history/{scan_id}">Open saved report</a></p>
<section class="panel tablepanel"><div class="tabletitle"><div><h2>Customers ranked by exposure</h2><p>Highest economic exposure first</p></div><form action="/export" method="post"><input type="hidden" name="report_json" value="{report_json}"><button class="small" type="submit">Export JSON</button></form></div><div class="scroll"><table><thead><tr><th>Source ID</th><th>Stripe customer</th><th>Status</th><th>Findings</th><th>Buckets</th><th>Underbilling</th><th>Overbilling</th><th>Exposure</th></tr></thead><tbody>{customer_table}</tbody></table></div></section>
{identity_block}{error_block}<p class="footnote">Read-only scan. Customers with API errors are isolated and excluded from exposure totals rather than aborting the entire portfolio scan.</p>"""
    return layout(body, "MeterTruth · Stripe Portfolio")


@app.post("/stripe/analyze", response_class=HTMLResponse)
async def stripe_analyze(
    raw_file: UploadFile = File(...), api_key: str = Form(...), meter_id: str = Form(...),
    customer_id: str = Form(...), metric: str = Form("default"), unit_price: str = Form("0.01"),
    start_time: str = Form(...), end_time: str = Form(...), grouping: str = Form("hour"), tolerance: str = Form("0")
) -> str:
    try:
        raw = normalize_raw_for_stripe(parse_csv_bytes(await raw_file.read()))
        start_epoch, end_epoch = parse_iso_epoch(start_time), parse_iso_epoch(end_time)
        price, tol = float(unit_price), float(tolerance)
        if price < 0 or tol < 0:
            raise ValueError("Unit price and tolerance must be non-negative")
        if grouping not in {"hour", "day"}:
            raise ValueError("Grouping must be hour or day")
        filtered = []
        for row in raw:
            ts = parse_iso_epoch(str(row["timestamp"]))
            if row["customer_id"] == customer_id and row["metric"] == metric and start_epoch <= ts < end_epoch:
                filtered.append(row)
        if not filtered:
            raise ValueError("No raw usage rows match the selected customer, metric and period")
        client = StripeReadClient(api_key)
        stripe_rows = client.list_meter_event_summaries(
            meter_id=meter_id, customer_id=customer_id, start_time=start_epoch, end_time=end_epoch, grouping=grouping)
        report = reconcile_stripe_summaries(
            filtered, stripe_rows, meter_to_metric={meter_id: metric}, grouping=grouping,
            tolerance=tol, unit_prices={metric: price})
        report["created_at"] = datetime.now(timezone.utc).isoformat()
        scan_id = scan_history.save(report, raw_file.filename or "raw.csv", f"stripe-meter-{meter_id}")
    except (ValueError, KeyError, StripeReadError) as exc:
        return HTMLResponse(layout(f'<section class="panel error"><h2>Stripe reconciliation failed</h2><p>{escape(str(exc))}</p><a class="buttonlink" href="/stripe">Try again</a></section>', "MeterTruth · Stripe Error"), status_code=400)

    s = report["summary"]
    rows = []
    for f in report["findings"]:
        when = datetime.fromtimestamp(int(f["bucket_start"]), tz=timezone.utc).isoformat().replace('+00:00','Z')
        rows.append(f'<tr><td>{escape(when)}</td><td>{escape(f["customer_id"])}</td><td>{escape(f["metric"])}</td><td>{f["expected_usage"]:,.4g}</td><td>{f["stripe_usage"]:,.4g}</td><td>{f["delta_usage"]:,.4g}</td><td><b>{escape(f["type"])}</b></td><td class="money">{money(float(f["impact_eur"]))}</td></tr>')
    table = ''.join(rows) or '<tr><td colspan="8" class="empty">No aggregate discrepancies found.</td></tr>'
    body = f'''<section class="results-head"><div><p class="eyebrow">STRIPE RECONCILIATION COMPLETE</p><h1>{s["findings"]} aggregate findings</h1>
<p class="lede">Compared {s["buckets_compared"]} {grouping} buckets for {escape(customer_id)}.</p></div><a class="buttonlink secondary" href="/stripe">New Stripe scan</a></section>
<section class="cards"><div class="card"><span>Underbilling</span><strong>{money(s["potential_underbilling_eur"])}</strong></div><div class="card"><span>Overbilling</span><strong>{money(s["potential_overbilling_eur"])}</strong></div><div class="card"><span>Period exposure</span><strong>{money(s["period_exposure_eur"])}</strong></div></section>
<section class="panel tablepanel"><div class="tabletitle"><div><h2>Stripe summary findings</h2><p>Official Stripe aggregate vs product-source aggregate</p></div><a class="buttonlink secondary" href="/history/{scan_id}">Open saved report</a></div><div class="scroll"><table><thead><tr><th>Bucket UTC</th><th>Customer</th><th>Metric</th><th>Expected</th><th>Stripe</th><th>Delta</th><th>Finding</th><th>Impact</th></tr></thead><tbody>{table}</tbody></table></div></section>
<p class="footnote">Read-only scan. No Stripe object was created, changed, adjusted or deleted.</p>'''
    return layout(body, "MeterTruth · Stripe Results")

# Zero-cost private-beta deployment on Render

This repository includes `render.yaml` for a single **Free** Python web service.

## Before deploying

Use the private-beta gate. In Render, set both secret environment variables:

- `BETA_USERNAME`
- `BETA_PASSWORD`

If either is missing, the application intentionally runs without Basic Auth for local development. For any internet-facing beta, set both.

## Deploy

1. Put this directory at the root of a Git repository.
2. In Render, create a Blueprint/Web Service from the repository.
3. Select the Free compute plan if it is not already selected from `render.yaml`.
4. Enter `BETA_USERNAME` and a strong, unique `BETA_PASSWORD` as secret environment variables.
5. Deploy.
6. Open `/health` first. It is intentionally unauthenticated for health checks.
7. Open `/start` and authenticate with the beta credentials.

## Render settings encoded in `render.yaml`

- Python runtime
- Free plan
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- Health check: `/health`

## Private-beta security model

- Browser Basic Auth can be enabled through environment variables.
- HTTPS/TLS should be supplied by the hosting platform.
- MeterTruth adds `no-store`, `nosniff`, `DENY` framing, `no-referrer`, and a restrictive CSP.
- `/robots.txt` disallows crawling.
- Stripe API keys are submitted as form data and are not persisted by application code.
- The connector only issues GET requests.
- Original usage uploads and Stripe keys are not retained. Derived reconciliation reports and issue evidence are stored in a local SQLite database for `/history`.

This is still a beta control, not a production identity system. Do not treat shared Basic Auth as multi-tenant authentication.

## Free-tier operational caveat

Free services can sleep when idle, so the first request after inactivity may be slow. Their local filesystem is ephemeral: scan history may disappear after a restart or replacement. This is acceptable for tester validation but not a production SLA or durable audit record.

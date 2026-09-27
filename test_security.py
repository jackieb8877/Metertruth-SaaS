import base64
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def _basic(user, password):
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def test_open_by_default_and_security_headers(monkeypatch):
    monkeypatch.delenv("BETA_USERNAME", raising=False)
    monkeypatch.delenv("BETA_PASSWORD", raising=False)
    r = client.get('/start')
    assert r.status_code == 200
    assert r.headers['x-frame-options'] == 'DENY'
    assert r.headers['cache-control'] == 'no-store'
    assert "frame-ancestors 'none'" in r.headers['content-security-policy']


def test_optional_private_beta_basic_auth(monkeypatch):
    monkeypatch.setenv("BETA_USERNAME", "tester")
    monkeypatch.setenv("BETA_PASSWORD", "secret-pass")
    assert client.get('/start').status_code == 401
    assert client.get('/start', headers=_basic('tester', 'wrong')).status_code == 401
    assert client.get('/start', headers=_basic('tester', 'secret-pass')).status_code == 200
    assert client.get('/health').status_code == 200


def test_robots_disallows_crawling(monkeypatch):
    monkeypatch.setenv("BETA_USERNAME", "tester")
    monkeypatch.setenv("BETA_PASSWORD", "secret-pass")
    r = client.get('/robots.txt')
    assert r.status_code == 200
    assert 'Disallow: /' in r.text

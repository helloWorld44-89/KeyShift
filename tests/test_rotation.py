import pytest
from sqlalchemy import text

from app import db
from app import rotation
from app.models import SSID
from conftest import make_ssid, login, make_user


@pytest.fixture
def controller(monkeypatch):
    """Stand-in for the controller: results are consumed in order, then it keeps failing."""
    calls = []
    results = []

    def fake(ssid, pw):
        calls.append(pw)
        return results.pop(0) if results else "Error: 500"

    monkeypatch.setattr(rotation, "_controllerChange", fake)
    fake.calls, fake.results = calls, results
    return fake


@pytest.fixture
def alerts(monkeypatch):
    sent = []
    monkeypatch.setattr(rotation, "alert", sent.append)
    return sent


def no_sleep(_):
    pass


def test_success_updates_password_and_clears_state(app, controller, alerts):
    s = make_ssid("Home", "abc")
    s.failCount, s.lastError, s.pendingPW = 2, "old error", "stale"
    db.session.commit()
    controller.results[:] = [True]

    r = rotation.rotate(s, "new-pw-123", sleep=no_sleep)

    assert r.ok
    db.session.expire_all()
    s = SSID.query.one()
    assert (s.ssidPW, s.pendingPW, s.failCount, s.lastError) == ("new-pw-123", None, 0, None)
    assert s.lastChanged is not None
    assert alerts == []


def test_new_password_is_saved_before_the_controller_is_called(app, monkeypatch):
    s = make_ssid("Home", "abc")
    seen = {}

    def fake(ssid, pw):
        seen["pending"] = db.session.execute(text("SELECT pendingPW FROM ssids")).scalar()
        seen["pw"] = pw
        return True

    monkeypatch.setattr(rotation, "_controllerChange", fake)
    rotation.rotate(s, sleep=no_sleep)
    assert seen["pending"].startswith("enc:v1:")        # already stored (encrypted) mid-call
    from app.crypto import decrypt
    assert decrypt(seen["pending"]) == seen["pw"]


def test_failure_keeps_old_password_saves_pending_and_alerts(app, controller, alerts):
    s = make_ssid("Home", "abc")
    sleeps = []

    r = rotation.rotate(s, attempts=3, delay=5, sleep=sleeps.append)

    assert not r.ok and "500" in r.error
    assert len(controller.calls) == 3 and len(set(controller.calls)) == 1   # same pw each retry
    assert sleeps == [5, 10]                                               # backoff, none after last
    db.session.expire_all()
    s = SSID.query.one()
    assert s.ssidPW == "p;w"                       # controller still has the old one
    assert s.pendingPW == controller.calls[0]
    assert s.failCount == 1 and "500" in s.lastError
    assert len(alerts) == 1 and "Home" in alerts[0]
    assert controller.calls[0] not in alerts[0]    # the password is never put in an alert


def test_transient_failure_recovers_within_attempts(app, controller, alerts):
    s = make_ssid("Home", "abc")
    controller.results[:] = ["Error: timeout", True]
    assert rotation.rotate(s, attempts=3, sleep=no_sleep).ok
    assert SSID.query.one().failCount == 0 and alerts == []


def test_next_attempt_reuses_pending_password_and_resets_counter(app, controller, alerts):
    s = make_ssid("Home", "abc")
    rotation.rotate(s, attempts=1, sleep=no_sleep)
    pending = SSID.query.one().pendingPW
    controller.calls.clear()
    controller.results[:] = [True]

    assert rotation.rotate(s, attempts=1, sleep=no_sleep).ok

    assert controller.calls == [pending]            # didn't invent another password
    s = SSID.query.one()
    assert s.ssidPW == pending and s.pendingPW is None and s.failCount == 0


def test_failures_accumulate(app, controller, alerts):
    s = make_ssid("Home", "abc")
    for _ in range(3):
        rotation.rotate(s, attempts=1, sleep=no_sleep)
    assert SSID.query.one().failCount == 3 and len(alerts) == 3


def test_manual_password_replaces_pending(app, controller, alerts):
    s = make_ssid("Home", "abc")
    rotation.rotate(s, attempts=1, sleep=no_sleep)
    controller.results[:] = [True]
    rotation.rotate(s, "chosen-by-admin", attempts=1, sleep=no_sleep)
    assert SSID.query.one().ssidPW == "chosen-by-admin"


# --- alerts -----------------------------------------------------------------

def test_alert_posts_to_webhook_and_survives_failures(monkeypatch):
    posted = []
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "http://hook.invalid/x")
    monkeypatch.setattr(rotation.requests, "post", lambda url, json, timeout: posted.append((url, json, timeout)))
    rotation.alert("boom")
    assert posted == [("http://hook.invalid/x", {"text": "boom", "content": "boom"}, 5)]

    def broken(*a, **k):
        raise OSError("down")
    monkeypatch.setattr(rotation.requests, "post", broken)
    rotation.alert("boom")                          # must not raise


def test_alert_without_webhook_only_logs(monkeypatch):
    monkeypatch.delenv("ALERT_WEBHOOK_URL", raising=False)
    monkeypatch.setattr(rotation.requests, "post", lambda *a, **k: pytest.fail("posted"))
    rotation.alert("boom")


# --- /changepw route ---------------------------------------------------------

def test_changepw_route_success_redirects(app, admin_client, controller):
    s = make_ssid("Home", "abc")
    controller.results[:] = [True]
    r = admin_client.post(f"/changepw/{s.id}")
    assert r.status_code == 302
    assert SSID.query.one().pendingPW is None


def test_changepw_route_failure_is_502_without_leaking_the_error(app, admin_client, controller, alerts):
    s = make_ssid("Home", "abc")
    controller.results[:] = ["Error: 401 secret-internal-detail"]
    r = admin_client.post(f"/changepw/{s.id}")
    assert r.status_code == 502
    assert "secret-internal-detail" not in r.get_data(as_text=True)
    assert len(controller.calls) == 1               # no sleeping retries inside a web request


def test_changepw_route_unknown_ssid_404(app, admin_client, controller):
    assert admin_client.post("/changepw/999").status_code == 404


def test_admin_page_shows_failed_rotation(app, admin_client, controller, alerts, monkeypatch):
    import app.routes.admin as admin
    monkeypatch.setattr(admin, "getConfig", lambda: {
        "apiType": "unifi", "controllerIp": "1.2.3.4",
        "apiUser": {"userName": None, "passWord": None, "apiKey": None}})
    s = make_ssid("Home", "abc")
    rotation.rotate(s, attempts=1, sleep=no_sleep)
    html = admin_client.get("/admin").get_data(as_text=True)
    assert "Change failed (1x)" in html and "Error: 500" in html   # admin sees the tooltip text

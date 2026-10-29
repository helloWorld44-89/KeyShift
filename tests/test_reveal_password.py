import app.routes.admin as admin
from app.models import SSID
from conftest import make_ssid


def _config(monkeypatch):
    monkeypatch.setattr(admin, "getConfig", lambda: {
        "apiType": "unifi", "controllerIp": "1.2.3.4",
        "apiUser": {"userName": None, "passWord": None, "apiKey": None}})


def test_admin_gets_password_of_any_ssid(app, admin_client):
    a = make_ssid("Home", "a")
    b = make_ssid("Guest", "b", guest=True)
    for s in (a, b):
        r = admin_client.post(f"/ssid/{s.id}/password")
        assert r.status_code == 200
        assert r.get_json() == {"password": "p;w"}
        assert r.headers["Cache-Control"] == "no-store"


def test_reflects_a_changed_password(app, admin_client):
    s = make_ssid("Home", "a")
    s.ssidPW = "new-one"
    from app import db
    db.session.commit()
    assert admin_client.post(f"/ssid/{s.id}/password").get_json() == {"password": "new-one"}


def test_standard_user_forbidden(app, standard_client):
    s = make_ssid("Home", "a")
    assert standard_client.post(f"/ssid/{s.id}/password").status_code == 403


def test_anonymous_not_served(app, client):
    s = make_ssid("Home", "a")
    r = client.post(f"/ssid/{s.id}/password")
    assert r.status_code in (302, 401)
    assert b"p;w" not in r.data


def test_get_not_allowed(app, admin_client):
    s = make_ssid("Home", "a")
    assert admin_client.get(f"/ssid/{s.id}/password").status_code == 405


def test_unknown_ssid_404(app, admin_client):
    assert admin_client.post("/ssid/999/password").status_code == 404


def test_requires_csrf(app):
    from conftest import make_user, login
    app.config["WTF_CSRF_ENABLED"] = True
    make_user("boss")
    s = make_ssid("Home", "a")
    c = app.test_client()
    c.get("/login")
    assert c.post(f"/ssid/{s.id}/password").status_code == 400


def test_reveal_is_logged_without_the_password(app, admin_client, caplog):
    s = make_ssid("Home", "a")
    with caplog.at_level("INFO"):
        admin_client.post(f"/ssid/{s.id}/password")
    text = caplog.text
    assert "boss revealed the password of Home" in text
    assert "p;w" not in text


def test_buttons_for_admin_only_and_password_not_in_html(app, admin_client, monkeypatch):
    _config(monkeypatch)
    from app import db
    make_ssid("Home", "a").ssidPW = "secret-xyz"
    make_ssid("Other", "b")
    db.session.commit()
    html = admin_client.get("/admin").get_data(as_text=True)
    assert html.count("pw-show") >= 2 and html.count("pw-copy") >= 2
    assert "secret-xyz" not in html
    assert 'data-ssid-pw="1"' in html and 'data-ssid-pw="2"' in html


def test_standard_user_sees_no_buttons(app, standard_client, monkeypatch):
    _config(monkeypatch)
    make_ssid("Home", "a")
    html = standard_client.get("/admin").get_data(as_text=True)
    assert "data-ssid-pw" not in html
    assert "pw-show" not in html

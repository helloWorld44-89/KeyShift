import pytest
from app.models import user, SSID
from app.utilities.genQR import genQRCode, escapeWifi, qrPath
from conftest import make_user, make_ssid, login


# --- QR access -----------------------------------------------------------

TOKEN = "test-setup-token"


def test_escape_wifi_special_chars():
    assert escapeWifi('a;b,c:d"e\\f') == r'a\;b\,c\:d\"e\\f'


def test_wifi_payload_is_escaped(app, monkeypatch):
    import app.utilities.genQR as genqr
    captured = {}
    real = genqr.qrcode.QRCode

    class Spy(real):
        def add_data(self, data, *a, **k):
            captured["data"] = data
            return super().add_data(data, *a, **k)
    monkeypatch.setattr(genqr.qrcode, "QRCode", Spy)
    s = make_ssid("net", "abc")
    genQRCode(s, 'x;y\\z')
    assert captured["data"] == r"WIFI:S:net;T:WPA;P:x\;y\\z;;"


def test_qr_not_served_from_static(app, client):
    s = make_ssid("guestnet", "g1", guest=True)
    genQRCode(s)
    assert client.get("/static/img/guestnet.png").status_code == 404
    assert client.get("/static/img/g1.png").status_code == 404


def test_guest_qr_is_public_but_only_for_guest(app, client):
    guest = make_ssid("guestnet", "g1", guest=True)
    other = make_ssid("private", "p1")
    genQRCode(guest)
    genQRCode(other)
    assert client.get("/api/guest").status_code == 200
    assert client.get(f"/qr/{other.id}").status_code == 302  # login redirect
    assert client.get(f"/qr/{guest.id}").status_code == 302


def test_guest_qr_404_without_guest(client):
    assert client.get("/api/guest").status_code == 404


def test_logged_in_user_can_fetch_any_qr(app, standard_client):
    other = make_ssid("private", "p1")
    genQRCode(other)
    assert standard_client.get(f"/qr/{other.id}").status_code == 200


# --- Roles ---------------------------------------------------------------

def test_non_admin_cannot_create_users(app, standard_client):
    r = standard_client.post("/users/add", data={
        "newUsername": "evil", "newPassword": "x", "newPasswordConfirm": "x",
        "newRole": "admin"})
    assert r.status_code == 403
    assert user.query.filter_by(username="evil").first() is None


def test_non_admin_blocked_from_admin_routes(app, standard_client):
    assert standard_client.post("/updateConfig", data={}).status_code == 403
    assert standard_client.post("/rescanSSIDs").status_code == 403
    assert standard_client.post("/manualCron/1", data={"schedule": "@daily"}).status_code == 403
    assert standard_client.post("/createCron/1").status_code == 403
    assert standard_client.post("/makeguest/1").status_code == 403


def test_admin_can_create_users(app, admin_client):
    r = admin_client.post("/users/add", data={
        "newUsername": "new", "newPassword": "x", "newPasswordConfirm": "x",
        "newRole": "admin"})
    assert r.status_code == 302
    assert user.query.filter_by(username="new").first().admin


def test_anonymous_cannot_create_users_once_one_exists(app, client):
    make_user("boss")
    r = client.post("/users/add", data={"newUsername": "evil", "newPassword": "x"},
                    headers={"Referer": "http://localhost/initApp"})
    assert r.status_code == 401
    assert user.query.count() == 1


# --- First-run setup -----------------------------------------------------

def test_setup_requires_visiting_initapp(client):
    r = client.post("/users/add", data={"newUsername": "a", "newPassword": "x", "setupToken": TOKEN})
    assert r.status_code == 401
    assert user.query.count() == 0


def test_setup_privileges_bound_to_creating_session(app):
    a, b = app.test_client(), app.test_client()
    a.get("/initApp")
    b.get("/initApp")  # attacker also arrives before setup finishes
    r = a.post("/users/add", data={"newUsername": "admin", "newPassword": "x", "setupToken": TOKEN})
    assert r.get_json() == {"message": "Success"}
    assert user.query.one().admin

    # session B can no longer create users or touch config
    assert b.post("/users/add", data={"newUsername": "evil", "newPassword": "x"}).status_code == 401
    assert b.post("/newConfig", data={}, headers={"Referer": "/initApp"}).status_code == 401
    assert b.get("/init").status_code == 401
    # session A still can
    assert a.post("/newConfig", data={}).status_code != 401


def test_setup_privileges_cleared_after_init(app, monkeypatch):
    import app.routes.setup as setup
    monkeypatch.setattr(setup, "getConfig", lambda: {"apiType": "unifi"})
    monkeypatch.setattr(setup.time, "sleep", lambda s: None)
    monkeypatch.setattr(setup.UNIFI, "initDBinfo", staticmethod(lambda: True))
    a = app.test_client()
    a.get("/initApp")
    a.post("/users/add", data={"newUsername": "admin", "newPassword": "x", "setupToken": TOKEN})
    assert a.get("/init").get_json()["message"] == "Success"
    assert a.get("/init").status_code == 401  # flag gone; not logged in


def test_setup_requires_valid_token(app):
    a = app.test_client()
    a.get("/initApp")
    for token in (None, "", "wrong"):
        data = {"newUsername": "admin", "newPassword": "x"}
        if token is not None:
            data["setupToken"] = token
        assert a.post("/users/add", data=data).status_code == 403
    assert user.query.count() == 0
    r = a.post("/users/add", data={"newUsername": "admin", "newPassword": "x", "setupToken": TOKEN})
    assert r.get_json() == {"message": "Success"}


def test_generated_setup_token_is_stored_and_cleared(tmp_path, monkeypatch):
    monkeypatch.delenv("SETUP_TOKEN", raising=False)
    from app import create_app, db
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://",
                      "WTF_CSRF_ENABLED": False, "RATELIMIT_ENABLED": False,
                      "QR_DIR": str(tmp_path)})
    app.instance_path = str(tmp_path / "inst")
    with app.app_context():
        db.create_all()
        c = app.test_client()
        c.get("/initApp")
        token = (tmp_path / "inst" / "setup_token").read_text()
        assert len(token) >= 16
        r = c.post("/users/add", data={"newUsername": "a", "newPassword": "x", "setupToken": token})
        assert r.get_json() == {"message": "Success"}
        assert not (tmp_path / "inst" / "setup_token").exists()


# --- State-changing routes are POST-only -----------------------------------

@pytest.mark.parametrize("path", ["/changepw/1", "/makeguest/1", "/rescanSSIDs",
                                  "/createCron/1?rotateFrequency=@daily", "/logout"])
def test_state_changing_routes_reject_get(app, admin_client, path):
    make_ssid("Home", "abc")
    assert admin_client.get(path).status_code == 405


def test_logout_via_post(app, admin_client):
    assert admin_client.post("/logout").status_code == 302
    assert admin_client.get("/admin").status_code == 302  # back to login


def test_state_changing_post_requires_csrf(app):
    app.config["WTF_CSRF_ENABLED"] = True
    make_user("boss")
    c = app.test_client()
    login_page = c.get("/login")
    assert login_page.status_code == 200
    # No CSRF token -> rejected before reaching the view
    assert c.post("/rescanSSIDs").status_code == 400
    assert c.post("/logout").status_code == 400


def test_admin_page_posts_state_changes_with_csrf(app, admin_client, monkeypatch):
    import re
    import app.routes.admin as admin
    monkeypatch.setattr(admin, "getConfig", lambda: {
        "apiType": "unifi", "controllerIp": "1.2.3.4",
        "apiUser": {"userName": None, "passWord": None, "apiKey": None}})
    make_ssid("Home", "abc")
    html = admin_client.get("/admin").get_data(as_text=True)
    assert 'name="csrf-token"' in html
    links = re.findall(r'<a [^>]*href="(/(?:logout|rescanSSIDs|makeguest|createCron|changepw)[^"]*)"[^>]*>', html)
    assert links
    for tag in re.findall(r'<a [^>]*href="/(?:logout|rescanSSIDs|makeguest|createCron|changepw)[^>]*>', html):
        assert "data-post" in tag, tag

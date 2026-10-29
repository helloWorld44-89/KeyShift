import pytest
from app import db
from app.models import SSID, PasswordListEntry
from app.settings import savePolicy
from app.utilities.passwordPolicy import PasswordPolicy
import app.rotation as rotation
import app.passwordList as pl
from conftest import make_ssid

PWS = ["alpha-pass-1", "bravo-pass-2", "charlie-pass-3"]


@pytest.fixture
def controller(monkeypatch):
    """Records passwords sent to the controller; set .ok to make it fail."""
    class C:
        ok = True
        sent = []
    c = C()
    c.sent = []

    def change(ssid, pw):
        c.sent.append(pw)
        return True if c.ok else "boom"
    monkeypatch.setattr(rotation, "_controllerChange", change)
    monkeypatch.setattr(rotation, "genQRCode", lambda s: None)
    monkeypatch.setattr(pl, "deleteCron", lambda s: c.sent.append("CRON-DELETED"))
    return c


def listed(passwords=PWS, mode="sequential", onEnd="restart", enabled=True):
    s = make_ssid("Home", "a")
    for i, p in enumerate(passwords):
        db.session.add(PasswordListEntry(ssid_id=s.id, password=p, position=i))
    s.listEnabled, s.listMode, s.listOnEnd = enabled, mode, onEnd
    s.listIndex = 0
    s.pwRotate, s.rotateFrequency = True, "@daily"
    db.session.commit()
    return s


def rotate_n(s, n):
    for _ in range(n):
        pl.rotateFromList(s, attempts=1)


# --- picking ---------------------------------------------------------------

def test_sequential_order_and_wraparound(app, controller):
    s = listed()
    rotate_n(s, 7)
    assert controller.sent == PWS + PWS + [PWS[0]]
    assert s.ssidPW == PWS[0] and s.pwRotate is True


def test_stop_at_end(app, controller):
    s = listed(onEnd="stop")
    rotate_n(s, 3)
    assert controller.sent == PWS + ["CRON-DELETED"]
    assert s.ssidPW == PWS[-1]          # the last password stays active
    assert s.pwRotate is False and s.rotateFrequency is None
    assert pl.isFinished(s)
    with pytest.raises(pl.ListUnavailable):
        pl.rotateFromList(s, attempts=1)
    assert s.ssidPW == PWS[-1]


def test_scheduled_run_on_finished_list_stops_rotation(app, controller, monkeypatch):
    s = listed(onEnd="restart")
    s.listIndex = 3                      # ran past the end, then the admin chose "stop"
    s.listOnEnd = "stop"
    db.session.commit()
    monkeypatch.setattr(rotation, "alert", lambda m: controller.sent.append("ALERT"))
    monkeypatch.setattr(pl, "alert", rotation.alert)
    assert pl.rotateScheduled(s) is None
    assert s.pwRotate is False
    assert "CRON-DELETED" in controller.sent and controller.sent.count(PWS[0]) == 0


def test_failed_controller_call_does_not_skip_an_entry(app, controller):
    s = listed()
    controller.ok = False
    assert pl.rotateFromList(s, attempts=1).ok is False
    assert s.listIndex == 0 and s.failCount == 1 and s.pendingPW == PWS[0]
    controller.ok = True
    assert pl.rotateFromList(s, attempts=1).ok
    assert controller.sent == [PWS[0], PWS[0]]
    assert (s.listIndex, s.ssidPW, s.pendingPW) == (1, PWS[0], None)


def test_random_modes_use_only_list_entries(app, controller):
    s = listed(mode="random")
    rotate_n(s, 30)
    assert set(controller.sent) <= set(PWS)
    assert len(set(controller.sent)) > 1


def test_random_norepeat_never_repeats_back_to_back(app, controller):
    s = listed(mode="random-norepeat")
    rotate_n(s, 60)
    assert all(a != b for a, b in zip(controller.sent, controller.sent[1:]))


def test_random_norepeat_single_entry_still_works(app, controller):
    s = listed(["only-one-pw1"], mode="random-norepeat")
    rotate_n(s, 3)
    assert controller.sent == ["only-one-pw1"] * 3


def test_failed_random_attempt_retries_the_same_entry(app, controller):
    s = listed(mode="random")
    controller.ok = False
    pl.rotateFromList(s, attempts=1)
    first = controller.sent[0]
    controller.ok = True
    pl.rotateFromList(s, attempts=1)
    assert controller.sent[1] == first


def test_empty_list_raises(app, controller):
    s = listed([])
    with pytest.raises(pl.ListUnavailable):
        pl.rotateFromList(s)
    assert controller.sent == []


def test_scheduled_uses_generator_when_list_off(app, controller):
    s = listed(enabled=False)
    pl.rotateScheduled(s, attempts=1)
    assert controller.sent and controller.sent[0] not in PWS and len(controller.sent[0]) == 40


def test_scheduled_empty_list_skips_and_alerts(app, controller, monkeypatch):
    alerts = []
    monkeypatch.setattr(pl, "alert", alerts.append)
    s = listed([])
    assert pl.rotateScheduled(s) is None
    assert controller.sent == [] and alerts and "empty" in alerts[0]


def test_entries_are_encrypted_at_rest(app):
    s = listed()
    raw = db.session.execute(db.text("SELECT password FROM ssid_passwords")).scalars().all()
    assert len(raw) == 3 and all(r.startswith("enc:v1:") for r in raw)


# --- routes ----------------------------------------------------------------

def url(s, tail=""):
    return f"/ssid/{s.id}/passwords{tail}"


def test_add_view_and_bulk_import(app, admin_client):
    s = make_ssid("Home", "a")
    r = admin_client.post(url(s, "/add"), data={"passwords": "alpha-pass-1\r\n\nbravo-pass-2\n"})
    d = r.get_json()
    assert r.status_code == 200 and [e["password"] for e in d["entries"]] == ["alpha-pass-1", "bravo-pass-2"]
    assert [e["position"] for e in d["entries"]] == [1, 2]
    got = admin_client.get(url(s)).get_json()
    assert len(got["entries"]) == 2 and got["enabled"] is False


def test_add_validates_every_line_and_adds_nothing_on_error(app, admin_client):
    s = make_ssid("Home", "a")
    r = admin_client.post(url(s, "/add"), data={"passwords": "good-password\nshort"})
    assert r.status_code == 400 and "Line 2" in r.get_json()["message"]
    assert PasswordListEntry.query.count() == 0


def test_add_applies_policy_when_enforced(app, admin_client):
    savePolicy(PasswordPolicy(enforceManual=True))
    s = make_ssid("Home", "a")
    assert admin_client.post(url(s, "/add"), data={"passwords": "alllowercase1"}).status_code == 400
    assert admin_client.post(url(s, "/add"), data={"passwords": "Abcdef1!xyz"}).status_code == 200


def test_add_requires_input_and_respects_cap(app, admin_client, monkeypatch):
    s = make_ssid("Home", "a")
    assert admin_client.post(url(s, "/add"), data={"passwords": "  \n"}).status_code == 400
    monkeypatch.setattr("app.routes.passwordLists.MAX_ENTRIES", 2)
    assert admin_client.post(url(s, "/add"), data={"passwords": "\n".join(PWS)}).status_code == 400


def test_same_password_allowed_on_two_ssids(app, admin_client):
    a, b = make_ssid("A", "a"), make_ssid("B", "b")
    for s in (a, b):
        assert admin_client.post(url(s, "/add"), data={"passwords": "shared-pass-1"}).status_code == 200


def test_delete_adjusts_index_and_positions(app, admin_client):
    s = listed()
    s.listIndex = 2
    db.session.commit()
    first = s.entries[0].id
    d = admin_client.post(url(s, f"/{first}/delete")).get_json()
    assert [e["password"] for e in d["entries"]] == PWS[1:] and [e["position"] for e in d["entries"]] == [1, 2]
    assert d["index"] == 1
    assert admin_client.post(url(s, "/999/delete")).status_code == 404


def test_delete_current_entry_clears_marker(app, admin_client, controller):
    s = listed()
    pl.rotateFromList(s, attempts=1)
    cur = s.listCurrentId
    d = admin_client.post(url(s, f"/{cur}/delete")).get_json()
    assert not any(e["current"] for e in d["entries"])


def test_move_entries(app, admin_client):
    s = listed()
    ids = [e.id for e in s.entries]
    d = admin_client.post(url(s, f"/{ids[2]}/move"), data={"direction": "up"}).get_json()
    assert [e["password"] for e in d["entries"]] == [PWS[0], PWS[2], PWS[1]]
    d = admin_client.post(url(s, f"/{ids[0]}/move"), data={"direction": "up"}).get_json()  # already first
    assert [e["password"] for e in d["entries"]][0] == PWS[0]
    assert admin_client.post(url(s, f"/{ids[0]}/move"), data={"direction": "left"}).status_code == 400


def test_settings_validation(app, admin_client):
    s = make_ssid("Home", "a")
    assert admin_client.post(url(s, "/settings"), data={"enabled": "1"}).status_code == 400  # empty list
    admin_client.post(url(s, "/add"), data={"passwords": "alpha-pass-1"})
    assert admin_client.post(url(s, "/settings"), data={"mode": "bogus"}).status_code == 400
    d = admin_client.post(url(s, "/settings"), data={"enabled": "1", "mode": "random", "onEnd": "stop"}).get_json()
    assert (d["enabled"], d["mode"], d["onEnd"]) == (True, "random", "stop")


def test_reset(app, admin_client, controller):
    s = listed(onEnd="stop")
    rotate_n(s, 3)
    d = admin_client.post(url(s, "/reset")).get_json()
    assert d["index"] == 0 and d["finished"] is False and not any(e["current"] for e in d["entries"])


def test_state_is_no_store(app, admin_client):
    s = listed()
    assert admin_client.get(url(s)).headers["Cache-Control"] == "no-store"


def test_standard_user_and_anonymous_blocked(app, standard_client):
    s = listed()
    for method, tail in (("get", ""), ("post", "/add"), ("post", "/settings"), ("post", "/reset"),
                         ("post", f"/{s.entries[0].id}/delete")):
        r = getattr(standard_client, method)(url(s, tail), data={"passwords": "zzzzzzzz1"})
        assert r.status_code == 403, tail
    assert PasswordListEntry.query.count() == 3
    assert b"alpha-pass-1" not in standard_client.get(url(s)).data


def test_anonymous_blocked(app, client):
    s = listed()
    r = client.get(url(s))
    assert r.status_code in (302, 401) and b"alpha-pass-1" not in r.data


def test_csrf_required(app):
    from conftest import make_user
    app.config["WTF_CSRF_ENABLED"] = True
    make_user("boss")
    s = listed()
    c = app.test_client()
    c.get("/login")
    assert c.post(url(s, "/add"), data={"passwords": "zzzzzzzz1"}).status_code == 400


# --- manual change ----------------------------------------------------------

def test_manual_change_pw_uses_list(app, admin_client, controller):
    s = listed()
    assert admin_client.post(f"/changepw/{s.id}").status_code == 302
    assert controller.sent == [PWS[0]] and s.listIndex == 1


def test_manual_typed_password_bypasses_list(app, admin_client, controller):
    s = listed()
    assert admin_client.post(f"/changepw/{s.id}", data={"pw": "typed-by-hand-1"}).status_code == 302
    assert controller.sent == ["typed-by-hand-1"] and s.listIndex == 0


def test_manual_change_on_used_up_list_is_409(app, admin_client, controller):
    s = listed(onEnd="stop")
    rotate_n(s, 3)
    controller.sent.clear()
    r = admin_client.post(f"/changepw/{s.id}")
    assert r.status_code == 409 and "used up" in r.get_json()["message"]
    assert controller.sent == []


# --- UI --------------------------------------------------------------------

def test_admin_page_has_list_button_only_for_admins(app, admin_client, monkeypatch):
    import app.routes.admin as admin
    monkeypatch.setattr(admin, "getConfig", lambda: {
        "apiType": "unifi", "controllerIp": "1.2.3.4",
        "apiUser": {"userName": None, "passWord": None, "apiKey": None}})
    s = listed()
    html = admin_client.get("/admin").get_data(as_text=True)
    assert 'id="passwordListModal"' in html and "List (3)" in html
    assert "alpha-pass-1" not in html


def test_standard_user_page_has_no_list_ui(app, standard_client, monkeypatch):
    import app.routes.admin as admin
    monkeypatch.setattr(admin, "getConfig", lambda: {
        "apiType": "unifi", "controllerIp": "1.2.3.4",
        "apiUser": {"userName": None, "passWord": None, "apiKey": None}})
    listed()
    html = standard_client.get("/admin").get_data(as_text=True)
    assert "passwordListModal" not in html and "pl-open" not in html
    assert "alpha-pass-1" not in html

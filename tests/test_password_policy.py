import string
import pytest
from app import db
from app.models import Setting, SSID
from app.settings import getPolicy, savePolicy
from app.utilities.genPW import genPW
from app.utilities.passwordPolicy import (PasswordPolicy, generate, validatePolicy, checkPassword,
                                          entropyBits, LOOKALIKES)
from conftest import make_ssid


def classes(pw):
    return (any(c.islower() for c in pw), any(c.isupper() for c in pw),
            any(c.isdigit() for c in pw), any(c in string.punctuation for c in pw))


def test_default_matches_original_generator():
    p = PasswordPolicy()
    assert (p.length, p.symbolSet) == (40, string.punctuation)
    for _ in range(50):
        pw = genPW()
        assert len(pw) == 40 and all(classes(pw))


@pytest.mark.parametrize("length", [8, 12, 40, 63])
def test_length_respected(length):
    assert len(generate(PasswordPolicy(length=length))) == length


def test_min_per_class_always_met():
    p = PasswordPolicy(length=12, minPerClass=3)
    for _ in range(200):
        pw = generate(p)
        assert sum(c.isupper() for c in pw) >= 3
        assert sum(c.islower() for c in pw) >= 3
        assert sum(c.isdigit() for c in pw) >= 3
        assert sum(c in string.punctuation for c in pw) >= 3


def test_disabled_classes_absent():
    p = PasswordPolicy(length=30, symbols=False, upper=False)
    for _ in range(50):
        pw = generate(p)
        assert not any(c.isupper() or c in string.punctuation for c in pw)


def test_custom_symbol_set_and_lookalikes():
    p = PasswordPolicy(length=40, symbolSet="!@#", excludeLookalikes=True)
    for _ in range(50):
        pw = generate(p)
        assert not set(pw) & set(LOOKALIKES)
        assert set(pw) - set(string.ascii_letters + string.digits) <= set("!@#")


def test_digits_only_policy():
    pw = generate(PasswordPolicy(length=10, upper=False, lower=False, symbols=False))
    assert pw.isdigit() and len(pw) == 10


def test_generation_is_random():
    assert len({generate(PasswordPolicy()) for _ in range(20)}) == 20


@pytest.mark.parametrize("kwargs", [
    {"length": 7}, {"length": 64}, {"length": "x"},
    {"upper": False, "lower": False, "digits": False, "symbols": False},
    {"length": 8, "minPerClass": 3},
    {"symbols": True, "symbolSet": ""},
    {"symbolSet": "ab"}, {"symbolSet": "! "}, {"minPerClass": -1},
])
def test_unsatisfiable_or_bad_policies_rejected(kwargs):
    p = PasswordPolicy(**kwargs)
    assert validatePolicy(p)
    with pytest.raises(ValueError):
        generate(p)


def test_symbols_off_ignores_empty_symbol_set():
    assert not validatePolicy(PasswordPolicy(symbols=False, symbolSet=""))


def test_entropy_estimate():
    assert entropyBits(PasswordPolicy(length=10, upper=False, lower=False, symbols=False)) == 33.2
    assert entropyBits(PasswordPolicy()) > 240


# --- manual passwords ------------------------------------------------------

def test_manual_wpa_limits_always_apply():
    assert checkPassword("short")
    assert checkPassword("x" * 64)
    assert checkPassword("passwordéok")
    assert not checkPassword("justlowercase")


def test_manual_class_rules_only_when_enforced():
    assert not checkPassword("justlowercase", PasswordPolicy())
    errs = checkPassword("justlowercase", PasswordPolicy(enforceManual=True))
    assert errs and "upper" in " ".join(errs)
    assert not checkPassword("Abcdef1!xyz", PasswordPolicy(enforceManual=True))


# --- storage ---------------------------------------------------------------

def test_policy_roundtrip_and_default(app):
    assert getPolicy() == PasswordPolicy()
    savePolicy(PasswordPolicy(length=20, symbols=False))
    got = getPolicy()
    assert got.length == 20 and got.symbols is False
    savePolicy(PasswordPolicy(length=21))
    assert getPolicy().length == 21 and Setting.query.count() == 1


def test_corrupt_stored_policy_falls_back(app):
    db.session.add(Setting(key="passwordPolicy", value="{not json"))
    db.session.commit()
    assert getPolicy() == PasswordPolicy()
    Setting.query.one().value = '{"length": 3}'
    db.session.commit()
    assert getPolicy() == PasswordPolicy()


def test_rotation_uses_saved_policy(app, monkeypatch):
    import app.rotation as rotation
    monkeypatch.setattr(rotation, "_controllerChange", lambda s, pw: True)
    monkeypatch.setattr(rotation, "genQRCode", lambda s: None)
    savePolicy(PasswordPolicy(length=16, symbols=False))
    s = make_ssid("Home", "a")
    assert rotation.rotate(s).ok
    assert len(s.ssidPW) == 16 and s.ssidPW.isalnum()


# --- routes ----------------------------------------------------------------

FORM = {"length": "20", "minPerClass": "2", "symbolSet": "!@#", "upper": "on", "lower": "on",
        "digits": "on", "symbols": "on", "excludeLookalikes": "on"}


def test_admin_saves_policy(app, admin_client):
    r = admin_client.post("/admin/passwordPolicy", data=FORM)
    assert r.status_code == 302
    p = getPolicy()
    assert (p.length, p.minPerClass, p.symbolSet, p.excludeLookalikes, p.enforceManual) == (20, 2, "!@#", True, False)


def test_unchecked_boxes_turn_classes_off(app, admin_client):
    admin_client.post("/admin/passwordPolicy", data={"length": "12", "minPerClass": "1", "lower": "on", "digits": "on"})
    p = getPolicy()
    assert (p.upper, p.symbols, p.lower) == (False, False, True)


def test_invalid_policy_rejected_and_not_saved(app, admin_client):
    r = admin_client.post("/admin/passwordPolicy", data={**FORM, "length": "4"})
    assert r.status_code == 400 and "Length" in r.get_json()["message"]
    assert getPolicy() == PasswordPolicy()
    assert admin_client.post("/admin/passwordPolicy", data={**FORM, "length": "abc"}).status_code in (302, 400)


def test_standard_user_cannot_change_or_preview(app, standard_client):
    assert standard_client.post("/admin/passwordPolicy", data=FORM).status_code == 403
    assert standard_client.post("/admin/passwordPolicy/preview", data=FORM).status_code == 403
    assert getPolicy() == PasswordPolicy()


def test_preview_returns_sample_without_saving(app, admin_client):
    r = admin_client.post("/admin/passwordPolicy/preview", data=FORM)
    d = r.get_json()
    assert r.status_code == 200 and len(d["sample"]) == 20 and d["bits"] > 0
    assert r.headers["Cache-Control"] == "no-store"
    assert Setting.query.count() == 0


def test_preview_reports_errors(app, admin_client):
    r = admin_client.post("/admin/passwordPolicy/preview", data={**FORM, "length": "8", "minPerClass": "5"})
    assert r.status_code == 400 and r.get_json()["errors"]


def test_changepw_rejects_bad_manual_password(app, admin_client, monkeypatch):
    import app.rotation as rotation
    called = []
    monkeypatch.setattr(rotation, "_controllerChange", lambda s, pw: called.append(pw) or True)
    s = make_ssid("Home", "a")
    r = admin_client.post(f"/changepw/{s.id}", data={"pw": "short"})
    assert r.status_code == 400 and "8 to 63" in r.get_json()["message"]
    assert not called


def test_changepw_enforces_class_rules_when_on(app, admin_client, monkeypatch):
    import app.rotation as rotation
    monkeypatch.setattr(rotation, "_controllerChange", lambda s, pw: True)
    monkeypatch.setattr(rotation, "genQRCode", lambda s: None)
    savePolicy(PasswordPolicy(enforceManual=True))
    s = make_ssid("Home", "a")
    assert admin_client.post(f"/changepw/{s.id}", data={"pw": "alllowercase"}).status_code == 400
    assert admin_client.post(f"/changepw/{s.id}", data={"pw": "Abcdef1!xyz"}).status_code == 302


def test_settings_tab_shows_policy_to_admin_only(app, admin_client, monkeypatch):
    import app.routes.admin as admin
    monkeypatch.setattr(admin, "getConfig", lambda: {
        "apiType": "unifi", "controllerIp": "1.2.3.4",
        "apiUser": {"userName": None, "passWord": None, "apiKey": None}})
    assert 'id="policyForm"' in admin_client.get("/admin?tab=settings").get_data(as_text=True)

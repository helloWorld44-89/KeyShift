import pytest

from app import db
from app.models import SSID
from conftest import make_ssid


@pytest.fixture
def crontab(tmp_path, monkeypatch):
    import app.config.crontab as ct
    f = tmp_path / "qrCron"
    f.write_text("")
    monkeypatch.setattr(ct, "filePath", str(f))
    return f


def found(name, ssid_id, **kw):
    return SSID(ssidName=name, ssidPW="controller-pw", siteID="site2", wlanGroupID="g2",
                ssidID=ssid_id, **kw)


# --- SSID.upsert / rescan (#7) -------------------------------------------

def test_upsert_keeps_local_state(app):
    s = make_ssid("Old", "abc", guest=True)
    s.pwRotate, s.rotateFrequency = True, "@daily"
    db.session.commit()

    assert SSID.upsert(found("Renamed", "abc")) is False
    db.session.commit()

    s = SSID.query.one()
    assert (s.ssidName, s.siteID, s.wlanGroupID) == ("Renamed", "site2", "g2")
    assert (s.ssidPW, s.isGuest, s.pwRotate, s.rotateFrequency) == ("p;w", True, True, "@daily")


def test_upsert_adds_new(app):
    assert SSID.upsert(found("New", "xyz")) is True
    db.session.commit()
    assert SSID.query.count() == 1


def test_rescan_preserves_rotation_and_guest(app, admin_client, monkeypatch):
    import app.routes.admin as admin
    s = make_ssid("Guest", "abc", guest=True)
    s.pwRotate, s.rotateFrequency = True, "@weekly"
    db.session.commit()

    def fake_init():
        SSID.upsert(found("Guest", "abc"))
        SSID.upsert(found("Other", "def"))
        db.session.commit()
        return True

    monkeypatch.setattr(admin, "getConfig", lambda: {"apiType": "unifi"})
    monkeypatch.setattr(admin.unifi.UNIFI, "initDBinfo", staticmethod(fake_init))
    r = admin_client.get("/rescanSSIDs", headers={"Referer": "/admin"})
    assert r.status_code == 302
    assert SSID.query.count() == 2
    g = SSID.query.filter_by(ssidID="abc").one()
    assert g.isGuest and g.pwRotate and g.rotateFrequency == "@weekly"


def test_rescan_controller_failure_keeps_ssids(app, admin_client, monkeypatch):
    import app.routes.admin as admin
    make_ssid("Guest", "abc")
    monkeypatch.setattr(admin, "getConfig", lambda: {"apiType": "omada"})
    monkeypatch.setattr(admin.omada.OMADA, "initDBinfo", staticmethod(lambda: False))
    assert admin_client.get("/rescanSSIDs").status_code == 502
    assert SSID.query.count() == 1


# --- /createCron (#13) ---------------------------------------------------

def test_createcron_first_create_uses_requested_frequency(app, admin_client, crontab):
    s = make_ssid("Home", "abc")
    r = admin_client.get(f"/createCron/{s.id}?rotateFrequency=@daily")
    assert r.status_code == 302
    s = db.session.get(SSID, s.id)
    assert s.pwRotate and s.rotateFrequency == "@daily"
    text = crontab.read_text()
    assert "@daily" in text and f"app.ssid {s.id}" in text and "# Home" in text


def test_createcron_change_updates_existing_job(app, admin_client, crontab):
    s = make_ssid("Home", "abc")
    admin_client.get(f"/createCron/{s.id}?rotateFrequency=@daily")
    admin_client.get(f"/createCron/{s.id}?rotateFrequency=@weekly")
    text = crontab.read_text()
    assert text.count("app.ssid") == 1 and "@weekly" in text and "@daily" not in text


def test_createcron_none_removes_job(app, admin_client, crontab):
    s = make_ssid("Home", "abc")
    admin_client.get(f"/createCron/{s.id}?rotateFrequency=@daily")
    admin_client.get(f"/createCron/{s.id}?rotateFrequency=None")
    s = db.session.get(SSID, s.id)
    assert not s.pwRotate and s.rotateFrequency is None
    assert "app.ssid" not in crontab.read_text()


@pytest.mark.parametrize("bad", [None, "", "garbage", "* * *"])
def test_createcron_rejects_invalid_frequency(app, admin_client, crontab, bad):
    s = make_ssid("Home", "abc")
    url = f"/createCron/{s.id}" + (f"?rotateFrequency={bad}" if bad is not None else "")
    assert admin_client.get(url).status_code == 400
    assert not db.session.get(SSID, s.id).pwRotate
    assert "app.ssid" not in crontab.read_text()


def test_createcron_unknown_ssid_404(app, admin_client, crontab):
    assert admin_client.get("/createCron/999?rotateFrequency=@daily").status_code == 404

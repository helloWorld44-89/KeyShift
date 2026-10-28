import json
import os
import stat

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import text

from app import crypto, db
from app.config import config as cfg
from app.models import SSID
from conftest import make_ssid


# --- app.crypto -------------------------------------------------------------

def test_round_trip_and_prefix(app):
    token = crypto.encrypt("p;w:1")
    assert token.startswith("enc:v1:") and "p;w:1" not in token
    assert crypto.decrypt(token) == "p;w:1"
    assert crypto.encrypt(token) == token          # never double-encrypted


def test_empty_and_legacy_plaintext_pass_through(app):
    assert crypto.encrypt(None) is None and crypto.encrypt("") == ""
    assert crypto.decrypt("old-plaintext") == "old-plaintext"
    assert crypto.decrypt(None) is None


def test_wrong_key_raises_instead_of_returning_ciphertext(app):
    token = crypto.encrypt("secret")
    app.config["ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    with pytest.raises(crypto.DecryptionError):
        crypto.decrypt(token)


def test_key_rotation_with_several_keys(app):
    old = app.config["ENCRYPTION_KEY"]
    token = crypto.encrypt("secret")
    new = Fernet.generate_key().decode()
    app.config["ENCRYPTION_KEY"] = f"{new},{old}"   # new key first: encrypts; old still decrypts
    assert crypto.decrypt(token) == "secret"
    assert crypto.decrypt(crypto.encrypt("again")) == "again"
    app.config["ENCRYPTION_KEY"] = new
    with pytest.raises(crypto.DecryptionError):
        crypto.decrypt(token)


def test_invalid_key_gives_clear_error(app):
    app.config["ENCRYPTION_KEY"] = "not-a-fernet-key"
    with pytest.raises(ValueError, match="Fernet"):
        crypto.encrypt("x")


def test_generated_keyfile_is_private_and_reused(app, tmp_path):
    app.config["ENCRYPTION_KEY"] = None
    app.instance_path = str(tmp_path / "inst")
    os.environ.pop("ENCRYPTION_KEY", None)
    token = crypto.encrypt("secret")
    keyfile = tmp_path / "inst" / "encryption.key"
    assert stat.S_IMODE(keyfile.stat().st_mode) == 0o600
    first = keyfile.read_text()
    assert crypto.decrypt(token) == "secret"
    assert keyfile.read_text() == first             # second use doesn't regenerate it
    assert not list((tmp_path / "inst").glob("*.tmp"))


# --- database --------------------------------------------------------------

def test_wifi_password_is_encrypted_at_rest_but_plain_in_python(app):
    make_ssid("Home", "abc")
    raw = db.session.execute(text("SELECT ssidPW FROM ssids")).scalar()
    assert raw.startswith("enc:v1:") and "p;w" not in raw
    db.session.expire_all()
    assert SSID.query.one().ssidPW == "p;w"


def test_qr_encodes_the_decrypted_password(app):
    from app.utilities.genQR import genQRCode, qrPath
    ssid = make_ssid("Home", "abc")
    genQRCode(ssid)
    assert os.path.exists(qrPath(ssid))


# --- config.json ---------------------------------------------------------

@pytest.fixture
def config_file(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    monkeypatch.setattr(cfg, "CONFIG_PATH", str(path))
    return path


def sample():
    return {"apiType": "omada", "controllerIp": "1.2.3.4",
            "apiUser": {"userName": "admin", "passWord": "hunter2", "apiKey": "key-123"}}


def test_update_config_encrypts_secrets_on_disk(app, config_file):
    cfg.updateConfig(sample())
    on_disk = json.loads(config_file.read_text())
    assert on_disk["apiUser"]["passWord"].startswith("enc:v1:")
    assert on_disk["apiUser"]["apiKey"].startswith("enc:v1:")
    assert on_disk["apiUser"]["userName"] == "admin" and on_disk["controllerIp"] == "1.2.3.4"
    assert "hunter2" not in config_file.read_text()
    assert stat.S_IMODE(config_file.stat().st_mode) == 0o600
    assert cfg.getConfig() == sample()


def test_unset_secrets_stay_unset(app, config_file):
    data = sample()
    data["apiUser"]["apiKey"] = None
    cfg.updateConfig(data)
    assert json.loads(config_file.read_text())["apiUser"]["apiKey"] is None
    assert cfg.getConfig()["apiUser"]["apiKey"] is None


def test_legacy_plaintext_config_is_encrypted_once(app, config_file):
    config_file.write_text(json.dumps(sample()))
    assert cfg.getConfig() == sample()              # plaintext still readable
    assert cfg.encryptConfigSecrets() is True
    assert "hunter2" not in config_file.read_text()
    assert cfg.getConfig() == sample()
    assert cfg.encryptConfigSecrets() is False      # nothing left to do


def test_missing_config_is_not_an_error(app, config_file):
    assert cfg.encryptConfigSecrets() is False


def test_update_pw_does_not_leak_decrypted_secrets(app, config_file):
    data = sample()
    data["wifiInfo"] = {"password": "old"}
    cfg.updateConfig(data)
    cfg.updatePW("new-wifi-pw")
    text_on_disk = config_file.read_text()
    assert "hunter2" not in text_on_disk and "new-wifi-pw" not in text_on_disk
    assert cfg.getConfig()["wifiInfo"]["password"] == "new-wifi-pw"

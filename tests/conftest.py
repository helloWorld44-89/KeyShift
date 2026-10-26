import os
import pytest

os.environ.setdefault("SECRET_KEY", "test-secret")

from app import create_app, db
from app.models import user, SSID


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "WTF_CSRF_ENABLED": False,
        "RATELIMIT_ENABLED": False,
        "QR_DIR": str(tmp_path),
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def make_user(name, pw="pw", admin=1):
    user.newUser(name, pw, admin)


def login(client, name, pw="pw"):
    return client.post("/login", data={"username": name, "password": pw})


@pytest.fixture
def admin_client(app, client):
    make_user("boss", admin=1)
    login(client, "boss")
    return client


@pytest.fixture
def standard_client(app, client):
    make_user("boss", admin=1)  # login() redirects to setup when no users exist
    make_user("joe", admin=0)
    login(client, "joe")
    return client


def make_ssid(name, ssid_id, guest=False):
    s = SSID(ssidName=name, ssidPW="p;w", siteID="s", wlanGroupID=None,
             ssidID=ssid_id, isGuest=guest)
    db.session.add(s)
    db.session.commit()
    return s

import pytest

from app import create_app, db, limiter
from conftest import make_user


def build(tmp_path, **cfg):
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://",
                      "WTF_CSRF_ENABLED": False, "RATELIMIT_ENABLED": True,
                      "QR_DIR": str(tmp_path), "SETUP_TOKEN": "t", **cfg})
    return app


@pytest.fixture
def ctx(tmp_path):
    def make(**cfg):
        app = build(tmp_path, **cfg)
        app.app_context().push()
        db.create_all()
        limiter.reset()
        make_user("boss")
        return app
    yield make
    limiter.reset()
    db.session.remove()
    db.drop_all()


def login_attempts(client, n, **kw):
    return [client.post("/login", data={"username": "boss", "password": "bad"}, **kw).status_code
            for _ in range(n)]


def test_static_files_are_not_rate_limited(ctx):
    app = ctx()
    c = app.test_client()
    assert {c.get("/static/img/KeyShift.png").status_code for _ in range(30)} == {200}


def test_without_trusted_proxy_forwarded_for_is_ignored(ctx):
    app = ctx()
    c = app.test_client()
    codes = [c.post("/login", data={"username": "boss", "password": "bad"},
                    headers={"X-Forwarded-For": f"10.0.0.{i}"}).status_code for i in range(7)]
    assert codes[-1] == 429  # spoofing the header doesn't dodge the limit


def test_trusted_proxy_limits_per_client(ctx):
    app = ctx(TRUSTED_PROXY_COUNT=1)
    c = app.test_client()
    a = login_attempts(c, 6, headers={"X-Forwarded-For": "10.0.0.1"})
    assert a[-1] == 429
    # a different client behind the same proxy is unaffected
    assert login_attempts(c, 1, headers={"X-Forwarded-For": "10.0.0.2"}) == [200]

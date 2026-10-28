import logging

import pytest

from app.logging_config import addFileHandler, logFilePath
from app.utilities.logTail import readLog, MAX_BYTES
from conftest import make_user

SAMPLE = (
    "[2026-10-28 10:00:00,000] INFO in app: started\n"
    "[2026-10-28 10:00:01,000] WARNING in app.rotation: retrying Home\n"
    "[2026-10-28 10:00:02,000] ERROR in rotation: change failed\n"
    "Traceback (most recent call last):\n"
    "  File \"x.py\", line 1, in <module>\n"
    "ValueError: boom\n"
    "[2026-10-28 10:00:03,000] INFO in app: recovered\n"
)


@pytest.fixture
def logfile(app, tmp_path):
    path = tmp_path / "keyshift.log"
    app.config["LOG_FILE"] = str(path)
    return path


# --- readLog -------------------------------------------------------------

def test_read_missing_file_is_empty(tmp_path):
    assert readLog(str(tmp_path / "nope.log")) == []


def test_read_keeps_tracebacks_with_their_entry(logfile):
    logfile.write_text(SAMPLE)
    entries = readLog(str(logfile))
    assert len(entries) == 4
    assert entries[2].startswith("[2026-10-28 10:00:02,000] ERROR")
    assert "ValueError: boom" in entries[2]


def test_read_filters_by_level_and_limits(logfile):
    logfile.write_text(SAMPLE)
    assert len(readLog(str(logfile), minLevel="WARNING")) == 2
    errors = readLog(str(logfile), minLevel="ERROR")
    assert len(errors) == 1 and "boom" in errors[0]
    assert len(readLog(str(logfile), lines=2)) == 2
    assert readLog(str(logfile), lines=1)[0].endswith("recovered")


def test_read_only_the_end_of_a_huge_file(logfile):
    filler = "[2026-10-28 09:00:00,000] INFO in app: filler line\n" * 40000
    logfile.write_text(filler + SAMPLE)
    assert logfile.stat().st_size > MAX_BYTES
    entries = readLog(str(logfile), lines=1000)
    assert entries[-1].endswith("recovered")
    assert all(e.startswith("[") for e in entries)   # the cut-off first line was dropped


# --- /admin/logs -----------------------------------------------------------

def test_logs_endpoint_returns_entries_no_store(app, admin_client, logfile):
    logfile.write_text(SAMPLE)
    r = admin_client.get("/admin/logs?level=WARNING&lines=10")
    assert r.status_code == 200
    assert len(r.get_json()["entries"]) == 2
    assert "no-store" in r.headers["Cache-Control"]


def test_logs_endpoint_without_a_log_file_yet(app, admin_client, logfile):
    assert admin_client.get("/admin/logs").get_json() == {"entries": []}


def test_logs_endpoint_validates_input(app, admin_client, logfile):
    assert admin_client.get("/admin/logs?level=LOUD").status_code == 400
    assert admin_client.get("/admin/logs?lines=abc").status_code == 400
    logfile.write_text(SAMPLE * 400)
    assert len(admin_client.get("/admin/logs?lines=99999").get_json()["entries"]) == 1000
    assert len(admin_client.get("/admin/logs?lines=-5").get_json()["entries"]) == 1


def test_logs_endpoint_forbidden_for_standard_users(app, standard_client, logfile):
    logfile.write_text(SAMPLE)
    assert standard_client.get("/admin/logs").status_code == 403


def test_logs_endpoint_redirects_anonymous_to_login(app, client, logfile):
    make_user("boss")
    logfile.write_text(SAMPLE)
    r = client.get("/admin/logs")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_log_viewer_card_only_for_admins(app, admin_client, monkeypatch):
    import app.routes.admin as admin
    monkeypatch.setattr(admin, "getConfig", lambda: {
        "apiType": "unifi", "controllerIp": "1.2.3.4",
        "apiUser": {"userName": None, "passWord": None, "apiKey": None}})
    assert 'id="logViewer"' in admin_client.get("/admin").get_data(as_text=True)


def test_log_viewer_card_hidden_from_standard_users(app, standard_client, monkeypatch):
    import app.routes.admin as admin
    monkeypatch.setattr(admin, "getConfig", lambda: {
        "apiType": "unifi", "controllerIp": "1.2.3.4",
        "apiUser": {"userName": None, "passWord": None, "apiKey": None}})
    assert 'id="logViewer"' not in standard_client.get("/admin").get_data(as_text=True)


# --- file handler ------------------------------------------------------------

def test_file_handler_writes_and_is_idempotent(app, logfile):
    root = logging.getLogger()
    before = list(root.handlers)
    try:
        addFileHandler(app)
        addFileHandler(app)
        assert len([h for h in root.handlers if h not in before]) == 1
        logging.getLogger("test").error("hello viewer")
        for h in root.handlers:
            h.flush()
        assert "ERROR in test: hello viewer" in logfile.read_text()
    finally:
        for h in list(root.handlers):
            if h not in before:
                root.removeHandler(h)
                h.close()


def test_default_log_path_is_under_instance(app):
    app.config.pop("LOG_FILE", None)
    assert logFilePath(app).endswith("logs/keyshift.log")

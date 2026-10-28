"""
Encryption of secrets at rest (Wi-Fi passwords in the database, controller
credentials in config.json).

Values are stored as ``enc:v1:<fernet token>``. Anything without that prefix is
treated as legacy plaintext and passed through on read, so databases and config
files written before encryption existed keep working until they are migrated.

Key: ``ENCRYPTION_KEY`` (a Fernet key; comma-separate several to rotate: the first
encrypts, all of them decrypt). If unset, a key is generated once into
``instance/encryption.key`` (mode 0600) next to the database.
"""
import logging
import os

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from flask import current_app
from sqlalchemy.types import Text, TypeDecorator

log = logging.getLogger(__name__)

PREFIX = "enc:v1:"


class DecryptionError(Exception):
    """A stored secret could not be decrypted with the configured key(s)."""


def _keyfile() -> str:
    return os.path.join(current_app.instance_path, "encryption.key")


def _load_or_create_keyfile() -> str:
    path = _keyfile()
    try:
        with open(path) as f:
            return f.read().strip()
    except FileNotFoundError:
        pass
    os.makedirs(current_app.instance_path, exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    fd = os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(Fernet.generate_key().decode())
    try:
        os.link(tmp, path)  # atomic: if another process won the race, theirs stays
        log.warning("No ENCRYPTION_KEY set; generated a key in %s. Back it up with the "
                    "database, or set ENCRYPTION_KEY instead.", path)
    except FileExistsError:
        pass
    finally:
        os.remove(tmp)
    with open(path) as f:
        return f.read().strip()


def _fernet() -> MultiFernet:
    raw = current_app.config.get("ENCRYPTION_KEY") or os.environ.get("ENCRYPTION_KEY")
    keys = [k.strip() for k in (raw or _load_or_create_keyfile()).split(",") if k.strip()]
    try:
        return MultiFernet([Fernet(k) for k in keys])
    except (ValueError, TypeError) as e:
        raise ValueError("ENCRYPTION_KEY must be Fernet keys (generate one with "
                         "`python -c \"from cryptography.fernet import Fernet; "
                         "print(Fernet.generate_key().decode())\"`)") from e


def is_encrypted(value) -> bool:
    return isinstance(value, str) and value.startswith(PREFIX)


def encrypt(value):
    """Encrypt a string; None, empty and already-encrypted values pass through."""
    if not value or is_encrypted(value):
        return value
    return PREFIX + _fernet().encrypt(value.encode()).decode()


def decrypt(value):
    """Decrypt a stored value; legacy plaintext passes through unchanged."""
    if not is_encrypted(value):
        return value
    try:
        return _fernet().decrypt(value[len(PREFIX):].encode()).decode()
    except InvalidToken as e:
        raise DecryptionError("Could not decrypt a stored secret: ENCRYPTION_KEY does not "
                              "match the key it was encrypted with") from e


class EncryptedText(TypeDecorator):
    """Text column whose value is encrypted in the database and plaintext in Python."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return encrypt(value)

    def process_result_value(self, value, dialect):
        return decrypt(value)

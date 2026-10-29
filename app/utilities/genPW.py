import logging

from app.utilities.passwordPolicy import PasswordPolicy, generate

log = logging.getLogger("utilities.genPW")


def genPW(length: int = 40) -> str:
    """Generate a password with the default policy at the given length (see passwordPolicy.generate)."""
    return generate(PasswordPolicy(length=length))

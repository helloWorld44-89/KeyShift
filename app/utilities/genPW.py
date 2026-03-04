import secrets
import string
import logging

log = logging.getLogger("utilities.genPW")


def genPW(length: int = 40) -> str:
    """
    Generate a cryptographically secure random password.

    Uses Python's `secrets` module (backed by the OS CSPRNG) to ensure
    passwords are suitable for security-sensitive contexts.

    The character set includes uppercase, lowercase, digits, and punctuation.
    Generation loops until all four complexity requirements are met.

    Args:
        length: Desired password length. Defaults to 40 characters.

    Returns:
        A password string meeting all complexity requirements,
        or an error message string if an exception occurs.
    """
    try:
        # Full printable character set (excluding whitespace)
        alphabet = string.ascii_letters + string.digits + string.punctuation

        while True:
            # Generate a candidate password using cryptographically secure random choices
            password = ''.join(secrets.choice(alphabet) for i in range(length))

            # Enforce complexity: must contain all four character classes
            if (any(c.islower() for c in password) and
                    any(c.isupper() for c in password) and
                    any(c.isdigit() for c in password) and
                    any(c in string.punctuation for c in password)):
                break  # All criteria met — exit loop

        log.info("Wi-Fi password generated successfully")
        return password
    except Exception as e:
        log.info(f"Error: {e}")
        return f"An Error has occured: {e}"

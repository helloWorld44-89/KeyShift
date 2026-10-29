"""
Password policy: how generated Wi-Fi passwords are built and what manual ones must satisfy.

The default policy reproduces the original generator (40 characters, all four classes,
every ASCII punctuation mark), so installs that never touch the setting see no change.
"""
import json
import logging
import math
import secrets
import string
from dataclasses import dataclass, asdict, fields

log = logging.getLogger("utilities.passwordPolicy")

WPA_MIN, WPA_MAX = 8, 63
LOOKALIKES = "0O1lI"
SETTING_KEY = "passwordPolicy"


@dataclass
class PasswordPolicy:
    length: int = 40
    upper: bool = True
    lower: bool = True
    digits: bool = True
    symbols: bool = True
    minPerClass: int = 1                      # minimum characters from each enabled class
    symbolSet: str = string.punctuation
    excludeLookalikes: bool = False
    enforceManual: bool = False               # also apply the class rules to hand-typed passwords


def _pools(p: PasswordPolicy) -> dict[str, str]:
    """Characters available per enabled class, after look-alike exclusion."""
    def clean(chars):
        return "".join(dict.fromkeys(c for c in chars if not (p.excludeLookalikes and c in LOOKALIKES)))
    pools = {}
    if p.upper:
        pools["upper"] = clean(string.ascii_uppercase)
    if p.lower:
        pools["lower"] = clean(string.ascii_lowercase)
    if p.digits:
        pools["digits"] = clean(string.digits)
    if p.symbols:
        pools["symbols"] = clean(p.symbolSet)
    return pools


def validatePolicy(p: PasswordPolicy) -> list[str]:
    """Reasons the policy can't be used; empty if it is fine."""
    errors = []
    if not isinstance(p.length, int) or not WPA_MIN <= p.length <= WPA_MAX:
        errors.append(f"Length must be between {WPA_MIN} and {WPA_MAX} (the WPA2/WPA3 limits).")
    if not isinstance(p.minPerClass, int) or p.minPerClass < 0:
        errors.append("Minimum per class can't be negative.")
    if not isinstance(p.symbolSet, str) or any(c not in string.printable or c.isspace() or c.isalnum()
                                               for c in p.symbolSet):
        errors.append("Symbols must be printable ASCII punctuation, without letters, digits or spaces.")
        return errors
    pools = _pools(p)
    if not pools:
        errors.append("Enable at least one character class.")
    elif p.symbols and not pools["symbols"]:
        errors.append("Symbols are enabled but the symbol set is empty.")
    if errors:
        return errors
    if p.minPerClass * len(pools) > p.length:
        errors.append(f"A length of {p.length} can't hold {p.minPerClass} of each of {len(pools)} classes.")
    return errors


def entropyBits(p: PasswordPolicy) -> float:
    """Approximate strength: length * log2(pool size). Ignores the class minimums."""
    pool = "".join(_pools(p).values())
    return round(p.length * math.log2(len(pool)), 1) if pool else 0.0


def generate(p: PasswordPolicy | None = None) -> str:
    """Cryptographically random password that satisfies the policy. Raises ValueError if the policy is invalid."""
    p = p or PasswordPolicy()
    errors = validatePolicy(p)
    if errors:
        raise ValueError(" ".join(errors))
    pools = _pools(p)
    chars = [secrets.choice(pool) for pool in pools.values() for _ in range(p.minPerClass)]
    everything = "".join(pools.values())
    chars += [secrets.choice(everything) for _ in range(p.length - len(chars))]
    secrets.SystemRandom().shuffle(chars)  # the guaranteed characters shouldn't sit at the front
    log.info("Wi-Fi password generated successfully")
    return "".join(chars)


def checkPassword(pw: str, p: PasswordPolicy | None = None) -> list[str]:
    """
    Reasons a hand-entered password is not acceptable; empty if it is.
    The WPA limits always apply. The policy's class rules apply only when enforceManual is on.
    """
    errors = []
    if not WPA_MIN <= len(pw) <= WPA_MAX:
        errors.append(f"Password must be {WPA_MIN} to {WPA_MAX} characters.")
    if any(c not in string.printable or c in "\t\n\r\x0b\x0c" for c in pw):
        errors.append("Password may only contain printable ASCII characters.")
    if p is not None and p.enforceManual and not errors:
        for name, pool in _pools(p).items():
            if sum(c in pool for c in pw) < max(p.minPerClass, 1):
                errors.append(f"Password needs at least {max(p.minPerClass, 1)} {name} character(s) "
                              f"(see the password policy).")
    return errors


def policyFromDict(data: dict) -> PasswordPolicy:
    """Build a policy from stored or submitted values; unknown keys are ignored, missing ones default."""
    known = {f.name for f in fields(PasswordPolicy)}
    return PasswordPolicy(**{k: v for k, v in data.items() if k in known})


def policyToJson(p: PasswordPolicy) -> str:
    return json.dumps(asdict(p))

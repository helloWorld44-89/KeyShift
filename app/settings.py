"""Runtime settings kept in the database."""
import json
import logging

from app import db
from app.models import Setting
from app.utilities.passwordPolicy import (PasswordPolicy, SETTING_KEY, policyFromDict,
                                          policyToJson, validatePolicy)

log = logging.getLogger(__name__)


def getPolicy() -> PasswordPolicy:
    """The saved password policy, or the default if none is saved or the saved one is unusable."""
    row = db.session.get(Setting, SETTING_KEY)
    if row is None or not row.value:
        return PasswordPolicy()
    try:
        policy = policyFromDict(json.loads(row.value))
        if not validatePolicy(policy):
            return policy
        log.warning("Saved password policy is invalid; using the default")
    except (ValueError, TypeError):
        log.warning("Saved password policy is unreadable; using the default")
    return PasswordPolicy()


def savePolicy(policy: PasswordPolicy) -> None:
    row = db.session.get(Setting, SETTING_KEY)
    if row is None:
        row = Setting(key=SETTING_KEY)
        db.session.add(row)
    row.value = policyToJson(policy)
    db.session.commit()

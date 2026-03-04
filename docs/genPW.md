# Password Generator

Module: `app/utilities/genPW.py`

---

## `genPW(length=40) → str`

Generates a cryptographically secure random password using Python's `secrets` module.

**Character set:** uppercase, lowercase, digits, and punctuation (`string.ascii_letters + string.digits + string.punctuation`)

**Complexity requirements (all must be satisfied):**

- At least one lowercase letter
- At least one uppercase letter
- At least one digit
- At least one punctuation character

The function loops until all criteria are met, guaranteeing a strong password on every call.

### Example

```python
from app.utilities.genPW import genPW

pw = genPW()        # 40-character password (default)
pw = genPW(16)      # 16-character password
```

### Returns
- `str` — the generated password
- `str` — error message prefixed with `"An Error has occured: "` on exception

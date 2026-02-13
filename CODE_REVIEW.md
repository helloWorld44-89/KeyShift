# KeyShift Project Code Review

**Date:** February 12, 2026
**Reviewer:** Claude
**Review Scope:** Security, Code Quality, Performance, Project Structure

---

## Executive Summary

KeyShift is a Flask-based web application for managing WiFi SSID passwords with automatic rotation capabilities, supporting both UniFi and Omada controllers. The application has a solid foundation but requires **critical security fixes** before production deployment.

**Overall Risk Level:** 🔴 **HIGH** - Multiple critical security vulnerabilities identified

---

## 🔴 CRITICAL SECURITY VULNERABILITIES

### 1. **Hardcoded Secret Keys** (SEVERITY: CRITICAL)
**Location:** `app/__init__.py` lines 14, 16

```python
app.config['SECRET_KEY'] = 'SECRETKEY'
app.secret_key = 'TEST KEY'
```

**Risk:** 
- Session hijacking
- CSRF token prediction
- Cookie tampering
- Complete authentication bypass possible

**Fix Required:**
```python
import os
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
# Remove duplicate app.secret_key line
```

**Action:** Generate a cryptographically secure key and store in environment variables immediately.

---

### 2. **Exposed API Key in Config File** (SEVERITY: CRITICAL)
**Location:** `app/config/config.json` line 5

```json
"apiKey": "JbcZXUU-WrNj2XTUBF3mAqNJR2vaF6gl"
```

**Risk:**
- API key visible in version control
- Full controller access if repository is compromised
- Plaintext storage of credentials

**Fix Required:**
```python
# Use environment variables
apiKey = os.environ.get('UNIFI_API_KEY')
# Or use proper secrets management (HashiCorp Vault, AWS Secrets Manager)
```

**Action:** 
1. Immediately revoke this API key
2. Move ALL credentials to environment variables
3. Add `config.json` to `.gitignore`
4. Use `.env` files with python-dotenv

---

### 3. **Disabled SSL Verification** (SEVERITY: CRITICAL)
**Location:** `app/api/unifi.py` lines 17, 22, 30, 46, etc.

```python
requests.packages.urllib3.disable_warnings()
response = session.get(update_url, headers=headers, verify=False)
```

**Risk:**
- Man-in-the-middle attacks
- API credentials intercepted in plaintext
- Complete compromise of WiFi infrastructure

**Fix Required:**
```python
# Option 1: Use proper CA certificate
response = session.get(update_url, headers=headers, verify='/path/to/ca-cert.pem')

# Option 2: If self-signed, add to trusted store
# Never use verify=False in production
```

**Action:** Implement proper SSL certificate verification before production deployment.

---

### 4. **SQL Injection Potential** (SEVERITY: HIGH)
**Location:** `app/pages.py` line 176

```python
filePath = Path(f"static/img/{name}.png")
```

**Risk:**
- Path traversal attacks
- Arbitrary file access
- Information disclosure

**Current route accepts user input without validation:**
```python
@bp.route("/qr/<n>")  # <n> is used as <name> in function
```

**Fix Required:**
```python
import re
from werkzeug.utils import secure_filename

@bp.route("/qr/<int:id>")  # Use ID instead of name
@login_required
def getImage(id):
    ssid = SSID.query.get_or_404(id)
    safe_filename = secure_filename(f"{ssid.ssidName}.png")
    filePath = Path("static/img") / safe_filename
    
    # Prevent path traversal
    if not filePath.resolve().is_relative_to(Path("static/img").resolve()):
        abort(403)
```

---

### 5. **Authentication Bypass Vulnerabilities** (SEVERITY: HIGH)
**Location:** `app/pages.py` lines 117, 151

```python
if current_user.is_authenticated or request.referrer.endswith("/initApp"):
```

**Risk:**
- Referrer can be spoofed
- Unauthorized user creation
- Unauthorized database initialization

**Fix Required:**
```python
# Use session-based flags instead of referrer checking
if current_user.is_authenticated or session.get('init_mode'):
    # ... authorized code

# Set init_mode only during actual initialization
@bp.route("/initApp", methods=["GET","POST"])
def initApp():
    session['init_mode'] = True
    return render_template("pages/initApp.html")
```

---

### 6. **Password Logged in Plain Text** (SEVERITY: HIGH)
**Location:** Multiple files

```python
# app/utilities/genPW.py line 25
log.info(f"New PW Generated: {password}")

# app/api/unifi.py line 32
log.info(f"Wi-Fi password changed to {newPw}")

# app/pages.py line 215
log.debug(f"Password changed for {ssid.ssidName} to {pw}")
```

**Risk:**
- Passwords exposed in log files
- Compliance violations (PCI-DSS, GDPR)
- Insider threats

**Fix Required:**
```python
# Never log passwords
log.info(f"New password generated")
log.info(f"Wi-Fi password changed successfully")
log.debug(f"Password changed for {ssid.ssidName}")
```

---

### 7. **No Rate Limiting** (SEVERITY: MEDIUM)
**Location:** `app/pages.py` - login route line 54

**Risk:**
- Brute force attacks on login
- Account enumeration
- DoS attacks

**Fix Required:**
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    # ... existing code
```

---

### 8. **CORS and CSRF Protection Missing** (SEVERITY: MEDIUM)

**Risk:**
- Cross-site request forgery
- Unauthorized API access

**Fix Required:**
```python
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()
csrf.init_app(app)
```

---

## 🟡 CODE QUALITY ISSUES

### 1. **Inconsistent Error Handling**

**Problem:** Mix of returning error strings, raising exceptions, and logging

**Examples:**
```python
# models.py returns string
return f'An Error has occured: {e}'

# pages.py returns dict
return {"message": f"An Error has occured: {e}"}, 500

# Some places just log
log.error(f"Error: {e}")
```

**Recommendation:**
```python
# Use consistent error handling with custom exceptions
class KeyShiftException(Exception):
    pass

class APIException(KeyShiftException):
    pass

# Use error handlers
@app.errorhandler(APIException)
def handle_api_error(error):
    return {"error": str(error)}, 500
```

---

### 2. **Magic Numbers and Hardcoded Values**

**Examples:**
```python
# genPW.py line 7
def genPW(length=40):  # Why 40?

# No constants defined
```

**Recommendation:**
```python
# config.py or constants.py
DEFAULT_PASSWORD_LENGTH = 40
MIN_PASSWORD_LENGTH = 12
MAX_LOGIN_ATTEMPTS = 5
SESSION_TIMEOUT = 3600
```

---

### 3. **Poor Variable Naming**

**Examples:**
```python
# Inconsistent naming conventions
myConfig  # camelCase
my_config  # snake_case
_user     # leading underscore suggests private
```

**Recommendation:**
```python
# Use consistent snake_case for Python
current_config
api_config
selected_user
```

---

### 4. **Missing Type Hints**

**Current:**
```python
def changePW(id:int):  # Only one function has types
def genPW(length=40):  # No return type
```

**Recommendation:**
```python
from typing import Optional, Dict, List

def change_password(ssid_id: int) -> bool:
    """Change the password for a given SSID."""
    pass

def generate_password(length: int = 40) -> str:
    """Generate a cryptographically secure password."""
    pass
```

---

### 5. **Duplicate Code**

**Example:** Password change logic duplicated in `pages.py` lines 194-209

**Recommendation:**
```python
def _change_ssid_password(ssid: SSID, password: str) -> bool:
    """Centralized password change logic."""
    config = getConfig()
    api_map = {
        'omada': OMADA.changePW,
        'unifi': UNIFI.changePW
    }
    
    api_func = api_map.get(config["apiType"])
    if not api_func:
        raise ValueError(f"Invalid API type: {config['apiType']}")
    
    return api_func(ssid, password)
```

---

### 6. **Class Methods Not Using @staticmethod**

**Location:** `models.py` lines 21, 65

```python
class user(db.Model, UserMixin):
    def newUser(userName, pw, role=0):  # Should be @staticmethod
```

**Recommendation:**
```python
@staticmethod
def create_user(username: str, password: str, is_admin: bool = False) -> 'user':
    """Create a new user."""
    pass
```

---

## ⚡ PERFORMANCE ISSUES

### 1. **N+1 Query Problem**

**Location:** `app/api/unifi.py` lines 86-95

```python
for i in siteIDs:
    for j in wlans:
        response = session.get(...)  # Multiple API calls in loop
```

**Impact:** 
- If 3 sites × 5 WLANs = 15 API calls
- Slow initialization
- API rate limiting issues

**Recommendation:**
```python
# Use concurrent requests
from concurrent.futures import ThreadPoolExecutor

def fetch_ssid_info(site_id, wlan_id):
    # ... fetch logic
    
with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(fetch_ssid_info, s, w) 
               for s in siteIDs for w in wlans]
    ssid_list = [f.result() for f in futures]
```

---

### 2. **Database Connection Not Pooled**

**Current:** No connection pooling configuration

**Recommendation:**
```python
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True
}
```

---

### 3. **Requests Session Not Reused Efficiently**

**Location:** `app/api/unifi.py` line 10

```python
session = requests.Session()  # Module level - good
# But no timeout configuration
```

**Recommendation:**
```python
session = requests.Session()
session.timeout = (5, 30)  # (connect, read) timeouts

# Add retry strategy
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
```

---

### 4. **No Caching**

**Missing:** Response caching for frequently accessed data

**Recommendation:**
```python
from flask_caching import Cache

cache = Cache(app, config={
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300
})

@bp.route("/admin")
@cache.cached(timeout=60, key_prefix='ssid_list')
def get_ssids():
    pass
```

---

## 🏗️ PROJECT STRUCTURE ISSUES

### 1. **Missing Files**

**Critical Missing:**
- `requirements.txt` - No dependency management
- `.env.example` - No environment variable template
- `.gitignore` - Secrets likely in version control
- `README.md` - No documentation
- `tests/` - No test coverage
- `migrations/` - No database version control

**Recommendation:**
Create these files immediately.

---

### 2. **Inconsistent Import Paths**

**Problem:**
```python
# cron.py
from utilities.genPW import genPW  # Relative
from config import config          # Relative

# pages.py  
from app.utilities.genPW import genPW  # Absolute
from .models import user               # Relative with dot
```

**Recommendation:**
```python
# Use absolute imports consistently
from app.utilities.genPW import genPW
from app.config import config
from app.models import user, SSID
```

---

### 3. **Poor Separation of Concerns**

**Issues:**
- Business logic in routes (`pages.py`)
- No service layer
- Models contain business logic

**Recommendation:**
```
app/
├── __init__.py
├── models/          # Data models only
├── services/        # Business logic
│   ├── auth_service.py
│   ├── ssid_service.py
│   └── password_service.py
├── routes/          # Route handlers only
├── api/             # External API clients
└── utils/           # Utilities
```

---

### 4. **Configuration Management**

**Current:** JSON file with hardcoded values

**Recommendation:**
```python
# config.py
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
class DevelopmentConfig(Config):
    DEBUG = True
    
class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_POOL_SIZE = 10
```

---

## 📋 IMMEDIATE ACTION ITEMS

### Priority 1 (Critical - Fix Before ANY Production Use)
- [ ] Remove all hardcoded secrets
- [ ] Implement environment variable configuration
- [ ] Revoke exposed API key
- [ ] Fix SSL verification
- [ ] Remove password logging
- [ ] Add `.gitignore` and remove secrets from git history

### Priority 2 (High - Fix Within 1 Week)
- [ ] Implement rate limiting
- [ ] Add CSRF protection
- [ ] Fix authentication bypass vulnerabilities
- [ ] Add input validation and sanitization
- [ ] Create requirements.txt

### Priority 3 (Medium - Fix Within 1 Month)
- [ ] Add comprehensive error handling
- [ ] Implement proper logging strategy
- [ ] Add unit tests (target 80% coverage)
- [ ] Add API request retry logic
- [ ] Optimize database queries

### Priority 4 (Low - Ongoing Improvements)
- [ ] Refactor code structure
- [ ] Add type hints
- [ ] Improve documentation
- [ ] Add integration tests
- [ ] Set up CI/CD pipeline

---

## 🔧 RECOMMENDED DEPENDENCIES

Create `requirements.txt`:
```
Flask==3.0.0
Flask-SQLAlchemy==3.1.1
Flask-Login==0.6.3
Flask-Migrate==4.0.5
Flask-Bcrypt==1.0.1
Flask-WTF==1.2.1
Flask-Limiter==3.5.0
Flask-Caching==2.1.0
python-dotenv==1.0.0
gunicorn==21.2.0
requests==2.31.0
qrcode==7.4.2
python-crontab==3.0.0
```

---

## 🛡️ SECURITY BEST PRACTICES CHECKLIST

- [ ] Environment-based configuration
- [ ] Secrets management system
- [ ] SSL/TLS verification enabled
- [ ] Input validation on all endpoints
- [ ] SQL injection prevention
- [ ] XSS protection
- [ ] CSRF protection
- [ ] Rate limiting
- [ ] Secure password hashing (bcrypt ✓)
- [ ] Session management
- [ ] Audit logging (without sensitive data)
- [ ] Regular dependency updates
- [ ] Security headers (helmet equivalent)
- [ ] Content Security Policy

---

## 💡 POSITIVE ASPECTS

**Good Practices Already Implemented:**
1. ✅ Using bcrypt for password hashing
2. ✅ Flask-Login for authentication
3. ✅ SQLAlchemy ORM (prevents basic SQL injection)
4. ✅ Blueprint organization
5. ✅ Logging infrastructure in place
6. ✅ Docker containerization
7. ✅ Database migrations ready (Flask-Migrate)
8. ✅ Separation of API clients (unifi, omada)

---

## 📊 CODE METRICS ESTIMATE

- **Security Risk:** 🔴 Critical (8/10)
- **Code Quality:** 🟡 Moderate (5/10)
- **Performance:** 🟡 Moderate (6/10)
- **Maintainability:** 🟡 Moderate (5/10)
- **Test Coverage:** 🔴 None (0%)
- **Documentation:** 🔴 Minimal (2/10)

---

## 🎯 CONCLUSION

KeyShift has a solid architectural foundation but requires **immediate security hardening** before any production deployment. The application demonstrates good understanding of Flask patterns, but critical security vulnerabilities make it unsuitable for production use in its current state.

**Estimated Time to Production Ready:**
- Critical fixes: 2-3 days
- High priority fixes: 1 week
- Full hardening: 2-3 weeks

**Recommendation:** Do NOT deploy to production until Priority 1 and Priority 2 items are completed.

---

## 📞 NEXT STEPS

1. Review this document with your team
2. Create GitHub issues for each action item
3. Prioritize security fixes
4. Implement comprehensive testing
5. Conduct security audit after fixes
6. Consider penetration testing before production launch

Would you like me to create detailed implementation guides for any specific section?

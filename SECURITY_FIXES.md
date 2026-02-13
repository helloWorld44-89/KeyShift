# CRITICAL SECURITY FIXES - DO THIS IMMEDIATELY

## 1. Generate a Secure Secret Key

Run this Python command to generate a secure key:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and add it to your `.env` file:
```
SECRET_KEY=<paste-the-generated-key-here>
```

## 2. Update app/__init__.py

Replace lines 14-16 with:

```python
import os
from dotenv import load_dotenv

load_dotenv()

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
if not app.config['SECRET_KEY']:
    raise ValueError("No SECRET_KEY set in environment variables")
```

## 3. Move API Credentials to Environment

### Step 1: Create .env file (copy from .env.example)
```bash
cp .env.example .env
```

### Step 2: Fill in your actual values in .env
```
CONTROLLER_IP=192.168.1.1
API_TYPE=unifi
UNIFI_API_KEY=your-actual-api-key
```

### Step 3: Update config.py to read from environment

Replace `app/config/config.py` with:

```python
import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("config.config")

def getConfig():
    """Get configuration from environment variables and config file."""
    config = {
        "apiUser": {
            "userName": os.environ.get('OMADA_USERNAME'),
            "passWord": os.environ.get('OMADA_PASSWORD'),
            "apiKey": os.environ.get('UNIFI_API_KEY')
        },
        "controllerIp": os.environ.get('CONTROLLER_IP', '192.168.1.1'),
        "apiType": os.environ.get('API_TYPE', 'unifi'),
        "logging": {
            "level": os.environ.get('LOG_LEVEL', 'INFO')
        }
    }
    
    # Merge with JSON config if it exists (for non-sensitive data)
    try:
        config_file = os.path.join(os.path.dirname(__file__), "config.json")
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                # Only merge non-sensitive fields
                if 'wifiInfo' in file_config:
                    config['wifiInfo'] = file_config['wifiInfo']
    except Exception as e:
        log.warning(f"Could not load config.json: {e}")
    
    return config
```

## 4. Remove Password Logging

### In app/utilities/genPW.py (line 25):
```python
# BEFORE:
log.info(f"New PW Generated: {password}")

# AFTER:
log.info("New password generated successfully")
```

### In app/api/unifi.py (line 32):
```python
# BEFORE:
log.info(f"Wi-Fi password changed to {newPw}")

# AFTER:
log.info("Wi-Fi password changed successfully")
```

### In app/pages.py (line 215):
```python
# BEFORE:
log.debug(f"Password changed for {ssid.ssidName} to {pw}")

# AFTER:
log.debug(f"Password changed for {ssid.ssidName}")
```

## 5. Fix SSL Verification

### In app/api/unifi.py, remove line 17:
```python
# DELETE THIS LINE:
requests.packages.urllib3.disable_warnings()
```

### Add SSL configuration at the top of the file:
```python
import os
import requests

# SSL Configuration
SSL_VERIFY = os.environ.get('SSL_CERT_PATH', True)  # Path to cert or True
if SSL_VERIFY == 'False':
    # Only for development
    import urllib3
    urllib3.disable_warnings()
    SSL_VERIFY = False
```

### Update all API calls to use SSL_VERIFY:
```python
# BEFORE:
response = session.get(update_url, headers=headers, verify=False)

# AFTER:
response = session.get(update_url, headers=headers, verify=SSL_VERIFY)
```

## 6. Revoke the Exposed API Key

⚠️ **IMPORTANT:** The API key in your config.json has been exposed in this review.

1. Log into your UniFi/Omada controller
2. Navigate to API settings
3. Revoke the key: `JbcZXUU-WrNj2XTUBF3mAqNJR2vaF6gl`
4. Generate a new API key
5. Add the new key to your `.env` file

## 7. Update Docker Configuration

### docker-compose.yml - Add environment file:
```yaml
services:
  web:
    image: keyshift:latest
    ports:
      - "5000:5000"
    env_file:
      - .env
    environment:
      - TZ=America/Chicago
    # Remove volume mount in production for security
    # volumes:
    #   - .:/app
```

## 8. Git Security

### Remove secrets from git history:
```bash
# Add .gitignore
git add .gitignore

# Remove config.json from tracking
git rm --cached app/config/config.json

# Commit
git commit -m "Security: Remove sensitive config from tracking"

# If config.json was already committed, you need to remove from history:
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch app/config/config.json' \
  --prune-empty --tag-name-filter cat -- --all

# Force push (BE CAREFUL - this rewrites history)
git push origin --force --all
```

## 9. Verify Fixes

Run this checklist:

- [ ] SECRET_KEY is in .env and not hardcoded
- [ ] API credentials are in .env
- [ ] config.json is in .gitignore
- [ ] Old API key has been revoked
- [ ] Password logging is removed
- [ ] SSL verification is enabled (or properly configured)
- [ ] .env file is NOT committed to git
- [ ] Secrets are removed from git history

## 10. Test the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Set up .env file
cp .env.example .env
# Edit .env with your actual values

# Test locally
flask run

# If everything works, rebuild Docker:
docker build -t keyshift:latest .
docker-compose up -d
```

## Need Help?

If you need assistance with any of these steps, please ask for clarification on specific sections.

import copy
import json
import logging
import os

from app.crypto import encrypt, decrypt, is_encrypted

log= logging.getLogger("config.config")

CONFIG_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), "file/config.json")

# Values in config.json that are stored encrypted (see app/crypto.py)
SECRET_PATHS = [("apiUser", "apiKey"), ("apiUser", "passWord"), ("wifiInfo", "password")]


def _map_secrets(config: dict, fn) -> dict:
    """Return a copy of config with fn applied to every secret value that is set."""
    config = copy.deepcopy(config)
    for section, key in SECRET_PATHS:
        if isinstance(config.get(section), dict) and config[section].get(key):
            config[section][key] = fn(config[section][key])
    return config


def getConfig():
    """Read config.json with secrets decrypted (legacy plaintext values pass through)."""
    file_path = CONFIG_PATH
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return _map_secrets(data, decrypt)

    except FileNotFoundError:
        log.info(f"Error: The file '{file_path}' was not found.")
        return f"Error: The file '{file_path}' was not found."
    except json.JSONDecodeError as e:
        log.info(f"Error decoding JSON from '{file_path}': {e}")
        return f"Error decoding JSON from '{file_path}': {e}"
    except Exception as e:
        log.info(f"Error: {e}")
        return f"An unexpected error occurred: {e}"
    
def updatePW(password):

    file_path = CONFIG_PATH
    try:
        data = getConfig()
        data["wifiInfo"]["password"] = password
        updateConfig(data)
        return data
    except FileNotFoundError:
        log.info(f"Error: The file '{file_path}' was not found.")
        return f"Error: The file '{file_path}' was not found."
    except json.JSONDecodeError as e:
        log.info(f"Error decoding JSON from '{file_path}': {e}")
        return f"Error decoding JSON from '{file_path}': {e}"
    except Exception as e:
        log.info(f"Error: {e}")
        return f"An unexpected error occurred: {e}"
    
def updateConfig(newConfig):
    """Write config.json with secrets encrypted; the file is readable by its owner only."""
    filename = CONFIG_PATH
    try:
        fd = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w') as json_file:
            json.dump(_map_secrets(newConfig, encrypt), json_file, indent=4)
        os.chmod(filename, 0o600)
        return f"Successfully updated config to {filename}"
    except IOError as e:
       log.info(f"Error writing to file {filename}: {e}")
       return f"Error writing to file {filename}: {e}"
    except Exception as e:
        log.info(f"Error: {e}")
        return f"An unexpected error occurred: {e}"


def encryptConfigSecrets() -> bool:
    """
    Encrypt any plaintext secrets already in config.json (installs from before
    encryption existed). Safe to run on every start; returns True if it rewrote the file.
    """
    try:
        with open(CONFIG_PATH, 'r') as f:
            raw = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return False
    plaintext = [(sec, key) for sec, key in SECRET_PATHS
                 if isinstance(raw.get(sec), dict) and raw[sec].get(key)
                 and not is_encrypted(raw[sec][key])]
    if not plaintext:
        return False
    updateConfig(raw)
    log.info("Encrypted controller credentials in config.json")
    return True

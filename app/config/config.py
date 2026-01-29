import json
import logging

log= logging.getLogger("config.config")


def getConfig():
    import os 
    BASE_DIR = os.path.abspath(os.path.dirname(__file__)) 
    CONFIG_PATH = os.path.join(BASE_DIR, "config.json") 
    #with open(CONFIG_PATH) as f: data = f.read()
    file_path = CONFIG_PATH
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
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
    
def updatePW(password):

    file_path = 'app/config/config.json' 
    try:
        data = getConfig()
        data["wifiInfo"]["password"] = password
        with open(file_path, 'w') as f:
            
            json.dump(data,f,indent=4)
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
    # Specify the filename
    filename = "app/config/config copy.json"

    # Open the file in write mode ('w') and dump the dictionary to it
    try:
        with open(filename, 'w') as json_file:
            json.dump(newConfig, json_file, indent=4) # Using 'indent' for pretty-printing
        return f"Successfully updated config to {filename}"
    except IOError as e:
       log.info(f"Error writing to file {filename}: {e}")
       return f"Error writing to file {filename}: {e}"
    except Exception as e:
        log.info(f"Error: {e}")
        return f"An unexpected error occurred: {e}"
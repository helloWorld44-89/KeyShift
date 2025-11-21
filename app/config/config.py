import json

def getConfig():
    file_path = 'app/config/config.json' 
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data

    except FileNotFoundError:
        return f"Error: The file '{file_path}' was not found."
    except json.JSONDecodeError as e:
        return f"Error decoding JSON from '{file_path}': {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"
    
def updatePW(password):

    file_path = 'app/config/config.json' 
    try:
        data = getConfig()
        data["wifiInfo"]["password"] = password
        with open(file_path, 'w') as f:
            
            json.dump(data,f,indent=4)
        return data
        print(data)
    except FileNotFoundError:
        return f"Error: The file '{file_path}' was not found."
    except json.JSONDecodeError as e:
        return f"Error decoding JSON from '{file_path}': {e}"
    except Exception as e:
        return f"An unexpected error occurred: {e}"
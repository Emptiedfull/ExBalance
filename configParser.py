import yaml

with open("config.yaml") as f:
    data = yaml.safe_load(f)

logging_config = data["Logging"]
App_config = data["Application"]

def verify_value(value,valid_values, default,bypass=False):
    if bypass:
        return value

    if value in valid_values:
        return value
    else:
        return default
    


logging_level = verify_value(logging_config["Level"], ["DEBUG", "INFO", "NONE"], "INFO")
AppLogPath = verify_value(logging_config["AppLogFile"], [], "app.log", True)
PortLogPath = verify_value(logging_config["PortLogPath"], [], "/logs/port.log", True)
ErrorLogPath = verify_value(logging_config["ErrorLogPath"], [], "/logs/error.log", True)

asgi = verify_value(App_config["asgi"], ["uvicorn","gunicorn","daphne"],"uvicorn", False)

app = verify_value(App_config["app"], [], "main:app", True)
port = verify_value(App_config["port"], [], 8000, True)
host = verify_value(App_config["host"], [], "localhost",True)
free_ports = verify_value(App_config["free_ports"], [], [8000,8001,8002,8003,8004], True)   
threshold = verify_value(App_config["threshold"], [], 10, True)


logging_config = {
    "level": logging_level,
    "AppLogPath": AppLogPath,
    "PortLogPath": PortLogPath,
    "ErrorLogPath": ErrorLogPath
}

App_config = {
    "asgi": asgi,
    "app": app,
    "port": port,
    "host": host,
    "free_ports": free_ports,
    "threshold": threshold
}


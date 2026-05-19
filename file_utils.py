import base64
import json
import os
import re
from datetime import datetime


def project_path(*parts):
    root_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(root_dir, *parts)


def get_frontend_dir():
    return project_path("frontend")


def ensure_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def now_compact():
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def safe_filename(name):
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", name)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)


def save_binary(path, data):
    with open(path, "wb") as handle:
        handle.write(data)


def image_input_to_bytes(image_base64):
    if image_base64.startswith("data:"):
        image_base64 = image_base64.split(",", 1)[1]
    return base64.b64decode(image_base64)


def image_bytes_to_data_url(image_bytes, mime_type):
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return "data:{0};base64,{1}".format(mime_type, encoded)

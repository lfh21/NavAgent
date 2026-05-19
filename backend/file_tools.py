import json
import os

from file_utils import ensure_directory, now_compact, safe_filename, save_binary, save_json


def save_debug_artifact(output_dir, original_name, image_bytes, response_payload):
    debug_dir = os.path.join(output_dir, "debug")
    ensure_directory(debug_dir)

    original_name = original_name or "debug_image.jpg"
    safe_name = safe_filename(original_name)
    stem, extension = os.path.splitext(safe_name)
    extension = extension or ".jpg"
    file_stem = "{0}_{1}".format(now_compact(), stem)
    image_path = os.path.join(debug_dir, "{0}{1}".format(file_stem, extension))
    json_path = os.path.join(debug_dir, "{0}.json".format(file_stem))

    save_binary(image_path, image_bytes)
    save_json(json_path, response_payload)

    return {
        "imagePath": image_path,
        "jsonPath": json_path,
    }


def append_formal_log(output_dir, session_id, payload):
    formal_dir = os.path.join(output_dir, "formal")
    ensure_directory(formal_dir)

    log_path = os.path.join(formal_dir, "{0}.jsonl".format(safe_filename(session_id or "default")))
    line = payload.copy()
    line["writtenAt"] = now_compact()

    with open(log_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(line, ensure_ascii=False) + "\n")

    return log_path

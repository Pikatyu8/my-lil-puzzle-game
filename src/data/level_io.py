import json
import os
import sys

from src.data.barrier_core import is_new_format
from src.data.barrier_parser import parse_item, parse_legacy_item


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def process_level_data(data):
    if not data:
        return data

    for lvl in data:
        if not isinstance(lvl, dict):
            continue

        for key in ["conditions", "global_conditions"]:
            if key in lvl:
                for cond in lvl[key]:
                    if "cells" in cond:
                        c = cond["cells"]
                        if isinstance(c, list) and c and not isinstance(c[0], list):
                            cond["cells"] = [tuple(c)]
                        else:
                            cond["cells"] = [tuple(item) for item in c]

        for key in ["poison", "walls"]:
            if key not in lvl:
                continue

            processed = []
            for item in lvl[key]:
                if is_new_format(item):
                    processed.extend(parse_item(item))
                else:
                    processed.extend(parse_legacy_item(item))

            lvl[key] = processed

    return data


def load_levels_from_file(filename, is_internal=True):
    if is_internal:
        path = resource_path(filename)
    else:
        path = os.path.abspath(filename)

    if not os.path.exists(path):
        print(f"[ERROR] Файл не найден: {path}")
        return None

    try:
        print(f"[LOAD] {path}")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return process_level_data(data)
    except Exception as e:
        print(f"[ERROR] JSON: {e}")
        import traceback
        traceback.print_exc()
        return None

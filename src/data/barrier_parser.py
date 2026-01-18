from src.data.barrier_core import (
    parse_sides,
    generate_rect_cells,
    generate_perimeter,
    is_coord,
)


def parse_item(item, default_type="both"):
    if not isinstance(item, dict):
        return []

    walls = []
    b_type = item.get("type", default_type)
    mode = item.get("mode", "fill")
    sides_str = item.get("sides", "all")
    sides = parse_sides(sides_str)

    targets = []

    if "cell" in item:
        c = item["cell"]
        targets.append(("cell", (int(c[0]), int(c[1]))))

    if "cells" in item:
        for c in item["cells"]:
            targets.append(("cell", (int(c[0]), int(c[1]))))

    if "range" in item:
        r = item["range"]
        targets.append((
            "range",
            (int(r[0][0]), int(r[0][1])),
            (int(r[1][0]), int(r[1][1]))
        ))

    if "ranges" in item:
        for r in item["ranges"]:
            targets.append((
                "range",
                (int(r[0][0]), int(r[0][1])),
                (int(r[1][0]), int(r[1][1]))
            ))

    except_set = set()
    if "except" in item:
        for exc in item["except"]:
            if isinstance(exc, dict):
                for coords, side, _ in parse_item(exc, b_type):
                    except_set.add((coords, side))

    for target in targets:
        if target[0] == "cell":
            cell = target[1]
            for side in sides:
                if (cell, side) not in except_set:
                    walls.append((cell, side, b_type))

        elif target[0] == "range":
            start, end = target[1], target[2]

            if mode == "perimeter":
                for coords, side in generate_perimeter(start, end, sides):
                    if (coords, side) not in except_set:
                        walls.append((coords, side, b_type))
            else:
                for cell in generate_rect_cells(start, end):
                    for side in sides:
                        if (cell, side) not in except_set:
                            walls.append((cell, side, b_type))

    return walls


def parse_legacy_item(item):
    if not isinstance(item, list) or len(item) != 2:
        return []

    raw_target, sides_dict = item[0], item[1]
    if not isinstance(sides_dict, dict):
        return []

    walls = []
    modes = sides_dict.get("modes", [])
    except_spec = sides_dict.get("except", [])

    is_perimeter = "perimeter" in modes or "box" in modes

    perimeter_sides_override = None
    if "sides" in sides_dict:
        perimeter_sides_override = parse_sides(sides_dict.get("sides", ""))

    sides_dict = {k: v for k, v in sides_dict.items() if k not in ("modes", "except", "sides")}

    except_set = set()
    for exc in except_spec:
        if is_coord(exc):
            except_set.add((tuple(exc), None))
        elif isinstance(exc, dict) and "cell" in exc:
            c = exc["cell"]
            for side in parse_sides(exc.get("sides", "")):
                except_set.add(((int(c[0]), int(c[1])), side))

    targets = []
    if is_coord(raw_target):
        targets.append(("cell", (int(raw_target[0]), int(raw_target[1]))))
    elif isinstance(raw_target, list) and len(raw_target) == 2 and all(is_coord(x) for x in raw_target):
        targets.append(("range",
                        (int(raw_target[0][0]), int(raw_target[0][1])),
                        (int(raw_target[1][0]), int(raw_target[1][1]))))

    for target in targets:
        if target[0] == "cell":
            cell = target[1]
            for side, b_type in sides_dict.items():
                if side in ["up", "down", "left", "right"]:
                    if ((cell, None) not in except_set) and ((cell, side) not in except_set):
                        walls.append((cell, side, b_type))

        elif target[0] == "range":
            start, end = target[1], target[2]

            if is_perimeter:
                sides = perimeter_sides_override if perimeter_sides_override else ["up", "down", "left", "right"]
                for coords, side in generate_perimeter(start, end, sides):
                    b_type = sides_dict.get(side, "both")
                    if ((coords, None) not in except_set) and ((coords, side) not in except_set):
                        walls.append((coords, side, b_type))
            else:
                for cell in generate_rect_cells(start, end):
                    for side, b_type in sides_dict.items():
                        if side in ["up", "down", "left", "right"]:
                            if ((cell, None) not in except_set) and ((cell, side) not in except_set):
                                walls.append((cell, side, b_type))

    return walls

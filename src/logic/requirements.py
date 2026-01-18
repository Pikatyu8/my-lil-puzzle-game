from src.logic.operators import OP_SYMBOLS
from src.logic.sequence import format_sequence_requirement
from src.logic.steps import format_steps
from src.utils.misc import resolve_cells


def get_condition_cells(level_data, cols, rows):
    cells = set()

    def extract(cond):
        if "cells" in cond:
            cells.update(resolve_cells(cond["cells"], cols, rows))
        if cond.get("check") == "group":
            for item in cond.get("items", []):
                extract(item)

    for cond in level_data.get("conditions", []):
        extract(cond)
    return list(cells)


def get_condition_requirements(level_data, cols, rows):
    requirements = {}
    global_reqs = []

    def add_req(cell, text, req_type="normal"):
        cell = tuple(cell)
        if cell not in requirements:
            requirements[cell] = []
        requirements[cell].append({"text": str(text), "type": req_type})

    def add_global(text, req_type="global"):
        global_reqs.append({"text": str(text), "type": req_type})

    def process(cond):
        check = cond.get("check", "")
        cells = resolve_cells(cond.get("cells", []), cols, rows)

        if check == "group":
            for item in cond.get("items", []):
                process(item)
            return

        if check == "sequence":
            text = format_sequence_requirement(cond)
            add_global(f"Ходы: {text}", "sequence")
            return

        if check == "visit":
            if "min" in cond or "max" in cond:
                min_c, max_c = cond.get("min", 0), cond.get("max", 999999)
                text = f"≥{min_c}" if max_c >= 999999 else f"≤{max_c}" if min_c <= 0 else f"{min_c}-{max_c}"
                for c in cells:
                    add_req(c, f"×{text}", "count")
            else:
                count = cond.get("count", 1)
                op = cond.get("operator", ">=")
                if count == 0:
                    for c in cells:
                        add_req(c, "✕", "avoid")
                elif count == 1 and op in (">=", "==", "="):
                    for c in cells:
                        add_req(c, "•", "visit")
                else:
                    for c in cells:
                        add_req(c, f"×{OP_SYMBOLS.get(op, op)}{count}", "count")

        elif check == "at_steps":
            step_text = format_steps(cond)
            mode = cond.get("mode", "require")
            for c in cells:
                add_req(
                    c,
                    f"⊘{step_text}" if mode == "avoid" else f"✓{step_text}",
                    "avoid_step" if mode == "avoid" else "require_step"
                )

        elif check == "end_at":
            for c in cells:
                add_req(c, "◎", "end")

        elif check == "order":
            for i, c in enumerate(cells):
                add_req(c, str(i + 1), "order")

        elif check == "consecutive":
            for c in cells:
                add_req(c, f"⟳{cond.get('count', 2)}", "consecutive")

        elif check == "no_revisit":
            exceptions = resolve_cells(cond.get("except", []), cols, rows)
            for c in exceptions:
                add_req(c, "∞", "special")
            add_global(f"Без повторов{f' (кроме {len(exceptions)})' if exceptions else ''}", "global")

        elif check == "total_steps":
            count = cond.get("count", 0)
            add_global(f"Шагов: {OP_SYMBOLS.get(cond.get('operator', '=='), '=')}{count}", "steps")

    for cond in level_data.get("conditions", []):
        process(cond)

    return requirements, global_reqs

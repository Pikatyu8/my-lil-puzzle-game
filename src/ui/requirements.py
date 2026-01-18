import pygame

from src.core import config
from src.ui.fonts import get_font
from src.ui.text import wrap_text


def draw_requirements(surface, requirements, cell_size):
    mini = cell_size // 3
    font_size_base = int(mini * 0.65)

    for pos, reqs in requirements.items():
        x, y = pos
        base_x, base_y = x * cell_size, y * cell_size

        for i, req in enumerate(reqs[:9]):
            text, req_type = req["text"], req["type"]
            col, row = i % 3, i // 3
            cx = base_x + col * mini + mini // 2
            cy = base_y + row * mini + mini // 2
            r = int(mini * 0.4)

            colors = {
                "avoid": config.COLOR_REQUIREMENT_AVOID, "avoid_step": config.COLOR_AVOID_STEP,
                "require_step": config.COLOR_REQUIRE_STEP, "end": config.COLOR_REQUIREMENT_END,
                "visit": (255, 255, 100), "consecutive": (255, 220, 100),
                "step": config.COLOR_REQUIREMENT, "order": config.COLOR_REQUIREMENT
            }
            color = colors.get(req_type, (200, 200, 100))

            if req_type == "avoid":
                off = int(r * 0.8)
                pygame.draw.line(surface, color, (cx - off, cy - off), (cx + off, cy + off), 2)
                pygame.draw.line(surface, color, (cx + off, cy - off), (cx - off, cy + off), 2)
            elif req_type == "end":
                pygame.draw.circle(surface, color, (cx, cy), r, 1)
                pygame.draw.circle(surface, color, (cx, cy), r // 2)
            elif req_type == "visit":
                pygame.draw.circle(surface, color, (cx, cy), r)
            elif req_type == "consecutive":
                arc_rect = pygame.Rect(cx - r, cy - r, r * 2, r * 2)
                pygame.draw.arc(surface, color, arc_rect, 0.5, 5.8, 2)
                f = get_font(int(mini * 0.6), bold=True)
                ts = f.render(text.replace("⟳", ""), True, color)
                surface.blit(ts, ts.get_rect(center=(cx, cy)))
            else:
                display_text = text
                for prefix in ["⊘", "✓", "①", "$"]:
                    display_text = display_text.replace(prefix, "")

                if req_type == "avoid_step":
                    pygame.draw.circle(surface, color, (cx, cy), r, 1)
                    pygame.draw.line(surface, color, (cx - r + 2, cy + r - 2), (cx + r - 2, cy - r + 2), 2)
                elif req_type == "require_step":
                    pygame.draw.circle(surface, color, (cx, cy), r, 2)
                elif req_type == "order":
                    pygame.draw.circle(surface, color, (cx, cy), r, 1)

                current_font_size = font_size_base
                if len(display_text) > 2:
                    current_font_size = int(mini * 0.45)

                font = get_font(current_font_size, bold=True)
                ts = font.render(display_text, True, color)
                surface.blit(ts, ts.get_rect(center=(cx, cy)))


def draw_global_requirements(surface, global_reqs, font, panel_x_start):
    """Отрисовывает глобальные требования с переносом текста."""
    y = 10
    max_width = config.SIDE_PANEL_WIDTH - 30
    line_spacing = 4
    block_spacing = 12

    for req in global_reqs:
        req_type = req.get("type", "global")
        text = req["text"]

        if req_type == "steps":
            color = config.COLOR_GLOBAL_REQ
        elif req_type == "sequence":
            color = (180, 150, 255)
        elif req_type == "global":
            color = (200, 200, 200)
        else:
            color = (180, 180, 180)

        lines = wrap_text(text, font, max_width)

        total_height = sum(font.get_height() for _ in lines) + line_spacing * (len(lines) - 1)

        bg_rect = pygame.Rect(panel_x_start + 5, y - 3, config.SIDE_PANEL_WIDTH - 10, total_height + 10)
        pygame.draw.rect(surface, (20, 20, 20), bg_rect)
        pygame.draw.rect(surface, color, bg_rect, 1)

        line_y = y
        for line in lines:
            ts = font.render(line, True, color)
            surface.blit(ts, (panel_x_start + 10, line_y))
            line_y += font.get_height() + line_spacing

        y += total_height + block_spacing


def draw_editor_indicator(surface, panel_x_start, panel_height):
    try:
        font = pygame.font.SysFont("arial", 14, bold=True)
        hint_font = pygame.font.SysFont("arial", 11)
    except Exception:
        font = pygame.font.Font(None, 16)
        hint_font = pygame.font.Font(None, 13)

    text = "EDITOR MODE"
    ts = font.render(text, True, config.COLOR_EDITOR_MODE)

    x = panel_x_start + 10
    y = panel_height - 60

    bg_rect = pygame.Rect(panel_x_start + 5, y - 5, config.SIDE_PANEL_WIDTH - 10, 50)
    pygame.draw.rect(surface, (30, 15, 30), bg_rect)
    pygame.draw.rect(surface, config.COLOR_EDITOR_MODE, bg_rect, 2)

    surface.blit(ts, (x, y))

    hint = hint_font.render("Enter - reload level", True, (180, 100, 180))
    surface.blit(hint, (x, y + 22))

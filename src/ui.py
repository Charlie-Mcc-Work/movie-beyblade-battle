import pygame
from .constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, FONT_SIZES,
    UI_BG, UI_PANEL, UI_ACCENT, UI_ACCENT_HOVER, UI_TEXT, UI_TEXT_DIM,
    VICTORY_GOLD, VICTORY_GLOW, WHITE, BLACK, SPEED_OPTIONS
)


class Button:
    def __init__(self, x: int, y: int, width: int, height: int, text: str,
                 font: pygame.font.Font, color=UI_ACCENT, hover_color=UI_ACCENT_HOVER):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.color = color
        self.hover_color = hover_color
        self.hovered = False
        self.enabled = True

    def update(self, mouse_pos: tuple):
        self.hovered = self.rect.collidepoint(mouse_pos) and self.enabled

    def draw(self, screen: pygame.Surface):
        color = self.hover_color if self.hovered else self.color
        if not self.enabled:
            color = UI_TEXT_DIM

        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        pygame.draw.rect(screen, WHITE, self.rect, 2, border_radius=8)

        text_surface = self.font.render(self.text, True, WHITE if self.enabled else UI_TEXT_DIM)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def is_clicked(self, mouse_pos: tuple, mouse_pressed: bool) -> bool:
        return self.enabled and self.hovered and mouse_pressed


class TextBox:
    def __init__(self, x: int, y: int, width: int, height: int, font: pygame.font.Font):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.text = ""
        self.active = False
        self.cursor_visible = True
        self.cursor_timer = 0
        self.scroll_offset = 0

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)

        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                self.text += "\n"
            elif event.key == pygame.K_v and (event.mod & pygame.KMOD_CTRL):
                # Paste from clipboard
                try:
                    clipboard_text = pygame.scrap.get(pygame.SCRAP_TEXT)
                    if clipboard_text:
                        self.text += clipboard_text.decode('utf-8').rstrip('\x00')
                except:
                    pass
            elif event.unicode and event.unicode.isprintable():
                self.text += event.unicode

    def update(self):
        self.cursor_timer += 1
        if self.cursor_timer >= 30:
            self.cursor_timer = 0
            self.cursor_visible = not self.cursor_visible

    def draw(self, screen: pygame.Surface):
        # Background
        pygame.draw.rect(screen, UI_PANEL, self.rect, border_radius=4)
        border_color = UI_ACCENT if self.active else UI_TEXT_DIM
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=4)

        # Text area with padding
        text_area = self.rect.inflate(-20, -20)
        lines = self.text.split('\n')

        # Calculate visible lines
        line_height = self.font.get_linesize()
        max_visible_lines = text_area.height // line_height

        # Auto-scroll to show latest lines
        if len(lines) > max_visible_lines:
            self.scroll_offset = len(lines) - max_visible_lines
        else:
            self.scroll_offset = 0

        # Draw lines
        y = text_area.top
        for i, line in enumerate(lines[self.scroll_offset:]):
            if y + line_height > text_area.bottom:
                break
            text_surface = self.font.render(line[:80], True, UI_TEXT)  # Truncate long lines
            screen.blit(text_surface, (text_area.left, y))
            y += line_height

        # Cursor
        if self.active and self.cursor_visible:
            cursor_x = text_area.left + self.font.size(lines[-1] if lines else "")[0]
            cursor_y = min(text_area.top + (len(lines) - self.scroll_offset - 1) * line_height,
                          text_area.bottom - line_height)
            if cursor_y >= text_area.top:
                pygame.draw.line(screen, UI_TEXT, (cursor_x, cursor_y),
                               (cursor_x, cursor_y + line_height), 2)

    def get_entries(self) -> list:
        """Parse text into list of movie titles."""
        lines = self.text.strip().split('\n')
        entries = [line.strip() for line in lines if line.strip()]
        return entries


class InputScreen:
    def __init__(self, fonts: dict):
        self.fonts = fonts
        center_x = WINDOW_WIDTH // 2

        self.text_box = TextBox(center_x - 300, 150, 600, 450, fonts['small'])
        self.battle_button = Button(center_x - 100, 630, 200, 50, "BATTLE!", fonts['medium'])

        self.error_message = ""
        self.error_timer = 0

    def handle_event(self, event: pygame.event.Event):
        self.text_box.handle_event(event)

    def update(self, mouse_pos: tuple) -> tuple:
        """Returns (should_start, movie_list)"""
        self.text_box.update()
        self.battle_button.update(mouse_pos)

        entries = self.text_box.get_entries()
        self.battle_button.enabled = len(entries) >= 2

        if self.error_timer > 0:
            self.error_timer -= 1

        return (False, [])

    def check_start(self, mouse_pos: tuple, mouse_clicked: bool) -> tuple:
        """Check if battle should start. Returns (should_start, movie_list)"""
        if self.battle_button.is_clicked(mouse_pos, mouse_clicked):
            entries = self.text_box.get_entries()
            if len(entries) >= 2:
                return (True, entries)
            else:
                self.error_message = "Need at least 2 movies!"
                self.error_timer = 120
        return (False, [])

    def draw(self, screen: pygame.Surface):
        screen.fill(UI_BG)

        # Title
        title = self.fonts['title'].render("MOVIE BEYBLADE BATTLE", True, UI_ACCENT)
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 60))
        screen.blit(title, title_rect)

        # Subtitle
        subtitle = self.fonts['small'].render("Enter movie titles (one per line) and let them fight!", True, UI_TEXT_DIM)
        subtitle_rect = subtitle.get_rect(center=(WINDOW_WIDTH // 2, 110))
        screen.blit(subtitle, subtitle_rect)

        # Text box
        self.text_box.draw(screen)

        # Entry count
        entries = self.text_box.get_entries()
        count_text = f"{len(entries)} movies entered"
        count_surface = self.fonts['small'].render(count_text, True, UI_TEXT_DIM)
        screen.blit(count_surface, (WINDOW_WIDTH // 2 - 300, 610))

        # Battle button
        self.battle_button.draw(screen)

        # Error message
        if self.error_timer > 0 and self.error_message:
            error_surface = self.fonts['medium'].render(self.error_message, True, (255, 100, 100))
            error_rect = error_surface.get_rect(center=(WINDOW_WIDTH // 2, 700))
            screen.blit(error_surface, error_rect)

        # Instructions
        instructions = [
            "Tip: Paste your movie list with Ctrl+V",
            "Each movie becomes a beyblade with random stats"
        ]
        y = 720
        for inst in instructions:
            text = self.fonts['tiny'].render(inst, True, UI_TEXT_DIM)
            rect = text.get_rect(center=(WINDOW_WIDTH // 2, y))
            screen.blit(text, rect)
            y += 20


class BattleHUD:
    def __init__(self, fonts: dict):
        self.fonts = fonts
        self.speed_buttons = []
        self.current_speed = 1

        # Speed control buttons
        for i, speed in enumerate(SPEED_OPTIONS):
            btn = Button(
                WINDOW_WIDTH - 180 + i * 55, 10, 50, 30,
                f"{speed}x", fonts['small']
            )
            self.speed_buttons.append((speed, btn))

    def update(self, mouse_pos: tuple):
        for speed, btn in self.speed_buttons:
            btn.update(mouse_pos)
            btn.color = UI_ACCENT if speed == self.current_speed else UI_PANEL

    def check_speed_click(self, mouse_pos: tuple, mouse_clicked: bool) -> int:
        if mouse_clicked:
            for speed, btn in self.speed_buttons:
                if btn.is_clicked(mouse_pos, True):
                    self.current_speed = speed
                    return speed
        return self.current_speed

    def draw(self, screen: pygame.Surface, alive_count: int, total_count: int, eliminated: list):
        # Top bar background
        pygame.draw.rect(screen, (0, 0, 0, 180), (0, 0, WINDOW_WIDTH, 50))

        # Remaining count
        remaining_text = f"Remaining: {alive_count} / {total_count}"
        text_surface = self.fonts['medium'].render(remaining_text, True, WHITE)
        screen.blit(text_surface, (20, 12))

        # Speed label
        speed_label = self.fonts['small'].render("Speed:", True, UI_TEXT_DIM)
        screen.blit(speed_label, (WINDOW_WIDTH - 250, 15))

        # Speed buttons
        for _, btn in self.speed_buttons:
            btn.draw(screen)

        # Eliminated list (right side panel)
        if eliminated:
            panel_width = 200
            panel_x = WINDOW_WIDTH - panel_width - 10
            panel_y = 60
            panel_height = min(400, len(eliminated) * 25 + 40)

            # Panel background
            panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
            panel_surface.fill((0, 0, 0, 150))
            screen.blit(panel_surface, (panel_x, panel_y))

            # Title
            elim_title = self.fonts['small'].render("ELIMINATED", True, (255, 100, 100))
            screen.blit(elim_title, (panel_x + 10, panel_y + 5))

            # List (show most recent first, limited number)
            y = panel_y + 30
            max_show = min(15, len(eliminated))
            for name in reversed(eliminated[-max_show:]):
                display_name = name if len(name) <= 22 else name[:19] + "..."
                name_surface = self.fonts['tiny'].render(display_name, True, UI_TEXT_DIM)
                screen.blit(name_surface, (panel_x + 10, y))
                y += 22


class VictoryScreen:
    def __init__(self, fonts: dict):
        self.fonts = fonts
        center_x = WINDOW_WIDTH // 2
        self.play_again_button = Button(center_x - 110, 550, 220, 50, "PLAY AGAIN", fonts['medium'])
        self.winner_name = ""
        self.animation_timer = 0

    def set_winner(self, name: str):
        self.winner_name = name
        self.animation_timer = 0

    def update(self, mouse_pos: tuple):
        self.animation_timer += 1
        self.play_again_button.update(mouse_pos)

    def check_restart(self, mouse_pos: tuple, mouse_clicked: bool) -> bool:
        return self.play_again_button.is_clicked(mouse_pos, mouse_clicked)

    def draw(self, screen: pygame.Surface):
        # Darken background
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))

        center_x = WINDOW_WIDTH // 2
        center_y = WINDOW_HEIGHT // 2

        # Pulsing glow effect
        pulse = abs((self.animation_timer % 60) - 30) / 30
        glow_size = int(300 + pulse * 50)

        # Draw glow circles
        for i in range(5):
            alpha = int(30 - i * 5)
            glow_color = (*VICTORY_GLOW[:3], alpha)
            glow_surface = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_surface, glow_color, (glow_size, glow_size), glow_size - i * 20)
            screen.blit(glow_surface, (center_x - glow_size, center_y - 150 - glow_size // 2))

        # "WINNER" text
        winner_label = self.fonts['title'].render("WINNER!", True, VICTORY_GOLD)
        winner_rect = winner_label.get_rect(center=(center_x, center_y - 150))

        # Shadow
        shadow_label = self.fonts['title'].render("WINNER!", True, (100, 80, 0))
        shadow_rect = shadow_label.get_rect(center=(center_x + 3, center_y - 147))
        screen.blit(shadow_label, shadow_rect)
        screen.blit(winner_label, winner_rect)

        # Movie title
        title_surface = self.fonts['huge'].render(self.winner_name, True, WHITE)
        title_rect = title_surface.get_rect(center=(center_x, center_y))

        # If title is too wide, use smaller font
        if title_rect.width > WINDOW_WIDTH - 100:
            title_surface = self.fonts['title'].render(self.winner_name, True, WHITE)
            title_rect = title_surface.get_rect(center=(center_x, center_y))

        # Still too wide? Truncate
        if title_rect.width > WINDOW_WIDTH - 100:
            truncated = self.winner_name[:30] + "..."
            title_surface = self.fonts['title'].render(truncated, True, WHITE)
            title_rect = title_surface.get_rect(center=(center_x, center_y))

        # Shadow for title
        shadow_surface = self.fonts['huge'].render(self.winner_name, True, (50, 50, 50))
        shadow_rect = shadow_surface.get_rect(center=(center_x + 3, center_y + 3))
        screen.blit(shadow_surface, shadow_rect)
        screen.blit(title_surface, title_rect)

        # Subtitle
        subtitle = self.fonts['medium'].render("Tonight's movie pick!", True, VICTORY_GLOW)
        subtitle_rect = subtitle.get_rect(center=(center_x, center_y + 80))
        screen.blit(subtitle, subtitle_rect)

        # Play again button
        self.play_again_button.draw(screen)


def create_fonts() -> dict:
    pygame.font.init()
    fonts = {}
    for name, size in FONT_SIZES.items():
        try:
            fonts[name] = pygame.font.SysFont('Arial', size, bold=(name in ['title', 'huge', 'large']))
        except:
            fonts[name] = pygame.font.Font(None, size)
    return fonts

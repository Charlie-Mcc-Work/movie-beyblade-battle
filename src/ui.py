import pygame
import os
from .constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, FONT_SIZES,
    UI_BG, UI_PANEL, UI_ACCENT, UI_ACCENT_HOVER, UI_TEXT, UI_TEXT_DIM,
    VICTORY_GOLD, VICTORY_GLOW, WHITE, BLACK, SPEED_OPTIONS,
    MOVIE_LIST_FILE, QUEUE_FILE, WATCHED_FILE
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

    def load_from_file(self, filepath: str) -> bool:
        """Load text from file. Returns True if successful."""
        try:
            with open(filepath, 'r') as f:
                self.text = f.read()
            return True
        except FileNotFoundError:
            return False


class InputScreen:
    def __init__(self, fonts: dict):
        self.fonts = fonts
        self.window_width = WINDOW_WIDTH
        self.window_height = WINDOW_HEIGHT
        center_x = WINDOW_WIDTH // 2

        self.text_box = TextBox(center_x - 300, 150, 600, 450, fonts['small'])
        if os.path.exists(MOVIE_LIST_FILE):
            self.text_box.load_from_file(MOVIE_LIST_FILE)
        self.battle_button = Button(center_x - 100, 630, 200, 50, "BATTLE!", fonts['medium'])

        self.error_message = ""
        self.error_timer = 0

        # Queue display
        self.queue_items = []
        self.queue_rects = []  # Clickable areas for queue items
        self.load_queue()

    def update_layout(self, window_width: int, window_height: int):
        """Update positions based on new window size."""
        self.window_width = window_width
        self.window_height = window_height
        center_x = window_width // 2

        # Recalculate text box size based on window
        box_width = min(600, window_width - 100)
        box_height = min(450, window_height - 250)
        self.text_box.rect = pygame.Rect(center_x - box_width // 2, 150, box_width, box_height)

        # Reposition button
        button_y = min(630, window_height - 170)
        self.battle_button.rect = pygame.Rect(center_x - 100, button_y, 200, 50)

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

    def load_queue(self):
        """Load queue items from queue.txt."""
        self.queue_items = []
        if os.path.exists(QUEUE_FILE):
            try:
                with open(QUEUE_FILE, 'r') as f:
                    lines = f.read().strip().split('\n')
                    self.queue_items = [line.strip() for line in lines if line.strip()]
            except:
                pass

    def check_queue_click(self, mouse_pos: tuple, mouse_clicked: bool) -> str:
        """Check if a queue item was clicked. Returns the item name if clicked, None otherwise."""
        if not mouse_clicked:
            return None
        for i, rect in enumerate(self.queue_rects):
            if rect.collidepoint(mouse_pos) and i < len(self.queue_items):
                return self.queue_items[i]
        return None

    def remove_from_queue(self, movie_name: str):
        """Remove a movie from the queue and update the file."""
        if movie_name in self.queue_items:
            self.queue_items.remove(movie_name)
            # Write updated queue to file
            with open(QUEUE_FILE, 'w') as f:
                f.write('\n'.join(self.queue_items))

    def draw(self, screen: pygame.Surface):
        screen.fill(UI_BG)
        center_x = self.window_width // 2

        # Title
        title = self.fonts['title'].render("MOVIE BEYBLADE BATTLE", True, UI_ACCENT)
        title_rect = title.get_rect(center=(center_x, 60))
        screen.blit(title, title_rect)

        # Subtitle
        subtitle = self.fonts['small'].render("Enter movie titles (one per line) and let them fight!", True, UI_TEXT_DIM)
        subtitle_rect = subtitle.get_rect(center=(center_x, 110))
        screen.blit(subtitle, subtitle_rect)

        # Text box
        self.text_box.draw(screen)

        # Entry count
        entries = self.text_box.get_entries()
        count_text = f"{len(entries)} movies entered"
        count_surface = self.fonts['small'].render(count_text, True, UI_TEXT_DIM)
        screen.blit(count_surface, (self.text_box.rect.left, self.text_box.rect.bottom + 10))

        # Battle button
        self.battle_button.draw(screen)

        # Error message
        if self.error_timer > 0 and self.error_message:
            error_surface = self.fonts['medium'].render(self.error_message, True, (255, 100, 100))
            error_rect = error_surface.get_rect(center=(center_x, self.battle_button.rect.bottom + 30))
            screen.blit(error_surface, error_rect)

        # Instructions
        instructions = [
            "Tip: Paste your movie list with Ctrl+V",
            "Each movie becomes a beyblade with random stats"
        ]
        y = self.window_height - 60
        for inst in instructions:
            text = self.fonts['tiny'].render(inst, True, UI_TEXT_DIM)
            rect = text.get_rect(center=(center_x, y))
            screen.blit(text, rect)
            y += 20

        # Queue panel on the right side
        if self.queue_items:
            panel_width = 250
            panel_x = self.window_width - panel_width - 20
            panel_y = 150
            line_height = 28
            max_items = min(10, len(self.queue_items))
            panel_height = max_items * line_height + 60

            # Panel background
            panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
            panel_surface.fill((40, 40, 55, 230))
            screen.blit(panel_surface, (panel_x, panel_y))
            pygame.draw.rect(screen, (255, 180, 100), (panel_x, panel_y, panel_width, panel_height), 2, border_radius=8)

            # Title
            queue_title = self.fonts['medium'].render("QUEUE", True, (255, 180, 100))
            screen.blit(queue_title, (panel_x + 10, panel_y + 8))

            # Subtitle
            queue_sub = self.fonts['tiny'].render("Click to remove from queue", True, UI_TEXT_DIM)
            screen.blit(queue_sub, (panel_x + 10, panel_y + 35))

            # Queue items (clickable)
            self.queue_rects = []
            item_y = panel_y + 55
            for i, item in enumerate(self.queue_items[:max_items]):
                display_name = item if len(item) <= 25 else item[:22] + "..."

                # Clickable area
                item_rect = pygame.Rect(panel_x + 5, item_y, panel_width - 10, line_height - 2)
                self.queue_rects.append(item_rect)

                # Highlight on hover
                mouse_pos = pygame.mouse.get_pos()
                if item_rect.collidepoint(mouse_pos):
                    pygame.draw.rect(screen, (80, 60, 50), item_rect, border_radius=4)

                # Item text
                item_text = self.fonts['small'].render(f"  {display_name}", True, (255, 200, 150))
                screen.blit(item_text, (panel_x + 10, item_y + 4))

                item_y += line_height

            # Show if there are more items
            if len(self.queue_items) > max_items:
                more_text = self.fonts['tiny'].render(f"+{len(self.queue_items) - max_items} more...", True, UI_TEXT_DIM)
                screen.blit(more_text, (panel_x + 10, item_y))


class BattleHUD:
    def __init__(self, fonts: dict):
        self.fonts = fonts
        self.speed_buttons = []
        self.current_speed = 1
        self.muted = False
        self.window_width = WINDOW_WIDTH
        self.window_height = WINDOW_HEIGHT

        # Speed control buttons (shifted left to make room for mute)
        for i, speed in enumerate(SPEED_OPTIONS):
            btn = Button(
                WINDOW_WIDTH - 240 + i * 55, 10, 50, 30,
                f"{speed}x", fonts['small']
            )
            self.speed_buttons.append((speed, btn))

        # Mute button (top right corner, after speed buttons)
        self.mute_button = Button(
            WINDOW_WIDTH - 65, 10, 55, 30,
            "MUTE", fonts['tiny'], color=(80, 80, 100)
        )

    def update_layout(self, window_width: int, window_height: int):
        """Update positions based on new window size."""
        self.window_width = window_width
        self.window_height = window_height

        # Reposition speed buttons
        for i, (speed, btn) in enumerate(self.speed_buttons):
            btn.rect.x = window_width - 240 + i * 55

        # Reposition mute button
        self.mute_button.rect.x = window_width - 65

    def update(self, mouse_pos: tuple):
        for speed, btn in self.speed_buttons:
            btn.update(mouse_pos)
            btn.color = UI_ACCENT if speed == self.current_speed else UI_PANEL
        self.mute_button.update(mouse_pos)
        self.mute_button.text = "UNMUTE" if self.muted else "MUTE"
        self.mute_button.color = (255, 100, 100) if self.muted else (80, 80, 100)

    def check_speed_click(self, mouse_pos: tuple, mouse_clicked: bool) -> int:
        if mouse_clicked:
            for speed, btn in self.speed_buttons:
                if btn.is_clicked(mouse_pos, True):
                    self.current_speed = speed
                    return speed
        return self.current_speed

    def check_mute_click(self, mouse_pos: tuple, mouse_clicked: bool) -> bool:
        """Check if mute button was clicked. Returns True if mute state toggled."""
        if mouse_clicked and self.mute_button.is_clicked(mouse_pos, True):
            self.muted = not self.muted
            return True
        return False

    def draw(self, screen: pygame.Surface, alive_count: int, total_count: int, eliminated: list, survivors: list = None, round_number: int = 1, heat_info: tuple = None):
        # Top bar background
        pygame.draw.rect(screen, (0, 0, 0, 180), (0, 0, self.window_width, 50))

        x_offset = 20

        # Heat info (if tournament mode)
        if heat_info:
            heat_text, _ = heat_info
            heat_color = (255, 100, 100) if heat_text == "FINALS" else (100, 200, 255)
            heat_surface = self.fonts['medium'].render(heat_text, True, heat_color)
            screen.blit(heat_surface, (x_offset, 12))
            x_offset += heat_surface.get_width() + 20

        # Round number
        round_text = f"Round {round_number}"
        round_surface = self.fonts['medium'].render(round_text, True, VICTORY_GOLD)
        screen.blit(round_surface, (x_offset, 12))
        x_offset += round_surface.get_width() + 20

        # Remaining count
        remaining_text = f"Remaining: {alive_count} / {total_count}"
        text_surface = self.fonts['medium'].render(remaining_text, True, WHITE)
        screen.blit(text_surface, (x_offset, 12))

        # Speed label
        speed_label = self.fonts['small'].render("Speed:", True, UI_TEXT_DIM)
        screen.blit(speed_label, (self.window_width - 310, 15))

        # Speed buttons
        for _, btn in self.speed_buttons:
            btn.draw(screen)

        # Mute button
        self.mute_button.draw(screen)

        # Right side panels
        panel_width = 200
        panel_x = self.window_width - panel_width - 10
        current_y = 60

        # Eliminated list
        if eliminated:
            max_elim_show = min(12, len(eliminated))
            panel_height = max_elim_show * 20 + 35

            # Panel background
            panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
            panel_surface.fill((0, 0, 0, 150))
            screen.blit(panel_surface, (panel_x, current_y))

            # Title
            elim_title = self.fonts['small'].render("ELIMINATED", True, (255, 100, 100))
            screen.blit(elim_title, (panel_x + 10, current_y + 5))

            # List (show most recent first)
            y = current_y + 28
            for name in reversed(eliminated[-max_elim_show:]):
                display_name = name if len(name) <= 22 else name[:19] + "..."
                name_surface = self.fonts['tiny'].render(display_name, True, UI_TEXT_DIM)
                screen.blit(name_surface, (panel_x + 10, y))
                y += 20

            current_y += panel_height + 10

        # Survivors list
        if survivors:
            max_surv_show = min(12, len(survivors))
            panel_height = max_surv_show * 20 + 35

            # Panel background
            panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
            panel_surface.fill((0, 0, 0, 150))
            screen.blit(panel_surface, (panel_x, current_y))

            # Title
            surv_title = self.fonts['small'].render("SURVIVORS", True, (100, 255, 100))
            screen.blit(surv_title, (panel_x + 10, current_y + 5))

            # List
            y = current_y + 28
            for name in survivors[:max_surv_show]:
                display_name = name if len(name) <= 22 else name[:19] + "..."
                name_surface = self.fonts['tiny'].render(display_name, True, (150, 255, 150))
                screen.blit(name_surface, (panel_x + 10, y))
                y += 20


class HeatTransitionScreen:
    """Screen shown between heats to display who advances."""
    def __init__(self, fonts: dict):
        self.fonts = fonts
        self.window_width = WINDOW_WIDTH
        self.window_height = WINDOW_HEIGHT
        center_x = WINDOW_WIDTH // 2
        self.continue_button = Button(center_x - 110, 600, 220, 50, "CONTINUE", fonts['medium'])
        self.advancers = []
        self.heat_number = 0
        self.total_heats = 0
        self.is_to_finals = False
        self.animation_timer = 0

    def update_layout(self, window_width: int, window_height: int):
        self.window_width = window_width
        self.window_height = window_height
        center_x = window_width // 2
        self.continue_button.rect = pygame.Rect(center_x - 110, window_height - 100, 220, 50)

    def set_advancers(self, advancers: list, heat_number: int, total_heats: int, is_to_finals: bool = False):
        self.advancers = advancers
        self.heat_number = heat_number
        self.total_heats = total_heats
        self.is_to_finals = is_to_finals
        self.animation_timer = 0

    def update(self, mouse_pos: tuple):
        self.animation_timer += 1
        self.continue_button.update(mouse_pos)

    def check_continue(self, mouse_pos: tuple, mouse_clicked: bool) -> bool:
        return self.continue_button.is_clicked(mouse_pos, mouse_clicked)

    def draw(self, screen: pygame.Surface):
        # Darken background
        overlay = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        screen.blit(overlay, (0, 0))

        center_x = self.window_width // 2
        center_y = self.window_height // 2

        # Title
        if self.is_to_finals:
            title_text = "ADVANCING TO FINALS!"
            title_color = (255, 215, 0)
        else:
            title_text = f"HEAT {self.heat_number} COMPLETE!"
            title_color = (100, 200, 255)

        title = self.fonts['title'].render(title_text, True, title_color)
        title_rect = title.get_rect(center=(center_x, 80))
        screen.blit(title, title_rect)

        # Subtitle
        if not self.is_to_finals:
            subtitle_text = f"Top {len(self.advancers)} advance to the next round"
        else:
            subtitle_text = f"{len(self.advancers)} contestants will battle in the finals!"
        subtitle = self.fonts['medium'].render(subtitle_text, True, UI_TEXT_DIM)
        subtitle_rect = subtitle.get_rect(center=(center_x, 130))
        screen.blit(subtitle, subtitle_rect)

        # Advancers list
        start_y = 180
        for i, name in enumerate(self.advancers):
            # Animate entry
            delay = i * 10
            if self.animation_timer > delay:
                alpha = min(1.0, (self.animation_timer - delay) / 20)
                display_name = name if len(name) <= 35 else name[:32] + "..."

                color = tuple(int(c * alpha) for c in (100, 255, 100))
                text = self.fonts['medium'].render(f"★ {display_name}", True, color)
                text_rect = text.get_rect(center=(center_x, start_y + i * 35))
                screen.blit(text, text_rect)

        # Continue button
        self.continue_button.draw(screen)


class VictoryScreen:
    def __init__(self, fonts: dict):
        self.fonts = fonts
        self.window_width = WINDOW_WIDTH
        self.window_height = WINDOW_HEIGHT
        center_x = WINDOW_WIDTH // 2
        self.leaderboard_button = Button(center_x - 130, 550, 260, 50, "SHOW LEADERBOARD", fonts['medium'])
        self.winner_name = ""
        self.animation_timer = 0

    def update_layout(self, window_width: int, window_height: int):
        """Update positions based on new window size."""
        self.window_width = window_width
        self.window_height = window_height
        center_x = window_width // 2
        center_y = window_height // 2
        self.leaderboard_button.rect = pygame.Rect(center_x - 130, center_y + 150, 260, 50)

    def set_winner(self, name: str):
        self.winner_name = name
        self.animation_timer = 0

    def update(self, mouse_pos: tuple):
        self.animation_timer += 1
        self.leaderboard_button.update(mouse_pos)

    def check_leaderboard(self, mouse_pos: tuple, mouse_clicked: bool) -> bool:
        return self.leaderboard_button.is_clicked(mouse_pos, mouse_clicked)

    def draw(self, screen: pygame.Surface):
        # Darken background
        overlay = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))

        center_x = self.window_width // 2
        center_y = self.window_height // 2

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
        if title_rect.width > self.window_width - 100:
            title_surface = self.fonts['title'].render(self.winner_name, True, WHITE)
            title_rect = title_surface.get_rect(center=(center_x, center_y))

        # Still too wide? Truncate
        if title_rect.width > self.window_width - 100:
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

        # Leaderboard button
        self.leaderboard_button.draw(screen)


class LeaderboardScreen:
    """Shows final rankings of all contestants."""
    def __init__(self, fonts: dict):
        self.fonts = fonts
        self.window_width = WINDOW_WIDTH
        self.window_height = WINDOW_HEIGHT
        center_x = WINDOW_WIDTH // 2
        # Top row buttons (for winner actions)
        self.choose_button = Button(center_x - 250, 700, 150, 50, "CHOOSE", fonts['medium'], color=(50, 150, 50), hover_color=(70, 200, 70))
        self.queue_button = Button(center_x - 75, 700, 150, 50, "QUEUE", fonts['medium'], color=(200, 150, 50), hover_color=(255, 180, 70))
        # Bottom row buttons
        self.play_again_button = Button(center_x + 100, 700, 150, 50, "PLAY AGAIN", fonts['medium'])
        self.quit_button = Button(center_x + 270, 700, 100, 50, "QUIT", fonts['medium'], color=(150, 60, 60), hover_color=(200, 80, 80))
        self.rankings = []  # List of names from winner to last eliminated
        self.scroll_offset = 0
        self.winner_name = ""

    def update_layout(self, window_width: int, window_height: int):
        self.window_width = window_width
        self.window_height = window_height
        center_x = window_width // 2
        self.choose_button.rect = pygame.Rect(center_x - 340, window_height - 80, 150, 50)
        self.queue_button.rect = pygame.Rect(center_x - 165, window_height - 80, 150, 50)
        self.play_again_button.rect = pygame.Rect(center_x + 10, window_height - 80, 150, 50)
        self.quit_button.rect = pygame.Rect(center_x + 185, window_height - 80, 100, 50)

    def set_rankings(self, winner: str, eliminated: list):
        """Set rankings from winner (1st) and elimination order (last eliminated = 2nd)."""
        self.rankings = [winner] + list(reversed(eliminated))
        self.scroll_offset = 0
        self.winner_name = winner

    def update(self, mouse_pos: tuple):
        self.play_again_button.update(mouse_pos)
        self.quit_button.update(mouse_pos)
        self.choose_button.update(mouse_pos)
        self.queue_button.update(mouse_pos)

    def handle_scroll(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEWHEEL:
            self.scroll_offset -= event.y * 3
            max_scroll = max(0, len(self.rankings) - 15)
            self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

    def check_play_again(self, mouse_pos: tuple, mouse_clicked: bool) -> bool:
        return self.play_again_button.is_clicked(mouse_pos, mouse_clicked)

    def check_quit(self, mouse_pos: tuple, mouse_clicked: bool) -> bool:
        return self.quit_button.is_clicked(mouse_pos, mouse_clicked)

    def check_choose(self, mouse_pos: tuple, mouse_clicked: bool) -> bool:
        return self.choose_button.is_clicked(mouse_pos, mouse_clicked)

    def check_queue(self, mouse_pos: tuple, mouse_clicked: bool) -> bool:
        return self.queue_button.is_clicked(mouse_pos, mouse_clicked)

    def draw(self, screen: pygame.Surface):
        screen.fill(UI_BG)

        center_x = self.window_width // 2

        # Title
        title = self.fonts['title'].render("LEADERBOARD", True, VICTORY_GOLD)
        title_rect = title.get_rect(center=(center_x, 50))
        screen.blit(title, title_rect)

        # Rankings
        start_y = 110
        line_height = 32
        max_visible = min(18, (self.window_height - 200) // line_height)

        for i, name in enumerate(self.rankings[self.scroll_offset:self.scroll_offset + max_visible]):
            rank = i + self.scroll_offset + 1
            y = start_y + i * line_height

            # Medal colors for top 3
            if rank == 1:
                color = (255, 215, 0)  # Gold
                prefix = "🥇"
            elif rank == 2:
                color = (192, 192, 192)  # Silver
                prefix = "🥈"
            elif rank == 3:
                color = (205, 127, 50)  # Bronze
                prefix = "🥉"
            else:
                color = UI_TEXT
                prefix = f"{rank}."

            display_name = name if len(name) <= 40 else name[:37] + "..."

            # Rank
            rank_text = self.fonts['medium'].render(f"{prefix}", True, color)
            screen.blit(rank_text, (center_x - 280, y))

            # Name
            name_text = self.fonts['medium'].render(display_name, True, color)
            screen.blit(name_text, (center_x - 220, y))

        # Scroll indicator
        if len(self.rankings) > max_visible:
            scroll_text = f"Showing {self.scroll_offset + 1}-{min(self.scroll_offset + max_visible, len(self.rankings))} of {len(self.rankings)}"
            scroll_surface = self.fonts['tiny'].render(scroll_text, True, UI_TEXT_DIM)
            scroll_rect = scroll_surface.get_rect(center=(center_x, self.window_height - 120))
            screen.blit(scroll_surface, scroll_rect)

        # Buttons
        self.choose_button.draw(screen)
        self.queue_button.draw(screen)
        self.play_again_button.draw(screen)
        self.quit_button.draw(screen)

        # Button labels
        choose_label = self.fonts['tiny'].render("Watch this movie", True, UI_TEXT_DIM)
        screen.blit(choose_label, (self.choose_button.rect.centerx - choose_label.get_width() // 2, self.choose_button.rect.bottom + 5))

        queue_label = self.fonts['tiny'].render("Add to queue, replay", True, UI_TEXT_DIM)
        screen.blit(queue_label, (self.queue_button.rect.centerx - queue_label.get_width() // 2, self.queue_button.rect.bottom + 5))


def create_fonts() -> dict:
    pygame.font.init()
    fonts = {}
    for name, size in FONT_SIZES.items():
        try:
            fonts[name] = pygame.font.SysFont('Arial', size, bold=(name in ['title', 'huge', 'large']))
        except:
            fonts[name] = pygame.font.Font(None, size)
    return fonts

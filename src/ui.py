import pygame
import os
from .constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, FONT_SIZES,
    UI_BG, UI_PANEL, UI_ACCENT, UI_ACCENT_HOVER, UI_TEXT, UI_TEXT_DIM,
    VICTORY_GOLD, VICTORY_GLOW, WHITE, BLACK, SPEED_OPTIONS,
    MOVIE_LIST_FILE, QUEUE_FILE, WATCHED_FILE, ABILITY_WINS_FILE,
    GOLDEN_DOCKET_FILE, DIAMOND_DOCKET_FILE, SHIT_DOCKET_FILE,
    DOCKET_GOLDEN, DOCKET_GOLDEN_DARK, DOCKET_DIAMOND, DOCKET_DIAMOND_DARK,
    DOCKET_SHIT, DOCKET_SHIT_DARK, ABILITIES
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
    def __init__(self, x: int, y: int, width: int, height: int, font: pygame.font.Font, save_path: str = None):
        self.rect = pygame.Rect(x, y, width, height)
        self.font = font
        self.text = ""
        self.active = False
        self.cursor_visible = True
        self.cursor_timer = 0
        self.scroll_offset = 0
        self.save_path = save_path  # File to auto-save to
        self._last_saved_text = ""  # Track changes for auto-save
        self.cursor_line = 0  # Which line the cursor is on
        self.cursor_pos = 0   # Position within the line

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            was_active = self.active
            self.active = self.rect.collidepoint(event.pos)
            # Click to position cursor
            if self.active and event.button == 1:
                self._click_to_cursor(event.pos)

        # Mousewheel scrolling (works when hovering over text box)
        if event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                lines = self.text.split('\n')
                line_height = self.font.get_linesize()
                max_visible = max(1, (self.rect.height - 20) // line_height)
                max_scroll = max(0, len(lines) - max_visible)
                # Scroll up (positive y) or down (negative y)
                self.scroll_offset -= event.y * 3  # 3 lines per scroll
                self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

        if event.type == pygame.KEYDOWN and self.active:
            lines = self.text.split('\n')
            text_changed = False

            if event.key == pygame.K_BACKSPACE:
                if self.cursor_pos > 0:
                    # Delete character before cursor
                    line = lines[self.cursor_line]
                    lines[self.cursor_line] = line[:self.cursor_pos - 1] + line[self.cursor_pos:]
                    self.cursor_pos -= 1
                    text_changed = True
                elif self.cursor_line > 0:
                    # Merge with previous line
                    prev_len = len(lines[self.cursor_line - 1])
                    lines[self.cursor_line - 1] += lines[self.cursor_line]
                    lines.pop(self.cursor_line)
                    self.cursor_line -= 1
                    self.cursor_pos = prev_len
                    text_changed = True
            elif event.key == pygame.K_DELETE:
                line = lines[self.cursor_line]
                if self.cursor_pos < len(line):
                    lines[self.cursor_line] = line[:self.cursor_pos] + line[self.cursor_pos + 1:]
                    text_changed = True
                elif self.cursor_line < len(lines) - 1:
                    # Merge with next line
                    lines[self.cursor_line] += lines[self.cursor_line + 1]
                    lines.pop(self.cursor_line + 1)
                    text_changed = True
            elif event.key == pygame.K_RETURN:
                # Split line at cursor
                line = lines[self.cursor_line]
                lines[self.cursor_line] = line[:self.cursor_pos]
                lines.insert(self.cursor_line + 1, line[self.cursor_pos:])
                self.cursor_line += 1
                self.cursor_pos = 0
                text_changed = True
            elif event.key == pygame.K_UP:
                if self.cursor_line > 0:
                    self.cursor_line -= 1
                    self.cursor_pos = min(self.cursor_pos, len(lines[self.cursor_line]))
                    self._ensure_cursor_visible()
            elif event.key == pygame.K_DOWN:
                if self.cursor_line < len(lines) - 1:
                    self.cursor_line += 1
                    self.cursor_pos = min(self.cursor_pos, len(lines[self.cursor_line]))
                    self._ensure_cursor_visible()
            elif event.key == pygame.K_LEFT:
                if self.cursor_pos > 0:
                    self.cursor_pos -= 1
                elif self.cursor_line > 0:
                    self.cursor_line -= 1
                    self.cursor_pos = len(lines[self.cursor_line])
                    self._ensure_cursor_visible()
            elif event.key == pygame.K_RIGHT:
                if self.cursor_pos < len(lines[self.cursor_line]):
                    self.cursor_pos += 1
                elif self.cursor_line < len(lines) - 1:
                    self.cursor_line += 1
                    self.cursor_pos = 0
                    self._ensure_cursor_visible()
            elif event.key == pygame.K_HOME:
                self.cursor_pos = 0
            elif event.key == pygame.K_END:
                self.cursor_pos = len(lines[self.cursor_line])
            elif event.key == pygame.K_v and (event.mod & pygame.KMOD_CTRL):
                # Paste from clipboard
                try:
                    clipboard_text = pygame.scrap.get(pygame.SCRAP_TEXT)
                    if clipboard_text:
                        paste_text = clipboard_text.decode('utf-8').rstrip('\x00')
                        paste_lines = paste_text.split('\n')
                        # Insert at cursor
                        line = lines[self.cursor_line]
                        if len(paste_lines) == 1:
                            lines[self.cursor_line] = line[:self.cursor_pos] + paste_lines[0] + line[self.cursor_pos:]
                            self.cursor_pos += len(paste_lines[0])
                        else:
                            # Multi-line paste
                            after_cursor = line[self.cursor_pos:]
                            lines[self.cursor_line] = line[:self.cursor_pos] + paste_lines[0]
                            for i, paste_line in enumerate(paste_lines[1:-1], 1):
                                lines.insert(self.cursor_line + i, paste_line)
                            lines.insert(self.cursor_line + len(paste_lines) - 1, paste_lines[-1] + after_cursor)
                            self.cursor_line += len(paste_lines) - 1
                            self.cursor_pos = len(paste_lines[-1])
                        text_changed = True
                except:
                    pass
            elif event.unicode and event.unicode.isprintable():
                # Insert character at cursor
                line = lines[self.cursor_line]
                lines[self.cursor_line] = line[:self.cursor_pos] + event.unicode + line[self.cursor_pos:]
                self.cursor_pos += 1
                text_changed = True

            if text_changed:
                self.text = '\n'.join(lines)
                self._auto_save()

    def _click_to_cursor(self, pos):
        """Position cursor based on click location."""
        lines = self.text.split('\n')
        line_height = self.font.get_linesize()
        padding = min(10, self.rect.height // 4)
        text_area = self.rect.inflate(-padding * 2, -padding * 2)

        # Determine which line was clicked
        rel_y = pos[1] - text_area.top
        clicked_line = self.scroll_offset + int(rel_y // line_height)
        clicked_line = max(0, min(clicked_line, len(lines) - 1))
        self.cursor_line = clicked_line

        # Determine position within line
        rel_x = pos[0] - text_area.left
        line = lines[clicked_line] if clicked_line < len(lines) else ""
        # Find closest character position
        best_pos = 0
        best_dist = abs(rel_x)
        for i in range(1, len(line) + 1):
            char_x = self.font.size(line[:i])[0]
            dist = abs(rel_x - char_x)
            if dist < best_dist:
                best_dist = dist
                best_pos = i
        self.cursor_pos = best_pos

    def _ensure_cursor_visible(self):
        """Scroll to keep cursor visible."""
        line_height = self.font.get_linesize()
        max_visible = max(1, (self.rect.height - 20) // line_height)

        if self.cursor_line < self.scroll_offset:
            self.scroll_offset = self.cursor_line
        elif self.cursor_line >= self.scroll_offset + max_visible:
            self.scroll_offset = self.cursor_line - max_visible + 1

    def _auto_save(self):
        """Save to file if path is set and text changed."""
        if self.save_path and self.text != self._last_saved_text:
            try:
                with open(self.save_path, 'w', encoding='utf-8') as f:
                    f.write(self.text)
                self._last_saved_text = self.text
            except:
                pass

    def update(self):
        self.cursor_timer += 1
        if self.cursor_timer >= 30:
            self.cursor_timer = 0
            self.cursor_visible = not self.cursor_visible

    def draw(self, screen: pygame.Surface, bg_color=None, text_color=None):
        # Background - use custom or default
        bg = bg_color if bg_color else UI_PANEL
        txt = text_color if text_color else UI_TEXT
        pygame.draw.rect(screen, bg, self.rect, border_radius=4)
        border_color = UI_ACCENT if self.active else UI_TEXT_DIM
        pygame.draw.rect(screen, border_color, self.rect, 2, border_radius=4)

        # Text area with padding
        padding = min(10, self.rect.height // 4)
        scrollbar_width = 12
        text_area = pygame.Rect(
            self.rect.left + padding,
            self.rect.top + padding,
            self.rect.width - padding * 2 - scrollbar_width,
            self.rect.height - padding * 2
        )
        lines = self.text.split('\n')

        # Calculate visible lines
        line_height = self.font.get_linesize()
        max_visible_lines = max(1, text_area.height // line_height)
        total_lines = len(lines)

        # Clamp scroll offset
        max_scroll = max(0, total_lines - max_visible_lines)
        self.scroll_offset = max(0, min(self.scroll_offset, max_scroll))

        # Draw lines
        y = text_area.top
        for i, line in enumerate(lines[self.scroll_offset:]):
            if y + line_height > text_area.bottom:
                break
            line_idx = self.scroll_offset + i
            # Highlight current line slightly if active
            if self.active and line_idx == self.cursor_line:
                highlight_rect = pygame.Rect(text_area.left - 2, y, text_area.width + 4, line_height)
                pygame.draw.rect(screen, (40, 45, 55), highlight_rect)
            text_surface = self.font.render(line[:100], True, txt)  # Truncate long lines
            screen.blit(text_surface, (text_area.left, y))
            y += line_height

        # Cursor
        if self.active and self.cursor_visible:
            if 0 <= self.cursor_line - self.scroll_offset < max_visible_lines:
                line = lines[self.cursor_line] if self.cursor_line < len(lines) else ""
                cursor_x = text_area.left + self.font.size(line[:self.cursor_pos])[0]
                cursor_y = text_area.top + (self.cursor_line - self.scroll_offset) * line_height
                pygame.draw.line(screen, txt, (cursor_x, cursor_y),
                               (cursor_x, cursor_y + line_height), 2)

        # Draw scrollbar if needed
        if total_lines > max_visible_lines:
            scrollbar_rect = pygame.Rect(
                self.rect.right - scrollbar_width - padding // 2,
                self.rect.top + padding,
                scrollbar_width - 4,
                self.rect.height - padding * 2
            )
            # Track
            pygame.draw.rect(screen, (30, 35, 45), scrollbar_rect, border_radius=3)

            # Thumb
            thumb_height = max(20, int(scrollbar_rect.height * (max_visible_lines / total_lines)))
            thumb_pos = int((self.scroll_offset / max_scroll) * (scrollbar_rect.height - thumb_height)) if max_scroll > 0 else 0
            thumb_rect = pygame.Rect(
                scrollbar_rect.left,
                scrollbar_rect.top + thumb_pos,
                scrollbar_rect.width,
                thumb_height
            )
            thumb_color = UI_ACCENT if self.active else (80, 90, 110)
            pygame.draw.rect(screen, thumb_color, thumb_rect, border_radius=3)

        # Movie count indicator
        entry_count = len([l for l in lines if l.strip()])
        count_text = f"{entry_count} movies"
        count_surface = self.font.render(count_text, True, UI_TEXT_DIM)
        count_rect = count_surface.get_rect(bottomright=(self.rect.right - padding, self.rect.bottom - 2))
        screen.blit(count_surface, count_rect)

    def get_entries(self) -> list:
        """Parse text into list of movie titles."""
        lines = self.text.strip().split('\n')
        entries = [line.strip() for line in lines if line.strip()]
        return entries

    def load_from_file(self, filepath: str) -> bool:
        """Load text from file. Returns True if successful."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.text = f.read()
            self._last_saved_text = self.text  # Mark as saved
            # Position cursor at end
            lines = self.text.split('\n')
            self.cursor_line = len(lines) - 1
            self.cursor_pos = len(lines[-1]) if lines else 0
            return True
        except FileNotFoundError:
            return False


class InputScreen:
    def __init__(self, fonts: dict):
        self.fonts = fonts
        self.window_width = WINDOW_WIDTH
        self.window_height = WINDOW_HEIGHT
        center_x = WINDOW_WIDTH // 2

        self.text_box = TextBox(center_x - 300, 150, 600, 450, fonts['small'], save_path=MOVIE_LIST_FILE)
        if os.path.exists(MOVIE_LIST_FILE):
            self.text_box.load_from_file(MOVIE_LIST_FILE)
        self.battle_button = Button(center_x - 100, 620, 200, 50, "BATTLE!", fonts['medium'])

        # Queue Battle button (below main battle button)
        self.queue_battle_button = Button(center_x - 100, 680, 200, 40, "QUEUE BATTLE", fonts['small'],
                                          color=(150, 100, 50), hover_color=(200, 150, 70))

        # Golden Docket button (bottom left)
        self.docket_button = Button(20, WINDOW_HEIGHT - 70, 180, 50, "GOLDEN DOCKET", fonts['small'],
                                    color=DOCKET_GOLDEN_DARK, hover_color=DOCKET_GOLDEN)

        # Quit button (bottom right)
        self.quit_button = Button(WINDOW_WIDTH - 100, WINDOW_HEIGHT - 70, 80, 50, "QUIT", fonts['small'],
                                  color=(100, 60, 60), hover_color=(150, 80, 80))

        self.error_message = ""
        self.error_timer = 0

        # Queue display
        self.queue_items = []
        self.queue_rects = []  # Clickable areas for queue items
        self.load_queue()

        # Docket picks display
        self.docket_picks = {'golden': [], 'diamond': [], 'shit': []}
        self.load_docket_picks()

    def update_layout(self, window_width: int, window_height: int):
        """Update positions based on new window size."""
        self.window_width = window_width
        self.window_height = window_height
        center_x = window_width // 2

        # Recalculate text box size based on window
        box_width = min(600, window_width - 100)
        box_height = min(450, window_height - 250)
        self.text_box.rect = pygame.Rect(center_x - box_width // 2, 150, box_width, box_height)

        # Reposition buttons
        button_y = min(620, window_height - 180)
        self.battle_button.rect = pygame.Rect(center_x - 100, button_y, 200, 50)
        self.queue_battle_button.rect = pygame.Rect(center_x - 100, button_y + 60, 200, 40)

        # Reposition docket button (bottom left)
        self.docket_button.rect = pygame.Rect(20, window_height - 70, 180, 50)

        # Reposition quit button (bottom right)
        self.quit_button.rect = pygame.Rect(window_width - 100, window_height - 70, 80, 50)

    def handle_event(self, event: pygame.event.Event):
        self.text_box.handle_event(event)

    def update(self, mouse_pos: tuple) -> tuple:
        """Returns (should_start, movie_list)"""
        self.text_box.update()
        self.battle_button.update(mouse_pos)
        self.queue_battle_button.update(mouse_pos)
        self.docket_button.update(mouse_pos)
        self.quit_button.update(mouse_pos)

        entries = self.text_box.get_entries()
        self.battle_button.enabled = len(entries) >= 2

        # Queue battle button enabled if queue has at least 2 items
        self.queue_battle_button.enabled = len(self.queue_items) >= 2

        if self.error_timer > 0:
            self.error_timer -= 1

        return (False, [])

    def check_docket(self, mouse_pos: tuple, mouse_clicked: bool) -> bool:
        """Check if docket button was clicked."""
        return self.docket_button.is_clicked(mouse_pos, mouse_clicked)

    def check_quit(self, mouse_pos: tuple, mouse_clicked: bool) -> bool:
        """Check if quit button was clicked."""
        return self.quit_button.is_clicked(mouse_pos, mouse_clicked)

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

    def check_queue_battle(self, mouse_pos: tuple, mouse_clicked: bool) -> tuple:
        """Check if queue battle should start. Returns (should_start, movie_list)"""
        if self.queue_battle_button.is_clicked(mouse_pos, mouse_clicked):
            if len(self.queue_items) >= 2:
                return (True, self.queue_items.copy())
            else:
                self.error_message = "Need at least 2 movies in queue!"
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

    def load_docket_picks(self):
        """Load docket picks from docket files."""
        self.docket_picks = {'golden': [], 'diamond': [], 'shit': []}
        docket_files = {
            'golden': GOLDEN_DOCKET_FILE,
            'diamond': DIAMOND_DOCKET_FILE,
            'shit': SHIT_DOCKET_FILE
        }
        for docket_type, filepath in docket_files.items():
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r') as f:
                        lines = f.read().strip().split('\n')
                        for line in lines:
                            line = line.strip()
                            if line and ' - ' in line:
                                parts = line.split(' - ', 1)
                                if len(parts) == 2:
                                    name, movie = parts[0].strip(), parts[1].strip()
                                    self.docket_picks[docket_type].append((name, movie))
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

        # Battle buttons
        self.battle_button.draw(screen)
        self.queue_battle_button.draw(screen)

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

        # Golden Docket button (bottom left)
        self.docket_button.draw(screen)

        # Quit button (bottom right)
        self.quit_button.draw(screen)

        # Queue panel on the right side
        if self.queue_items:
            panel_width = 300
            panel_x = self.window_width - panel_width - 20
            panel_y = 150
            line_height = 24
            max_items = min(50, len(self.queue_items))
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
                display_name = item if len(item) <= 22 else item[:19] + "..."

                # Clickable area
                item_rect = pygame.Rect(panel_x + 5, item_y, panel_width - 10, line_height - 2)
                self.queue_rects.append(item_rect)

                # Highlight on hover
                mouse_pos = pygame.mouse.get_pos()
                if item_rect.collidepoint(mouse_pos):
                    pygame.draw.rect(screen, (80, 60, 50), item_rect, border_radius=4)

                # Item text (medium font for better visibility)
                item_text = self.fonts['medium'].render(f"  {display_name}", True, (255, 200, 150))
                screen.blit(item_text, (panel_x + 10, item_y + 4))

                item_y += line_height

            # Show if there are more items
            if len(self.queue_items) > max_items:
                more_text = self.fonts['tiny'].render(f"+{len(self.queue_items) - max_items} more...", True, UI_TEXT_DIM)
                screen.blit(more_text, (panel_x + 10, item_y))

        # Docket picks panel on the left side
        self._draw_docket_picks(screen)

    def _draw_docket_picks(self, screen: pygame.Surface):
        """Draw the docket picks panel on the left side of the input screen."""
        # Reload docket picks to get latest
        self.load_docket_picks()

        # Check if any docket has picks
        total_picks = sum(len(picks) for picks in self.docket_picks.values())
        if total_picks == 0:
            return

        panel_width = 280
        panel_x = 20
        panel_y = 150
        line_height = 22

        # Calculate panel height based on content
        section_count = sum(1 for picks in self.docket_picks.values() if picks)
        total_lines = total_picks + section_count  # entries + headers
        panel_height = total_lines * line_height + 50

        # Panel background
        panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        panel_surface.fill((40, 40, 55, 230))
        screen.blit(panel_surface, (panel_x, panel_y))
        pygame.draw.rect(screen, UI_ACCENT, (panel_x, panel_y, panel_width, panel_height), 2, border_radius=8)

        # Title
        title = self.fonts['medium'].render("DOCKET PICKS", True, UI_ACCENT)
        screen.blit(title, (panel_x + 10, panel_y + 8))

        # Draw each docket section
        y = panel_y + 40
        docket_colors = {
            'golden': DOCKET_GOLDEN,
            'diamond': DOCKET_DIAMOND,
            'shit': DOCKET_SHIT
        }
        docket_names = {
            'golden': 'GOLDEN',
            'diamond': 'DIAMOND',
            'shit': 'SHIT'
        }

        for docket_type in ['golden', 'diamond', 'shit']:
            picks = self.docket_picks[docket_type]
            if not picks:
                continue

            color = docket_colors[docket_type]
            name = docket_names[docket_type]

            # Section header
            header = self.fonts['small'].render(f"{name}:", True, color)
            screen.blit(header, (panel_x + 10, y))
            y += line_height

            # Picks in this docket
            for person, movie in picks:
                # Truncate if too long
                display_person = person if len(person) <= 10 else person[:8] + ".."
                display_movie = movie if len(movie) <= 18 else movie[:16] + ".."
                entry_text = f"  {display_person}: {display_movie}"
                entry = self.fonts['tiny'].render(entry_text, True, UI_TEXT)
                screen.blit(entry, (panel_x + 10, y + 2))
                y += line_height


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
        self.is_preliminary = False
        self.is_preliminary_complete = False
        self.animation_timer = 0

    def update_layout(self, window_width: int, window_height: int):
        self.window_width = window_width
        self.window_height = window_height
        center_x = window_width // 2
        self.continue_button.rect = pygame.Rect(center_x - 110, window_height - 100, 220, 50)

    def set_advancers(self, advancers: list, heat_number: int, total_heats: int, is_to_finals: bool = False,
                      is_preliminary: bool = False, is_preliminary_complete: bool = False):
        self.advancers = advancers
        self.heat_number = heat_number
        self.total_heats = total_heats
        self.is_to_finals = is_to_finals
        self.is_preliminary = is_preliminary
        self.is_preliminary_complete = is_preliminary_complete
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
        if self.is_preliminary:
            title_text = "PRELIMINARY ROUND COMPLETE!"
            title_color = (255, 215, 0)
        elif self.is_to_finals:
            title_text = "ADVANCING TO FINALS!"
            title_color = (255, 215, 0)
        else:
            title_text = f"HEAT {self.heat_number} COMPLETE!"
            title_color = (100, 200, 255)

        title = self.fonts['title'].render(title_text, True, title_color)
        title_rect = title.get_rect(center=(center_x, 80))
        screen.blit(title, title_rect)

        # Subtitle
        if self.is_preliminary:
            # Extract movie count from winner name like "Group 2 (55 movies)"
            winner_name = self.advancers[0] if self.advancers else "Unknown"
            subtitle_text = f"{winner_name} wins! Their movies advance to the tournament."
        elif not self.is_to_finals:
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

        # Queue display (non-clickable)
        self.queue_items = []

        # Ability wins leaderboard
        self.ability_wins = {}  # {ability_key: win_count}

        # Flag to hide queue button (for queue battles)
        self.hide_queue_button = False

    def update_layout(self, window_width: int, window_height: int):
        self.window_width = window_width
        self.window_height = window_height
        center_x = window_width // 2
        self.choose_button.rect = pygame.Rect(center_x - 340, window_height - 80, 150, 50)
        self.queue_button.rect = pygame.Rect(center_x - 165, window_height - 80, 150, 50)
        self.play_again_button.rect = pygame.Rect(center_x + 10, window_height - 80, 150, 50)
        self.quit_button.rect = pygame.Rect(center_x + 185, window_height - 80, 100, 50)

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

    def load_ability_wins(self):
        """Load ability win counts from file."""
        self.ability_wins = {}
        if os.path.exists(ABILITY_WINS_FILE):
            try:
                with open(ABILITY_WINS_FILE, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if ':' in line:
                            ability, count = line.rsplit(':', 1)
                            self.ability_wins[ability.strip()] = int(count.strip())
            except:
                pass

    def set_rankings(self, winner: str, eliminated: list, is_queue_battle: bool = False):
        """Set rankings from winner (1st) and elimination order (last eliminated = 2nd)."""
        self.rankings = [winner] + list(reversed(eliminated))
        self.scroll_offset = 0
        self.winner_name = winner
        self.hide_queue_button = is_queue_battle
        # Reload queue and ability wins
        self.load_queue()
        self.load_ability_wins()

    def update(self, mouse_pos: tuple):
        self.play_again_button.update(mouse_pos)
        self.quit_button.update(mouse_pos)
        self.choose_button.update(mouse_pos)
        if not self.hide_queue_button:
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
        if self.hide_queue_button:
            return False
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
        if not self.hide_queue_button:
            self.queue_button.draw(screen)
        self.play_again_button.draw(screen)
        self.quit_button.draw(screen)

        # Button labels
        choose_label = self.fonts['tiny'].render("Watch this movie", True, UI_TEXT_DIM)
        screen.blit(choose_label, (self.choose_button.rect.centerx - choose_label.get_width() // 2, self.choose_button.rect.bottom + 5))

        if not self.hide_queue_button:
            queue_label = self.fonts['tiny'].render("Add to queue, replay", True, UI_TEXT_DIM)
            screen.blit(queue_label, (self.queue_button.rect.centerx - queue_label.get_width() // 2, self.queue_button.rect.bottom + 5))

        # Ability wins panel on the left side
        if self.ability_wins:
            panel_width = 220
            panel_x = 20
            panel_y = 100
            line_height = 26
            # Sort by wins descending
            sorted_abilities = sorted(self.ability_wins.items(), key=lambda x: x[1], reverse=True)
            max_items = min(15, len(sorted_abilities))
            panel_height = max_items * line_height + 50

            # Panel background
            panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
            panel_surface.fill((40, 50, 60, 220))
            screen.blit(panel_surface, (panel_x, panel_y))
            pygame.draw.rect(screen, (100, 180, 255), (panel_x, panel_y, panel_width, panel_height), 2, border_radius=8)

            # Title
            ability_title = self.fonts['small'].render("ABILITY WINS", True, (100, 180, 255))
            screen.blit(ability_title, (panel_x + 10, panel_y + 8))

            # Ability rankings
            item_y = panel_y + 38
            for i, (ability_key, wins) in enumerate(sorted_abilities[:max_items]):
                # Get ability display name and color
                ability_data = ABILITIES.get(ability_key, {})
                ability_name = ability_data.get('name', ability_key)
                ability_color = ability_data.get('color', (200, 200, 200))

                # Brighten the color for readability
                bright_color = tuple(min(255, c + 60) for c in ability_color)

                # Rank number
                rank_text = self.fonts['tiny'].render(f"{i+1}.", True, UI_TEXT_DIM)
                screen.blit(rank_text, (panel_x + 10, item_y))

                # Ability name (truncated if needed)
                display_name = ability_name if len(ability_name) <= 14 else ability_name[:12] + ".."
                name_text = self.fonts['tiny'].render(display_name, True, bright_color)
                screen.blit(name_text, (panel_x + 35, item_y))

                # Win count
                wins_text = self.fonts['tiny'].render(f"{wins}", True, VICTORY_GOLD)
                screen.blit(wins_text, (panel_x + panel_width - 30, item_y))

                item_y += line_height

        # Queue panel on the right side (non-clickable)
        if self.queue_items:
            panel_width = 250
            panel_x = self.window_width - panel_width - 20
            panel_y = 100
            line_height = 28
            max_items = min(12, len(self.queue_items))
            panel_height = max_items * line_height + 50

            # Panel background
            panel_surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
            panel_surface.fill((50, 45, 40, 220))
            screen.blit(panel_surface, (panel_x, panel_y))
            pygame.draw.rect(screen, (255, 180, 100), (panel_x, panel_y, panel_width, panel_height), 2, border_radius=8)

            # Title
            queue_title = self.fonts['small'].render("QUEUE", True, (255, 180, 100))
            screen.blit(queue_title, (panel_x + 10, panel_y + 8))

            # Queue items (display only)
            item_y = panel_y + 38
            for i, item in enumerate(self.queue_items[:max_items]):
                display_name = item if len(item) <= 22 else item[:19] + "..."
                item_text = self.fonts['tiny'].render(f"  {display_name}", True, (255, 200, 150))
                screen.blit(item_text, (panel_x + 10, item_y))
                item_y += line_height

            # Show if there are more items
            if len(self.queue_items) > max_items:
                more_text = self.fonts['tiny'].render(f"+{len(self.queue_items) - max_items} more...", True, UI_TEXT_DIM)
                screen.blit(more_text, (panel_x + 10, item_y))


class ParticipantSelectScreen:
    """Screen to select which participants are present for the docket."""
    def __init__(self, fonts: dict, permanent_people: list, people_counter: dict, docket_data: dict):
        """
        permanent_people: list of names from permanentpeople.txt
        people_counter: dict of {name: count} from peoplecounter.txt
        docket_data: dict with 'golden', 'diamond', 'shit' keys containing {name: movie}
        """
        self.fonts = fonts
        self.window_width = WINDOW_WIDTH
        self.window_height = WINDOW_HEIGHT

        # Categorize people
        self.permanent_people = permanent_people  # From file (truly permanent)
        self.people_counter = people_counter.copy()  # {name: count}
        self.docket_data = docket_data

        # All people from counter go in recurring section
        # Sort so people with docket entries (starred) come first
        all_recurring = list(people_counter.keys())
        self.starred_people = set(name for name in all_recurring
                                   if name in docket_data.get('golden', {}))
        self.recurring_people = sorted(all_recurring,
                                       key=lambda n: (0 if n in self.starred_people else 1, n))

        # No more graduated_people - everyone from counter stays in recurring
        self.graduated_people = []

        # All permanent participants (only from permanentpeople.txt)
        self.all_permanent = permanent_people

        # Selection state - permanent checked by default, recurring NOT checked
        self.selected_permanent = {name: True for name in self.all_permanent}
        self.selected_recurring = {name: False for name in self.recurring_people}

        # Track people added via text box this session (so we don't double-count them)
        self.newly_added = []

        # New name input (taller for better text visibility)
        self.new_name_input = TextBox(0, 0, 220, 50, fonts['small'])
        self.new_name_input.active = False

        # Docket pick inputs for people reaching 5 (shown when needed)
        self.pending_graduation = []  # Names that will reach 5 this round
        self.graduation_inputs = {}  # {name: {'golden': TextBox, 'diamond': TextBox, 'shit': TextBox}}

        center_x = WINDOW_WIDTH // 2
        self.start_button = Button(center_x - 140, 550, 280, 50, "START GOLDEN DOCKET", fonts['small'],
                                   color=DOCKET_GOLDEN_DARK, hover_color=DOCKET_GOLDEN)

        self.scroll_offset = 0
        self._build_layout()

    def _build_layout(self):
        """Build clickable areas for all sections."""
        self.permanent_rects = []
        self.recurring_rects = []

        center_x = self.window_width // 2
        left_x = 50  # Left column for permanent
        middle_x = center_x - 100  # Middle column for new entry
        right_x = center_x + 150  # Right column for recurring

        # Permanent people checkboxes (left side)
        y = 180
        for name in self.all_permanent:
            rect = pygame.Rect(left_x, y, 280, 35)
            self.permanent_rects.append((name, rect))
            y += 38

        # Recurring people checkboxes (right side)
        y = 180
        for name in self.recurring_people:
            count = self.people_counter.get(name, 0)
            rect = pygame.Rect(right_x, y, 280, 35)
            self.recurring_rects.append((name, rect, count))
            y += 38

        # New name input position (middle column, fixed position)
        self.new_name_input.rect = pygame.Rect(middle_x, 180, 220, 50)

        # Update button positions
        self.start_button.rect = pygame.Rect(center_x - 140, self.window_height - 100, 280, 50)

    def update_layout(self, window_width: int, window_height: int):
        self.window_width = window_width
        self.window_height = window_height
        self._build_layout()

    def update(self, mouse_pos: tuple):
        self.start_button.update(mouse_pos)
        self.new_name_input.update()

        # Update graduation inputs
        for name, inputs in self.graduation_inputs.items():
            for textbox in inputs.values():
                textbox.update()

        # Enable start button if at least one selected AND all graduation inputs filled
        has_selection = any(self.selected_permanent.values()) or any(self.selected_recurring.values())
        graduation_complete = self._check_graduation_inputs_complete()
        self.start_button.enabled = has_selection and graduation_complete

        # Check for pending graduations
        self._update_pending_graduations()

    def _update_pending_graduations(self):
        """Check which recurring people will graduate to 5 and need inputs."""
        new_pending = []
        for name in self.recurring_people:
            if self.selected_recurring.get(name, False):
                current_count = self.people_counter.get(name, 0)
                # Will reach 5 after increment AND doesn't have docket entries
                if current_count == 4 and name not in self.docket_data.get('golden', {}):
                    new_pending.append(name)

        # Create inputs for newly pending people
        for name in new_pending:
            if name not in self.graduation_inputs:
                self._create_graduation_inputs(name)

        # Remove inputs for people no longer pending
        for name in list(self.graduation_inputs.keys()):
            if name not in new_pending:
                del self.graduation_inputs[name]

        self.pending_graduation = new_pending

    def _create_graduation_inputs(self, name: str):
        """Create text inputs for a person graduating to permanent status."""
        # Position below their checkbox
        base_y = 0
        for n, rect, count in self.recurring_rects:
            if n == name:
                base_y = rect.bottom + 5
                break

        right_x = self.window_width // 2 + 150
        self.graduation_inputs[name] = {
            'golden': TextBox(right_x, base_y, 250, 45, self.fonts['small']),
            'diamond': TextBox(right_x, base_y + 50, 250, 45, self.fonts['small']),
            'shit': TextBox(right_x, base_y + 100, 250, 45, self.fonts['small']),
        }

    def _check_graduation_inputs_complete(self) -> bool:
        """Check if all graduation inputs are filled."""
        for name, inputs in self.graduation_inputs.items():
            for textbox in inputs.values():
                if not textbox.text.strip():
                    return False
        return True

    def handle_event(self, event):
        """Handle text input events."""
        # Handle new name input
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN and self.new_name_input.active:
            new_name = self.new_name_input.text.strip()
            if new_name and new_name not in self.people_counter and new_name not in self.all_permanent:
                self._add_new_person(new_name)
                self.new_name_input.text = ""
            return

        self.new_name_input.handle_event(event)

        # Handle graduation inputs
        for inputs in self.graduation_inputs.values():
            for textbox in inputs.values():
                textbox.handle_event(event)

    def _add_new_person(self, name: str):
        """Add a new person to the recurring list."""
        self.people_counter[name] = 1
        self.recurring_people.append(name)
        self.selected_recurring[name] = False  # Not auto-selected
        self.newly_added.append(name)  # Track as newly added this session
        self._build_layout()

    def handle_click(self, mouse_pos: tuple, mouse_clicked: bool):
        """Handle checkbox clicks."""
        if not mouse_clicked:
            return

        # Permanent people checkboxes
        for name, rect in self.permanent_rects:
            if rect.collidepoint(mouse_pos):
                self.selected_permanent[name] = not self.selected_permanent.get(name, False)
                return

        # Recurring people checkboxes
        for name, rect, count in self.recurring_rects:
            if rect.collidepoint(mouse_pos):
                self.selected_recurring[name] = not self.selected_recurring.get(name, False)
                return

    def check_start(self, mouse_pos: tuple, mouse_clicked: bool) -> bool:
        return self.start_button.is_clicked(mouse_pos, mouse_clicked)

    def get_selected_participants(self) -> list:
        """Return list of all selected participant names."""
        selected = []
        for name, is_selected in self.selected_permanent.items():
            if is_selected:
                selected.append(name)
        for name, is_selected in self.selected_recurring.items():
            if is_selected and name not in selected:
                selected.append(name)
        return selected

    def get_graduation_picks(self) -> dict:
        """Return docket picks for graduating people: {name: {'golden': movie, 'diamond': movie, 'shit': movie}}"""
        picks = {}
        for name, inputs in self.graduation_inputs.items():
            picks[name] = {
                'golden': inputs['golden'].text.strip(),
                'diamond': inputs['diamond'].text.strip(),
                'shit': inputs['shit'].text.strip(),
            }
        return picks

    def get_counter_updates(self) -> tuple:
        """Return (increments, decrements, newly_added) - lists of names."""
        increments = []
        decrements = []

        # Handle all recurring people (including starred ones)
        for name in self.recurring_people:
            # Skip newly added people - their count of 1 already represents this visit
            if name in self.newly_added:
                continue
            if self.selected_recurring.get(name, False):
                increments.append(name)
            else:
                decrements.append(name)

        return increments, decrements, self.newly_added

    def draw(self, screen: pygame.Surface):
        screen.fill(UI_BG)

        center_x = self.window_width // 2

        # Title
        title = self.fonts['title'].render("GOLDEN DOCKET", True, DOCKET_GOLDEN)
        title_rect = title.get_rect(center=(center_x, 40))
        screen.blit(title, title_rect)

        # Subtitle
        subtitle = self.fonts['medium'].render("Who's here tonight?", True, UI_TEXT_DIM)
        subtitle_rect = subtitle.get_rect(center=(center_x, 80))
        screen.blit(subtitle, subtitle_rect)

        mouse_pos = pygame.mouse.get_pos()
        left_x = 50
        middle_x = center_x - 100
        right_x = center_x + 150

        # === LEFT COLUMN: Permanent People ===
        section_title = self.fonts['small'].render("PERMANENT MEMBERS", True, DOCKET_GOLDEN)
        screen.blit(section_title, (left_x, 140))

        for name, rect in self.permanent_rects:
            # Hover highlight
            if rect.collidepoint(mouse_pos):
                pygame.draw.rect(screen, UI_PANEL, rect, border_radius=6)

            # Checkbox
            checkbox_rect = pygame.Rect(rect.x + 5, rect.y + 6, 22, 22)
            pygame.draw.rect(screen, DOCKET_GOLDEN_DARK, checkbox_rect, border_radius=3)
            if self.selected_permanent.get(name, False):
                pygame.draw.rect(screen, DOCKET_GOLDEN, checkbox_rect.inflate(-5, -5), border_radius=2)

            # Name
            name_text = self.fonts['small'].render(name, True, UI_TEXT)
            screen.blit(name_text, (rect.x + 35, rect.y + 8))

        # === MIDDLE COLUMN: Add New Person ===
        if not self.graduation_inputs:  # Only show if no graduation inputs active
            new_label = self.fonts['small'].render("ADD NEW PERSON", True, (100, 200, 100))
            screen.blit(new_label, (middle_x, 140))
            self.new_name_input.draw(screen, bg_color=(80, 90, 80), text_color=(255, 255, 255))

            hint = self.fonts['tiny'].render("Type name + Enter", True, UI_TEXT_DIM)
            screen.blit(hint, (middle_x, self.new_name_input.rect.bottom + 5))

        # === RIGHT COLUMN: Recurring People ===
        section_title2 = self.fonts['small'].render("RECURRING GUESTS", True, (150, 150, 200))
        screen.blit(section_title2, (right_x, 140))

        for name, rect, count in self.recurring_rects:
            # Hover highlight
            if rect.collidepoint(mouse_pos):
                pygame.draw.rect(screen, UI_PANEL, rect, border_radius=6)

            # Checkbox
            checkbox_rect = pygame.Rect(rect.x + 5, rect.y + 6, 22, 22)
            pygame.draw.rect(screen, (100, 100, 150), checkbox_rect, border_radius=3)
            if self.selected_recurring.get(name, False):
                pygame.draw.rect(screen, (150, 150, 220), checkbox_rect.inflate(-5, -5), border_radius=2)

            # Name with count (and star if they have docket entries)
            star = "★ " if name in self.starred_people else ""
            name_color = DOCKET_GOLDEN if name in self.starred_people else UI_TEXT
            name_text = self.fonts['small'].render(f"{star}{name} ({count})", True, name_color)
            screen.blit(name_text, (rect.x + 35, rect.y + 8))

            # Draw graduation inputs if this person is pending
            if name in self.graduation_inputs:
                inputs = self.graduation_inputs[name]
                label_x = right_x - 60

                # Golden pick
                golden_label = self.fonts['tiny'].render("Golden:", True, DOCKET_GOLDEN)
                screen.blit(golden_label, (label_x, inputs['golden'].rect.y + 12))
                inputs['golden'].draw(screen, bg_color=(80, 70, 50), text_color=(255, 255, 255))

                # Diamond pick
                diamond_label = self.fonts['tiny'].render("Diamond:", True, DOCKET_DIAMOND)
                screen.blit(diamond_label, (label_x, inputs['diamond'].rect.y + 12))
                inputs['diamond'].draw(screen, bg_color=(50, 70, 90), text_color=(255, 255, 255))

                # Shit pick
                shit_label = self.fonts['tiny'].render("Shit:", True, DOCKET_SHIT)
                screen.blit(shit_label, (label_x, inputs['shit'].rect.y + 12))
                inputs['shit'].draw(screen, bg_color=(80, 60, 50), text_color=(255, 255, 255))

        # Button
        self.start_button.draw(screen)


class DocketResultScreen:
    """Screen shown after a docket spin completes."""
    def __init__(self, fonts: dict):
        self.fonts = fonts
        self.window_width = WINDOW_WIDTH
        self.window_height = WINDOW_HEIGHT

        center_x = WINDOW_WIDTH // 2
        self.title_button = Button(center_x - 220, 550, 200, 60, "TITLE SCREEN", fonts['medium'])
        self.quit_button = Button(center_x + 20, 550, 200, 60, "QUIT", fonts['medium'],
                                  color=(150, 60, 60), hover_color=(200, 80, 80))

        # For golden docket replacement input
        self.replacement_input = TextBox(center_x - 200, 450, 400, 60, fonts['medium'])
        self.confirm_button = Button(center_x - 75, 510, 150, 40, "CONFIRM", fonts['small'],
                                     color=(50, 150, 50), hover_color=(70, 200, 70))

        self.winner_name = ""
        self.winner_movie = ""
        self.docket_type = "golden"
        self.needs_replacement = False
        self.replacement_confirmed = False
        self.animation_timer = 0

    def update_layout(self, window_width: int, window_height: int):
        self.window_width = window_width
        self.window_height = window_height
        center_x = window_width // 2
        center_y = window_height // 2

        self.title_button.rect = pygame.Rect(center_x - 220, center_y + 180, 200, 60)
        self.quit_button.rect = pygame.Rect(center_x + 20, center_y + 180, 200, 60)
        self.replacement_input.rect = pygame.Rect(center_x - 200, center_y + 80, 400, 60)
        self.confirm_button.rect = pygame.Rect(center_x - 75, center_y + 140, 150, 40)

    def set_result(self, name: str, movie: str, docket_type: str):
        """Set the winning result."""
        self.winner_name = name
        self.winner_movie = movie
        self.docket_type = docket_type
        self.needs_replacement = (docket_type == "golden")
        self.replacement_confirmed = False
        self.replacement_input.text = ""
        # Auto-activate textbox for golden docket so user can type immediately
        self.replacement_input.active = self.needs_replacement
        self.animation_timer = 0
        # Update layout to ensure rect positions are correct
        self.update_layout(self.window_width, self.window_height)

    def update(self, mouse_pos: tuple):
        self.animation_timer += 1
        self.replacement_input.update()

        # Only show title/quit after replacement confirmed (or if not needed)
        show_final_buttons = not self.needs_replacement or self.replacement_confirmed
        if show_final_buttons:
            self.title_button.update(mouse_pos)
            self.quit_button.update(mouse_pos)

        if self.needs_replacement and not self.replacement_confirmed:
            self.confirm_button.update(mouse_pos)
            self.confirm_button.enabled = len(self.replacement_input.text.strip()) > 0

    def handle_event(self, event):
        """Handle text input events. Returns True if ENTER was pressed to confirm."""
        if self.needs_replacement and not self.replacement_confirmed:
            # Check for ENTER key to trigger confirmation
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                if self.replacement_input.text.strip():
                    return True  # Signal to confirm
                return False  # Ignore if empty
            # Handle other events normally (but filter out RETURN from TextBox)
            if not (event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN):
                self.replacement_input.handle_event(event)
        return False

    def check_confirm(self, mouse_pos: tuple, mouse_clicked: bool) -> str:
        """Check if replacement was confirmed. Returns new movie name or None."""
        if self.needs_replacement and not self.replacement_confirmed:
            if self.confirm_button.is_clicked(mouse_pos, mouse_clicked):
                new_movie = self.replacement_input.text.strip()
                if new_movie:
                    self.replacement_confirmed = True
                    return new_movie
        return None

    def check_title(self, mouse_pos: tuple, mouse_clicked: bool) -> bool:
        show_final = not self.needs_replacement or self.replacement_confirmed
        return show_final and self.title_button.is_clicked(mouse_pos, mouse_clicked)

    def check_quit(self, mouse_pos: tuple, mouse_clicked: bool) -> bool:
        show_final = not self.needs_replacement or self.replacement_confirmed
        return show_final and self.quit_button.is_clicked(mouse_pos, mouse_clicked)

    def draw(self, screen: pygame.Surface):
        # Background color based on docket type
        if self.docket_type == "golden":
            bg_color = (40, 35, 20)
            accent = DOCKET_GOLDEN
            label = "GOLDEN DOCKET"
        elif self.docket_type == "diamond":
            bg_color = (20, 30, 45)
            accent = DOCKET_DIAMOND
            label = "DIAMOND DOCKET"
        elif self.docket_type == "final":
            bg_color = (40, 35, 25)
            accent = (255, 200, 50)  # Gold for final wheel
            label = "FINAL WHEEL"
        else:
            bg_color = (35, 25, 20)
            accent = DOCKET_SHIT
            label = "SHIT DOCKET"

        screen.fill(bg_color)

        center_x = self.window_width // 2
        center_y = self.window_height // 2

        # Pulsing glow
        pulse = abs((self.animation_timer % 60) - 30) / 30
        glow_size = int(200 + pulse * 30)

        for i in range(4):
            alpha = int(25 - i * 5)
            glow_surface = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)
            glow_color = (*accent[:3], alpha)
            pygame.draw.circle(glow_surface, glow_color, (glow_size, glow_size), glow_size - i * 15)
            screen.blit(glow_surface, (center_x - glow_size, center_y - 120 - glow_size // 2))

        # Docket type label
        type_label = self.fonts['medium'].render(label, True, accent)
        type_rect = type_label.get_rect(center=(center_x, center_y - 180))
        screen.blit(type_label, type_rect)

        # Winner announcement
        winner_label = self.fonts['large'].render("WINNER!", True, accent)
        winner_rect = winner_label.get_rect(center=(center_x, center_y - 120))
        screen.blit(winner_label, winner_rect)

        # Movie title
        movie_surface = self.fonts['huge'].render(self.winner_movie, True, WHITE)
        movie_rect = movie_surface.get_rect(center=(center_x, center_y - 40))
        if movie_rect.width > self.window_width - 100:
            movie_surface = self.fonts['title'].render(self.winner_movie, True, WHITE)
            movie_rect = movie_surface.get_rect(center=(center_x, center_y - 40))
        screen.blit(movie_surface, movie_rect)

        # Picked by (or source for final wheel)
        if self.docket_type == "final":
            source_text = f"From: {self.winner_name}"
        else:
            source_text = f"Picked by {self.winner_name}"
        picked_by = self.fonts['medium'].render(source_text, True, UI_TEXT_DIM)
        picked_rect = picked_by.get_rect(center=(center_x, center_y + 20))
        screen.blit(picked_by, picked_rect)

        # Golden docket replacement input
        if self.needs_replacement and not self.replacement_confirmed:
            prompt = self.fonts['small'].render(f"{self.winner_name}, enter your new golden pick:", True, accent)
            prompt_rect = prompt.get_rect(center=(center_x, center_y + 60))
            screen.blit(prompt, prompt_rect)

            self.replacement_input.draw(screen, bg_color=(60, 55, 40), text_color=(255, 255, 255))
            self.confirm_button.draw(screen)
        elif self.replacement_confirmed:
            confirmed_text = self.fonts['small'].render(f"New pick saved! Enjoy the movie!", True, (100, 255, 100))
            confirmed_rect = confirmed_text.get_rect(center=(center_x, center_y + 80))
            screen.blit(confirmed_text, confirmed_rect)

            self.title_button.draw(screen)
            self.quit_button.draw(screen)
        else:
            # Diamond, shit, or final - no replacement needed
            if self.docket_type == "final":
                enjoy_text = self.fonts['medium'].render("Removed from list! Enjoy the movie!", True, (100, 255, 100))
            else:
                enjoy_text = self.fonts['medium'].render("Enjoy the movie!", True, UI_TEXT)
            enjoy_rect = enjoy_text.get_rect(center=(center_x, center_y + 80))
            screen.blit(enjoy_text, enjoy_rect)

            self.title_button.draw(screen)
            self.quit_button.draw(screen)


class DocketSpinScreen:
    """Screen that displays the spinning docket wheel."""
    def __init__(self, fonts: dict):
        self.fonts = fonts
        self.window_width = WINDOW_WIDTH
        self.window_height = WINDOW_HEIGHT
        self.wheel = None
        self.zoom_transition = None
        self.spin_button = None
        self.force_upgrade_button = None  # Debug button to force landing on sliver

    def update_layout(self, window_width: int, window_height: int):
        self.window_width = window_width
        self.window_height = window_height

    def set_wheel(self, wheel):
        """Set the wheel to display."""
        self.wheel = wheel
        center_x = self.window_width // 2
        self.spin_button = Button(center_x - 60, self.window_height - 80, 120, 50, "SPIN!", self.fonts['medium'],
                                  color=wheel.colors['dark'], hover_color=wheel.colors['primary'])
        # Debug button to force upgrade (for golden, diamond, and shit)
        if wheel.docket_type in ('golden', 'diamond', 'shit'):
            self.force_upgrade_button = Button(20, self.window_height - 80, 180, 40, "FORCE UPGRADE", self.fonts['small'],
                                               color=(100, 50, 100), hover_color=(150, 80, 150))
        else:
            self.force_upgrade_button = None

    def set_zoom_transition(self, transition):
        """Set a zoom transition to display."""
        self.zoom_transition = transition

    def update(self, mouse_pos: tuple):
        if self.zoom_transition:
            self.zoom_transition.update()
            if self.zoom_transition.complete:
                self.wheel = self.zoom_transition.get_new_wheel()
                self.zoom_transition = None
                # Update spin button for new wheel
                center_x = self.window_width // 2
                self.spin_button = Button(center_x - 60, self.window_height - 80, 120, 50, "SPIN!", self.fonts['medium'],
                                          color=self.wheel.colors['dark'], hover_color=self.wheel.colors['primary'])
                # Update force upgrade button for new wheel
                if self.wheel.docket_type in ('golden', 'diamond', 'shit'):
                    self.force_upgrade_button = Button(20, self.window_height - 80, 180, 40, "FORCE UPGRADE", self.fonts['small'],
                                                       color=(100, 50, 100), hover_color=(150, 80, 150))
                else:
                    self.force_upgrade_button = None
        elif self.wheel:
            self.wheel.update()
            if self.spin_button:
                self.spin_button.update(mouse_pos)
                # Hide spin button while spinning or stopped
                self.spin_button.enabled = not self.wheel.spinning and not self.wheel.stopped
            if self.force_upgrade_button:
                self.force_upgrade_button.update(mouse_pos)
                self.force_upgrade_button.enabled = not self.wheel.spinning and not self.wheel.stopped

    def check_spin(self, mouse_pos: tuple, mouse_clicked: bool) -> bool:
        if self.spin_button and self.wheel and not self.wheel.spinning and not self.wheel.stopped:
            return self.spin_button.is_clicked(mouse_pos, mouse_clicked)
        return False

    def check_force_upgrade(self, mouse_pos: tuple, mouse_clicked: bool) -> bool:
        """Check if force upgrade debug button was clicked."""
        if self.force_upgrade_button and self.wheel and not self.wheel.spinning and not self.wheel.stopped:
            return self.force_upgrade_button.is_clicked(mouse_pos, mouse_clicked)
        return False

    def is_stopped(self) -> bool:
        return self.wheel and self.wheel.stopped

    def is_transitioning(self) -> bool:
        return self.zoom_transition is not None

    def get_result(self):
        if self.wheel:
            return self.wheel.get_result()
        return None

    def draw(self, screen: pygame.Surface):
        # Background - same as beyblade arena
        screen.fill(UI_BG)

        if self.zoom_transition:
            self.zoom_transition.draw(screen)
        elif self.wheel:
            self.wheel.draw(screen)

            # Title
            center_x = self.window_width // 2
            if self.wheel.docket_type == "golden":
                title = "GOLDEN DOCKET"
                color = DOCKET_GOLDEN
            elif self.wheel.docket_type == "diamond":
                title = "DIAMOND DOCKET"
                color = DOCKET_DIAMOND
            elif self.wheel.docket_type == "final":
                title = "FINAL WHEEL"
                color = (255, 200, 50)  # Gold
            else:
                title = "SHIT DOCKET"
                color = DOCKET_SHIT

            title_surf = self.fonts['title'].render(title, True, color)
            title_rect = title_surf.get_rect(center=(center_x, 40))
            screen.blit(title_surf, title_rect)

            # Spin button
            if self.spin_button and self.spin_button.enabled:
                self.spin_button.draw(screen)

            # Force upgrade debug button
            if self.force_upgrade_button and self.force_upgrade_button.enabled:
                self.force_upgrade_button.draw(screen)

            # Status text
            if self.wheel.spinning:
                status = self.fonts['medium'].render("Spinning...", True, UI_TEXT_DIM)
            elif self.wheel.stopped:
                status = self.fonts['medium'].render("Click anywhere to continue", True, color)
            else:
                status = None

            if status:
                status_rect = status.get_rect(center=(center_x, self.window_height - 40))
                screen.blit(status, status_rect)


def create_fonts() -> dict:
    pygame.font.init()
    fonts = {}
    for name, size in FONT_SIZES.items():
        try:
            fonts[name] = pygame.font.SysFont('Arial', size, bold=(name in ['title', 'huge', 'large']))
        except:
            fonts[name] = pygame.font.Font(None, size)
    return fonts

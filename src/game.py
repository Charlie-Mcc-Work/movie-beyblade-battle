import pygame
import random
from .constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, FPS, UI_BG,
    STATE_INPUT, STATE_BATTLE, STATE_VICTORY
)
from .beyblade import Beyblade, check_collision, resolve_collision
from .arena import Arena
from .effects import EffectsManager
from .ui import InputScreen, BattleHUD, VictoryScreen, create_fonts


class Game:
    def __init__(self):
        pygame.init()
        pygame.scrap.init()

        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Movie Beyblade Battle")

        self.clock = pygame.time.Clock()
        self.fonts = create_fonts()

        self.arena = Arena()
        self.effects = EffectsManager()

        self.input_screen = InputScreen(self.fonts)
        self.battle_hud = BattleHUD(self.fonts)
        self.victory_screen = VictoryScreen(self.fonts)

        self.beyblades: list[Beyblade] = []
        self.eliminated: list[str] = []
        self.state = STATE_INPUT
        self.speed_multiplier = 1
        self.winner = None

        self.running = True

    def start_battle(self, movie_list: list):
        """Initialize a new battle with the given movie list."""
        self.beyblades.clear()
        self.eliminated.clear()
        self.effects.clear()
        self.winner = None

        # Shuffle for random spawn positions
        random.shuffle(movie_list)

        # Get spawn positions
        positions = self.arena.get_spawn_positions(len(movie_list))

        # Create beyblades
        for i, (movie, pos) in enumerate(zip(movie_list, positions)):
            beyblade = Beyblade(movie, pos[0], pos[1], i)
            self.beyblades.append(beyblade)

        self.state = STATE_BATTLE
        self.speed_multiplier = 1
        self.battle_hud.current_speed = 1

    def handle_events(self):
        mouse_clicked = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_clicked = True

            if self.state == STATE_INPUT:
                self.input_screen.handle_event(event)

        return mouse_clicked

    def update(self, mouse_clicked: bool):
        mouse_pos = pygame.mouse.get_pos()

        if self.state == STATE_INPUT:
            self.input_screen.update(mouse_pos)
            should_start, movie_list = self.input_screen.check_start(mouse_pos, mouse_clicked)
            if should_start:
                self.start_battle(movie_list)

        elif self.state == STATE_BATTLE:
            self.battle_hud.update(mouse_pos)
            self.speed_multiplier = self.battle_hud.check_speed_click(mouse_pos, mouse_clicked)

            # Update physics multiple times for speed multiplier
            for _ in range(self.speed_multiplier):
                self.update_battle()

        elif self.state == STATE_VICTORY:
            self.victory_screen.update(mouse_pos)
            if self.victory_screen.check_restart(mouse_pos, mouse_clicked):
                self.state = STATE_INPUT

    def update_battle(self):
        # Update all beyblades
        for beyblade in self.beyblades:
            beyblade.update()
            if beyblade.alive:
                self.arena.apply_boundary(beyblade)

        # Check for collisions
        alive_beyblades = [b for b in self.beyblades if b.alive]
        for i, b1 in enumerate(alive_beyblades):
            for b2 in alive_beyblades[i+1:]:
                if check_collision(b1, b2):
                    collision_x, collision_y, intensity = resolve_collision(b1, b2)
                    if intensity > 1:
                        self.effects.spawn_collision_sparks(collision_x, collision_y, intensity * 0.5)

        # Check for new eliminations
        for beyblade in self.beyblades:
            if not beyblade.alive and beyblade.name not in self.eliminated:
                self.eliminated.append(beyblade.name)
                self.effects.spawn_knockout_effect(
                    beyblade.x, beyblade.y, beyblade.color, beyblade.name
                )

        # Update effects
        self.effects.update()

        # Check for victory
        alive_beyblades = [b for b in self.beyblades if b.alive]
        if len(alive_beyblades) == 1:
            self.winner = alive_beyblades[0]
            self.victory_screen.set_winner(self.winner.name)
            self.state = STATE_VICTORY
        elif len(alive_beyblades) == 0:
            # Tie - pick the last eliminated
            if self.eliminated:
                self.victory_screen.set_winner(self.eliminated[-1])
            else:
                self.victory_screen.set_winner("No Winner")
            self.state = STATE_VICTORY

    def draw(self):
        if self.state == STATE_INPUT:
            self.input_screen.draw(self.screen)

        elif self.state == STATE_BATTLE:
            self.screen.fill(UI_BG)
            self.arena.draw(self.screen)

            # Draw beyblades (alive ones on top)
            dead_beyblades = [b for b in self.beyblades if not b.alive]
            alive_beyblades = [b for b in self.beyblades if b.alive]

            for beyblade in dead_beyblades:
                beyblade.draw(self.screen, self.fonts['tiny'])

            for beyblade in alive_beyblades:
                beyblade.draw(self.screen, self.fonts['tiny'])

            # Draw effects
            self.effects.draw(self.screen, self.fonts['medium'])

            # Draw HUD
            alive_count = len(alive_beyblades)
            total_count = len(self.beyblades)
            self.battle_hud.draw(self.screen, alive_count, total_count, self.eliminated)

        elif self.state == STATE_VICTORY:
            # Draw the final arena state behind victory screen
            self.screen.fill(UI_BG)
            self.arena.draw(self.screen)

            for beyblade in self.beyblades:
                beyblade.draw(self.screen, self.fonts['tiny'])

            # Draw victory overlay
            self.victory_screen.draw(self.screen)

        pygame.display.flip()

    def run(self):
        while self.running:
            mouse_clicked = self.handle_events()
            self.update(mouse_clicked)
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()

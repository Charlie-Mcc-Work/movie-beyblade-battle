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
        self.round_number = 1

        # Tournament state
        self.heats: list[list[str]] = []
        self.current_heat = 0
        self.heat_winners: list[str] = []
        self.is_finals = False
        self.advancers_per_heat = 2  # Top N from each heat advance
        self.max_per_heat = 8  # Max beyblades per heat

        self.running = True

    def start_battle(self, movie_list: list):
        """Initialize a new tournament with the given movie list."""
        self.eliminated.clear()
        self.effects.clear()
        self.winner = None
        self.round_number = 1
        self.heat_winners.clear()
        self.current_heat = 0
        self.is_finals = False

        # Shuffle movies
        random.shuffle(movie_list)

        # If few movies, just run single battle (no heats needed)
        if len(movie_list) <= self.max_per_heat:
            self.heats = [movie_list]
        else:
            # Split into heats
            self.heats = []
            for i in range(0, len(movie_list), self.max_per_heat):
                heat = movie_list[i:i + self.max_per_heat]
                if heat:
                    self.heats.append(heat)

        # Start first heat
        self._start_heat(0)

        self.state = STATE_BATTLE
        self.speed_multiplier = 1
        self.battle_hud.current_speed = 1

    def _start_heat(self, heat_index: int):
        """Start a specific heat battle."""
        self.current_heat = heat_index
        self.round_number = 1
        self.beyblades.clear()
        self.effects.clear()

        if self.is_finals:
            movies = self.heat_winners
        else:
            movies = self.heats[heat_index]

        self._spawn_beyblades(movies)

    def _spawn_beyblades(self, movie_list: list):
        """Spawn beyblades with positions and tangential velocities."""
        random.shuffle(movie_list)
        spawns = self.arena.get_spawn_positions(len(movie_list))

        for i, (movie, spawn) in enumerate(zip(movie_list, spawns)):
            x, y, vx, vy = spawn
            beyblade = Beyblade(movie, x, y, i)
            beyblade.vx = vx
            beyblade.vy = vy
            self.beyblades.append(beyblade)

    def start_new_round(self):
        """Start a new round with surviving beyblades."""
        self.round_number += 1
        survivors = [b for b in self.beyblades if b.alive]
        survivor_names = [b.name for b in survivors]

        # Store color indices to keep consistent colors
        color_map = {b.name: b.color for b in survivors}

        self.beyblades.clear()
        self.effects.clear()

        spawns = self.arena.get_spawn_positions(len(survivor_names))

        for i, (name, spawn) in enumerate(zip(survivor_names, spawns)):
            x, y, vx, vy = spawn
            beyblade = Beyblade(name, x, y, i)
            beyblade.vx = vx
            beyblade.vy = vy
            beyblade.color = color_map[name]  # Keep original color
            self.beyblades.append(beyblade)

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
                    if intensity > 0.5:
                        self.effects.spawn_collision_sparks(collision_x, collision_y, intensity)

        # Check for new eliminations
        for beyblade in self.beyblades:
            if not beyblade.alive and beyblade.name not in self.eliminated:
                self.eliminated.append(beyblade.name)
                self.effects.spawn_knockout_effect(
                    beyblade.x, beyblade.y, beyblade.color, beyblade.name
                )

        # Update effects
        self.effects.update()

        # Check for heat/battle end
        alive_beyblades = [b for b in self.beyblades if b.alive]
        alive_count = len(alive_beyblades)

        # Determine how many need to survive this heat
        if self.is_finals:
            # Finals: fight until 1 remains
            target_survivors = 1
        elif len(self.heats) == 1:
            # Single heat (few movies): fight until 1 remains
            target_survivors = 1
        else:
            # Regular heat: fight until advancers_per_heat remain
            target_survivors = self.advancers_per_heat

        if alive_count <= target_survivors:
            self._end_current_heat(alive_beyblades)
        elif alive_count > target_survivors:
            # Check if all beyblades have stopped - start new round within heat
            all_stopped = all(b.speed < 0.3 for b in alive_beyblades)
            if all_stopped:
                self.start_new_round()

    def _end_current_heat(self, survivors: list):
        """Handle end of a heat - advance winners or end tournament."""
        survivor_names = [b.name for b in survivors]

        if self.is_finals or len(self.heats) == 1:
            # Tournament over - we have a winner
            if survivor_names:
                self.victory_screen.set_winner(survivor_names[0])
            elif self.eliminated:
                self.victory_screen.set_winner(self.eliminated[-1])
            else:
                self.victory_screen.set_winner("No Winner")
            self.state = STATE_VICTORY
        else:
            # Add survivors to heat winners
            self.heat_winners.extend(survivor_names)

            # Check if more heats remain
            if self.current_heat < len(self.heats) - 1:
                # Start next heat
                self._start_heat(self.current_heat + 1)
            else:
                # All heats done - start finals
                self.is_finals = True
                self._start_heat(0)

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
            heat_info = None
            if len(self.heats) > 1:
                if self.is_finals:
                    heat_info = ("FINALS", len(self.heat_winners))
                else:
                    heat_info = (f"Heat {self.current_heat + 1}/{len(self.heats)}", len(self.heats[self.current_heat]))
            self.battle_hud.draw(self.screen, alive_count, total_count, self.eliminated, self.round_number, heat_info)

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

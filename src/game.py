import pygame
import random
from .constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, FPS, UI_BG,
    STATE_INPUT, STATE_BATTLE, STATE_HEAT_TRANSITION, STATE_VICTORY, STATE_LEADERBOARD
)
from .beyblade import Beyblade, check_collision, resolve_collision
from .arena import Arena
from .effects import EffectsManager
from .avatar import AvatarManager
from .ui import InputScreen, BattleHUD, HeatTransitionScreen, VictoryScreen, LeaderboardScreen, create_fonts


class Game:
    def __init__(self):
        pygame.init()
        pygame.scrap.init()

        # Make window resizable
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("Movie Beyblade Battle")

        # Get actual window size (may differ from requested due to WM)
        actual_size = self.screen.get_size()
        self.window_width = actual_size[0]
        self.window_height = actual_size[1]

        self.clock = pygame.time.Clock()
        self.fonts = create_fonts()

        self.arena = Arena()
        self.effects = EffectsManager()
        self.avatar_manager = AvatarManager()

        self.input_screen = InputScreen(self.fonts)
        self.battle_hud = BattleHUD(self.fonts)
        self.heat_transition_screen = HeatTransitionScreen(self.fonts)
        self.victory_screen = VictoryScreen(self.fonts)
        self.leaderboard_screen = LeaderboardScreen(self.fonts)

        # Always update layouts for actual window size
        self.arena.update_center(self.window_width, self.window_height)
        self.input_screen.update_layout(self.window_width, self.window_height)
        self.battle_hud.update_layout(self.window_width, self.window_height)
        self.heat_transition_screen.update_layout(self.window_width, self.window_height)
        self.victory_screen.update_layout(self.window_width, self.window_height)
        self.leaderboard_screen.update_layout(self.window_width, self.window_height)

        self.beyblades: list[Beyblade] = []
        self.eliminated: list[str] = []  # Current heat eliminations
        self.all_eliminated: list[str] = []  # Full tournament elimination order
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
        self.max_per_heat = 11  # Max beyblades per heat

        self.running = True

    def start_battle(self, movie_list: list):
        """Initialize a new tournament with the given movie list."""
        self.eliminated.clear()
        self.all_eliminated.clear()
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

        # Create avatars for this batch of beyblades
        self.avatar_manager.create_avatars(self.beyblades, self.arena)

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

            if event.type == pygame.VIDEORESIZE:
                self.window_width = event.w
                self.window_height = event.h
                self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                # Update arena center and get offset
                dx, dy = self.arena.update_center(event.w, event.h)
                # Move all beyblades by the offset to keep them centered
                for beyblade in self.beyblades:
                    beyblade.x += dx
                    beyblade.y += dy
                # Update avatar positions
                self.avatar_manager.update_positions(self.arena)
                # Update UI components
                self.input_screen.update_layout(event.w, event.h)
                self.battle_hud.update_layout(event.w, event.h)
                self.heat_transition_screen.update_layout(event.w, event.h)
                self.victory_screen.update_layout(event.w, event.h)
                self.leaderboard_screen.update_layout(event.w, event.h)

            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                # Toggle fullscreen
                self.fullscreen = not getattr(self, 'fullscreen', False)
                if self.fullscreen:
                    self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                else:
                    self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
                # Update window dimensions and layouts
                actual_size = self.screen.get_size()
                self.window_width = actual_size[0]
                self.window_height = actual_size[1]
                dx, dy = self.arena.update_center(self.window_width, self.window_height)
                for beyblade in self.beyblades:
                    beyblade.x += dx
                    beyblade.y += dy
                self.avatar_manager.update_positions(self.arena)
                self.input_screen.update_layout(self.window_width, self.window_height)
                self.battle_hud.update_layout(self.window_width, self.window_height)
                self.heat_transition_screen.update_layout(self.window_width, self.window_height)
                self.victory_screen.update_layout(self.window_width, self.window_height)
                self.leaderboard_screen.update_layout(self.window_width, self.window_height)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_clicked = True

            if self.state == STATE_INPUT:
                self.input_screen.handle_event(event)

            if self.state == STATE_LEADERBOARD:
                self.leaderboard_screen.handle_scroll(event)

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

            # Check mute toggle
            if self.battle_hud.check_mute_click(mouse_pos, mouse_clicked):
                self.effects.sound.muted = self.battle_hud.muted

            # Update physics multiple times for speed multiplier
            for _ in range(self.speed_multiplier):
                self.update_battle()

        elif self.state == STATE_HEAT_TRANSITION:
            self.heat_transition_screen.update(mouse_pos)
            if self.heat_transition_screen.check_continue(mouse_pos, mouse_clicked):
                self._continue_after_heat()

        elif self.state == STATE_VICTORY:
            self.victory_screen.update(mouse_pos)
            if self.victory_screen.check_leaderboard(mouse_pos, mouse_clicked):
                self.leaderboard_screen.set_rankings(self.winner, self.all_eliminated)
                self.state = STATE_LEADERBOARD

        elif self.state == STATE_LEADERBOARD:
            self.leaderboard_screen.update(mouse_pos)
            if self.leaderboard_screen.check_play_again(mouse_pos, mouse_clicked):
                self.state = STATE_INPUT
            elif self.leaderboard_screen.check_quit(mouse_pos, mouse_clicked):
                self.running = False

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
                    collision_x, collision_y, intensity, triggers = resolve_collision(b1, b2)
                    if intensity > 0.5:
                        self.effects.spawn_collision_sparks(collision_x, collision_y, intensity)
                        # Play hit sound
                        if intensity > 5:
                            self.effects.sound.play('big_hit')
                        else:
                            self.effects.sound.play('hit')
                    # Process ability triggers with appropriate sounds
                    for name, text, color in triggers:
                        sound = self._get_ability_sound(text)
                        self.effects.spawn_ability_notification(name, text, color, sound)

        # Check for turbo and bouncy triggers
        for beyblade in self.beyblades:
            if beyblade.turbo_triggered:
                from .constants import ABILITIES
                self.effects.spawn_ability_notification(beyblade.name, 'Turbo!', ABILITIES['turbo']['color'], 'turbo')
                beyblade.turbo_triggered = False
            if beyblade.bouncy_triggered:
                from .constants import ABILITIES
                self.effects.spawn_ability_notification(beyblade.name, 'Bouncy save!', ABILITIES['bouncy']['color'], 'bouncy')
                beyblade.bouncy_triggered = False

        # Check for new eliminations
        for beyblade in self.beyblades:
            if not beyblade.alive and beyblade.name not in self.eliminated:
                self.eliminated.append(beyblade.name)
                self.all_eliminated.append(beyblade.name)  # Track for leaderboard
                self.effects.spawn_knockout_effect(
                    beyblade.x, beyblade.y, beyblade.color, beyblade.name
                )
                self.effects.sound.play('knockout')

        # Update effects
        self.effects.update()

        # Update avatars
        self.avatar_manager.sync_with_beyblades(self.beyblades)
        self.avatar_manager.update()

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

    def _get_ability_sound(self, text: str) -> str:
        """Get the appropriate sound name for an ability trigger."""
        text_lower = text.lower()
        if 'burst' in text_lower:
            return 'burst'
        elif 'dodge' in text_lower:
            return 'dodge'
        elif 'counter' in text_lower:
            return 'counter'
        elif 'vampire' in text_lower:
            return 'vampire'
        elif 'rage' in text_lower:
            return 'burst'
        elif 'gambler win' in text_lower:
            return 'gambler_win'
        elif 'gambler lose' in text_lower:
            return 'gambler_lose'
        elif 'mirror' in text_lower:
            return 'ability'
        return 'ability'

    def _end_current_heat(self, survivors: list):
        """Handle end of a heat - advance winners or end tournament."""
        survivor_names = [b.name for b in survivors]

        if self.is_finals or len(self.heats) == 1:
            # Tournament over - we have a winner
            if survivor_names:
                self.winner = survivor_names[0]
                self.victory_screen.set_winner(survivor_names[0])
            elif self.all_eliminated:
                self.winner = self.all_eliminated[-1]
                self.victory_screen.set_winner(self.all_eliminated[-1])
            else:
                self.winner = "No Winner"
                self.victory_screen.set_winner("No Winner")
            self.effects.sound.play('victory')
            self.avatar_manager.sync_with_beyblades(self.beyblades, winner_name=self.winner)
            self.state = STATE_VICTORY
        else:
            # Add survivors to heat winners
            self.heat_winners.extend(survivor_names)

            # Check if more heats remain
            if self.current_heat < len(self.heats) - 1:
                # Show transition screen before next heat
                self.heat_transition_screen.set_advancers(
                    survivor_names,
                    self.current_heat + 1,
                    len(self.heats),
                    is_to_finals=False
                )
                self.pending_next_heat = self.current_heat + 1
                self.pending_is_finals = False
                self.state = STATE_HEAT_TRANSITION
            else:
                # All heats done - show transition to finals
                self.heat_transition_screen.set_advancers(
                    self.heat_winners,
                    len(self.heats),
                    len(self.heats),
                    is_to_finals=True
                )
                self.pending_next_heat = 0
                self.pending_is_finals = True
                self.state = STATE_HEAT_TRANSITION

    def _continue_after_heat(self):
        """Continue to the next heat or finals after transition screen."""
        if self.pending_is_finals:
            self.is_finals = True
        self.eliminated.clear()  # Clear heat eliminations for next heat
        self._start_heat(self.pending_next_heat)
        self.state = STATE_BATTLE

    def draw(self):
        if self.state == STATE_INPUT:
            self.input_screen.draw(self.screen)

        elif self.state == STATE_BATTLE:
            self.screen.fill(UI_BG)
            self.arena.draw(self.screen)

            # Draw avatars around the arena
            self.avatar_manager.draw(self.screen)

            # Draw beyblades (alive ones on top)
            dead_beyblades = [b for b in self.beyblades if not b.alive]
            alive_beyblades = [b for b in self.beyblades if b.alive]

            for beyblade in dead_beyblades:
                beyblade.draw(self.screen, self.fonts['small'])

            for beyblade in alive_beyblades:
                beyblade.draw(self.screen, self.fonts['small'])

            # Draw effects
            self.effects.draw(self.screen, self.fonts['medium'])

            # Draw HUD
            alive_count = len(alive_beyblades)
            total_count = len(self.beyblades)
            survivor_names = [b.name for b in alive_beyblades]
            heat_info = None
            if len(self.heats) > 1:
                if self.is_finals:
                    heat_info = ("FINALS", len(self.heat_winners))
                else:
                    heat_info = (f"Heat {self.current_heat + 1}/{len(self.heats)}", len(self.heats[self.current_heat]))
            self.battle_hud.draw(self.screen, alive_count, total_count, self.eliminated, survivor_names, self.round_number, heat_info)

        elif self.state == STATE_HEAT_TRANSITION:
            # Draw the arena state behind transition screen
            self.screen.fill(UI_BG)
            self.arena.draw(self.screen)

            # Draw avatars around the arena
            self.avatar_manager.draw(self.screen)

            for beyblade in self.beyblades:
                beyblade.draw(self.screen, self.fonts['small'])

            # Draw transition overlay
            self.heat_transition_screen.draw(self.screen)

        elif self.state == STATE_VICTORY:
            # Draw the final arena state behind victory screen
            self.screen.fill(UI_BG)
            self.arena.draw(self.screen)

            # Draw avatars around the arena
            self.avatar_manager.draw(self.screen)

            for beyblade in self.beyblades:
                beyblade.draw(self.screen, self.fonts['small'])

            # Draw victory overlay
            self.victory_screen.draw(self.screen)

        elif self.state == STATE_LEADERBOARD:
            self.leaderboard_screen.draw(self.screen)

        pygame.display.flip()

    def run(self):
        while self.running:
            mouse_clicked = self.handle_events()
            self.update(mouse_clicked)
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()

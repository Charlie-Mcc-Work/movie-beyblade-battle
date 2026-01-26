import pygame
import random
import math
import os
import threading
from .constants import (
    WINDOW_WIDTH, WINDOW_HEIGHT, FPS, UI_BG, WHITE, LIGHT_BLUE,
    STATE_INPUT, STATE_BATTLE, STATE_HEAT_TRANSITION, STATE_VICTORY, STATE_LEADERBOARD,
    STATE_DOCKET_SELECT, STATE_DOCKET_SPIN, STATE_DOCKET_RESULT, STATE_DOCKET_ZOOM,
    BEYBLADE_COLORS, ABILITY_CHANCE, ABILITIES, ARENA_RADIUS, AVATAR_ABILITIES,
    MOVIE_LIST_FILE, QUEUE_FILE, WATCHED_FILE, ABILITY_WINS_FILE, ABILITY_STATS_FILE,
    GOLDEN_DOCKET_FILE, DIAMOND_DOCKET_FILE, SHIT_DOCKET_FILE,
    PERMANENT_PEOPLE_FILE, PEOPLE_COUNTER_FILE
)
from .beyblade import Beyblade, check_collision, resolve_collision
from .arena import Arena
from .effects import EffectsManager
from .avatar import AvatarManager, AvatarState
from .ui import (InputScreen, BattleHUD, HeatTransitionScreen, VictoryScreen, LeaderboardScreen,
                 ParticipantSelectScreen, DocketResultScreen, DocketSpinScreen, create_fonts)
from .docket import DocketWheel, DocketZoomTransition


class Game:
    def __init__(self, web_mode=False):
        pygame.init()

        # Web mode flag for streaming to browsers
        self.web_mode = web_mode
        if web_mode:
            print(f"[Game] Starting in web mode, cwd: {os.getcwd()}")
        self.frame_callback = None  # Called after each frame with screen surface
        self.external_events = []  # Events injected from web clients
        self._external_events_lock = threading.Lock()  # Thread safety for web events
        self._web_mouse_pos = (0, 0)  # Mouse position from web client

        # Make window resizable
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)

        # Scrap (clipboard) must be initialized after display
        pygame.scrap.init()
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

        # Docket screens (initialized when needed)
        self.participant_select_screen = None
        self.docket_spin_screen = DocketSpinScreen(self.fonts)
        self.docket_result_screen = DocketResultScreen(self.fonts)

        # Docket state
        self.docket_participants = []  # Selected participant names
        self.current_docket_type = 'golden'  # 'golden', 'diamond', or 'shit'
        self.docket_data = {'golden': {}, 'diamond': {}, 'shit': {}}
        self.people_counter = {}  # {name: count} for recurring people

        # Always update layouts for actual window size
        self.arena.update_center(self.window_width, self.window_height)
        self.input_screen.update_layout(self.window_width, self.window_height)
        self.battle_hud.update_layout(self.window_width, self.window_height)
        self.heat_transition_screen.update_layout(self.window_width, self.window_height)
        self.victory_screen.update_layout(self.window_width, self.window_height)
        self.leaderboard_screen.update_layout(self.window_width, self.window_height)
        self.docket_spin_screen.update_layout(self.window_width, self.window_height)
        self.docket_result_screen.update_layout(self.window_width, self.window_height)

        self.beyblades: list[Beyblade] = []
        self.eliminated: list[str] = []  # Current heat eliminations
        self.all_eliminated: list[str] = []  # Full tournament elimination order
        self.state = STATE_INPUT
        self.speed_multiplier = 1
        self.winner = None
        self.round_number = 1
        self.ability_win_recorded = False  # Prevent double-recording ability wins
        self.is_queue_battle = False  # True if battling queue.txt movies

        # Tournament state
        self.heats: list[list[str]] = []
        self.current_heat = 0
        self.heat_winners: list[str] = []
        self.is_finals = False
        self.advancers_per_heat = 2  # Top N from each heat advance
        self.max_per_heat = 11  # Max beyblades per heat

        # Preliminary round state (for large tournaments >55 movies)
        self.preliminary_groups: list[list[str]] = []  # Groups of movies for preliminary battles
        self.preliminary_winning_movies: list[str] = []  # Movies from the winning group
        self.is_preliminary = False  # True when running preliminary rounds
        self.preliminary_max_size = 55  # Max movies per preliminary group

        # Persistent movie data (survives across heats)
        self.movie_abilities: dict[str, tuple] = {}  # name -> (ability_key, color)
        self.zombie_used: set[str] = set()  # Track which movies have used zombie (persists across heats)
        self.swamp_thing_used: set[str] = set()  # Track which movies have used swamp thing (persists across heats)
        self.andy_respawn_used: set[str] = set()  # Track which movies have used Andy Dufresne respawn

        # Portal state: [{'x': float, 'y': float, 'partner_idx': int}]
        self.portals: list[dict] = []
        self.portal_cooldown = 0  # Cooldown between portal uses

        # Countdown state
        self.countdown_timer = 0
        self.countdown_active = False
        self.countdown_last_num = 0  # Track which number was last shown for sound

        # Fireballs list: [{'x', 'y', 'vx', 'vy', 'owner_name', 'color'}]
        self.fireballs = []

        # Ice projectiles list: [{'x', 'y', 'vx', 'vy', 'owner_name', 'color', 'lifetime'}]
        self.ice_projectiles = []

        # Ice trails list: [{'x', 'y', 'lifetime', 'color'}]
        self.ice_trails = []

        # Grenades list: [{'x', 'y', 'target_x', 'target_y', 'progress', 'owner_name', 'color'}]
        # progress 0-1 represents flight, 1 = landed/explode
        self.grenades = []

        # Kamehameha beams list: [{'start_x', 'start_y', 'angle', 'length', 'width', 'lifetime', 'owner_name', 'color'}]
        self.kamehameha_beams = []

        # Water waves list: [{'x', 'y', 'angle', 'width', 'progress', 'owner_name'}]
        self.water_waves = []

        # Obelisk bumpers spawned by The Obelisk ability
        self.obelisk_bumpers = []

        # Kevin McAllister traps: [{'x', 'y', 'type', 'owner_name', 'lifetime'}]
        self.traps = []

        # John Wick bullets: [{'x', 'y', 'vx', 'vy', 'owner_name', 'lifetime'}]
        self.bullets = []

        # Interstellar black holes: [{'x', 'y', 'owner_name'}]
        self.black_holes = []

        # Neo heat reset tracking
        self.heat_start_frame = 0
        self.current_frame = 0
        self.neo_reset_used_this_heat = False
        self.neo_reset_countdown = 0  # Frames to show reset message
        self.neo_reset_name = ""  # Name of Neo who triggered reset

        # Once-per-game ability tracking
        self.barry_lyndon_used = set()
        self.oppenheimer_used = set()

        # Transition state
        self.pending_next_heat = 0
        self.pending_is_finals = False
        self.pending_start_main_tournament = False

        self.running = True

    def start_battle(self, movie_list: list):
        """Initialize a new tournament with the given movie list."""
        # Deduplicate movie list (preserve order, keep first occurrence)
        # Case-insensitive and whitespace-tolerant
        seen = set()
        unique_movies = []
        for movie in movie_list:
            normalized = movie.strip().lower()
            if normalized not in seen:
                seen.add(normalized)
                unique_movies.append(movie)
        movie_list = unique_movies

        self.eliminated.clear()
        self.all_eliminated.clear()
        self.effects.clear()
        self.winner = None
        self.round_number = 1
        self.ability_win_recorded = False  # Reset for new tournament
        self.heat_winners.clear()
        self.current_heat = 0
        self.is_finals = False
        self.movie_abilities.clear()  # Fresh abilities for new tournament
        self.zombie_used.clear()  # Fresh zombie uses for new tournament
        self.swamp_thing_used.clear()  # Fresh swamp thing uses for new tournament
        self.portals.clear()
        self.andy_respawn_used = set()  # Track Andy Dufresne respawns

        # Pre-assign abilities - 100% chance, unique abilities distributed first
        # Create a pool of abilities that ensures each ability is used once before repeating
        ability_keys = list(ABILITIES.keys())
        ability_pool = []

        # Build pool: each ability appears once per "round", shuffle each round
        num_rounds = (len(movie_list) // len(ability_keys)) + 2  # Extra rounds for prestige duplicates
        for _ in range(num_rounds):
            round_abilities = ability_keys.copy()
            random.shuffle(round_abilities)
            ability_pool.extend(round_abilities)

        pool_index = 0
        prestige_movies = []

        for movie in movie_list:
            ability_key = ability_pool[pool_index]
            pool_index += 1

            if ability_key == 'the_prestige':
                prestige_movies.append(movie)
                # Store ability for both copies
                color = BEYBLADE_COLORS[len(self.movie_abilities) % len(BEYBLADE_COLORS)]
                self.movie_abilities[movie] = (ability_key, color)
                self.movie_abilities[f"{movie} (Double)"] = (ability_key, color)
            else:
                color = BEYBLADE_COLORS[len(self.movie_abilities) % len(BEYBLADE_COLORS)]
                self.movie_abilities[movie] = (ability_key, color)

        # Add prestige duplicates to movie list
        for movie in prestige_movies:
            movie_list.append(f"{movie} (Double)")

        # Shuffle all movies (including prestige duplicates) for random heat placement
        random.shuffle(movie_list)

        # Check if we need a preliminary round (>55 movies)
        if len(movie_list) > self.preliminary_max_size:
            # Split movies into groups of max 55
            self.preliminary_groups = []
            for i in range(0, len(movie_list), self.preliminary_max_size):
                group = movie_list[i:i + self.preliminary_max_size]
                if group:
                    self.preliminary_groups.append(group)

            self.is_preliminary = True

            # Create group names showing actual movie count in each group
            group_names = [f"Group {i+1} ({len(g)} movies)" for i, g in enumerate(self.preliminary_groups)]

            # Group beyblades get abilities just like regular beyblades
            group_ability_pool = list(ABILITIES.keys())
            random.shuffle(group_ability_pool)
            for i, group_name in enumerate(group_names):
                color = BEYBLADE_COLORS[i % len(BEYBLADE_COLORS)]
                ability_key = group_ability_pool[i % len(group_ability_pool)]
                self.movie_abilities[group_name] = (ability_key, color)

            # Set up the preliminary battle with group beyblades
            self.heats = [group_names]
            self._start_heat(0)
        else:
            # Normal tournament flow
            self.is_preliminary = False
            self.preliminary_groups.clear()

            # If few movies, just run single battle (no heats needed)
            if len(movie_list) <= self.max_per_heat:
                self.heats = [movie_list.copy()]  # Use copy to avoid reference issues
                if self.web_mode:
                    print(f"[Battle] Single heat with {len(movie_list)} movies")
            else:
                # Split into heats (slicing creates new lists)
                self.heats = []
                for i in range(0, len(movie_list), self.max_per_heat):
                    heat = movie_list[i:i + self.max_per_heat]
                    if heat:
                        self.heats.append(heat)
                if self.web_mode:
                    print(f"[Battle] {len(self.heats)} heats created: {[len(h) for h in self.heats]} movies each")

            # Start first heat
            self._start_heat(0)

        self.state = STATE_BATTLE
        self.speed_multiplier = 1
        self.battle_hud.current_speed = 1

    def _start_heat(self, heat_index: int, is_neo_reset: bool = False):
        """Start a specific heat battle."""
        self.current_heat = heat_index
        self.round_number = 1
        self.beyblades.clear()
        self.effects.clear()
        self.fireballs.clear()
        self.ice_projectiles.clear()
        self.ice_trails.clear()
        self.grenades.clear()
        self.kamehameha_beams.clear()
        self.water_waves.clear()
        self.portals.clear()
        self.portal_cooldown = 0
        self.obelisk_bumpers.clear()
        self.traps.clear()
        self.bullets.clear()
        self.black_holes.clear()
        self.heat_start_frame = self.current_frame

        # Only reset Neo flag if this is a normal heat start, not a Neo reset
        if not is_neo_reset:
            self.neo_reset_used_this_heat = False

        if self.is_finals:
            movies = self.heat_winners
        else:
            movies = self.heats[heat_index]

        # Use rectangle finals arena for the deciding battle (not for preliminary rounds)
        is_final_battle = (self.is_finals or len(self.heats) == 1) and not self.is_preliminary
        self.arena.set_finals_mode(is_final_battle)

        # Use smaller preliminary arena with pillars for the group stage
        if self.is_preliminary and heat_index == 0:
            self.arena.set_preliminary_mode(True)
        elif not is_final_battle:
            self.arena.set_preliminary_mode(False)

        self._spawn_beyblades(movies)

        # Start countdown (3 seconds at 60 FPS = 180 frames)
        self.countdown_timer = 180
        self.countdown_active = True
        self.countdown_last_num = 4  # Start above 3 so first beep plays
        self.effects.sound.play('countdown_beep')  # Play first beep immediately

    def _spawn_beyblades(self, movie_list: list):
        """Spawn beyblades with positions and tangential velocities."""
        # Create a copy to shuffle for spawn positions without modifying original
        # Defensive: deduplicate to prevent mystery duplicate spawns
        seen = set()
        movies_to_spawn = []
        for movie in movie_list:
            if movie not in seen:
                seen.add(movie)
                movies_to_spawn.append(movie)
        random.shuffle(movies_to_spawn)
        spawns = self.arena.get_spawn_positions(len(movies_to_spawn))

        for i, (movie, spawn) in enumerate(zip(movies_to_spawn, spawns)):
            x, y, vx, vy = spawn
            beyblade = Beyblade(movie, x, y, i)
            beyblade.vx = vx
            beyblade.vy = vy

            # Restore or store persistent data (ability and color)
            if movie in self.movie_abilities:
                # Returning movie - restore its ability and color
                ability_key, color = self.movie_abilities[movie]
                beyblade.ability = ability_key
                if ability_key:
                    beyblade.ability_data = ABILITIES[ability_key].copy()
                    # Reapply size modifiers
                    if ability_key == 'giant':
                        beyblade.radius = int(beyblade.base_radius * 1.4)
                    elif ability_key == 'tiny':
                        beyblade.radius = int(beyblade.base_radius * 0.7)
                beyblade.color = color
            else:
                # New movie - store its generated ability and color
                self.movie_abilities[movie] = (beyblade.ability, beyblade.color)

            # Initialize ability timers
            if beyblade.ability == 'timebomb':
                beyblade.timebomb_timer = 1200  # 20 seconds
            if beyblade.ability == 'earthquake':
                beyblade.earthquake_timer = 900  # 15 seconds
            if beyblade.ability == 'lightning_storm':
                beyblade.lightning_timer = 600  # 10 seconds
            if beyblade.ability == 'doomsday':
                beyblade.doomsday_timer = 1800  # 30 seconds

            # Truman: spawn in center of arena
            if beyblade.ability == 'truman':
                beyblade.x = self.arena.center_x
                beyblade.y = self.arena.center_y
                beyblade.vx = random.uniform(-2, 2)
                beyblade.vy = random.uniform(-2, 2)

            # Interstellar: record spawn position for black hole
            if beyblade.ability == 'interstellar':
                beyblade.interstellar_spawn_x = beyblade.x
                beyblade.interstellar_spawn_y = beyblade.y
                self.black_holes.append({
                    'x': beyblade.x,
                    'y': beyblade.y,
                    'owner_name': beyblade.name
                })

            # Neo: record spawn frame for reset check
            if beyblade.ability == 'neo':
                beyblade.neo_spawn_frame = self.current_frame

            # Marty McFly: record spawn position for teleport ability
            if beyblade.ability == 'marty_mcfly':
                beyblade.marty_mcfly_spawn_x = beyblade.x
                beyblade.marty_mcfly_spawn_y = beyblade.y
                beyblade.marty_mcfly_used = False

            self.beyblades.append(beyblade)

            # Naruto: create 2 clones, each with 1/3 HP (including original)
            if beyblade.ability == 'naruto' and not beyblade.naruto_cloned:
                beyblade.naruto_cloned = True
                # Split HP into thirds
                third_hp = beyblade.max_stamina / 3
                beyblade.stamina = third_hp
                beyblade.max_stamina = third_hp

                # Create 2 clones - spawn in distinct positions to avoid immediate collision
                clone_offsets = [
                    (80, 40),   # Clone 1: offset right and down
                    (-80, -40), # Clone 2: offset left and up
                ]
                for clone_num in range(2):
                    offset_x, offset_y = clone_offsets[clone_num]
                    clone = Beyblade(f"{movie} (Clone {clone_num + 1})", x, y, i)
                    clone.vx = vx + random.uniform(-2, 2)
                    clone.vy = vy + random.uniform(-2, 2)
                    clone.x = x + offset_x + random.uniform(-10, 10)
                    clone.y = y + offset_y + random.uniform(-10, 10)
                    clone.ability = 'naruto'
                    clone.ability_data = beyblade.ability_data.copy() if beyblade.ability_data else None
                    clone.color = beyblade.color
                    clone.stamina = third_hp
                    clone.max_stamina = third_hp
                    clone.is_clone = True
                    clone.original_name = movie
                    clone.naruto_cloned = True  # Prevent clones from cloning
                    self.beyblades.append(clone)

        # Create avatars for this batch of beyblades
        self.avatar_manager.create_avatars(self.beyblades, self.arena)

        # Post-spawn ability setup
        from .arena import ObeliskBumper
        for beyblade in self.beyblades:
            # Kill Bill: select a random target for this heat
            if beyblade.ability == 'kill_bill':
                targets = [b for b in self.beyblades if b != beyblade and b.name != beyblade.name]
                if targets:
                    beyblade.kill_bill_target = random.choice(targets).name
                    self.effects.spawn_ability_notification(
                        beyblade.name, f'TARGET: {beyblade.kill_bill_target[:12]}', ABILITIES['kill_bill']['color'], 'ability', 'Kill Bill'
                    )

            # The Obelisk: spawn a bumper at random arena position
            if beyblade.ability == 'the_obelisk':
                if self.arena.finals_mode:
                    bx = random.uniform(self.arena.rect_left + 80, self.arena.rect_right - 80)
                    by = random.uniform(self.arena.rect_top + 80, self.arena.rect_bottom - 80)
                else:
                    angle = random.uniform(0, 2 * math.pi)
                    dist = random.uniform(50, self.arena.radius * 0.6)
                    bx = self.arena.center_x + math.cos(angle) * dist
                    by = self.arena.center_y + math.sin(angle) * dist
                # Create 2001-style monolith obelisk
                bumper = ObeliskBumper(int(bx), int(by), width=25, height=70)
                self.obelisk_bumpers.append(bumper)
                self.effects.spawn_ability_notification(beyblade.name, 'OBELISK RISES!', ABILITIES['the_obelisk']['color'], 'ability')

            # American Psycho: initialize damage tracking
            if beyblade.ability == 'american_psycho':
                beyblade.american_psycho_timer = 1200  # 20 seconds
                beyblade.american_psycho_stored_stamina = beyblade.stamina

            # Amadeus: pick a rival for this heat
            if beyblade.ability == 'amadeus':
                targets = [b for b in self.beyblades if b != beyblade and b.name != beyblade.name]
                if targets:
                    beyblade.amadeus_rival = random.choice(targets).name
                    self.effects.spawn_ability_notification(
                        beyblade.name, f'RIVAL: {beyblade.amadeus_rival[:12]}', ABILITIES['amadeus']['color'], 'ability', 'Amadeus'
                    )

            # Terminator: pick a target for this heat
            if beyblade.ability == 'terminator':
                targets = [b for b in self.beyblades if b != beyblade and b.name != beyblade.name]
                if targets:
                    beyblade.terminator_target = random.choice(targets).name
                    beyblade.terminator_no_hit_timer = 0
                    self.effects.spawn_ability_notification(
                        beyblade.name, f'TARGET: {beyblade.terminator_target[:12]}', ABILITIES['terminator']['color'], 'ability', 'Terminator'
                    )

            # Ferris Bueller: starts hidden, spawns 5 seconds late
            if beyblade.ability == 'ferris_bueller' and beyblade.ferris_late_entry:
                beyblade.alive = False
                beyblade.x = -1000  # Off screen
                beyblade.y = -1000
                beyblade.ferris_timer = 300  # 5 seconds

    def _handle_resize(self, new_width, new_height):
        """Handle window resize - updates all layouts."""
        if new_width == self.window_width and new_height == self.window_height:
            return
        self.window_width = new_width
        self.window_height = new_height
        # Update arena center and get offset
        dx, dy = self.arena.update_center(new_width, new_height)
        # Move all beyblades by the offset to keep them centered
        for beyblade in self.beyblades:
            beyblade.x += dx
            beyblade.y += dy
        # Update avatar positions
        self.avatar_manager.update_positions(self.arena)
        # Update UI components
        self.input_screen.update_layout(new_width, new_height)
        self.battle_hud.update_layout(new_width, new_height)
        self.heat_transition_screen.update_layout(new_width, new_height)
        self.victory_screen.update_layout(new_width, new_height)
        self.leaderboard_screen.update_layout(new_width, new_height)
        self.docket_spin_screen.update_layout(new_width, new_height)
        self.docket_result_screen.update_layout(new_width, new_height)
        if self.participant_select_screen:
            self.participant_select_screen.update_layout(new_width, new_height)

    def inject_event(self, event_dict):
        """Inject an event from external source (web client)."""
        with self._external_events_lock:
            self.external_events.append(event_dict)

    def handle_events(self):
        mouse_clicked = False

        # Check for window size changes every frame (works better with tiling WMs like i3)
        current_size = self.screen.get_size()
        if current_size[0] != self.window_width or current_size[1] != self.window_height:
            self._handle_resize(current_size[0], current_size[1])

        # Process external events from web clients (thread-safe)
        with self._external_events_lock:
            events_to_process = self.external_events[:]
            self.external_events.clear()
        for ext in events_to_process:
            event = self._convert_external_event(ext)
            if event:
                pygame.event.post(event)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if event.type == pygame.VIDEORESIZE:
                self._handle_resize(event.w, event.h)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_clicked = True

            if self.state == STATE_INPUT:
                self.input_screen.handle_event(event)

            if self.state == STATE_LEADERBOARD:
                self.leaderboard_screen.handle_scroll(event)

            if self.state == STATE_DOCKET_RESULT:
                if self.docket_result_screen.handle_event(event):
                    # ENTER was pressed with valid input - trigger confirmation
                    new_movie = self.docket_result_screen.replacement_input.text.strip()
                    if new_movie:
                        self.docket_result_screen.replacement_confirmed = True
                        self._update_golden_docket(self.docket_result_screen.winner_name, new_movie)

            if self.state == STATE_DOCKET_SELECT and self.participant_select_screen:
                self.participant_select_screen.handle_event(event)

        return mouse_clicked

    def _convert_external_event(self, ext):
        """Convert external event dict to pygame event."""
        try:
            if ext['type'] == 'mousedown':
                return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=ext.get('button', 1), pos=(ext['x'], ext['y']))
            elif ext['type'] == 'mouseup':
                return pygame.event.Event(pygame.MOUSEBUTTONUP, button=ext.get('button', 1), pos=(ext['x'], ext['y']))
            elif ext['type'] == 'mousemove':
                # Pygame doesn't have a move event, but we track position via get_pos()
                # We'll handle this differently - set a stored position
                self._web_mouse_pos = (ext['x'], ext['y'])
                return None
            elif ext['type'] == 'keydown':
                key = ext.get('key', 0)
                mod = ext.get('mod', 0)
                unicode_char = ext.get('unicode', '')
                return pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod, unicode=unicode_char)
            elif ext['type'] == 'keyup':
                key = ext.get('key', 0)
                mod = ext.get('mod', 0)
                return pygame.event.Event(pygame.KEYUP, key=key, mod=mod)
            elif ext['type'] == 'mousewheel':
                # Pygame 2.x scroll event
                return pygame.event.Event(pygame.MOUSEWHEEL, y=ext.get('y', 0), x=ext.get('x', 0))
        except Exception:
            pass
        return None

    def update(self, mouse_clicked: bool):
        # Use web mouse position if available, otherwise pygame's
        if self.web_mode and hasattr(self, '_web_mouse_pos'):
            mouse_pos = self._web_mouse_pos
        else:
            mouse_pos = pygame.mouse.get_pos()

        if self.state == STATE_INPUT:
            self.input_screen.update(mouse_pos)
            should_start, movie_list = self.input_screen.check_start(mouse_pos, mouse_clicked)
            if should_start:
                self.is_queue_battle = False
                self.start_battle(movie_list)

            # Check for queue battle start
            should_start_queue, queue_movies = self.input_screen.check_queue_battle(mouse_pos, mouse_clicked)
            if should_start_queue:
                self.is_queue_battle = True
                self.start_battle(queue_movies)

            # Check for queue item click (to remove from queue)
            clicked_queue_item = self.input_screen.check_queue_click(mouse_pos, mouse_clicked)
            if clicked_queue_item:
                self.input_screen.remove_from_queue(clicked_queue_item)

            # Check for Golden Docket button click
            if self.input_screen.check_docket(mouse_pos, mouse_clicked):
                print(f"[UI] Golden Docket button clicked")
                self._start_docket_select()

            # Check for Quit button click
            if self.input_screen.check_quit(mouse_pos, mouse_clicked):
                self.running = False

        elif self.state == STATE_BATTLE:
            self.battle_hud.update(mouse_pos)
            self.speed_multiplier = self.battle_hud.check_speed_click(mouse_pos, mouse_clicked)

            # Check mute toggle
            if self.battle_hud.check_mute_click(mouse_pos, mouse_clicked):
                self.effects.sound.muted = self.battle_hud.muted

            # Handle Neo reset message countdown
            if self.neo_reset_countdown > 0:
                self.neo_reset_countdown -= 1

            # Handle countdown
            if self.countdown_active:
                self.countdown_timer -= 1
                # Update avatars during countdown (for launch animation)
                self.avatar_manager.update()

                # Determine current number and play sound on change
                if self.countdown_timer > 120:
                    current_num = 3
                elif self.countdown_timer > 60:
                    current_num = 2
                elif self.countdown_timer > 0:
                    current_num = 1
                else:
                    current_num = 0  # GO!

                if current_num != self.countdown_last_num:
                    self.countdown_last_num = current_num
                    if current_num == 0:
                        self.effects.sound.play('countdown_go')
                    elif current_num > 0:
                        self.effects.sound.play('countdown_beep')

                if self.countdown_timer <= 0:
                    self.countdown_active = False
            else:
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
                self.leaderboard_screen.set_rankings(self.winner, self.all_eliminated, self.is_queue_battle)
                self.state = STATE_LEADERBOARD

        elif self.state == STATE_LEADERBOARD:
            self.leaderboard_screen.update(mouse_pos)
            if self.leaderboard_screen.check_play_again(mouse_pos, mouse_clicked):
                self.is_queue_battle = False
                self.state = STATE_INPUT
            elif self.leaderboard_screen.check_quit(mouse_pos, mouse_clicked):
                self.running = False
            elif self.leaderboard_screen.check_choose(mouse_pos, mouse_clicked):
                # CHOOSE: Move winner from movies.txt (or queue.txt) to watched.txt
                self._choose_movie(self.winner)
                self.is_queue_battle = False
                self.state = STATE_INPUT
            elif self.leaderboard_screen.check_queue(mouse_pos, mouse_clicked):
                # QUEUE: Move winner from movies.txt to queue.txt and restart
                self._queue_movie(self.winner)
                self.is_queue_battle = False
                self.state = STATE_INPUT

        elif self.state == STATE_DOCKET_SELECT:
            self.participant_select_screen.update(mouse_pos)
            self.participant_select_screen.handle_click(mouse_pos, mouse_clicked)

            if self.participant_select_screen.check_start(mouse_pos, mouse_clicked):
                print(f"[UI] Start Golden Docket button clicked")
                self._start_docket_spin()

        elif self.state == STATE_DOCKET_SPIN:
            self.docket_spin_screen.update(mouse_pos)

            # Check if spin button clicked
            if self.docket_spin_screen.check_spin(mouse_pos, mouse_clicked):
                self.docket_spin_screen.wheel.spin()

            # Check if force upgrade debug button clicked
            if self.docket_spin_screen.check_force_upgrade(mouse_pos, mouse_clicked):
                self.docket_spin_screen.wheel.force_upgrade()

            # Check if wheel stopped - click anywhere to continue
            if self.docket_spin_screen.is_stopped() and mouse_clicked:
                result = self.docket_spin_screen.get_result()
                if result:
                    result_type, entry = result
                    if result_type == 'upgrade':
                        # Transition to next docket tier
                        self._start_docket_zoom()
                    else:
                        # Show result screen
                        name, movie = entry
                        # For final wheel, remove the movie from source file
                        if self.current_docket_type == 'final':
                            self._remove_final_wheel_winner(movie)
                        self.docket_result_screen.set_result(name, movie, self.current_docket_type)
                        self.state = STATE_DOCKET_RESULT

        elif self.state == STATE_DOCKET_ZOOM:
            self.docket_spin_screen.update(mouse_pos)

            # Check if zoom transition complete
            if not self.docket_spin_screen.is_transitioning():
                self.state = STATE_DOCKET_SPIN

        elif self.state == STATE_DOCKET_RESULT:
            self.docket_result_screen.update(mouse_pos)

            # Check for replacement confirmation (golden docket only)
            new_movie = self.docket_result_screen.check_confirm(mouse_pos, mouse_clicked)
            if new_movie:
                self._update_golden_docket(self.docket_result_screen.winner_name, new_movie)

            if self.docket_result_screen.check_title(mouse_pos, mouse_clicked):
                self.state = STATE_INPUT
            elif self.docket_result_screen.check_quit(mouse_pos, mouse_clicked):
                self.running = False

    def update_battle(self):
        # Increment frame counter
        self.current_frame += 1

        # Update arena (bumper animations)
        self.arena.update()

        # Interstellar: black holes pull ALL beyblades on the map (Batman immune)
        for black_hole in self.black_holes:
            for beyblade in self.beyblades:
                if beyblade.alive and beyblade.name != black_hole['owner_name'] and beyblade.ability != 'batman':
                    dx = black_hole['x'] - beyblade.x
                    dy = black_hole['y'] - beyblade.y
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist > 5:  # Avoid division issues when very close
                        # Constant pull strength across entire map, weaker but always active
                        pull_strength = 0.08
                        beyblade.vx += (dx / dist) * pull_strength
                        beyblade.vy += (dy / dist) * pull_strength

        # Deadpool: regenerate health over time
        for beyblade in self.beyblades:
            if beyblade.alive and beyblade.ability == 'deadpool':
                regen_rate = 0.05  # HP per frame
                beyblade.stamina = min(beyblade.max_stamina, beyblade.stamina + regen_rate)

        # Update Amadeus rival status (needed for edge bounce check)
        alive_names = {b.name for b in self.beyblades if b.alive}
        for beyblade in self.beyblades:
            if beyblade.ability == 'amadeus' and beyblade.amadeus_rival:
                beyblade.amadeus_rival_alive = beyblade.amadeus_rival in alive_names

        # Update all beyblades
        for beyblade in self.beyblades:
            beyblade.update()
            if beyblade.alive:
                # Marty McFly: teleport back to spawn when within 10% of edge (once per heat)
                if beyblade.ability == 'marty_mcfly' and not beyblade.marty_mcfly_used:
                    near_edge = False
                    if self.arena.finals_mode:
                        # Rectangle arena: check distance from closing left/right edges
                        arena_width = self.arena.current_rect_right - self.arena.current_rect_left
                        edge_threshold = arena_width * 0.1
                        if (beyblade.x < self.arena.current_rect_left + edge_threshold or
                            beyblade.x > self.arena.current_rect_right - edge_threshold):
                            near_edge = True
                    else:
                        # Circular arena: check distance from center vs radius
                        dx = beyblade.x - self.arena.center_x
                        dy = beyblade.y - self.arena.center_y
                        dist_from_center = math.sqrt(dx**2 + dy**2)
                        if dist_from_center > self.arena.radius * 0.9:
                            near_edge = True

                    if near_edge:
                        # Teleport back to spawn position
                        beyblade.x = beyblade.marty_mcfly_spawn_x
                        beyblade.y = beyblade.marty_mcfly_spawn_y
                        beyblade.vx = 0
                        beyblade.vy = 0
                        beyblade.marty_mcfly_used = True
                        self.effects.spawn_ability_notification(
                            beyblade.name, 'BACK IN TIME!', ABILITIES['marty_mcfly']['color'], 'ability', 'Marty McFly'
                        )
                        self.effects.sound.play('teleport')

                bumper_hit = self.arena.apply_boundary(beyblade)
                if bumper_hit:
                    # Spawn sparks and play sound for bumper hit
                    self.effects.spawn_collision_sparks(beyblade.x, beyblade.y, 1.5)
                    self.effects.sound.play('bumper')

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
                    for trigger in triggers:
                        if len(trigger) == 4:
                            name, text, color, ability_name = trigger
                        else:
                            name, text, color = trigger
                            ability_name = None
                        sound = self._get_ability_sound(text)
                        self.effects.spawn_ability_notification(name, text, color, sound, ability_name)

        # Handle parasite damage sharing
        for beyblade in self.beyblades:
            if beyblade.alive and beyblade.parasite_target:
                # Find the target and share damage (both take stamina drain)
                target = next((b for b in self.beyblades if b.name == beyblade.parasite_target and b.alive), None)
                if target:
                    # Slowly drain both (parasitic relationship hurts both)
                    drain = 0.02
                    beyblade.stamina -= drain
                    target.stamina -= drain
                    # If either dies, break the link
                    if beyblade.stamina <= 0 or target.stamina <= 0:
                        beyblade.parasite_target = None
                        target.parasite_host = None
                else:
                    # Target is dead, clear the link
                    beyblade.parasite_target = None

        # Check for explosive triggers
        for beyblade in self.beyblades:
            if beyblade.explosive_triggered:
                beyblade.explosive_triggered = False
                # Push all alive beyblades away (Batman immune)
                for other in self.beyblades:
                    if other.alive and other != beyblade and other.ability != 'batman':
                        dx = other.x - beyblade.x
                        dy = other.y - beyblade.y
                        dist = math.sqrt(dx**2 + dy**2)
                        if dist < 300 and dist > 0:  # Explosion radius
                            force = 15 * (1 - dist / 300)  # Stronger when closer
                            other.vx += (dx / dist) * force
                            other.vy += (dy / dist) * force
                # Visual and sound
                self.effects.spawn_collision_sparks(beyblade.x, beyblade.y, 5.0)
                self.effects.spawn_ability_notification(beyblade.name, 'EXPLOSION!', ABILITIES['explosive']['color'], 'burst')

        # Handle fireball ability - avatars shoot fireballs toward arena (continues after death)
        for beyblade in self.beyblades:
            if beyblade.ability == 'fireball':
                avatar = self.avatar_manager.avatars.get(beyblade.name)
                if avatar and avatar.state not in (AvatarState.ELIMINATED, AvatarState.LAUNCHING):
                    avatar.fireball_cooldown -= 1
                    if avatar.fireball_cooldown <= 0:
                        # Spawn a fireball from avatar toward a random point in arena
                        dx = self.arena.center_x - avatar.x
                        dy = self.arena.center_y - avatar.y
                        base_angle = math.atan2(dy, dx)
                        # Add randomness to direction
                        shoot_angle = base_angle + random.uniform(-0.6, 0.6)
                        speed = 8
                        self.fireballs.append({
                            'x': avatar.x,
                            'y': avatar.y,
                            'vx': math.cos(shoot_angle) * speed,
                            'vy': math.sin(shoot_angle) * speed,
                            'owner_name': beyblade.name,
                            'color': beyblade.color,
                            'lifetime': 180,  # 3 seconds max
                        })
                        avatar.fireball_cooldown = 90  # 1.5 second cooldown

        # Update fireballs - movement and collision
        fireballs_to_remove = []
        for fireball in self.fireballs:
            fireball['x'] += fireball['vx']
            fireball['y'] += fireball['vy']
            fireball['lifetime'] -= 1

            # Check collision with beyblades
            for beyblade in self.beyblades:
                if beyblade.alive and beyblade.name != fireball['owner_name']:
                    dx = beyblade.x - fireball['x']
                    dy = beyblade.y - fireball['y']
                    dist = math.sqrt(dx**2 + dy**2)
                    if dist < beyblade.radius + 8:  # 8 is fireball radius
                        # Marty Mauser: reflect projectiles back
                        if beyblade.ability == 'marty_mauser':
                            fireball['vx'] = -fireball['vx']
                            fireball['vy'] = -fireball['vy']
                            fireball['owner_name'] = beyblade.name
                            fireball['lifetime'] = 180
                            self.effects.spawn_collision_sparks(fireball['x'], fireball['y'], 0.5)
                            self.effects.spawn_ability_notification(beyblade.name, 'REFLECT!', ABILITIES['marty_mauser']['color'], 'ability', 'Marty Mauser')
                            break
                        # Hit! Apply knockback like a regular collision (Batman immune)
                        if dist > 0 and beyblade.ability != 'batman':
                            knockback = 10
                            beyblade.vx += (dx / dist) * knockback
                            beyblade.vy += (dy / dist) * knockback
                        self.effects.spawn_collision_sparks(fireball['x'], fireball['y'], 1.5)
                        self.effects.sound.play('hit')
                        fireballs_to_remove.append(fireball)
                        break

            # Remove if expired or out of arena
            if fireball['lifetime'] <= 0:
                fireballs_to_remove.append(fireball)

        for fb in fireballs_to_remove:
            if fb in self.fireballs:
                self.fireballs.remove(fb)

        # Handle ice ability - avatars shoot ice toward arena (continues after death)
        for beyblade in self.beyblades:
            if beyblade.ability == 'ice':
                avatar = self.avatar_manager.avatars.get(beyblade.name)
                if avatar and avatar.state not in (AvatarState.ELIMINATED, AvatarState.LAUNCHING):
                    avatar.ice_cooldown -= 1
                    if avatar.ice_cooldown <= 0:
                        # Spawn an ice projectile from avatar toward a random point in arena
                        dx = self.arena.center_x - avatar.x
                        dy = self.arena.center_y - avatar.y
                        base_angle = math.atan2(dy, dx)
                        # Add randomness to direction
                        shoot_angle = base_angle + random.uniform(-0.6, 0.6)
                        speed = 6  # Slower than fireball
                        self.ice_projectiles.append({
                            'x': avatar.x,
                            'y': avatar.y,
                            'vx': math.cos(shoot_angle) * speed,
                            'vy': math.sin(shoot_angle) * speed,
                            'owner_name': beyblade.name,
                            'color': (150, 220, 255),
                            'lifetime': 240,  # 4 seconds max
                        })
                        avatar.ice_cooldown = 120  # 2 second cooldown

        # Update ice projectiles - movement, trails, and collision
        ice_to_remove = []
        for ice in self.ice_projectiles:
            ice['x'] += ice['vx']
            ice['y'] += ice['vy']
            ice['lifetime'] -= 1

            # Leave ice trail every few frames
            if ice['lifetime'] % 3 == 0:
                self.ice_trails.append({
                    'x': ice['x'],
                    'y': ice['y'],
                    'lifetime': 600,  # 10 seconds
                    'color': (150, 220, 255),
                })

            # Check collision with beyblades
            for beyblade in self.beyblades:
                if beyblade.alive and beyblade.name != ice['owner_name']:
                    dx = beyblade.x - ice['x']
                    dy = beyblade.y - ice['y']
                    dist = math.sqrt(dx**2 + dy**2)
                    if dist < beyblade.radius + 10:  # 10 is ice radius
                        # Marty Mauser: reflect projectiles back
                        if beyblade.ability == 'marty_mauser':
                            ice['vx'] = -ice['vx']
                            ice['vy'] = -ice['vy']
                            ice['owner_name'] = beyblade.name
                            ice['lifetime'] = 240
                            self.effects.spawn_collision_sparks(ice['x'], ice['y'], 0.5)
                            self.effects.spawn_ability_notification(beyblade.name, 'REFLECT!', ABILITIES['marty_mauser']['color'], 'ability', 'Marty Mauser')
                            break
                        # Hit! Freeze the beyblade (Batman immune)
                        if beyblade.ability != 'batman':
                            beyblade.ice_frozen_timer = 60  # 1 second freeze
                            beyblade.vx = 0
                            beyblade.vy = 0
                            self.effects.spawn_ability_notification(beyblade.name, 'FROZEN!', ABILITIES['ice']['color'], 'ability', 'Ice')
                        self.effects.spawn_collision_sparks(ice['x'], ice['y'], 1.5)
                        ice_to_remove.append(ice)
                        break

            # Remove if expired
            if ice['lifetime'] <= 0:
                ice_to_remove.append(ice)

        for ice in ice_to_remove:
            if ice in self.ice_projectiles:
                self.ice_projectiles.remove(ice)

        # Handle ice freeze (prevent movement during freeze)
        for beyblade in self.beyblades:
            if beyblade.ice_frozen_timer > 0:
                beyblade.ice_frozen_timer -= 1
                beyblade.vx = 0
                beyblade.vy = 0

        # Handle beyblades slipping on ice trails (Batman immune)
        for beyblade in self.beyblades:
            if beyblade.alive and beyblade.ice_frozen_timer <= 0 and beyblade.ability != 'batman':
                for trail in self.ice_trails:
                    dx = beyblade.x - trail['x']
                    dy = beyblade.y - trail['y']
                    dist = math.sqrt(dx**2 + dy**2)
                    if dist < beyblade.radius + 8:  # Close enough to ice
                        # Slip effect: slight angle change and speed boost
                        if beyblade.speed > 0.5:
                            # Rotate velocity by small random angle
                            angle_change = random.uniform(-0.15, 0.15)
                            cos_a = math.cos(angle_change)
                            sin_a = math.sin(angle_change)
                            new_vx = beyblade.vx * cos_a - beyblade.vy * sin_a
                            new_vy = beyblade.vx * sin_a + beyblade.vy * cos_a
                            beyblade.vx = new_vx * 1.03  # Small speed boost
                            beyblade.vy = new_vy * 1.03
                        break  # Only slip on one trail per frame

        # Update ice trail lifetimes
        trails_to_remove = []
        for trail in self.ice_trails:
            trail['lifetime'] -= 1
            if trail['lifetime'] <= 0:
                trails_to_remove.append(trail)
        for trail in trails_to_remove:
            self.ice_trails.remove(trail)

        # Handle grenade ability - avatars throw grenades at random arena spots
        for beyblade in self.beyblades:
            if beyblade.ability == 'grenade':  # Continues after death
                avatar = self.avatar_manager.avatars.get(beyblade.name)
                if avatar and avatar.state not in (AvatarState.ELIMINATED, AvatarState.LAUNCHING):
                    avatar.grenade_cooldown -= 1
                    if avatar.grenade_cooldown <= 0:
                        # Pick random target in arena
                        if self.arena.finals_mode:
                            target_x = random.uniform(self.arena.rect_left + 50, self.arena.rect_right - 50)
                            target_y = random.uniform(self.arena.rect_top + 50, self.arena.rect_bottom - 50)
                        else:
                            angle = random.uniform(0, 2 * math.pi)
                            dist = random.uniform(0, self.arena.radius * 0.8)
                            target_x = self.arena.center_x + math.cos(angle) * dist
                            target_y = self.arena.center_y + math.sin(angle) * dist

                        self.grenades.append({
                            'start_x': avatar.x,
                            'start_y': avatar.y,
                            'target_x': target_x,
                            'target_y': target_y,
                            'progress': 0.0,
                            'owner_name': beyblade.name,
                            'color': beyblade.color,
                        })
                        avatar.grenade_cooldown = 180  # 3 second cooldown

        # Update grenades - flight and explosion
        grenades_to_remove = []
        for grenade in self.grenades:
            grenade['progress'] += 0.02  # Takes ~50 frames (less than 1 second) to land

            if grenade['progress'] >= 1.0:
                # Grenade landed - EXPLODE!
                tx, ty = grenade['target_x'], grenade['target_y']
                explosion_radius = 80

                for beyblade in self.beyblades:
                    if beyblade.alive:
                        dx = beyblade.x - tx
                        dy = beyblade.y - ty
                        dist = math.sqrt(dx**2 + dy**2)
                        if dist < explosion_radius and dist > 0:
                            # Knockback like a regular hit (Batman immune)
                            if beyblade.ability != 'batman':
                                force = 12 * (1 - dist / explosion_radius)
                                beyblade.vx += (dx / dist) * force
                                beyblade.vy += (dy / dist) * force

                self.effects.spawn_collision_sparks(tx, ty, 4.0)
                self.effects.sound.play('big_hit')
                grenades_to_remove.append(grenade)

        for grenade in grenades_to_remove:
            self.grenades.remove(grenade)

        # Handle kamehameha ability - avatars charge and fire beams (continues after death)
        for beyblade in self.beyblades:
            if beyblade.ability == 'kamehameha':
                avatar = self.avatar_manager.avatars.get(beyblade.name)
                if avatar and avatar.state not in (AvatarState.ELIMINATED, AvatarState.LAUNCHING):
                    if avatar.kamehameha_charging:
                        avatar.kamehameha_charge_timer -= 1
                        if avatar.kamehameha_charge_timer <= 0:
                            # FIRE THE BEAM!
                            # Calculate beam direction toward arena
                            dx = self.arena.center_x - avatar.x
                            dy = self.arena.center_y - avatar.y
                            base_angle = math.atan2(dy, dx)
                            # Add some randomness to the angle
                            beam_angle = base_angle + random.uniform(-0.5, 0.5)

                            self.kamehameha_beams.append({
                                'start_x': avatar.x,
                                'start_y': avatar.y,
                                'angle': beam_angle,
                                'length': 0,
                                'max_length': 900,
                                'width': 30,
                                'lifetime': 45,  # Beam lasts 0.75 seconds
                                'owner_name': beyblade.name,
                                'color': (100, 180, 255),
                                'hit_targets': set(),  # Track who we've hit
                            })

                            avatar.kamehameha_charging = False
                            avatar.kamehameha_cooldown = random.randint(600, 900)  # 10-15 seconds
                            self.effects.spawn_ability_notification(beyblade.name, 'KAMEHAMEHA!', ABILITIES['kamehameha']['color'], 'burst')
                    else:
                        avatar.kamehameha_cooldown -= 1
                        if avatar.kamehameha_cooldown <= 0:
                            # Start charging
                            avatar.kamehameha_charging = True
                            avatar.kamehameha_charge_timer = 90  # 1.5 second charge

        # Update kamehameha beams
        beams_to_remove = []
        for beam in self.kamehameha_beams:
            # Extend beam length
            if beam['length'] < beam['max_length']:
                beam['length'] += 40  # Fast beam extension

            beam['lifetime'] -= 1

            # Check collision with beyblades along the beam
            start_x, start_y = beam['start_x'], beam['start_y']
            angle = beam['angle']
            length = beam['length']

            for beyblade in self.beyblades:
                if beyblade.alive and beyblade.name != beam['owner_name'] and beyblade.name not in beam['hit_targets']:
                    # Check if beyblade is within beam rectangle
                    # Project beyblade position onto beam axis
                    dx = beyblade.x - start_x
                    dy = beyblade.y - start_y

                    # Distance along beam
                    along_beam = dx * math.cos(angle) + dy * math.sin(angle)
                    # Distance perpendicular to beam
                    perp_beam = abs(-dx * math.sin(angle) + dy * math.cos(angle))

                    if 0 < along_beam < length and perp_beam < beam['width'] / 2 + beyblade.radius:
                        # HIT! Apply hitstun then knockback (Batman immune)
                        beam['hit_targets'].add(beyblade.name)
                        if beyblade.ability != 'batman':
                            beyblade.hitstun_timer = 15  # 0.25 second hitstun
                            beyblade.vx = 0
                            beyblade.vy = 0
                            # Store knockback to apply after hitstun
                            knockback_force = 18
                            beyblade.hitstun_knockback = (
                                math.cos(angle) * knockback_force,
                                math.sin(angle) * knockback_force
                            )
                        self.effects.spawn_collision_sparks(beyblade.x, beyblade.y, 2.5)

            if beam['lifetime'] <= 0:
                beams_to_remove.append(beam)

        for beam in beams_to_remove:
            self.kamehameha_beams.remove(beam)

        # Handle hitstun (freeze then knockback)
        for beyblade in self.beyblades:
            if beyblade.hitstun_timer > 0:
                beyblade.hitstun_timer -= 1
                beyblade.vx = 0
                beyblade.vy = 0
                if beyblade.hitstun_timer == 0:
                    # Apply the stored knockback
                    beyblade.vx, beyblade.vy = beyblade.hitstun_knockback
                    beyblade.hitstun_knockback = (0, 0)

        # Handle water ability - avatars create waves that push everything
        for beyblade in self.beyblades:
            if beyblade.ability == 'water':  # Continues after death
                avatar = self.avatar_manager.avatars.get(beyblade.name)
                if avatar and avatar.state not in (AvatarState.ELIMINATED, AvatarState.LAUNCHING):
                    avatar.water_cooldown -= 1
                    if avatar.water_cooldown <= 0:
                        # Spawn a wave from avatar toward arena
                        dx = self.arena.center_x - avatar.x
                        dy = self.arena.center_y - avatar.y
                        base_angle = math.atan2(dy, dx)
                        # Add randomness to direction
                        wave_angle = base_angle + random.uniform(-0.4, 0.4)

                        self.water_waves.append({
                            'start_x': avatar.x,
                            'start_y': avatar.y,
                            'angle': wave_angle,
                            'progress': 0.0,
                            'width': 300,
                            'owner_name': beyblade.name,
                            'color': (50, 150, 255),
                            'hit_targets': set(),
                        })
                        avatar.water_cooldown = random.randint(600, 900)  # 10-15 seconds
                        self.effects.spawn_ability_notification(beyblade.name, 'WAVE!', ABILITIES['water']['color'], 'ability', 'Water')

        # Update water waves
        waves_to_remove = []
        for wave in self.water_waves:
            wave['progress'] += 0.025  # Wave moves across arena

            # Calculate wave front position
            max_dist = 700  # How far wave travels
            current_dist = wave['progress'] * max_dist
            wave_x = wave['start_x'] + math.cos(wave['angle']) * current_dist
            wave_y = wave['start_y'] + math.sin(wave['angle']) * current_dist

            # Push beyblades in wave direction
            for beyblade in self.beyblades:
                if beyblade.alive and beyblade.name not in wave['hit_targets']:
                    # Check if beyblade is within wave front
                    dx = beyblade.x - wave_x
                    dy = beyblade.y - wave_y
                    # Distance perpendicular to wave direction
                    perp_dist = abs(-dx * math.sin(wave['angle']) + dy * math.cos(wave['angle']))
                    # Distance along wave direction
                    along_dist = dx * math.cos(wave['angle']) + dy * math.sin(wave['angle'])

                    if perp_dist < wave['width'] / 2 + beyblade.radius and abs(along_dist) < 40:
                        # Hit by wave - push in wave direction (Batman immune)
                        wave['hit_targets'].add(beyblade.name)
                        if beyblade.ability != 'batman':
                            push_force = 10
                            beyblade.vx += math.cos(wave['angle']) * push_force
                            beyblade.vy += math.sin(wave['angle']) * push_force
                        self.effects.spawn_collision_sparks(beyblade.x, beyblade.y, 1.5)

            if wave['progress'] >= 1.0:
                waves_to_remove.append(wave)

        for wave in waves_to_remove:
            self.water_waves.remove(wave)

        # Handle venom DoT ticks
        for beyblade in self.beyblades:
            if beyblade.alive and beyblade.venom_dot > 0:
                beyblade.venom_tick_timer -= 1
                if beyblade.venom_tick_timer <= 0:
                    # Apply tick damage (spread over 3 seconds = 180 frames, tick every 30 frames = 6 ticks)
                    tick_damage = beyblade.venom_dot / 6
                    beyblade.stamina -= tick_damage
                    beyblade.venom_dot -= tick_damage
                    beyblade.venom_tick_timer = 30
                    # Visual feedback
                    self.effects.spawn_collision_sparks(beyblade.x, beyblade.y, 0.5)
                    if beyblade.stamina <= 0:
                        beyblade.die()

        # Update timebomb countdowns
        for beyblade in self.beyblades:
            if beyblade.alive and beyblade.ability == 'timebomb' and beyblade.timebomb_timer > 0:
                beyblade.timebomb_timer -= 1
                if beyblade.timebomb_timer <= 0:
                    # BOOM! Massive explosion
                    for other in self.beyblades:
                        if other.alive and other != beyblade:
                            dx = other.x - beyblade.x
                            dy = other.y - beyblade.y
                            dist = math.sqrt(dx**2 + dy**2)
                            if dist > 0:
                                # Huge knockback to everyone (Batman immune)
                                if other.ability != 'batman':
                                    force = 25 * max(0, 1 - dist / 500)
                                    other.vx += (dx / dist) * force
                                    other.vy += (dy / dist) * force
                                    # Also deal damage
                                    if dist < 200:
                                        other.take_damage(15 * (1 - dist / 200))
                    # Self-destruct
                    beyblade.die()
                    self.effects.spawn_collision_sparks(beyblade.x, beyblade.y, 8.0)
                    self.effects.spawn_ability_notification(beyblade.name, 'TIMEBOMB!', ABILITIES['timebomb']['color'], 'burst')

        # Swamp Thing: stop own momentum when going fast (once per game)
        for beyblade in self.beyblades:
            if beyblade.alive and beyblade.ability == 'swamp_thing':
                if beyblade.name not in self.swamp_thing_used and beyblade.speed >= 12:
                    # Trigger swamp thing - freeze only self
                    self.swamp_thing_used.add(beyblade.name)
                    beyblade.swamp_thing_freeze_timer = 45  # 0.75 seconds
                    beyblade.vx = 0
                    beyblade.vy = 0
                    self.effects.spawn_ability_notification(beyblade.name, 'SWAMP THING!', ABILITIES['swamp_thing']['color'], 'ability')

        # Handle swamp thing freeze (prevent movement during freeze)
        for beyblade in self.beyblades:
            if beyblade.swamp_thing_freeze_timer > 0:
                beyblade.swamp_thing_freeze_timer -= 1
                beyblade.vx = 0
                beyblade.vy = 0

        # Goku: teleport behind random enemy every 5-20 seconds
        for beyblade in self.beyblades:
            if beyblade.alive and beyblade.ability == 'goku':
                beyblade.goku_teleport_cooldown -= 1
                if beyblade.goku_teleport_cooldown <= 0:
                    # Find a random target
                    targets = [b for b in self.beyblades if b.alive and b != beyblade]
                    if targets:
                        target = random.choice(targets)
                        # Teleport behind the target (opposite side from their movement direction)
                        if target.speed > 0.5:
                            # Behind based on velocity
                            behind_x = target.x - (target.vx / target.speed) * (target.radius + beyblade.radius + 10)
                            behind_y = target.y - (target.vy / target.speed) * (target.radius + beyblade.radius + 10)
                        else:
                            # Random offset if target is stationary
                            angle = random.uniform(0, 2 * math.pi)
                            behind_x = target.x + math.cos(angle) * (target.radius + beyblade.radius + 10)
                            behind_y = target.y + math.sin(angle) * (target.radius + beyblade.radius + 10)

                        beyblade.x = behind_x
                        beyblade.y = behind_y
                        # Give a burst of speed toward target
                        dx = target.x - beyblade.x
                        dy = target.y - beyblade.y
                        dist = math.sqrt(dx**2 + dy**2)
                        if dist > 0:
                            beyblade.vx = (dx / dist) * 12
                            beyblade.vy = (dy / dist) * 12
                        self.effects.spawn_collision_sparks(beyblade.x, beyblade.y, 2.0)
                        self.effects.spawn_ability_notification(beyblade.name, 'INSTANT TRANSMISSION!', ABILITIES['goku']['color'], 'ability', 'Goku')
                    # Reset cooldown (random 5-20 seconds)
                    beyblade.goku_teleport_cooldown = random.randint(300, 1200)

        # Last Stand: activate at 10% HP, invincible for 5 seconds
        for beyblade in self.beyblades:
            if beyblade.alive and beyblade.ability == 'last_stand':
                if not beyblade.last_stand_active and beyblade.stamina <= beyblade.max_stamina * 0.1:
                    beyblade.last_stand_active = True
                    beyblade.last_stand_timer = 300  # 5 seconds
                    self.effects.spawn_ability_notification(beyblade.name, 'LAST STAND!', ABILITIES['last_stand']['color'], 'ability')
                if beyblade.last_stand_active:
                    beyblade.last_stand_timer -= 1
                    beyblade.stamina = max(1, beyblade.stamina)  # Can't die during last stand
                    if beyblade.last_stand_timer <= 0:
                        beyblade.last_stand_active = False

        # Earthquake: shake all beyblades every 15 seconds
        for beyblade in self.beyblades:
            if beyblade.alive and beyblade.ability == 'earthquake':
                beyblade.earthquake_timer -= 1
                if beyblade.earthquake_timer <= 0:
                    beyblade.earthquake_timer = 900  # Reset for next quake
                    for other in self.beyblades:
                        if other.alive and other.ability != 'batman':  # Batman immune
                            # Random velocity change
                            other.vx += random.uniform(-8, 8)
                            other.vy += random.uniform(-8, 8)
                    self.effects.spawn_ability_notification(beyblade.name, 'EARTHQUAKE!', ABILITIES['earthquake']['color'], 'burst')

        # Lightning Storm: strike 3 random enemies every 10 seconds
        for beyblade in self.beyblades:
            if beyblade.alive and beyblade.ability == 'lightning_storm':
                beyblade.lightning_timer -= 1
                if beyblade.lightning_timer <= 0:
                    beyblade.lightning_timer = 600  # Reset
                    targets = [b for b in self.beyblades if b.alive and b != beyblade and b.ability != 'batman']  # Batman immune
                    random.shuffle(targets)
                    for target in targets[:3]:  # Up to 3 targets
                        target.take_damage(5)
                        target.vx += random.uniform(-5, 5)
                        target.vy += random.uniform(-5, 5)
                        self.effects.spawn_collision_sparks(target.x, target.y, 2.0)
                    self.effects.spawn_ability_notification(beyblade.name, 'LIGHTNING!', ABILITIES['lightning_storm']['color'], 'ability')

        # Doomsday Clock: after 30 seconds, eliminate 2 beyblades closest to edge
        for beyblade in self.beyblades:
            if beyblade.alive and beyblade.ability == 'doomsday':
                beyblade.doomsday_timer -= 1
                if beyblade.doomsday_timer <= 0:
                    beyblade.doomsday_timer = 9999999  # Only triggers once
                    # Find 2 beyblades closest to arena edge (excluding self and Batman)
                    others = [b for b in self.beyblades if b.alive and b != beyblade and b.ability != 'batman']
                    if self.arena.finals_mode:
                        # Distance to left/right edge
                        def edge_dist(b):
                            return min(b.x - self.arena.rect_left, self.arena.rect_right - b.x)
                    else:
                        # Distance from center (closer to edge = larger dist)
                        def edge_dist(b):
                            dx = b.x - self.arena.center_x
                            dy = b.y - self.arena.center_y
                            return self.arena.radius - math.sqrt(dx**2 + dy**2)
                    others.sort(key=edge_dist)
                    for victim in others[:2]:
                        victim.die()
                        self.effects.spawn_collision_sparks(victim.x, victim.y, 5.0)
                    self.effects.spawn_ability_notification(beyblade.name, 'DOOMSDAY!', ABILITIES['doomsday']['color'], 'knockout')

        # Portal: create linked portals, teleport beyblades that touch them
        portal_owner = None
        for beyblade in self.beyblades:
            if beyblade.alive and beyblade.ability == 'portal':
                portal_owner = beyblade
                break

        if portal_owner and len(self.portals) == 0:
            # Create two portals at random positions in arena
            for i in range(2):
                if self.arena.finals_mode:
                    px = random.uniform(self.arena.rect_left + 50, self.arena.rect_right - 50)
                    py = random.uniform(self.arena.rect_top + 50, self.arena.rect_bottom - 50)
                else:
                    angle = random.uniform(0, 2 * math.pi)
                    dist = random.uniform(50, self.arena.radius * 0.7)
                    px = self.arena.center_x + math.cos(angle) * dist
                    py = self.arena.center_y + math.sin(angle) * dist
                self.portals.append({'x': px, 'y': py, 'color': portal_owner.color})
            self.effects.spawn_ability_notification(portal_owner.name, 'PORTAL!', ABILITIES['portal']['color'], 'ability')

        # Handle portal teleportation
        if len(self.portals) >= 2 and self.portal_cooldown <= 0:
            for beyblade in self.beyblades:
                if beyblade.alive:
                    for i, portal in enumerate(self.portals):
                        dx = beyblade.x - portal['x']
                        dy = beyblade.y - portal['y']
                        dist = math.sqrt(dx**2 + dy**2)
                        if dist < 25:  # Portal radius
                            # Teleport to other portal
                            other_portal = self.portals[1 - i]
                            beyblade.x = other_portal['x']
                            beyblade.y = other_portal['y']
                            self.portal_cooldown = 60  # 1 second cooldown
                            self.effects.spawn_collision_sparks(portal['x'], portal['y'], 2.0)
                            break
        if self.portal_cooldown > 0:
            self.portal_cooldown -= 1

        # Handle obelisk bumper collisions
        for bumper in self.obelisk_bumpers:
            bumper.update()
            for beyblade in self.beyblades:
                if beyblade.alive and bumper.check_collision(beyblade):
                    bumper.apply_bounce(beyblade)
                    self.effects.spawn_collision_sparks(beyblade.x, beyblade.y, 1.5)
                    self.effects.sound.play('bumper')

        # Andy Dufresne: respawn after 20 seconds dead if heat continues
        for beyblade in self.beyblades:
            if not beyblade.alive and beyblade.ability == 'andy_dufresne':
                if beyblade.name not in self.andy_respawn_used:
                    beyblade.andy_death_timer += 1
                    if beyblade.andy_death_timer >= 1200:  # 20 seconds
                        # Respawn with full HP at arena center
                        self.andy_respawn_used.add(beyblade.name)
                        beyblade.alive = True
                        beyblade.stamina = beyblade.max_stamina
                        beyblade.knockout_timer = 0
                        beyblade.x = self.arena.center_x + random.uniform(-50, 50)
                        beyblade.y = self.arena.center_y + random.uniform(-50, 50)
                        beyblade.vx = random.uniform(-5, 5)
                        beyblade.vy = random.uniform(-5, 5)
                        # Remove from eliminated list if present
                        if beyblade.name in self.eliminated:
                            self.eliminated.remove(beyblade.name)
                        if beyblade.name in self.all_eliminated:
                            self.all_eliminated.remove(beyblade.name)
                        self.effects.spawn_ability_notification(beyblade.name, 'HOPE PREVAILS!', ABILITIES['andy_dufresne']['color'], 'ability', 'Andy Dufresne')
                        self.effects.spawn_collision_sparks(beyblade.x, beyblade.y, 3.0)

        # Shelob: crawl after 5 seconds without being hit
        for beyblade in self.beyblades:
            if beyblade.alive and beyblade.ability == 'shelob':
                beyblade.shelob_no_hit_timer += 1
                if beyblade.shelob_no_hit_timer >= 300:  # 5 seconds
                    if not beyblade.shelob_is_crawling:
                        beyblade.shelob_is_crawling = True
                        beyblade.shelob_crawl_angle = random.uniform(0, 2 * math.pi)
                        self.effects.spawn_ability_notification(beyblade.name, 'CRAWLING...', ABILITIES['shelob']['color'], 'ability', 'Shelob')

                    # Crawl in current direction
                    beyblade.shelob_crawl_timer -= 1
                    if beyblade.shelob_crawl_timer <= 0:
                        # Change direction periodically
                        beyblade.shelob_crawl_angle += random.uniform(-0.5, 0.5)
                        beyblade.shelob_crawl_timer = random.randint(30, 90)

                    # Move in crawl direction at slow speed
                    crawl_speed = 2.0
                    beyblade.vx = math.cos(beyblade.shelob_crawl_angle) * crawl_speed
                    beyblade.vy = math.sin(beyblade.shelob_crawl_angle) * crawl_speed

                    # Don't walk off edge - check distance from center
                    if not self.arena.finals_mode:
                        dx = beyblade.x - self.arena.center_x
                        dy = beyblade.y - self.arena.center_y
                        dist = math.sqrt(dx**2 + dy**2)
                        if dist > self.arena.radius * 0.7:
                            # Turn toward center
                            beyblade.shelob_crawl_angle = math.atan2(-dy, -dx)
                    else:
                        # Rectangle arena - stay away from CURRENT edges (accounts for moving walls)
                        # Use larger margin when walls are closing to stay safe
                        margin = 150 if self.arena.edges_closing else 100
                        current_left = self.arena.current_rect_left
                        current_right = self.arena.current_rect_right

                        # Check if too close to left wall
                        if beyblade.x < current_left + margin:
                            beyblade.shelob_crawl_angle = 0  # Turn right (away from left wall)
                        # Check if too close to right wall
                        elif beyblade.x > current_right - margin:
                            beyblade.shelob_crawl_angle = math.pi  # Turn left (away from right wall)

                        # If walls are very close together, move toward center
                        arena_width = current_right - current_left
                        if arena_width < 400:
                            center_x = (current_left + current_right) / 2
                            if beyblade.x < center_x:
                                beyblade.shelob_crawl_angle = 0  # Move right toward center
                            else:
                                beyblade.shelob_crawl_angle = math.pi  # Move left toward center

        # American Psycho: reset own damage after 20 seconds
        for beyblade in self.beyblades:
            if beyblade.alive and beyblade.ability == 'american_psycho':
                beyblade.american_psycho_timer -= 1
                if beyblade.american_psycho_timer <= 0:
                    # Reset stamina to stored value
                    if beyblade.stamina < beyblade.american_psycho_stored_stamina:
                        beyblade.stamina = beyblade.american_psycho_stored_stamina
                        self.effects.spawn_ability_notification(beyblade.name, 'DAMAGE RESET!', ABILITIES['american_psycho']['color'], 'ability', 'American Psycho')
                    # Store current stamina and reset timer
                    beyblade.american_psycho_stored_stamina = beyblade.stamina
                    beyblade.american_psycho_timer = 1200  # 20 seconds

        # Barry Lyndon: random duel trigger (once per game)
        for beyblade in self.beyblades:
            if beyblade.alive and beyblade.ability == 'barry_lyndon':
                if beyblade.name not in self.barry_lyndon_used:
                    if random.random() < 0.001:  # ~6% chance per second at 60fps
                        targets = [b for b in self.beyblades if b.alive and b != beyblade]
                        if targets:
                            opponent = random.choice(targets)
                            self.barry_lyndon_used.add(beyblade.name)
                            self.effects.spawn_ability_notification(
                                beyblade.name, f'DUEL vs {opponent.name[:10]}!', ABILITIES['barry_lyndon']['color'], 'ability', 'Barry Lyndon'
                            )
                            # 90% Barry wins
                            if random.random() < 0.9:
                                opponent.die()
                                self.effects.spawn_knockout_effect(opponent.x, opponent.y, opponent.color, opponent.name)
                                self.effects.spawn_ability_notification(beyblade.name, 'WINS DUEL!', ABILITIES['barry_lyndon']['color'], 'ability')
                            else:
                                beyblade.die()
                                self.effects.spawn_knockout_effect(beyblade.x, beyblade.y, beyblade.color, beyblade.name)
                                self.effects.spawn_ability_notification(opponent.name, 'WINS DUEL!', (255, 255, 255), 'ability')

        # Kevin McAllister: drop traps behind
        for beyblade in self.beyblades:
            if beyblade.alive and beyblade.ability == 'kevin_mcallister':
                beyblade.trap_cooldown -= 1
                if beyblade.trap_cooldown <= 0:
                    trap_type = random.choice(['nail', 'banana'])
                    self.traps.append({
                        'x': beyblade.x,
                        'y': beyblade.y,
                        'type': trap_type,
                        'owner_name': beyblade.name,
                        'lifetime': 600,  # 10 seconds
                    })
                    beyblade.trap_cooldown = 120  # Drop every 2 seconds

        # Update traps
        traps_to_remove = []
        for trap in self.traps:
            trap['lifetime'] -= 1
            if trap['lifetime'] <= 0:
                traps_to_remove.append(trap)
                continue

            for beyblade in self.beyblades:
                if beyblade.alive and beyblade.name != trap['owner_name'] and beyblade.ability != 'batman':
                    dx = beyblade.x - trap['x']
                    dy = beyblade.y - trap['y']
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist < beyblade.radius + 10:
                        if trap['type'] == 'nail':
                            beyblade.stamina -= 3  # Minor damage
                            self.effects.spawn_collision_sparks(trap['x'], trap['y'], 0.5)
                        else:  # banana
                            # Slip effect like ice
                            angle = random.uniform(0, 2 * math.pi)
                            speed = max(beyblade.speed, 5)
                            beyblade.vx = math.cos(angle) * speed * 1.3
                            beyblade.vy = math.sin(angle) * speed * 1.3
                            self.effects.spawn_collision_sparks(trap['x'], trap['y'], 0.3)
                        traps_to_remove.append(trap)
                        break

        for trap in traps_to_remove:
            if trap in self.traps:
                self.traps.remove(trap)

        # Ferris Bueller: late entry (5 seconds into heat)
        for beyblade in self.beyblades:
            if beyblade.ability == 'ferris_bueller' and beyblade.ferris_late_entry:
                beyblade.ferris_timer -= 1
                if beyblade.ferris_timer <= 0:
                    beyblade.ferris_late_entry = False
                    beyblade.alive = True
                    # Spawn at random position
                    if self.arena.finals_mode:
                        beyblade.x = random.uniform(self.arena.rect_left + 50, self.arena.rect_right - 50)
                        beyblade.y = random.uniform(self.arena.rect_top + 50, self.arena.rect_bottom - 50)
                    else:
                        angle = random.uniform(0, 2 * math.pi)
                        dist = random.uniform(50, self.arena.radius * 0.6)
                        beyblade.x = self.arena.center_x + math.cos(angle) * dist
                        beyblade.y = self.arena.center_y + math.sin(angle) * dist
                    beyblade.vx = random.uniform(-3, 3)
                    beyblade.vy = random.uniform(-3, 3)
                    self.effects.spawn_ability_notification(beyblade.name, 'ARRIVES LATE!', ABILITIES['ferris_bueller']['color'], 'ability', 'Ferris Bueller')

        # Alien: gestation and bursting
        for beyblade in self.beyblades:
            if beyblade.ability == 'alien' and beyblade.alien_host:
                host = next((b for b in self.beyblades if b.name == beyblade.alien_host), None)
                if host and host.alive:
                    beyblade.alien_gestation_timer -= 1
                    beyblade.x, beyblade.y = host.x, host.y  # Follow host
                    if beyblade.alien_gestation_timer <= 0:
                        # Burst out!
                        host.die()
                        beyblade.alive = True
                        beyblade.alien_is_juvenile = False
                        beyblade.alien_host = None
                        # Apply adult bonus (+10% stats)
                        if not beyblade.alien_adult_bonus_applied:
                            beyblade.attack *= 1.1
                            beyblade.defense *= 1.1
                            beyblade.max_stamina *= 1.1
                            beyblade.stamina = beyblade.max_stamina
                            beyblade.alien_adult_bonus_applied = True
                        self.effects.spawn_knockout_effect(host.x, host.y, host.color, host.name)
                        self.effects.spawn_ability_notification(beyblade.name, 'BURSTS OUT!', ABILITIES['alien']['color'], 'ability', 'Alien')
                        self.effects.spawn_collision_sparks(beyblade.x, beyblade.y, 4.0)
                else:
                    # Host died some other way, alien emerges early
                    if not beyblade.alive:
                        beyblade.alive = True
                        beyblade.alien_is_juvenile = False
                        beyblade.alien_host = None
                        if not beyblade.alien_adult_bonus_applied:
                            beyblade.attack *= 1.1
                            beyblade.defense *= 1.1
                            beyblade.max_stamina *= 1.1
                            beyblade.stamina = beyblade.max_stamina
                            beyblade.alien_adult_bonus_applied = True
                        self.effects.spawn_ability_notification(beyblade.name, 'EMERGES!', ABILITIES['alien']['color'], 'ability', 'Alien')

        # Amadeus: refuse to die while rival lives (use the flag computed earlier this frame)
        for beyblade in self.beyblades:
            if beyblade.ability == 'amadeus' and beyblade.amadeus_rival_alive:
                if beyblade.stamina <= 0:
                    beyblade.stamina = 1  # Refuse to die
                    beyblade.alive = True
                    beyblade.knockout_timer = 0

        # Terminator: hunt target after 3s without being hit
        for beyblade in self.beyblades:
            if beyblade.alive and beyblade.ability == 'terminator' and beyblade.terminator_target:
                beyblade.terminator_no_hit_timer += 1
                if beyblade.terminator_no_hit_timer >= 180:  # 3 seconds
                    target = next((b for b in self.beyblades if b.name == beyblade.terminator_target and b.alive), None)
                    if target:
                        dx = target.x - beyblade.x
                        dy = target.y - beyblade.y
                        dist = math.sqrt(dx * dx + dy * dy)
                        if dist > 0:
                            force = 0.3
                            beyblade.vx += (dx / dist) * force
                            beyblade.vy += (dy / dist) * force

        # Oppenheimer: 1/200 chance to nuke half the field (once per game)
        for beyblade in self.beyblades:
            if beyblade.alive and beyblade.ability == 'oppenheimer':
                if beyblade.name not in self.oppenheimer_used:
                    if random.random() < 1/200:
                        self.oppenheimer_used.add(beyblade.name)
                        self.effects.spawn_ability_notification(beyblade.name, 'I AM BECOME DEATH!', ABILITIES['oppenheimer']['color'], 'knockout', 'Oppenheimer')

                        # Nuke left or right half
                        nuke_left = random.choice([True, False])
                        center_x = self.arena.center_x

                        # Spawn massive nuke blast effect
                        self.effects.spawn_nuke_blast(center_x, self.arena.center_y, nuke_left, self.arena.radius)

                        for target in self.beyblades:
                            if target.alive and target != beyblade:
                                if (nuke_left and target.x < center_x) or (not nuke_left and target.x >= center_x):
                                    target.die()
                                    self.effects.spawn_knockout_effect(target.x, target.y, target.color, target.name)
                                    self.effects.spawn_collision_sparks(target.x, target.y, 5.0)

        # John Wick: avatar shoots double-tap pistol pattern
        for beyblade in self.beyblades:
            if beyblade.ability == 'john_wick':
                avatar = self.avatar_manager.avatars.get(beyblade.name)
                if avatar and avatar.state not in (AvatarState.ELIMINATED, AvatarState.LAUNCHING):
                    avatar.pistol_cooldown -= 1
                    if avatar.pistol_cooldown <= 0:
                        # Target random point in arena
                        if self.arena.finals_mode:
                            target_x = random.uniform(self.arena.rect_left, self.arena.rect_right)
                            target_y = random.uniform(self.arena.rect_top, self.arena.rect_bottom)
                        else:
                            target_angle = random.uniform(0, 2 * math.pi)
                            target_dist = random.uniform(0, self.arena.radius * 0.8)
                            target_x = self.arena.center_x + math.cos(target_angle) * target_dist
                            target_y = self.arena.center_y + math.sin(target_angle) * target_dist

                        dx = target_x - avatar.x
                        dy = target_y - avatar.y
                        dist = math.sqrt(dx * dx + dy * dy)
                        if dist > 0:
                            speed = 15
                            shoot_angle = math.atan2(dy, dx)

                            # Single bullet per shot (double-tap pattern)
                            self.bullets.append({
                                'x': avatar.x,
                                'y': avatar.y,
                                'vx': math.cos(shoot_angle) * speed,
                                'vy': math.sin(shoot_angle) * speed,
                                'owner_name': beyblade.name,
                                'lifetime': 90,
                            })
                            self.effects.sound.play('hit')

                        # Double-tap timing: quick follow-up, then longer wait
                        if avatar.pistol_followup_pending:
                            # This was the follow-up shot, wait longer before next double-tap
                            avatar.pistol_cooldown = 120  # 2 seconds before next double-tap
                            avatar.pistol_followup_pending = False
                        else:
                            # First shot done, quick follow-up coming
                            avatar.pistol_cooldown = 10  # ~0.17 seconds for follow-up
                            avatar.pistol_followup_pending = True

        # Update bullets
        bullets_to_remove = []
        for bullet in self.bullets:
            bullet['x'] += bullet['vx']
            bullet['y'] += bullet['vy']
            bullet['lifetime'] -= 1

            if bullet['lifetime'] <= 0:
                bullets_to_remove.append(bullet)
                continue

            for target in self.beyblades:
                if target.alive and target.name != bullet['owner_name'] and target.ability != 'batman':
                    dx = target.x - bullet['x']
                    dy = target.y - bullet['y']
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist < target.radius + 4:
                        # Marty Mauser: reflect projectiles back
                        if target.ability == 'marty_mauser':
                            bullet['vx'] = -bullet['vx']
                            bullet['vy'] = -bullet['vy']
                            bullet['owner_name'] = target.name  # Now owned by reflector
                            bullet['lifetime'] = 90  # Reset lifetime
                            self.effects.spawn_collision_sparks(bullet['x'], bullet['y'], 0.5)
                            self.effects.spawn_ability_notification(target.name, 'REFLECT!', ABILITIES['marty_mauser']['color'], 'ability', 'Marty Mauser')
                            break
                        # Hit! Minimal knockback but decent damage
                        if dist > 0:
                            knockback = 2
                            target.vx += (dx / dist) * knockback
                            target.vy += (dy / dist) * knockback
                            target.stamina -= 4
                        self.effects.spawn_collision_sparks(bullet['x'], bullet['y'], 0.3)
                        bullets_to_remove.append(bullet)
                        break

        for bullet in bullets_to_remove:
            if bullet in self.bullets:
                self.bullets.remove(bullet)

        # Check for new eliminations (with zombie revival and mutually assured)
        for beyblade in self.beyblades:
            if not beyblade.alive and beyblade.name not in self.eliminated:
                # Neo: reset heat if killed in first 0.5 seconds (30 frames), once per heat
                if beyblade.ability == 'neo' and not self.neo_reset_used_this_heat:
                    frames_alive = self.current_frame - beyblade.neo_spawn_frame
                    if frames_alive <= 30:
                        self.neo_reset_used_this_heat = True  # Mark as used before reset
                        # Big visual notification
                        self.effects.spawn_ability_notification(beyblade.name, 'MATRIX RESET!', ABILITIES['neo']['color'], 'ability', 'Neo')
                        # Add a countdown-style reset message
                        self.neo_reset_countdown = 120  # 2 second display
                        self.neo_reset_name = beyblade.name
                        # Reset the heat
                        self._start_heat(self.current_heat, is_neo_reset=True)
                        return  # Exit update_battle, heat is restarting

                # Barbie: split into two fragile pieces on death
                if beyblade.ability == 'barbie' and not beyblade.barbie_split_done and not beyblade.barbie_is_fragment:
                    beyblade.barbie_split_done = True
                    # Create two fragments
                    for i, offset in enumerate([(-30, -20), (30, 20)]):
                        fragment = Beyblade(f"{beyblade.name} (Fragment {i+1})", beyblade.x + offset[0], beyblade.y + offset[1], 0)
                        fragment.color = beyblade.color
                        fragment.ability = 'barbie'
                        fragment.ability_data = ABILITIES['barbie'].copy()
                        fragment.barbie_is_fragment = True
                        fragment.barbie_split_done = True
                        fragment.stamina = 1  # Dies from one hit
                        fragment.max_stamina = 1
                        fragment.radius = int(beyblade.radius * 0.7)
                        fragment.vx = random.uniform(-5, 5)
                        fragment.vy = random.uniform(-5, 5)
                        self.beyblades.append(fragment)
                    self.effects.spawn_ability_notification(beyblade.name, 'SPLIT!', ABILITIES['barbie']['color'], 'ability', 'Barbie')
                    self.effects.spawn_collision_sparks(beyblade.x, beyblade.y, 2.0)
                    # Still add original to eliminated
                    self.eliminated.append(beyblade.name)
                    self.all_eliminated.append(beyblade.name)
                    continue

                # Check for zombie revival
                if beyblade.ability == 'zombie' and beyblade.name not in self.zombie_used:
                    # Revive with 50% HP
                    self.zombie_used.add(beyblade.name)
                    beyblade.alive = True
                    beyblade.stamina = beyblade.max_stamina * 0.5
                    beyblade.knockout_timer = 0
                    self.effects.spawn_ability_notification(beyblade.name, 'ZOMBIE RISE!', ABILITIES['zombie']['color'], 'ability')
                    self.effects.spawn_collision_sparks(beyblade.x, beyblade.y, 3.0)
                    continue  # Don't add to eliminated

                # Check for mutually assured destruction
                if beyblade.ability == 'mutually_assured' and not beyblade.mutually_assured_triggered:
                    beyblade.mutually_assured_triggered = True
                    for other in self.beyblades:
                        if other.alive and other != beyblade:
                            # Deal 50% of their CURRENT HP as damage
                            damage = other.stamina * 0.5
                            other.stamina -= damage
                            self.effects.spawn_collision_sparks(other.x, other.y, 2.0)
                    self.effects.spawn_ability_notification(beyblade.name, 'M.A.D. TRIGGERED!', ABILITIES['mutually_assured']['color'], 'knockout')

                # Normal elimination
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

    def _get_base_movie_name(self, movie_name: str) -> str:
        """Strip ability suffixes like (Double), (Clone X), (Fragment X) from movie name."""
        import re
        # Remove common suffixes added by abilities
        base_name = re.sub(r'\s*\((Double|Clone \d+|Fragment \d+)\)\s*$', '', movie_name)
        return base_name.strip()

    def _choose_movie(self, movie_name: str):
        """Move winner from movies.txt (or queue.txt for queue battles) to watched.txt."""
        # Get base name (strip ability suffixes)
        base_name = self._get_base_movie_name(movie_name)
        base_lower = base_name.lower()

        # Determine source file based on battle type
        source_file = QUEUE_FILE if self.is_queue_battle else MOVIE_LIST_FILE

        # Read current items from source
        items = []
        if os.path.exists(source_file):
            with open(source_file, 'r', encoding='utf-8') as f:
                items = [line.strip() for line in f.read().strip().split('\n') if line.strip()]

        # Remove the chosen movie (match base name case-insensitively)
        items = [m for m in items if m.strip().lower() != base_lower]

        # Write updated list back to source
        with open(source_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(items))

        # Add to watched list (use base name)
        watched = []
        if os.path.exists(WATCHED_FILE):
            with open(WATCHED_FILE, 'r', encoding='utf-8') as f:
                watched = [line.strip() for line in f.read().strip().split('\n') if line.strip()]
        watched.append(base_name)
        with open(WATCHED_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(watched))

        # Reload the input screen text box and queue
        if os.path.exists(MOVIE_LIST_FILE):
            self.input_screen.text_box.load_from_file(MOVIE_LIST_FILE)
        self.input_screen.load_queue()

    def _queue_movie(self, movie_name: str):
        """Move winner from movies.txt to queue.txt and restart."""
        # Get base name (strip ability suffixes)
        base_name = self._get_base_movie_name(movie_name)

        # Read current movies
        movies = []
        if os.path.exists(MOVIE_LIST_FILE):
            with open(MOVIE_LIST_FILE, 'r', encoding='utf-8') as f:
                movies = [line.strip() for line in f.read().strip().split('\n') if line.strip()]

        # Remove the queued movie (match base name case-insensitively)
        base_lower = base_name.lower()
        movies = [m for m in movies if m.strip().lower() != base_lower]

        # Write updated movies list
        with open(MOVIE_LIST_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(movies))

        # Add to queue list (use base name)
        queue = []
        if os.path.exists(QUEUE_FILE):
            with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
                queue = [line.strip() for line in f.read().strip().split('\n') if line.strip()]
        queue.append(base_name)
        with open(QUEUE_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(queue))

        # Reload the input screen text box and queue
        if os.path.exists(MOVIE_LIST_FILE):
            self.input_screen.text_box.load_from_file(MOVIE_LIST_FILE)
        self.input_screen.load_queue()

    def _record_ability_win(self, winner_name: str):
        """Record the winning movie's ability to the ability wins file."""
        # Get the winner's ability from movie_abilities
        if winner_name not in self.movie_abilities:
            return

        ability_key, _ = self.movie_abilities[winner_name]
        if not ability_key:
            return

        # Load current ability wins
        ability_wins = {}
        if os.path.exists(ABILITY_WINS_FILE):
            try:
                with open(ABILITY_WINS_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if ':' in line:
                            ability, count = line.rsplit(':', 1)
                            ability_wins[ability.strip()] = int(count.strip())
            except:
                pass

        # Increment the win count for this ability
        ability_wins[ability_key] = ability_wins.get(ability_key, 0) + 1

        # Save updated ability wins
        with open(ABILITY_WINS_FILE, 'w', encoding='utf-8') as f:
            for ability, count in sorted(ability_wins.items()):
                f.write(f"{ability}: {count}\n")

    def _record_ability_stats(self):
        """Record all ability scores for the tournament to ability stats file.

        Each movie gets a score based on placement:
        - Winner gets num_participants points
        - First eliminated gets 1 point
        - Rankings are based on elimination order
        """
        # Build the final ranking: all_eliminated (first to last) + winner
        # Winner is not in all_eliminated, they're the survivor
        total_participants = len(self.all_eliminated) + 1  # +1 for winner

        # Load current ability stats: {ability: {'wins': int, 'total_score': int, 'num_battles': int}}
        ability_stats = {}
        if os.path.exists(ABILITY_STATS_FILE):
            try:
                with open(ABILITY_STATS_FILE, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if '|' in line:
                            parts = line.split('|')
                            if len(parts) == 4:
                                ability = parts[0]
                                ability_stats[ability] = {
                                    'wins': int(parts[1]),
                                    'total_score': int(parts[2]),
                                    'num_battles': int(parts[3])
                                }
            except:
                pass

        # Record scores for all participants
        # Eliminated movies: score = position in all_eliminated + 1 (1 for first out, 2 for second, etc.)
        for i, movie_name in enumerate(self.all_eliminated):
            if movie_name in self.movie_abilities:
                ability_key, _ = self.movie_abilities[movie_name]
                if ability_key:
                    if ability_key not in ability_stats:
                        ability_stats[ability_key] = {'wins': 0, 'total_score': 0, 'num_battles': 0}
                    score = i + 1  # First eliminated gets 1, second gets 2, etc.
                    ability_stats[ability_key]['total_score'] += score
                    ability_stats[ability_key]['num_battles'] += 1

        # Winner gets the top score
        if self.winner and self.winner != "No Winner" and self.winner in self.movie_abilities:
            ability_key, _ = self.movie_abilities[self.winner]
            if ability_key:
                if ability_key not in ability_stats:
                    ability_stats[ability_key] = {'wins': 0, 'total_score': 0, 'num_battles': 0}
                ability_stats[ability_key]['wins'] += 1
                ability_stats[ability_key]['total_score'] += total_participants
                ability_stats[ability_key]['num_battles'] += 1

        # Save updated ability stats
        with open(ABILITY_STATS_FILE, 'w', encoding='utf-8') as f:
            for ability in sorted(ability_stats.keys()):
                stats = ability_stats[ability]
                f.write(f"{ability}|{stats['wins']}|{stats['total_score']}|{stats['num_battles']}\n")

    def _load_docket_file(self, filepath: str) -> dict:
        """Load docket entries from file. Returns {name: movie} dict."""
        entries = {}
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    for line in f.read().strip().split('\n'):
                        if ' - ' in line:
                            parts = line.split(' - ', 1)
                            if len(parts) == 2:
                                name, movie = parts[0].strip(), parts[1].strip()
                                if name and movie:
                                    entries[name] = movie
            except:
                pass
        return entries

    def _save_docket_file(self, filepath: str, entries: dict):
        """Save docket entries to file."""
        lines = [f"{name} - {movie}" for name, movie in entries.items()]
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def _load_permanent_people(self) -> list:
        """Load permanent people list from file."""
        people = []
        print(f"[Load] Checking for permanent people file: {PERMANENT_PEOPLE_FILE} (exists: {os.path.exists(PERMANENT_PEOPLE_FILE)})")
        if os.path.exists(PERMANENT_PEOPLE_FILE):
            try:
                with open(PERMANENT_PEOPLE_FILE, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print(f"[Load] Raw file content: {repr(content[:200])}")
                    for line in content.strip().split('\n'):
                        name = line.strip()
                        if name:
                            people.append(name)
                print(f"[Load] Loaded permanent people: {people}")
            except Exception as e:
                print(f"Error loading permanent people: {e}")
        else:
            print(f"Permanent people file not found: {PERMANENT_PEOPLE_FILE} (cwd: {os.getcwd()})")
        return people

    def _load_people_counter(self) -> dict:
        """Load people counter from file. Returns {name: count} dict."""
        counter = {}
        if os.path.exists(PEOPLE_COUNTER_FILE):
            try:
                with open(PEOPLE_COUNTER_FILE, 'r', encoding='utf-8') as f:
                    for line in f.read().strip().split('\n'):
                        if ' - ' in line:
                            parts = line.split(' - ', 1)
                            if len(parts) == 2:
                                name = parts[0].strip()
                                try:
                                    count = int(parts[1].strip())
                                    if name:
                                        counter[name] = count
                                except ValueError:
                                    pass
            except:
                pass
        return counter

    def _save_people_counter(self, counter: dict):
        """Save people counter to file."""
        lines = [f"{name} - {count}" for name, count in counter.items()]
        with open(PEOPLE_COUNTER_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def _remove_from_dockets(self, name: str):
        """Remove a person from all docket files."""
        for docket_type in ['golden', 'diamond', 'shit']:
            if name in self.docket_data[docket_type]:
                del self.docket_data[docket_type][name]
        # Save updated docket files
        self._save_docket_file(GOLDEN_DOCKET_FILE, self.docket_data['golden'])
        self._save_docket_file(DIAMOND_DOCKET_FILE, self.docket_data['diamond'])
        self._save_docket_file(SHIT_DOCKET_FILE, self.docket_data['shit'])

    def _add_graduation_picks(self, name: str, picks: dict):
        """Add a graduating person's docket picks."""
        self.docket_data['golden'][name] = picks['golden']
        self.docket_data['diamond'][name] = picks['diamond']
        self.docket_data['shit'][name] = picks['shit']
        # Save updated docket files
        self._save_docket_file(GOLDEN_DOCKET_FILE, self.docket_data['golden'])
        self._save_docket_file(DIAMOND_DOCKET_FILE, self.docket_data['diamond'])
        self._save_docket_file(SHIT_DOCKET_FILE, self.docket_data['shit'])

    def _start_docket_select(self):
        """Start the docket participant selection screen."""
        print(f"[Docket] _start_docket_select called, cwd={os.getcwd()}")

        # Load all docket files
        self.docket_data['golden'] = self._load_docket_file(GOLDEN_DOCKET_FILE)
        self.docket_data['diamond'] = self._load_docket_file(DIAMOND_DOCKET_FILE)
        self.docket_data['shit'] = self._load_docket_file(SHIT_DOCKET_FILE)
        print(f"[Docket] Loaded docket files - golden: {len(self.docket_data['golden'])} entries")

        # Load permanent people and people counter
        permanent_people = self._load_permanent_people()
        people_counter = self._load_people_counter()
        print(f"[Docket] Loaded permanent_people={permanent_people}, counter_keys={list(people_counter.keys())}")

        # Store people_counter for later updates
        self.people_counter = people_counter

        # Check if we have any people (permanent or in counter)
        if not permanent_people and not people_counter and not self.docket_data['golden']:
            # No participants at all, can't proceed
            print(f"[Docket] No participants at all, returning to input")
            return

        # Create participant select screen with all data
        self.participant_select_screen = ParticipantSelectScreen(
            self.fonts,
            permanent_people,
            people_counter,
            self.docket_data
        )
        self.participant_select_screen.update_layout(self.window_width, self.window_height)
        self.state = STATE_DOCKET_SELECT
        print(f"[Docket] State set to STATE_DOCKET_SELECT")

    def _start_docket_spin(self):
        """Start the wheel spin with selected participants."""
        print(f"[Docket] _start_docket_spin called")

        # Get selected participants
        self.docket_participants = self.participant_select_screen.get_selected_participants()
        print(f"[Docket] Selected participants: {self.docket_participants}")

        if not self.docket_participants:
            print(f"[Docket] No participants selected, returning to input")
            self.state = STATE_INPUT
            return
        print(f"[Docket] Starting spin with {len(self.docket_participants)} participants: {self.docket_participants}")

        # Handle counter updates for recurring people
        increments, decrements, newly_added = self.participant_select_screen.get_counter_updates()

        # Add newly added people to the counter (they start at count 1)
        for name in newly_added:
            self.people_counter[name] = 1

        # Process increments
        for name in increments:
            if name in self.people_counter:
                self.people_counter[name] += 1

        # Process decrements and remove at 0
        for name in decrements:
            if name in self.people_counter:
                self.people_counter[name] -= 1
                if self.people_counter[name] <= 0:
                    # Remove from counter
                    del self.people_counter[name]
                    # Remove from all docket files
                    self._remove_from_dockets(name)
                    # Also remove from selected participants
                    if name in self.docket_participants:
                        self.docket_participants.remove(name)

        # Handle graduation picks (people who just reached 5)
        graduation_picks = self.participant_select_screen.get_graduation_picks()
        for name, picks in graduation_picks.items():
            self._add_graduation_picks(name, picks)

        # Save updated people counter
        self._save_people_counter(self.people_counter)

        # Check if we still have participants after removals
        if not self.docket_participants:
            self.state = STATE_INPUT
            return

        # Start with golden docket
        self.current_docket_type = 'golden'

        # Build entries list for the wheel
        entries = []
        for name in self.docket_participants:
            if name in self.docket_data['golden']:
                entries.append((name, self.docket_data['golden'][name]))

        if not entries:
            print(f"[Docket] No entries found for selected participants in golden docket, returning to input")
            self.state = STATE_INPUT
            return

        # Build next tier entries for preview (diamond docket)
        next_tier_entries = []
        for name in self.docket_participants:
            if name in self.docket_data['diamond']:
                next_tier_entries.append((name, self.docket_data['diamond'][name]))

        # Create the wheel
        center = (self.window_width // 2, self.window_height // 2)
        radius = min(self.window_width, self.window_height) // 2 - 100
        wheel = DocketWheel(entries, 'golden', self.fonts, center, radius, self.effects.sound,
                           next_tier_entries=next_tier_entries if next_tier_entries else None)

        self.docket_spin_screen.set_wheel(wheel)
        self.state = STATE_DOCKET_SPIN

    def _start_docket_zoom(self):
        """Start zoom transition to next docket tier."""
        # Determine next tier
        if self.current_docket_type == 'golden':
            next_type = 'diamond'
        elif self.current_docket_type == 'diamond':
            next_type = 'shit'
        elif self.current_docket_type == 'shit':
            next_type = 'final'
        else:
            # Already at final, shouldn't happen but handle gracefully
            return

        # Build entries for next tier
        entries = []
        if next_type == 'final':
            # Final wheel: combine movies.txt and queue.txt
            entries = self._load_final_wheel_entries()
        else:
            for name in self.docket_participants:
                if name in self.docket_data[next_type]:
                    entries.append((name, self.docket_data[next_type][name]))

        if not entries:
            # No entries for next tier, show current result instead
            return

        # Update current docket type
        self.current_docket_type = next_type

        # Build next-next tier entries for preview (shit docket if going to diamond)
        next_next_entries = None
        if next_type == 'diamond':
            next_next_entries = []
            for name in self.docket_participants:
                if name in self.docket_data['shit']:
                    next_next_entries.append((name, self.docket_data['shit'][name]))
            if not next_next_entries:
                next_next_entries = None

        # Create zoom transition
        center = (self.window_width // 2, self.window_height // 2)
        radius = min(self.window_width, self.window_height) // 2 - 100

        transition = DocketZoomTransition(
            self.docket_spin_screen.wheel,
            next_type,
            entries,
            self.fonts,
            center,
            radius,
            sound_manager=self.effects.sound,
            next_tier_entries=next_next_entries
        )

        self.docket_spin_screen.set_zoom_transition(transition)
        self.state = STATE_DOCKET_ZOOM

    def _load_final_wheel_entries(self):
        """Load combined entries from movies.txt and queue.txt for final wheel."""
        entries = []

        # Track which file each movie came from
        self.final_wheel_sources = {}

        # Load from movies.txt
        try:
            with open(MOVIE_LIST_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    movie = line.strip()
                    if movie:
                        entries.append(("Movies", movie))
                        self.final_wheel_sources[movie] = MOVIE_LIST_FILE
        except FileNotFoundError:
            pass

        # Load from queue.txt
        try:
            with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    movie = line.strip()
                    if movie:
                        entries.append(("Queue", movie))
                        self.final_wheel_sources[movie] = QUEUE_FILE
        except FileNotFoundError:
            pass

        return entries

    def _remove_final_wheel_winner(self, movie: str):
        """Remove the winning movie from its source file."""
        if not hasattr(self, 'final_wheel_sources') or movie not in self.final_wheel_sources:
            return

        source_file = self.final_wheel_sources[movie]

        # Read all movies from source file
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                movies = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            return

        # Remove the winning movie
        if movie in movies:
            movies.remove(movie)

        # Write back
        with open(source_file, 'w', encoding='utf-8') as f:
            for m in movies:
                f.write(m + '\n')

    def _update_golden_docket(self, name: str, new_movie: str):
        """Update a participant's golden docket pick and remove from movies/queue."""
        self.docket_data['golden'][name] = new_movie
        self._save_docket_file(GOLDEN_DOCKET_FILE, self.docket_data['golden'])

        # Remove the movie from movies.txt if present
        movie_lower = new_movie.strip().lower()
        if os.path.exists(MOVIE_LIST_FILE):
            with open(MOVIE_LIST_FILE, 'r', encoding='utf-8') as f:
                movies = [line.strip() for line in f.read().strip().split('\n') if line.strip()]
            movies = [m for m in movies if m.strip().lower() != movie_lower]
            with open(MOVIE_LIST_FILE, 'w', encoding='utf-8') as f:
                f.write('\n'.join(movies))
            # Reload the input screen text box
            self.input_screen.text_box.load_from_file(MOVIE_LIST_FILE)

        # Remove the movie from queue.txt if present
        if os.path.exists(QUEUE_FILE):
            with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
                queue = [line.strip() for line in f.read().strip().split('\n') if line.strip()]
            queue = [m for m in queue if m.strip().lower() != movie_lower]
            with open(QUEUE_FILE, 'w', encoding='utf-8') as f:
                f.write('\n'.join(queue))

    def _end_current_heat(self, survivors: list):
        """Handle end of a heat - advance winners or end tournament."""
        survivor_names = [b.name for b in survivors]

        # Handle preliminary round ending
        if self.is_preliminary:
            # Determine winner - either last survivor or last eliminated
            if survivor_names:
                winner_name = survivor_names[0]
            elif self.all_eliminated:
                winner_name = self.all_eliminated[-1]
            else:
                winner_name = "Group 1"  # Fallback

            # Extract group index from winner name (e.g., "Group 2 (55 movies)" -> index 1)
            try:
                group_num = int(winner_name.split()[1])
                winning_group_index = group_num - 1
            except (IndexError, ValueError):
                winning_group_index = 0

            # Store the winning group's movies
            self.preliminary_winning_movies = self.preliminary_groups[winning_group_index].copy()

            # Show transition screen
            self.heat_transition_screen.set_advancers(
                [winner_name],
                1,
                len(self.preliminary_groups),
                is_to_finals=False,
                is_preliminary=True,
                is_preliminary_complete=True
            )
            self.pending_start_main_tournament = True
            self.state = STATE_HEAT_TRANSITION
            return

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
            # Record ability stats (only once per tournament)
            if not self.ability_win_recorded:
                if self.winner and self.winner != "No Winner":
                    self._record_ability_win(self.winner)
                self._record_ability_stats()
                self.ability_win_recorded = True
            self.effects.sound.play('victory')
            self.avatar_manager.sync_with_beyblades(self.beyblades, winner_name=self.winner)
            self.state = STATE_VICTORY
        else:
            # Add survivors to heat winners (skip clones and fragments to prevent duplicates)
            # When Naruto clones or Barbie fragments survive, only the original should advance
            # Otherwise the clone/fragment would spawn AND the original would create new clones
            for survivor in survivors:
                if survivor.is_clone or survivor.barbie_is_fragment:
                    continue  # Skip clones and fragments
                # Defensive: also skip if name already in heat_winners (prevents mystery duplicates)
                if survivor.name in self.heat_winners:
                    continue
                self.heat_winners.append(survivor.name)

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
        self.eliminated.clear()  # Clear heat eliminations for next heat

        # Handle preliminary round completion - start main tournament with winning group's movies
        if self.pending_start_main_tournament:
            self.pending_start_main_tournament = False
            self.is_preliminary = False
            self._start_main_tournament_with_movies(self.preliminary_winning_movies)
            return

        # Normal tournament flow
        if self.pending_is_finals:
            self.is_finals = True
        self._start_heat(self.pending_next_heat)
        self.state = STATE_BATTLE

    def _start_main_tournament_with_movies(self, movie_list: list):
        """Start the main tournament using the winning group's movies."""
        # Reset tournament state for main tournament
        self.eliminated.clear()
        self.all_eliminated.clear()
        self.heat_winners.clear()
        self.current_heat = 0
        self.is_finals = False

        movie_list = movie_list.copy()
        random.shuffle(movie_list)

        # Set up heats for the main tournament
        if len(movie_list) <= self.max_per_heat:
            self.heats = [movie_list]
        else:
            self.heats = []
            for i in range(0, len(movie_list), self.max_per_heat):
                heat = movie_list[i:i + self.max_per_heat]
                if heat:
                    self.heats.append(heat)

        # Start first heat of main tournament
        self._start_heat(0)
        self.state = STATE_BATTLE

    def _draw_ability_legend(self):
        """Draw a legend showing current movies, their abilities, and descriptions."""
        # Get unique beyblades (excluding clones and fragments for cleaner display)
        legend_entries = []
        seen_names = set()
        for beyblade in self.beyblades:
            # Skip clones and fragments
            if beyblade.is_clone or beyblade.barbie_is_fragment:
                continue
            # Skip duplicates (from prestige)
            base_name = beyblade.name.replace(' (Double)', '')
            if base_name in seen_names:
                continue
            seen_names.add(base_name)

            if beyblade.ability and beyblade.ability in ABILITIES:
                ability_data = ABILITIES[beyblade.ability]
                legend_entries.append({
                    'name': beyblade.name[:15] + '...' if len(beyblade.name) > 15 else beyblade.name,
                    'ability_name': ability_data['name'],
                    'description': ability_data['description'],
                    'color': ability_data['color'],
                    'alive': beyblade.alive
                })

        if not legend_entries:
            return

        # Limit to prevent overflow
        max_entries = 12
        legend_entries = legend_entries[:max_entries]

        # Drawing parameters - doubled font sizes for readability
        font_name = pygame.font.Font(None, 32)
        font_desc = pygame.font.Font(None, 24)
        font_title = pygame.font.Font(None, 36)
        line_height = 55
        padding = 12
        box_width = 420
        box_height = len(legend_entries) * line_height + padding * 2 + 40

        # Position in bottom right
        box_x = self.window_width - box_width - 10
        box_y = self.window_height - box_height - 10

        # Draw solid background
        pygame.draw.rect(self.screen, (20, 20, 30), (box_x, box_y, box_width, box_height))

        # Draw border
        pygame.draw.rect(self.screen, (100, 100, 100), (box_x, box_y, box_width, box_height), 2)

        # Draw title
        title = font_title.render("ABILITIES", True, (255, 255, 255))
        self.screen.blit(title, (box_x + padding, box_y + padding))

        # Draw entries
        y_offset = box_y + padding + 40
        for entry in legend_entries:
            # Dim if dead
            alpha = 255 if entry['alive'] else 120

            # Ability color indicator
            pygame.draw.circle(self.screen, entry['color'], (box_x + padding + 8, y_offset + 12), 6)

            # Movie name
            name_color = (255, 255, 255) if entry['alive'] else (150, 150, 150)
            name_surface = font_name.render(entry['name'], True, name_color)
            self.screen.blit(name_surface, (box_x + padding + 22, y_offset))

            # Ability name and description
            ability_text = f"{entry['ability_name']}: {entry['description'][:35]}..."
            if len(entry['description']) <= 35:
                ability_text = f"{entry['ability_name']}: {entry['description']}"
            desc_color = entry['color'] if entry['alive'] else (100, 100, 100)
            desc_surface = font_desc.render(ability_text, True, desc_color)
            self.screen.blit(desc_surface, (box_x + padding + 22, y_offset + 26))

            y_offset += line_height

    def _draw_countdown(self):
        """Draw the 3, 2, 1, GO! countdown in the center of the screen."""
        # Determine which number/text to show
        if self.countdown_timer > 120:
            text = "3"
            progress = (180 - self.countdown_timer) / 60  # 0 to 1 during this second
        elif self.countdown_timer > 60:
            text = "2"
            progress = (120 - self.countdown_timer) / 60
        elif self.countdown_timer > 0:
            text = "1"
            progress = (60 - self.countdown_timer) / 60
        else:
            text = "GO!"
            progress = 1.0

        # Create large font for countdown
        font_size = 150
        font = pygame.font.Font(None, font_size)

        # Scale effect: start big and shrink, with a pop at the start
        if progress < 0.1:
            scale = 1.0 + (0.1 - progress) * 3  # Pop effect at start
        else:
            scale = 1.0 - progress * 0.3  # Shrink over time

        # Color cycling for visual interest
        if text == "GO!":
            color = (50, 255, 50)  # Green for GO
        elif text == "1":
            color = (255, 100, 100)  # Red-ish for 1
        elif text == "2":
            color = (255, 200, 100)  # Orange-ish for 2
        else:
            color = (255, 255, 100)  # Yellow-ish for 3

        # Render text
        text_surface = font.render(text, True, color)

        # Scale the text
        scaled_width = int(text_surface.get_width() * scale)
        scaled_height = int(text_surface.get_height() * scale)
        if scaled_width > 0 and scaled_height > 0:
            scaled_surface = pygame.transform.scale(text_surface, (scaled_width, scaled_height))

            # Center on screen
            x = self.window_width // 2 - scaled_width // 2
            y = self.window_height // 2 - scaled_height // 2

            # Draw shadow
            shadow_surface = font.render(text, True, (0, 0, 0))
            shadow_scaled = pygame.transform.scale(shadow_surface, (scaled_width, scaled_height))
            self.screen.blit(shadow_scaled, (x + 4, y + 4))

            # Draw main text
            self.screen.blit(scaled_surface, (x, y))

    def _draw_neo_reset_message(self):
        """Draw the Neo MATRIX RESET message prominently."""
        # Create a semi-transparent overlay
        overlay = pygame.Surface((self.window_width, self.window_height), pygame.SRCALPHA)
        overlay.fill((0, 50, 0, 150))  # Green tint
        self.screen.blit(overlay, (0, 0))

        # Create large font
        font_large = pygame.font.Font(None, 100)
        font_small = pygame.font.Font(None, 50)

        # Main message
        main_text = "MATRIX RESET"
        main_surface = font_large.render(main_text, True, (0, 255, 0))
        main_x = self.window_width // 2 - main_surface.get_width() // 2
        main_y = self.window_height // 2 - 60

        # Shadow
        shadow_surface = font_large.render(main_text, True, (0, 50, 0))
        self.screen.blit(shadow_surface, (main_x + 4, main_y + 4))
        self.screen.blit(main_surface, (main_x, main_y))

        # Sub message with movie name
        sub_text = f"{self.neo_reset_name} died too fast - rewinding time!"
        sub_surface = font_small.render(sub_text, True, (150, 255, 150))
        sub_x = self.window_width // 2 - sub_surface.get_width() // 2
        sub_y = self.window_height // 2 + 40
        self.screen.blit(sub_surface, (sub_x, sub_y))

        # Add some matrix-style falling characters effect
        font_matrix = pygame.font.Font(None, 24)
        for i in range(20):
            char = random.choice("01アイウエオカキクケコサシスセソタチツテト")
            char_x = random.randint(0, self.window_width)
            char_y = random.randint(0, self.window_height)
            alpha = random.randint(50, 200)
            char_surface = font_matrix.render(char, True, (0, alpha, 0))
            self.screen.blit(char_surface, (char_x, char_y))

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

            # Draw obelisk bumpers
            for bumper in self.obelisk_bumpers:
                bumper.draw(self.screen)

            # Draw Interstellar black holes
            for black_hole in self.black_holes:
                bx, by = int(black_hole['x']), int(black_hole['y'])
                # Swirling accretion disk effect
                swirl = (pygame.time.get_ticks() / 50) % (2 * math.pi)
                # Outer dark glow
                pygame.draw.circle(self.screen, (10, 5, 20), (bx, by), 35)
                # Accretion disk rings
                for ring in range(3):
                    ring_r = 30 - ring * 8
                    ring_color = (40 + ring * 20, 20 + ring * 10, 60 + ring * 30)
                    pygame.draw.circle(self.screen, ring_color, (bx, by), ring_r, 2)
                # Rotating streaks
                for j in range(6):
                    angle = swirl + j * math.pi / 3
                    sx = bx + math.cos(angle) * 25
                    sy = by + math.sin(angle) * 25
                    pygame.draw.line(self.screen, (80, 40, 120), (bx, by), (int(sx), int(sy)), 1)
                # Event horizon (pure black center)
                pygame.draw.circle(self.screen, (0, 0, 0), (bx, by), 12)
                # Bright spot (light warping)
                bright_x = bx + int(math.cos(swirl * 2) * 6)
                bright_y = by + int(math.sin(swirl * 2) * 6)
                pygame.draw.circle(self.screen, (100, 80, 150), (bright_x, bright_y), 3)

            # Draw portals
            for i, portal in enumerate(self.portals):
                px, py = int(portal['x']), int(portal['y'])
                # Swirling effect based on time
                swirl = (pygame.time.get_ticks() / 100) % (2 * math.pi)
                # Outer glow
                pygame.draw.circle(self.screen, (100, 50, 150), (px, py), 30)
                # Inner swirl
                pygame.draw.circle(self.screen, (150, 50, 255), (px, py), 25)
                pygame.draw.circle(self.screen, (200, 100, 255), (px, py), 18)
                # Center
                pygame.draw.circle(self.screen, (255, 200, 255), (px, py), 10)
                # Rotating lines
                for j in range(4):
                    angle = swirl + j * math.pi / 2
                    ex = px + math.cos(angle) * 22
                    ey = py + math.sin(angle) * 22
                    pygame.draw.line(self.screen, (200, 150, 255), (px, py), (int(ex), int(ey)), 2)

            # Draw fireballs
            for fireball in self.fireballs:
                fx, fy = int(fireball['x']), int(fireball['y'])
                # Outer glow
                pygame.draw.circle(self.screen, (255, 200, 50), (fx, fy), 12)
                # Core
                pygame.draw.circle(self.screen, (255, 100, 0), (fx, fy), 8)
                # Hot center
                pygame.draw.circle(self.screen, (255, 255, 200), (fx, fy), 4)

            # Draw ice trails (underneath everything else, so draw first)
            for trail in self.ice_trails:
                tx, ty = int(trail['x']), int(trail['y'])
                # Fade based on lifetime
                alpha = min(1.0, trail['lifetime'] / 300)
                # Icy blue color
                color = (int(100 * alpha), int(180 * alpha), int(220 * alpha))
                pygame.draw.circle(self.screen, color, (tx, ty), 6)
                # Sparkle highlight
                if trail['lifetime'] % 20 < 10:
                    pygame.draw.circle(self.screen, (200, 240, 255), (tx - 2, ty - 2), 2)

            # Draw ice projectiles
            for ice in self.ice_projectiles:
                ix, iy = int(ice['x']), int(ice['y'])
                # Outer glow
                pygame.draw.circle(self.screen, (100, 180, 220), (ix, iy), 14)
                # Main body
                pygame.draw.circle(self.screen, (150, 220, 255), (ix, iy), 10)
                # Bright center
                pygame.draw.circle(self.screen, (220, 245, 255), (ix, iy), 5)
                # Sparkle
                pygame.draw.circle(self.screen, (255, 255, 255), (ix - 3, iy - 3), 2)

            # Draw grenades in flight
            for grenade in self.grenades:
                p = grenade['progress']
                # Interpolate position with arc
                start_x, start_y = grenade['start_x'], grenade['start_y']
                target_x, target_y = grenade['target_x'], grenade['target_y']
                # Linear interpolation for x/y
                gx = start_x + (target_x - start_x) * p
                gy = start_y + (target_y - start_y) * p
                # Add arc height (parabola: max height at p=0.5)
                arc_height = 100 * (1 - (2 * p - 1) ** 2)
                gy -= arc_height

                gx, gy = int(gx), int(gy)
                # Shadow on ground (at target)
                shadow_alpha = int(100 * p)
                pygame.draw.circle(self.screen, (30, 30, 30), (int(target_x), int(target_y)), int(8 + 12 * p))
                # Grenade body
                pygame.draw.circle(self.screen, (60, 80, 40), (gx, gy), 10)
                pygame.draw.circle(self.screen, (80, 100, 50), (gx, gy), 7)
                # Fuse spark
                if pygame.time.get_ticks() % 100 < 50:
                    pygame.draw.circle(self.screen, (255, 200, 50), (gx, gy - 8), 3)

            # Draw kamehameha charging indicators (continues after death for avatar abilities)
            for beyblade in self.beyblades:
                if beyblade.ability == 'kamehameha':
                    avatar = self.avatar_manager.avatars.get(beyblade.name)
                    if avatar and avatar.kamehameha_charging:
                        # Draw charging effect at avatar hands
                        charge_progress = 1 - (avatar.kamehameha_charge_timer / 90)
                        charge_size = int(5 + charge_progress * 20)
                        # Pulsing glow
                        pulse = (math.sin(pygame.time.get_ticks() * 0.02) + 1) * 0.5
                        glow_size = int(charge_size * (1 + pulse * 0.3))
                        ax, ay = int(avatar.x), int(avatar.y)
                        pygame.draw.circle(self.screen, (50, 100, 200), (ax, ay), glow_size + 5)
                        pygame.draw.circle(self.screen, (100, 180, 255), (ax, ay), charge_size)
                        pygame.draw.circle(self.screen, (200, 230, 255), (ax, ay), charge_size // 2)

            # Draw kamehameha beams
            for beam in self.kamehameha_beams:
                start_x, start_y = beam['start_x'], beam['start_y']
                angle = beam['angle']
                length = beam['length']
                width = beam['width']

                # Calculate beam end point
                end_x = start_x + math.cos(angle) * length
                end_y = start_y + math.sin(angle) * length

                # Draw beam as a series of circles for glow effect
                # Outer glow
                num_segments = max(1, int(length / 15))
                for i in range(num_segments + 1):
                    t = i / num_segments
                    bx = start_x + (end_x - start_x) * t
                    by = start_y + (end_y - start_y) * t
                    # Pulsing width
                    pulse = (math.sin(pygame.time.get_ticks() * 0.03 + i * 0.5) + 1) * 0.5
                    segment_width = int(width * (0.8 + pulse * 0.4))
                    # Outer glow
                    pygame.draw.circle(self.screen, (50, 100, 200), (int(bx), int(by)), segment_width)
                    # Inner beam
                    pygame.draw.circle(self.screen, (100, 180, 255), (int(bx), int(by)), int(segment_width * 0.7))
                    # Core
                    pygame.draw.circle(self.screen, (200, 230, 255), (int(bx), int(by)), int(segment_width * 0.4))

            # Draw water waves
            for wave in self.water_waves:
                start_x, start_y = wave['start_x'], wave['start_y']
                angle = wave['angle']
                progress = wave['progress']
                wave_width = wave['width']

                # Wave travels outward from start position
                max_distance = ARENA_RADIUS * 2.5
                distance = progress * max_distance

                # Calculate wave front center
                wave_cx = start_x + math.cos(angle) * distance
                wave_cy = start_y + math.sin(angle) * distance

                # Draw multiple wave lines for depth
                for i in range(3):
                    offset = (i - 1) * 15  # -15, 0, 15
                    wave_dist = distance + offset
                    if wave_dist < 0:
                        continue

                    wcx = start_x + math.cos(angle) * wave_dist
                    wcy = start_y + math.sin(angle) * wave_dist

                    # Perpendicular direction for wave width
                    perp_angle = angle + math.pi / 2

                    # Calculate wave endpoints
                    half_width = wave_width / 2
                    w_start_x = wcx + math.cos(perp_angle) * half_width
                    w_start_y = wcy + math.sin(perp_angle) * half_width
                    w_end_x = wcx - math.cos(perp_angle) * half_width
                    w_end_y = wcy - math.sin(perp_angle) * half_width

                    # Color intensity based on wave layer
                    intensity = [0.5, 1.0, 0.7][i]
                    alpha = max(0, 1 - progress) * intensity

                    # Wave colors (blue water)
                    base_color = (50, 150, 255)
                    color = (int(base_color[0] * alpha), int(base_color[1] * alpha), int(base_color[2] * alpha))

                    # Line thickness varies
                    thickness = [3, 6, 4][i]
                    pygame.draw.line(self.screen, color,
                                   (int(w_start_x), int(w_start_y)),
                                   (int(w_end_x), int(w_end_y)), thickness)

                    # Add foam/splash dots along the wave front
                    if i == 1:  # Main wave only
                        num_dots = 10
                        for d in range(num_dots):
                            t = d / (num_dots - 1)
                            dot_x = w_start_x + (w_end_x - w_start_x) * t
                            dot_y = w_start_y + (w_end_y - w_start_y) * t
                            # Randomize position slightly using ticks for animation
                            jitter = math.sin(pygame.time.get_ticks() * 0.01 + d) * 5
                            dot_x += math.cos(angle) * jitter
                            dot_y += math.sin(angle) * jitter
                            pygame.draw.circle(self.screen, (150, 200, 255), (int(dot_x), int(dot_y)), 3)

            # Draw Kevin McAllister traps
            for trap in self.traps:
                tx, ty = int(trap['x']), int(trap['y'])
                if trap['type'] == 'nail':
                    # Gray triangle spikes
                    pygame.draw.polygon(self.screen, (150, 150, 150), [
                        (tx, ty - 8), (tx - 5, ty + 4), (tx + 5, ty + 4)
                    ])
                    pygame.draw.polygon(self.screen, (100, 100, 100), [
                        (tx, ty - 8), (tx - 5, ty + 4), (tx + 5, ty + 4)
                    ], 1)
                else:  # banana
                    # Yellow banana peel
                    pygame.draw.ellipse(self.screen, (255, 255, 0), (tx - 10, ty - 5, 20, 10))
                    pygame.draw.ellipse(self.screen, (200, 200, 0), (tx - 10, ty - 5, 20, 10), 1)
                    # Peel edges
                    pygame.draw.arc(self.screen, (255, 220, 0), (tx - 12, ty - 8, 10, 10), 0, 3.14, 2)
                    pygame.draw.arc(self.screen, (255, 220, 0), (tx + 2, ty - 8, 10, 10), 0, 3.14, 2)

            # Draw John Wick bullets
            for bullet in self.bullets:
                bx, by = int(bullet['x']), int(bullet['y'])
                pygame.draw.circle(self.screen, (220, 220, 220), (bx, by), 4)
                pygame.draw.circle(self.screen, (150, 150, 150), (bx, by), 4, 1)

            # Draw effects
            self.effects.draw(self.screen, self.fonts['medium'])

            # Draw HUD
            alive_count = len(alive_beyblades)
            total_count = len(self.beyblades)
            survivor_names = [b.name for b in alive_beyblades]
            heat_info = None
            if self.is_preliminary:
                heat_info = (f"PRELIMINARY ({len(self.preliminary_groups)} groups)", len(self.preliminary_groups))
            elif len(self.heats) > 1:
                if self.is_finals:
                    heat_info = ("FINALS", len(self.heat_winners))
                else:
                    heat_info = (f"Heat {self.current_heat + 1}/{len(self.heats)}", len(self.heats[self.current_heat]))
            self.battle_hud.draw(self.screen, alive_count, total_count, self.eliminated, survivor_names, self.round_number, heat_info)

            # Draw ability legend in bottom right
            self._draw_ability_legend()

            # Draw countdown overlay
            if self.countdown_active:
                self._draw_countdown()

            # Draw Neo reset message
            if self.neo_reset_countdown > 0:
                self._draw_neo_reset_message()

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

        elif self.state == STATE_DOCKET_SELECT:
            self.participant_select_screen.draw(self.screen)

        elif self.state in (STATE_DOCKET_SPIN, STATE_DOCKET_ZOOM):
            self.docket_spin_screen.draw(self.screen)

        elif self.state == STATE_DOCKET_RESULT:
            self.docket_result_screen.draw(self.screen)

        pygame.display.flip()

        # Call frame callback for web streaming
        if self.frame_callback:
            self.frame_callback(self.screen)

    def run(self):
        while self.running:
            mouse_clicked = self.handle_events()
            self.update(mouse_clicked)
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()

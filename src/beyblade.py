import pygame
import random
import math
from .constants import (
    STAT_RANGES, BEYBLADE_RADIUS, BEYBLADE_MIN_RADIUS, BEYBLADE_MAX_RADIUS,
    MAX_SPEED, FRICTION, BEYBLADE_COLORS, WHITE, BLACK,
    KNOCKOUT_DURATION, KNOCKOUT_FLASH_SPEED,
    ABILITY_CHANCE, ABILITIES, AVATAR_ABILITIES
)


class Beyblade:
    def __init__(self, name: str, x: float, y: float, color_index: int):
        self.name = name
        self.x = x
        self.y = y
        # Will be set by arena spawn with tangential velocity
        self.vx = 0
        self.vy = 0

        # Generate random stats
        self.spin_power = random.uniform(*STAT_RANGES['spin_power'])
        self.attack = random.uniform(*STAT_RANGES['attack'])
        self.defense = random.uniform(*STAT_RANGES['defense'])
        self.max_stamina = random.uniform(*STAT_RANGES['stamina'])
        self.stamina = self.max_stamina
        self.weight = random.uniform(*STAT_RANGES['weight'])

        # Visual properties
        self.color = BEYBLADE_COLORS[color_index % len(BEYBLADE_COLORS)]
        self.base_radius = int(BEYBLADE_MIN_RADIUS + (self.weight - 0.5) *
                         (BEYBLADE_MAX_RADIUS - BEYBLADE_MIN_RADIUS))
        self.radius = self.base_radius
        self.rotation = random.uniform(0, 360)

        # Ability system
        self.ability = None
        self.ability_data = None
        if random.random() < ABILITY_CHANCE:
            ability_key = random.choice(list(ABILITIES.keys()))
            self.ability = ability_key
            self.ability_data = ABILITIES[ability_key].copy()
            # Apply passive size changes
            if ability_key == 'giant':
                self.radius = int(self.base_radius * 1.4)
            elif ability_key == 'tiny':
                self.radius = int(self.base_radius * 0.7)

        # Ability state
        self.rage_active = False
        self.rage_multiplier = 1.0
        self.explosive_triggered = False
        self.vengeance_stored = 0.0  # Damage stored for vengeance
        self.parasite_target = None  # Name of beyblade we're parasitically linked to
        self.parasite_host = None    # Name of beyblade that parasited us
        self.timebomb_timer = 0      # Countdown for timebomb (in frames)
        self.fireball_cooldown = 0   # Cooldown between fireball shots

        # New ability state
        self.last_stand_active = False
        self.last_stand_timer = 0    # 5 seconds = 300 frames
        self.inflation_scale = 1.0   # Current size multiplier
        self.shrink_scale = 1.0      # Current size multiplier (for victims of shrinking)
        self.earthquake_timer = 0    # Countdown for earthquake
        self.lightning_timer = 0     # Countdown for lightning storm
        self.doomsday_timer = 0      # Countdown for doomsday (30s = 1800 frames)
        self.mutually_assured_triggered = False
        self.swamp_thing_freeze_timer = 0  # Frames remaining for momentum freeze
        self.ice_frozen_timer = 0  # Frames remaining for ice freeze
        self.hitstun_timer = 0  # Frames remaining for kamehameha hitstun
        self.hitstun_knockback = (0, 0)  # Knockback to apply after hitstun
        self.venom_dot = 0.0  # Damage to apply over time from venom
        self.venom_tick_timer = 0  # Timer for venom damage ticks
        self.goku_teleport_cooldown = random.randint(300, 1200)  # 5-20 seconds
        self.luffy_edge_saves = 2  # Luffy can survive 2 edge hits per heat
        self.is_clone = False  # True if this is a Naruto clone
        self.original_name = None  # Name of original beyblade if this is a clone
        self.naruto_cloned = False  # True if Naruto has already created clones
        self.andy_death_timer = 0  # Frames since death for Andy Dufresne
        self.andy_respawned = False  # Has Andy already respawned this heat
        self.shelob_no_hit_timer = 0  # Frames since last hit for Shelob
        self.shelob_crawl_angle = 0  # Current crawl direction
        self.shelob_crawl_timer = 0  # Timer to change crawl direction
        self.shelob_is_crawling = False  # Whether Shelob is in crawl mode
        self.kill_bill_target = None  # Name of the revenge target
        self.american_psycho_timer = 0  # Timer for damage reset
        self.american_psycho_stored_stamina = 0  # Stamina at start of 20s window

        # Kevin McAllister
        self.trap_cooldown = 0  # Cooldown between dropping traps

        # Ferris Bueller
        self.ferris_late_entry = True  # Hasn't spawned yet
        self.ferris_timer = 300  # 5 seconds at 60 FPS

        # Alien
        self.alien_is_juvenile = True  # Starts as juvenile
        self.alien_host = None  # Name of beyblade we're inside
        self.alien_gestation_timer = 0  # 5 second countdown
        self.alien_adult_bonus_applied = False

        # Amadeus
        self.amadeus_rival = None  # Name of the rival
        self.amadeus_rival_alive = False  # Set by game.py each frame

        # Terminator
        self.terminator_target = None  # Current target name
        self.terminator_no_hit_timer = 0  # Frames since last hit

        # Interstellar - black hole tracking
        self.interstellar_spawn_x = 0  # Where to place black hole
        self.interstellar_spawn_y = 0

        # Barbie - split on death
        self.barbie_is_fragment = False  # True if this is a Barbie fragment
        self.barbie_split_done = False  # True if already split

        # Neo - death timer for reset check
        self.neo_spawn_frame = 0  # Frame number when spawned
        self.neo_reset_used = False  # True if already reset this heat

        # Marty McFly - teleport back to spawn once per heat when near edge
        self.marty_mcfly_spawn_x = 0
        self.marty_mcfly_spawn_y = 0
        self.marty_mcfly_used = False  # True if already teleported this heat

        # State
        self.alive = True
        self.knockout_timer = 0
        self.flash_state = False

    @property
    def speed(self) -> float:
        return math.sqrt(self.vx**2 + self.vy**2)

    def update(self, dt: float = 1.0):
        if not self.alive:
            if self.knockout_timer > 0:
                self.knockout_timer -= dt
                self.flash_state = (int(self.knockout_timer / KNOCKOUT_FLASH_SPEED) % 2) == 0
            return

        # Update position (Flash moves 2x faster)
        speed_mult = 2.0 if self.ability == 'flash' else 1.0
        self.x += self.vx * dt * speed_mult
        self.y += self.vy * dt * speed_mult

        # Apply friction - beyblades naturally slow down over time
        # Friction increases as spin_power (stamina) decreases
        spin_ratio = self.stamina / self.max_stamina
        effective_friction = FRICTION - (1 - spin_ratio) * 0.01  # More friction as they tire
        # Flash has less friction to maintain speed
        if self.ability == 'flash':
            effective_friction = 0.998
        self.vx *= effective_friction
        self.vy *= effective_friction

        # Clamp speed (Flash has higher max speed)
        max_spd = MAX_SPEED * 2 if self.ability == 'flash' else MAX_SPEED
        if self.speed > max_spd:
            scale = max_spd / self.speed
            self.vx *= scale
            self.vy *= scale

        # Update rotation based on spin power
        self.rotation += self.spin_power * 0.1 * dt
        if self.rotation > 360:
            self.rotation -= 360

        # Very slow stamina decay (backup elimination if no ring-outs)
        self.stamina -= 0.005 * dt
        # Amadeus cannot die while rival lives
        if self.ability == 'amadeus' and self.amadeus_rival_alive:
            self.stamina = max(1, self.stamina)
        elif self.stamina <= 0:
            self.die()

    def apply_force(self, fx: float, fy: float):
        # Heavier beyblades are harder to push
        mass_factor = 1.0 / self.weight
        self.vx += fx * mass_factor
        self.vy += fy * mass_factor

    def take_damage(self, damage: float):
        actual_damage = max(0, damage - self.defense * 0.3)
        self.stamina -= actual_damage
        # Amadeus cannot die while rival lives
        if self.ability == 'amadeus' and self.amadeus_rival_alive:
            self.stamina = max(1, self.stamina)
        elif self.stamina <= 0:
            self.die()

    def die(self):
        if self.ability == 'explosive' and not self.explosive_triggered:
            self.explosive_triggered = True
        self.alive = False
        self.knockout_timer = KNOCKOUT_DURATION
        self.stamina = 0

    def get_collision_damage(self, relative_speed: float) -> float:
        return self.attack * 0.5 + relative_speed * 0.3 + self.spin_power * 0.02

    def draw(self, screen: pygame.Surface, font: pygame.font.Font):
        if not self.alive and self.knockout_timer <= 0:
            return

        x, y = int(self.x), int(self.y)

        # Knockout flash effect
        if not self.alive and self.flash_state:
            alpha_color = tuple(min(255, c + 100) for c in self.color)
        else:
            alpha_color = self.color

        # Draw outer ring
        pygame.draw.circle(screen, alpha_color, (x, y), self.radius)

        # Draw inner details (spinning pattern)
        inner_radius = self.radius - 4
        if inner_radius > 5:
            # Darker center
            center_color = tuple(max(0, c - 60) for c in self.color)
            pygame.draw.circle(screen, center_color, (x, y), inner_radius)

            # Spinning spokes
            num_spokes = 3
            for i in range(num_spokes):
                angle = math.radians(self.rotation + i * (360 / num_spokes))
                spoke_len = inner_radius - 3
                end_x = x + math.cos(angle) * spoke_len
                end_y = y + math.sin(angle) * spoke_len
                pygame.draw.line(screen, alpha_color, (x, y), (end_x, end_y), 3)

            # Center circle
            pygame.draw.circle(screen, alpha_color, (x, y), 5)

        # Draw rim highlight
        pygame.draw.circle(screen, WHITE, (x, y), self.radius, 2)

        # Draw name above (truncate if too long)
        display_name = self.name if len(self.name) <= 20 else self.name[:17] + "..."
        text_surface = font.render(display_name, True, WHITE)

        # Calculate label height based on ability
        label_height = 12
        if self.ability:
            label_height = 22  # Extra space for ability name

        text_rect = text_surface.get_rect(center=(x, y - self.radius - label_height))

        # Background for readability
        bg_rect = text_rect.inflate(8, 4)
        bg_surface = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
        bg_surface.fill((0, 0, 0, 150))
        screen.blit(bg_surface, bg_rect)
        screen.blit(text_surface, text_rect)

        # Draw ability name below movie name
        if self.ability and self.ability_data:
            ability_name = self.ability_data['name']
            # Mark avatar abilities with (Avatar) suffix
            if self.ability in AVATAR_ABILITIES:
                ability_name = f"{ability_name} (Avatar)"
            # Brighten the ability color for readability
            base_color = self.ability_data['color']
            bright_color = tuple(min(255, c + 100) for c in base_color)
            ability_rect_pos = (x, y - self.radius - 2)
            # Draw shadow/outline for contrast
            shadow_surface = font.render(ability_name, True, (0, 0, 0))
            for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1), (0, -1), (0, 1), (-1, 0), (1, 0)]:
                shadow_rect = shadow_surface.get_rect(center=(ability_rect_pos[0] + dx, ability_rect_pos[1] + dy))
                screen.blit(shadow_surface, shadow_rect)
            # Draw main text
            ability_surface = font.render(ability_name, True, bright_color)
            ability_rect = ability_surface.get_rect(center=ability_rect_pos)
            screen.blit(ability_surface, ability_rect)

        # Draw stamina bar
        bar_width = self.radius * 2
        bar_height = 4
        bar_x = x - bar_width // 2
        bar_y = y + self.radius + 6

        # Background
        pygame.draw.rect(screen, (40, 40, 40), (bar_x, bar_y, bar_width, bar_height))

        # Stamina fill
        stamina_ratio = max(0, self.stamina / self.max_stamina)
        fill_width = int(bar_width * stamina_ratio)

        # Color based on health
        if stamina_ratio > 0.5:
            bar_color = (100, 255, 100)
        elif stamina_ratio > 0.25:
            bar_color = (255, 200, 50)
        else:
            bar_color = (255, 80, 80)

        if fill_width > 0:
            pygame.draw.rect(screen, bar_color, (bar_x, bar_y, fill_width, bar_height))

        # Border
        pygame.draw.rect(screen, WHITE, (bar_x, bar_y, bar_width, bar_height), 1)


def check_collision(b1: Beyblade, b2: Beyblade) -> bool:
    if not b1.alive or not b2.alive:
        return False
    dx = b2.x - b1.x
    dy = b2.y - b1.y
    dist = math.sqrt(dx**2 + dy**2)
    return dist < (b1.radius + b2.radius)


def resolve_collision(b1: Beyblade, b2: Beyblade) -> tuple:
    """Resolve collision between two beyblades. Returns collision point, intensity, and ability triggers."""
    dx = b2.x - b1.x
    dy = b2.y - b1.y
    dist = math.sqrt(dx**2 + dy**2)

    if dist == 0:
        dist = 0.1
        dx = 0.1

    # Normalize
    nx = dx / dist
    ny = dy / dist

    # Relative velocity
    dvx = b1.vx - b2.vx
    dvy = b1.vy - b2.vy
    relative_speed = math.sqrt(dvx**2 + dvy**2)

    # Track ability triggers for notifications
    triggers = []

    # Zoro: 25% chance to slice through without bouncing
    zoro_slice = False
    if b1.ability == 'zoro' and random.random() < 0.25:
        # b1 slices through b2 - moderate damage but no bounce
        slice_damage = b1.attack * 0.5 + relative_speed * 0.3
        if b2.ability != 'batman':  # Batman is immune
            b2.stamina -= slice_damage
        triggers.append((b1.name, 'SLICE!', ABILITIES['zoro']['color'], 'Zoro'))
        zoro_slice = True
    if b2.ability == 'zoro' and random.random() < 0.25:
        slice_damage = b2.attack * 0.5 + relative_speed * 0.3
        if b1.ability != 'batman':
            b1.stamina -= slice_damage
        triggers.append((b2.name, 'SLICE!', ABILITIES['zoro']['color'], 'Zoro'))
        zoro_slice = True

    if zoro_slice:
        # Don't separate or bounce - just slice through
        collision_x = (b1.x + b2.x) / 2
        collision_y = (b1.y + b2.y) / 2
        return (collision_x, collision_y, relative_speed, triggers)

    # Separate the beyblades
    overlap = (b1.radius + b2.radius) - dist
    if overlap > 0:
        separation = overlap / 2 + 1
        b1.x -= nx * separation
        b1.y -= ny * separation
        b2.x += nx * separation
        b2.y += ny * separation

    # Calculate base impulse
    total_weight = b1.weight + b2.weight
    w1 = b2.weight / total_weight
    w2 = b1.weight / total_weight

    base_impulse = 5.8  # Increased for harder hits
    speed_impulse = relative_speed * 1.4  # Increased for harder hits
    attack_bonus = (b1.attack + b2.attack) * 0.13  # Increased
    impulse = base_impulse + speed_impulse + attack_bonus

    # Calculate knockback multipliers for each beyblade
    b1_dealt_mult = 1.0  # Multiplier for knockback b1 deals to b2
    b2_dealt_mult = 1.0  # Multiplier for knockback b2 deals to b1
    b1_recv_mult = 1.0   # Multiplier for knockback b1 receives
    b2_recv_mult = 1.0   # Multiplier for knockback b2 receives

    # --- Process abilities ---

    # Reset Shelob no-hit timer when hit
    if b1.ability == 'shelob':
        b1.shelob_no_hit_timer = 0
        b1.shelob_is_crawling = False
    if b2.ability == 'shelob':
        b2.shelob_no_hit_timer = 0
        b2.shelob_is_crawling = False

    # Kill Bill: 5x damage vs designated target
    if b1.ability == 'kill_bill' and b1.kill_bill_target == b2.name:
        b1_dealt_mult *= 5.0
        triggers.append((b1.name, 'REVENGE!', ABILITIES['kill_bill']['color'], 'Kill Bill'))
    if b2.ability == 'kill_bill' and b2.kill_bill_target == b1.name:
        b2_dealt_mult *= 5.0
        triggers.append((b2.name, 'REVENGE!', ABILITIES['kill_bill']['color'], 'Kill Bill'))

    # Little Miss Sunshine: no knockback from red or green beyblades (but still takes damage)
    def is_red_or_green(color):
        r, g, b = color
        # Check if color is predominantly red (R is the dominant channel)
        is_red = r > 120 and r > g and r > b and (r - max(g, b)) > 30
        # Check if color is predominantly green (G is the dominant channel)
        is_green = g > 120 and g > r and g > b and (g - max(r, b)) > 30
        return is_red or is_green

    if b1.ability == 'little_miss_sunshine' and is_red_or_green(b2.color):
        b1_recv_mult = 0  # No knockback from red/green (but damage still applies via other means)
        triggers.append((b1.name, 'Color blind!', ABILITIES['little_miss_sunshine']['color'], 'Little Miss Sunshine'))
    if b2.ability == 'little_miss_sunshine' and is_red_or_green(b1.color):
        b2_recv_mult = 0  # No knockback from red/green (but damage still applies via other means)
        triggers.append((b2.name, 'Color blind!', ABILITIES['little_miss_sunshine']['color'], 'Little Miss Sunshine'))

    # Luffy: bounces 2x harder (receives 2x knockback)
    if b1.ability == 'luffy':
        b1_recv_mult *= 2.0
    if b2.ability == 'luffy':
        b2_recv_mult *= 2.0

    # Glass Cannon: +50% dealt and received
    if b1.ability == 'glass_cannon':
        b1_dealt_mult *= 1.5
        b1_recv_mult *= 1.5
    if b2.ability == 'glass_cannon':
        b2_dealt_mult *= 1.5
        b2_recv_mult *= 1.5

    # Brutal: +40% damage dealt
    if b1.ability == 'brutal':
        b1_dealt_mult *= 1.4
    if b2.ability == 'brutal':
        b2_dealt_mult *= 1.4

    # Momentum: more damage at high speed (up to +60% at max speed)
    if b1.ability == 'momentum':
        speed_ratio = min(1.0, b1.speed / 14.0)  # 14 is MAX_SPEED
        b1_dealt_mult *= 1.0 + (speed_ratio * 0.6)
    if b2.ability == 'momentum':
        speed_ratio = min(1.0, b2.speed / 14.0)
        b2_dealt_mult *= 1.0 + (speed_ratio * 0.6)

    # Berserker: more damage at low HP (up to +80% at near-death)
    if b1.ability == 'berserker':
        hp_ratio = b1.stamina / b1.max_stamina
        damage_bonus = (1.0 - hp_ratio) * 0.8  # 0% at full HP, 80% at 0 HP
        b1_dealt_mult *= 1.0 + damage_bonus
    if b2.ability == 'berserker':
        hp_ratio = b2.stamina / b2.max_stamina
        damage_bonus = (1.0 - hp_ratio) * 0.8
        b2_dealt_mult *= 1.0 + damage_bonus

    # Burst: chance for 2.5x knockback
    if b1.ability == 'burst' and random.random() < ABILITIES['burst']['trigger_chance']:
        b1_dealt_mult *= 2.5
        triggers.append((b1.name, 'BURST!', ABILITIES['burst']['color']))
    if b2.ability == 'burst' and random.random() < ABILITIES['burst']['trigger_chance']:
        b2_dealt_mult *= 2.5
        triggers.append((b2.name, 'BURST!', ABILITIES['burst']['color']))

    # Gambler: random 2x or 0.5x
    if b1.ability == 'gambler':
        mult = 2.0 if random.random() < 0.5 else 0.5
        b1_dealt_mult *= mult
        if mult == 2.0:
            triggers.append((b1.name, 'GAMBLER WIN!', ABILITIES['gambler']['color']))
        else:
            triggers.append((b1.name, 'GAMBLER LOSE...', (150, 150, 150)))
    if b2.ability == 'gambler':
        mult = 2.0 if random.random() < 0.5 else 0.5
        b2_dealt_mult *= mult
        if mult == 2.0:
            triggers.append((b2.name, 'GAMBLER WIN!', ABILITIES['gambler']['color']))
        else:
            triggers.append((b2.name, 'GAMBLER LOSE...', (150, 150, 150)))

    # Rage: if active, 2x knockback then reset
    if b1.rage_active:
        b1_dealt_mult *= 2.0
        b1.rage_active = False
        triggers.append((b1.name, 'RAGE!', ABILITIES['rage']['color']))
    if b2.rage_active:
        b2_dealt_mult *= 2.0
        b2.rage_active = False
        triggers.append((b2.name, 'RAGE!', ABILITIES['rage']['color']))

    # Dodge: chance to ignore knockback
    b1_dodged = False
    b2_dodged = False
    if b1.ability == 'dodge' and random.random() < ABILITIES['dodge']['trigger_chance']:
        b1_recv_mult = 0
        b1_dodged = True
        triggers.append((b1.name, 'DODGE!', ABILITIES['dodge']['color']))
    if b2.ability == 'dodge' and random.random() < ABILITIES['dodge']['trigger_chance']:
        b2_recv_mult = 0
        b2_dodged = True
        triggers.append((b2.name, 'DODGE!', ABILITIES['dodge']['color']))

    # Counter: reflect knockback (only if didn't dodge)
    if b1.ability == 'counter' and not b1_dodged and random.random() < ABILITIES['counter']['trigger_chance']:
        # b1 reflects: b2's knockback goes back to b2
        b2_recv_mult += b1_recv_mult
        b1_recv_mult = 0
        triggers.append((b1.name, 'Counter!', ABILITIES['counter']['color']))
    if b2.ability == 'counter' and not b2_dodged and random.random() < ABILITIES['counter']['trigger_chance']:
        b1_recv_mult += b2_recv_mult
        b2_recv_mult = 0
        triggers.append((b2.name, 'Counter!', ABILITIES['counter']['color']))

    # Apply knockback
    # b1 receives knockback from b2's attack
    b1_knockback = impulse * w1 * b2_dealt_mult * b1_recv_mult
    # b2 receives knockback from b1's attack
    b2_knockback = impulse * w2 * b1_dealt_mult * b2_recv_mult

    b1.vx -= nx * b1_knockback
    b1.vy -= ny * b1_knockback
    b2.vx += nx * b2_knockback
    b2.vy += ny * b2_knockback

    # Vampire: steal stamina (Batman immune)
    if b1.ability == 'vampire' and b2.ability != 'batman':
        steal = 5 + relative_speed * 0.5
        b1.stamina = min(b1.max_stamina, b1.stamina + steal)
        b2.stamina -= steal * 0.5
        triggers.append((b1.name, 'Vampire drain', ABILITIES['vampire']['color']))
    if b2.ability == 'vampire' and b1.ability != 'batman':
        steal = 5 + relative_speed * 0.5
        b2.stamina = min(b2.max_stamina, b2.stamina + steal)
        b1.stamina -= steal * 0.5
        triggers.append((b2.name, 'Vampire drain', ABILITIES['vampire']['color']))

    # Venom: apply 200% damage as DoT (Batman immune)
    if b1.ability == 'venom' and b2.ability != 'batman':
        base_damage = b1.get_collision_damage(relative_speed)
        venom_damage = base_damage * 2.0  # 200% damage
        b2.venom_dot += venom_damage
        b2.venom_tick_timer = 30  # Start ticking
        triggers.append((b1.name, 'Venom!', ABILITIES['venom']['color']))
    if b2.ability == 'venom' and b1.ability != 'batman':
        base_damage = b2.get_collision_damage(relative_speed)
        venom_damage = base_damage * 2.0  # 200% damage
        b1.venom_dot += venom_damage
        b1.venom_tick_timer = 30  # Start ticking
        triggers.append((b2.name, 'Venom!', ABILITIES['venom']['color']))

    # Rage: activate if took big hit (knockback > 8)
    if b1.ability == 'rage' and b1_knockback > 8:
        b1.rage_active = True
    if b2.ability == 'rage' and b2_knockback > 8:
        b2.rage_active = True

    # Mirror: chance to copy opponent's ability
    if b1.ability == 'mirror' and b2.ability and b2.ability != 'mirror':
        if random.random() < ABILITIES['mirror']['trigger_chance']:
            b1.ability = b2.ability
            b1.ability_data = ABILITIES[b2.ability].copy()
            triggers.append((b1.name, f'Mirror -> {b1.ability_data["name"]}', ABILITIES['mirror']['color']))
    if b2.ability == 'mirror' and b1.ability and b1.ability != 'mirror':
        if random.random() < ABILITIES['mirror']['trigger_chance']:
            old_b1_ability = b1.ability  # Use original, not potentially mirrored
            b2.ability = old_b1_ability
            b2.ability_data = ABILITIES[old_b1_ability].copy()
            triggers.append((b2.name, f'Mirror -> {b2.ability_data["name"]}', ABILITIES['mirror']['color']))

    # Copycat: guaranteed copy on first hit (one-time)
    if b1.ability == 'copycat' and b2.ability and b2.ability not in ('copycat', 'mirror'):
        b1.ability = b2.ability
        b1.ability_data = ABILITIES[b2.ability].copy()
        triggers.append((b1.name, f'Copycat -> {b1.ability_data["name"]}', ABILITIES['copycat']['color']))
    if b2.ability == 'copycat' and b1.ability and b1.ability not in ('copycat', 'mirror'):
        old_b1_ability = b1.ability
        b2.ability = old_b1_ability
        b2.ability_data = ABILITIES[old_b1_ability].copy()
        triggers.append((b2.name, f'Copycat -> {b2.ability_data["name"]}', ABILITIES['copycat']['color']))

    # Vengeance: release stored damage, then store damage taken
    if b1.ability == 'vengeance' and b1.vengeance_stored > 0:
        # Release stored damage as bonus knockback
        b1_dealt_mult *= 1.0 + (b1.vengeance_stored / 10.0)
        triggers.append((b1.name, f'Vengeance! (+{b1.vengeance_stored:.0f})', ABILITIES['vengeance']['color']))
        b1.vengeance_stored = 0
    if b2.ability == 'vengeance' and b2.vengeance_stored > 0:
        b2_dealt_mult *= 1.0 + (b2.vengeance_stored / 10.0)
        triggers.append((b2.name, f'Vengeance! (+{b2.vengeance_stored:.0f})', ABILITIES['vengeance']['color']))
        b2.vengeance_stored = 0

    # Store damage for next vengeance hit (based on knockback received)
    if b1.ability == 'vengeance':
        b1.vengeance_stored += b1_knockback * 0.5
    if b2.ability == 'vengeance':
        b2.vengeance_stored += b2_knockback * 0.5

    # Reversal: 10% chance to swap positions (Batman immune - can't be swapped)
    if b1.ability == 'reversal' or b2.ability == 'reversal':
        # Check if either is Batman (immune to being swapped)
        if b1.ability != 'batman' and b2.ability != 'batman':
            if random.random() < ABILITIES['reversal']['trigger_chance']:
                # Swap positions
                b1.x, b2.x = b2.x, b1.x
                b1.y, b2.y = b2.y, b1.y
                # Also swap velocities for disorientation
                b1.vx, b2.vx = b2.vx, b1.vx
                b1.vy, b2.vy = b2.vy, b1.vy
                reverser = b1 if b1.ability == 'reversal' else b2
                triggers.append((reverser.name, 'Reversal!', ABILITIES['reversal']['color']))

    # Parasite: latch onto enemy, share damage (Batman immune)
    if b1.ability == 'parasite' and b1.parasite_target is None and b2.parasite_host != b1.name and b2.ability != 'batman':
        b1.parasite_target = b2.name
        b2.parasite_host = b1.name
        triggers.append((b1.name, f'Parasites {b2.name[:10]}!', ABILITIES['parasite']['color']))
    if b2.ability == 'parasite' and b2.parasite_target is None and b1.parasite_host != b2.name and b1.ability != 'batman':
        b2.parasite_target = b1.name
        b1.parasite_host = b2.name
        triggers.append((b2.name, f'Parasites {b1.name[:10]}!', ABILITIES['parasite']['color']))

    # Inflation: grow 5% larger when hit
    if b1.ability == 'inflation':
        b1.inflation_scale *= 1.05
        b1.radius = int(b1.base_radius * b1.inflation_scale)
        if b1.inflation_scale > 1.5:  # Cap at 150% size
            triggers.append((b1.name, 'MAX SIZE!', ABILITIES['inflation']['color'], 'Inflation'))
    if b2.ability == 'inflation':
        b2.inflation_scale *= 1.05
        b2.radius = int(b2.base_radius * b2.inflation_scale)
        if b2.inflation_scale > 1.5:
            triggers.append((b2.name, 'MAX SIZE!', ABILITIES['inflation']['color'], 'Inflation'))

    # Shrinking: you shrink 10% when hit (smaller = harder to hit)
    if b1.ability == 'shrinking':
        b1.shrink_scale *= 0.9
        b1.radius = int(b1.base_radius * b1.inflation_scale * b1.shrink_scale)
        b1.radius = max(10, b1.radius)  # Minimum size
        triggers.append((b1.name, 'Shrinking!', ABILITIES['shrinking']['color']))
    if b2.ability == 'shrinking':
        b2.shrink_scale *= 0.9
        b2.radius = int(b2.base_radius * b2.inflation_scale * b2.shrink_scale)
        b2.radius = max(10, b2.radius)
        triggers.append((b2.name, 'Shrinking!', ABILITIES['shrinking']['color']))

    # Alien: juvenile enters first beyblade it hits
    # When infecting, alien becomes hidden (alive=False) until it bursts out
    if b1.ability == 'alien' and b1.alien_is_juvenile and b1.alien_host is None:
        if b2.ability != 'batman':
            b1.alien_host = b2.name
            b1.alien_gestation_timer = 300  # 5 seconds
            b1.alive = False  # Hide alien while gestating inside host
            triggers.append((b1.name, f'INFECTS {b2.name[:10]}!', ABILITIES['alien']['color'], 'Alien'))
    if b2.ability == 'alien' and b2.alien_is_juvenile and b2.alien_host is None:
        if b1.ability != 'batman':
            b2.alien_host = b1.name
            b2.alien_gestation_timer = 300  # 5 seconds
            b2.alive = False  # Hide alien while gestating inside host
            triggers.append((b2.name, f'INFECTS {b1.name[:10]}!', ABILITIES['alien']['color'], 'Alien'))

    # Terminator: reset no-hit timer on collision
    if b1.ability == 'terminator':
        b1.terminator_no_hit_timer = 0
    if b2.ability == 'terminator':
        b2.terminator_no_hit_timer = 0

    # Return collision point for effects
    collision_x = b1.x + nx * b1.radius
    collision_y = b1.y + ny * b1.radius

    return (collision_x, collision_y, relative_speed, triggers)

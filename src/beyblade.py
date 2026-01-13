import pygame
import random
import math
from .constants import (
    STAT_RANGES, BEYBLADE_RADIUS, BEYBLADE_MIN_RADIUS, BEYBLADE_MAX_RADIUS,
    MAX_SPEED, FRICTION, BEYBLADE_COLORS, WHITE, BLACK,
    KNOCKOUT_DURATION, KNOCKOUT_FLASH_SPEED,
    ABILITY_CHANCE, ABILITIES
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
        self.bouncy_used = False
        self.bouncy_triggered = False
        self.turbo_triggered = False
        self.rage_active = False
        self.rage_multiplier = 1.0

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

        # Update position
        self.x += self.vx * dt
        self.y += self.vy * dt

        # Apply friction - beyblades naturally slow down over time
        # Friction increases as spin_power (stamina) decreases
        spin_ratio = self.stamina / self.max_stamina
        effective_friction = FRICTION - (1 - spin_ratio) * 0.01  # More friction as they tire
        self.vx *= effective_friction
        self.vy *= effective_friction

        # Clamp speed
        if self.speed > MAX_SPEED:
            scale = MAX_SPEED / self.speed
            self.vx *= scale
            self.vy *= scale

        # Update rotation based on spin power
        self.rotation += self.spin_power * 0.1 * dt
        if self.rotation > 360:
            self.rotation -= 360

        # Very slow stamina decay (backup elimination if no ring-outs)
        self.stamina -= 0.005 * dt
        if self.stamina <= 0:
            self.die()

        # Turbo ability - random speed boost
        self.turbo_triggered = False
        if self.ability == 'turbo' and self.alive:
            if random.random() < ABILITIES['turbo']['trigger_chance']:
                boost = random.uniform(3, 6)
                angle = random.uniform(0, 2 * math.pi)
                self.vx += math.cos(angle) * boost
                self.vy += math.sin(angle) * boost
                self.turbo_triggered = True

    def apply_force(self, fx: float, fy: float):
        # Heavier beyblades are harder to push
        mass_factor = 1.0 / self.weight
        self.vx += fx * mass_factor
        self.vy += fy * mass_factor

    def take_damage(self, damage: float):
        actual_damage = max(0, damage - self.defense * 0.3)
        self.stamina -= actual_damage
        if self.stamina <= 0:
            self.die()

    def die(self):
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
            ability_color = self.ability_data['color']
            ability_surface = font.render(ability_name, True, ability_color)
            ability_rect = ability_surface.get_rect(center=(x, y - self.radius - 2))
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

    # Separate the beyblades
    overlap = (b1.radius + b2.radius) - dist
    if overlap > 0:
        separation = overlap / 2 + 1
        b1.x -= nx * separation
        b1.y -= ny * separation
        b2.x += nx * separation
        b2.y += ny * separation

    # Track ability triggers for notifications
    triggers = []

    # Calculate base impulse
    total_weight = b1.weight + b2.weight
    w1 = b2.weight / total_weight
    w2 = b1.weight / total_weight

    base_impulse = 6.0
    speed_impulse = relative_speed * 1.8
    attack_bonus = (b1.attack + b2.attack) * 0.12
    impulse = base_impulse + speed_impulse + attack_bonus

    # Calculate knockback multipliers for each beyblade
    b1_dealt_mult = 1.0  # Multiplier for knockback b1 deals to b2
    b2_dealt_mult = 1.0  # Multiplier for knockback b2 deals to b1
    b1_recv_mult = 1.0   # Multiplier for knockback b1 receives
    b2_recv_mult = 1.0   # Multiplier for knockback b2 receives

    # --- Process abilities ---

    # Glass Cannon: +50% dealt and received
    if b1.ability == 'glass_cannon':
        b1_dealt_mult *= 1.5
        b1_recv_mult *= 1.5
    if b2.ability == 'glass_cannon':
        b2_dealt_mult *= 1.5
        b2_recv_mult *= 1.5

    # Burst: chance for 2.5x knockback
    if b1.ability == 'burst' and random.random() < ABILITIES['burst']['trigger_chance']:
        b1_dealt_mult *= 2.5
        triggers.append((b1.name, 'Burst', ABILITIES['burst']['color']))
    if b2.ability == 'burst' and random.random() < ABILITIES['burst']['trigger_chance']:
        b2_dealt_mult *= 2.5
        triggers.append((b2.name, 'Burst', ABILITIES['burst']['color']))

    # Gambler: random 2x or 0.5x
    if b1.ability == 'gambler':
        mult = 2.0 if random.random() < 0.5 else 0.5
        b1_dealt_mult *= mult
        if mult == 2.0:
            triggers.append((b1.name, 'Gambler WIN!', ABILITIES['gambler']['color']))
        else:
            triggers.append((b1.name, 'Gambler lose...', (150, 150, 150)))
    if b2.ability == 'gambler':
        mult = 2.0 if random.random() < 0.5 else 0.5
        b2_dealt_mult *= mult
        if mult == 2.0:
            triggers.append((b2.name, 'Gambler WIN!', ABILITIES['gambler']['color']))
        else:
            triggers.append((b2.name, 'Gambler lose...', (150, 150, 150)))

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
        triggers.append((b1.name, 'Dodge!', ABILITIES['dodge']['color']))
    if b2.ability == 'dodge' and random.random() < ABILITIES['dodge']['trigger_chance']:
        b2_recv_mult = 0
        b2_dodged = True
        triggers.append((b2.name, 'Dodge!', ABILITIES['dodge']['color']))

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

    # Vampire: steal stamina
    if b1.ability == 'vampire':
        steal = 5 + relative_speed * 0.5
        b1.stamina = min(b1.max_stamina, b1.stamina + steal)
        b2.stamina -= steal * 0.5
        triggers.append((b1.name, 'Vampire drain', ABILITIES['vampire']['color']))
    if b2.ability == 'vampire':
        steal = 5 + relative_speed * 0.5
        b2.stamina = min(b2.max_stamina, b2.stamina + steal)
        b1.stamina -= steal * 0.5
        triggers.append((b2.name, 'Vampire drain', ABILITIES['vampire']['color']))

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

    # Return collision point for effects
    collision_x = b1.x + nx * b1.radius
    collision_y = b1.y + ny * b1.radius

    return (collision_x, collision_y, relative_speed, triggers)

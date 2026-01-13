import pygame
import random
import math
from .constants import (
    STAT_RANGES, BEYBLADE_RADIUS, BEYBLADE_MIN_RADIUS, BEYBLADE_MAX_RADIUS,
    MAX_SPEED, FRICTION, BEYBLADE_COLORS, WHITE, BLACK,
    KNOCKOUT_DURATION, KNOCKOUT_FLASH_SPEED
)


class Beyblade:
    def __init__(self, name: str, x: float, y: float, color_index: int):
        self.name = name
        self.x = x
        self.y = y
        self.vx = random.uniform(-2, 2)
        self.vy = random.uniform(-2, 2)

        # Generate random stats
        self.spin_power = random.uniform(*STAT_RANGES['spin_power'])
        self.attack = random.uniform(*STAT_RANGES['attack'])
        self.defense = random.uniform(*STAT_RANGES['defense'])
        self.max_stamina = random.uniform(*STAT_RANGES['stamina'])
        self.stamina = self.max_stamina
        self.weight = random.uniform(*STAT_RANGES['weight'])

        # Visual properties
        self.color = BEYBLADE_COLORS[color_index % len(BEYBLADE_COLORS)]
        self.radius = int(BEYBLADE_MIN_RADIUS + (self.weight - 0.5) *
                         (BEYBLADE_MAX_RADIUS - BEYBLADE_MIN_RADIUS))
        self.rotation = random.uniform(0, 360)

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

        # Apply friction
        self.vx *= FRICTION
        self.vy *= FRICTION

        # Clamp speed
        if self.speed > MAX_SPEED:
            scale = MAX_SPEED / self.speed
            self.vx *= scale
            self.vy *= scale

        # Update rotation based on spin power
        self.rotation += self.spin_power * 0.1 * dt
        if self.rotation > 360:
            self.rotation -= 360

        # Stamina decay over time (very slow)
        self.stamina -= 0.02 * dt
        if self.stamina <= 0:
            self.die()

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
        text_rect = text_surface.get_rect(center=(x, y - self.radius - 12))

        # Background for readability
        bg_rect = text_rect.inflate(8, 4)
        bg_surface = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
        bg_surface.fill((0, 0, 0, 150))
        screen.blit(bg_surface, bg_rect)
        screen.blit(text_surface, text_rect)

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
    """Resolve collision between two beyblades. Returns collision point for effects."""
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

    # Calculate collision response
    # Momentum-like exchange based on weight
    total_weight = b1.weight + b2.weight
    w1 = b2.weight / total_weight
    w2 = b1.weight / total_weight

    # Impulse
    impulse = relative_speed * 0.8

    b1.vx -= nx * impulse * w1
    b1.vy -= ny * impulse * w1
    b2.vx += nx * impulse * w2
    b2.vy += ny * impulse * w2

    # Deal damage to each other
    damage1 = b1.get_collision_damage(relative_speed)
    damage2 = b2.get_collision_damage(relative_speed)

    b1.take_damage(damage2)
    b2.take_damage(damage1)

    # Return collision point for effects
    collision_x = b1.x + nx * b1.radius
    collision_y = b1.y + ny * b1.radius

    return (collision_x, collision_y, relative_speed)

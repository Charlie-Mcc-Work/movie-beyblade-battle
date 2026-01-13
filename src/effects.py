import pygame
import random
import math
from .constants import SPARK_COLORS, SPARK_LIFETIME, SPARK_COUNT


class Particle:
    def __init__(self, x: float, y: float, vx: float, vy: float, color: tuple, lifetime: int):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.lifetime = lifetime
        self.max_lifetime = lifetime

    def update(self, dt: float = 1.0):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vx *= 0.95
        self.vy *= 0.95
        self.lifetime -= dt

    @property
    def alive(self) -> bool:
        return self.lifetime > 0

    def draw(self, screen: pygame.Surface):
        if not self.alive:
            return

        # Fade out based on lifetime
        alpha_ratio = self.lifetime / self.max_lifetime
        size = max(1, int(4 * alpha_ratio))

        # Draw particle
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), size)


class EffectsManager:
    def __init__(self):
        self.particles: list[Particle] = []
        self.knockout_effects: list[dict] = []

    def spawn_collision_sparks(self, x: float, y: float, intensity: float = 1.0):
        """Spawn spark particles at a collision point."""
        num_sparks = int(SPARK_COUNT * min(2.0, intensity))

        for _ in range(num_sparks):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 5) * intensity
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            color = random.choice(SPARK_COLORS)
            lifetime = SPARK_LIFETIME + random.randint(-5, 5)

            self.particles.append(Particle(x, y, vx, vy, color, lifetime))

    def spawn_knockout_effect(self, x: float, y: float, color: tuple, name: str):
        """Spawn a knockout explosion effect."""
        # Ring of particles
        for i in range(16):
            angle = (2 * math.pi * i / 16)
            speed = 4
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed

            self.particles.append(Particle(x, y, vx, vy, color, 30))

        # Inner burst
        for _ in range(20):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1, 6)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            particle_color = tuple(min(255, c + 50) for c in color)

            self.particles.append(Particle(x, y, vx, vy, particle_color, 25))

        # Add text effect
        self.knockout_effects.append({
            'x': x,
            'y': y,
            'name': name,
            'timer': 60,
            'color': color
        })

    def update(self, dt: float = 1.0):
        # Update particles
        for particle in self.particles:
            particle.update(dt)

        # Remove dead particles
        self.particles = [p for p in self.particles if p.alive]

        # Update knockout text effects
        for effect in self.knockout_effects:
            effect['timer'] -= dt
            effect['y'] -= 0.5 * dt  # Float upward

        # Remove expired effects
        self.knockout_effects = [e for e in self.knockout_effects if e['timer'] > 0]

    def draw(self, screen: pygame.Surface, font: pygame.font.Font):
        # Draw all particles
        for particle in self.particles:
            particle.draw(screen)

        # Draw knockout text effects
        for effect in self.knockout_effects:
            alpha = min(255, int(255 * (effect['timer'] / 60)))
            text = f"{effect['name']} OUT!"

            # Render text with shadow
            text_surface = font.render(text, True, effect['color'])
            text_rect = text_surface.get_rect(center=(int(effect['x']), int(effect['y'])))

            # Shadow
            shadow_surface = font.render(text, True, (0, 0, 0))
            shadow_rect = shadow_surface.get_rect(center=(int(effect['x']) + 2, int(effect['y']) + 2))
            screen.blit(shadow_surface, shadow_rect)

            screen.blit(text_surface, text_rect)

    def clear(self):
        self.particles.clear()
        self.knockout_effects.clear()

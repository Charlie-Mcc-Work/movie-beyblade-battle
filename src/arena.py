import pygame
import math
from .constants import (
    ARENA_CENTER, ARENA_RADIUS, ARENA_SLOPE_STRENGTH,
    ARENA_FLOOR, ARENA_EDGE, ARENA_RIM, WHITE, DARK_GRAY
)
from .beyblade import Beyblade


class Arena:
    def __init__(self):
        self.center_x, self.center_y = ARENA_CENTER
        self.radius = ARENA_RADIUS

    def apply_boundary(self, beyblade: Beyblade):
        """Apply arena boundary physics - bowl shape with centripetal force for orbiting."""
        dx = beyblade.x - self.center_x
        dy = beyblade.y - self.center_y
        dist_from_center = math.sqrt(dx**2 + dy**2)

        if dist_from_center == 0:
            return

        # Normalize direction from center
        nx = dx / dist_from_center
        ny = dy / dist_from_center

        # Bowl physics: slope force toward center (like gravity in a bowl)
        # Stronger near edges, simulating steeper bowl walls
        edge_proximity = dist_from_center / self.radius
        slope_force = ARENA_SLOPE_STRENGTH * (edge_proximity ** 1.5)

        # Apply centripetal force (toward center)
        beyblade.vx -= nx * slope_force
        beyblade.vy -= ny * slope_force

        # Add slight tangential force to maintain circular motion
        # This simulates how spinning beyblades convert some energy into orbital motion
        if beyblade.speed > 0.5:
            # Tangent is perpendicular to radius
            tx = -ny
            ty = nx
            # Determine spin direction from current velocity
            cross = beyblade.vx * ty - beyblade.vy * tx
            spin_dir = 1 if cross > 0 else -1
            # Small tangential boost based on distance from center
            tangent_force = 0.02 * edge_proximity * spin_dir
            beyblade.vx += tx * tangent_force
            beyblade.vy += ty * tangent_force

        # Ring-out: if center of beyblade exits arena, it's eliminated
        if dist_from_center > self.radius:
            # Bouncy ability: survive one ring-out
            if beyblade.ability == 'bouncy' and not beyblade.bouncy_used:
                beyblade.bouncy_used = True
                # Bounce back into arena
                beyblade.x = self.center_x + nx * (self.radius * 0.7)
                beyblade.y = self.center_y + ny * (self.radius * 0.7)
                # Reverse velocity and boost back in
                beyblade.vx = -nx * 5
                beyblade.vy = -ny * 5
                beyblade.bouncy_triggered = True  # For notification
            else:
                beyblade.die()

    def draw(self, screen: pygame.Surface):
        """Draw the arena with a stadium-like appearance."""
        cx, cy = self.center_x, self.center_y

        # Outer rim shadow
        pygame.draw.circle(screen, DARK_GRAY, (cx + 5, cy + 5), self.radius + 15)

        # Outer rim
        pygame.draw.circle(screen, ARENA_RIM, (cx, cy), self.radius + 15)

        # Edge ring
        pygame.draw.circle(screen, ARENA_EDGE, (cx, cy), self.radius + 5)

        # Main floor
        pygame.draw.circle(screen, ARENA_FLOOR, (cx, cy), self.radius)

        # Floor detail rings (concentric circles for depth)
        for i in range(1, 6):
            ring_radius = self.radius * (i / 6)
            alpha = 30 + i * 5
            ring_color = tuple(min(255, c + alpha) for c in ARENA_FLOOR)
            pygame.draw.circle(screen, ring_color, (cx, cy), int(ring_radius), 1)

        # Center mark
        pygame.draw.circle(screen, ARENA_EDGE, (cx, cy), 20)
        pygame.draw.circle(screen, ARENA_RIM, (cx, cy), 10)

        # Highlight on rim (3D effect)
        highlight_rect = pygame.Rect(
            cx - self.radius - 10,
            cy - self.radius - 10,
            (self.radius + 10) * 2,
            (self.radius + 10) * 2
        )
        pygame.draw.arc(screen, WHITE, highlight_rect, math.radians(200), math.radians(340), 3)

    def get_spawn_positions(self, count: int) -> list:
        """Generate spawn positions evenly distributed around the arena with tangential velocities."""
        spawns = []
        spawn_radius = self.radius * 0.6  # Spawn in inner 60% of arena

        for i in range(count):
            angle = (2 * math.pi * i / count) + (math.pi / 4)  # Offset for variety
            dist = spawn_radius * (0.5 + 0.5 * ((i % 3) / 2))
            x = self.center_x + math.cos(angle) * dist
            y = self.center_y + math.sin(angle) * dist

            # Tangential velocity (perpendicular to radius, like spinning in)
            # All spin same direction for realistic orbiting, with speed variation
            speed = 5 + (i % 4) * 1.5  # Vary initial speeds (5-9.5)
            vx = -math.sin(angle) * speed
            vy = math.cos(angle) * speed

            spawns.append((x, y, vx, vy))

        return spawns

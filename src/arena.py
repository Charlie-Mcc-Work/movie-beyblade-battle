import pygame
import math
from .constants import (
    ARENA_CENTER, ARENA_RADIUS, ARENA_SLOPE_STRENGTH,
    ARENA_FLOOR, ARENA_EDGE, ARENA_RIM, WHITE, DARK_GRAY
)
from .beyblade import Beyblade


class Bumper:
    """Pinball-style bumper obstacle that bounces beyblades."""

    def __init__(self, x: int, y: int, radius: int = 30):
        self.x = x
        self.y = y
        self.radius = radius
        self.base_radius = radius
        self.hit_timer = 0  # Animation timer when hit
        self.color = (255, 100, 50)  # Orange
        self.glow_color = (255, 200, 100)  # Bright yellow-orange when hit
        self.boost_force = 12  # How hard it pushes beyblades

    def check_collision(self, beyblade: Beyblade) -> bool:
        """Check if beyblade is colliding with this bumper."""
        dx = beyblade.x - self.x
        dy = beyblade.y - self.y
        dist = math.sqrt(dx**2 + dy**2)
        return dist < (self.radius + beyblade.radius)

    def apply_bounce(self, beyblade: Beyblade):
        """Bounce the beyblade away from the bumper with force."""
        dx = beyblade.x - self.x
        dy = beyblade.y - self.y
        dist = math.sqrt(dx**2 + dy**2)

        if dist == 0:
            return

        # Normalize direction away from bumper
        nx = dx / dist
        ny = dy / dist

        # Push beyblade outside bumper
        overlap = (self.radius + beyblade.radius) - dist
        beyblade.x += nx * overlap
        beyblade.y += ny * overlap

        # Apply boost force in the direction away from bumper
        beyblade.vx = nx * self.boost_force
        beyblade.vy = ny * self.boost_force

        # Trigger hit animation
        self.hit_timer = 15

    def update(self):
        """Update bumper animation."""
        if self.hit_timer > 0:
            self.hit_timer -= 1

    def draw(self, screen: pygame.Surface):
        """Draw the bumper."""
        # Pulse effect when hit
        if self.hit_timer > 0:
            pulse = 1 + (self.hit_timer / 15) * 0.3
            draw_radius = int(self.radius * pulse)
            color = self.glow_color
        else:
            draw_radius = self.radius
            color = self.color

        # Outer glow/shadow
        pygame.draw.circle(screen, (40, 20, 10), (self.x + 3, self.y + 3), draw_radius + 5)

        # Main bumper body
        pygame.draw.circle(screen, color, (self.x, self.y), draw_radius)

        # Inner highlight
        pygame.draw.circle(screen, (255, 220, 180), (self.x - 5, self.y - 5), draw_radius // 3)

        # Outer ring
        pygame.draw.circle(screen, (200, 80, 40), (self.x, self.y), draw_radius, 3)


class ObeliskBumper:
    """2001-style monolith bumper - rectangular and black."""

    def __init__(self, x: int, y: int, width: int = 25, height: int = 70):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.hit_timer = 0
        self.color = (20, 20, 25)  # Almost black
        self.glow_color = (60, 60, 80)  # Subtle blue-gray glow when hit
        self.boost_force = 14  # Slightly stronger than regular bumpers
        # For collision purposes, use the larger dimension
        self.radius = max(width, height) // 2

    def check_collision(self, beyblade: Beyblade) -> bool:
        """Check if beyblade is colliding with this rectangular bumper."""
        # Use rectangle-circle collision
        half_w = self.width / 2
        half_h = self.height / 2

        # Find closest point on rectangle to circle center
        closest_x = max(self.x - half_w, min(beyblade.x, self.x + half_w))
        closest_y = max(self.y - half_h, min(beyblade.y, self.y + half_h))

        # Check distance from closest point to circle center
        dx = beyblade.x - closest_x
        dy = beyblade.y - closest_y
        dist = math.sqrt(dx**2 + dy**2)

        return dist < beyblade.radius

    def apply_bounce(self, beyblade: Beyblade):
        """Bounce the beyblade away from the obelisk."""
        half_w = self.width / 2
        half_h = self.height / 2

        # Find closest point on rectangle
        closest_x = max(self.x - half_w, min(beyblade.x, self.x + half_w))
        closest_y = max(self.y - half_h, min(beyblade.y, self.y + half_h))

        dx = beyblade.x - closest_x
        dy = beyblade.y - closest_y
        dist = math.sqrt(dx**2 + dy**2)

        if dist == 0:
            # Beyblade is inside, push out based on center
            dx = beyblade.x - self.x
            dy = beyblade.y - self.y
            dist = math.sqrt(dx**2 + dy**2)
            if dist == 0:
                dx, dy, dist = 1, 0, 1

        nx = dx / dist
        ny = dy / dist

        # Push beyblade outside
        overlap = beyblade.radius - dist + 2
        if overlap > 0:
            beyblade.x += nx * overlap
            beyblade.y += ny * overlap

        # Apply bounce force
        beyblade.vx = nx * self.boost_force
        beyblade.vy = ny * self.boost_force

        self.hit_timer = 15

    def update(self):
        """Update animation."""
        if self.hit_timer > 0:
            self.hit_timer -= 1

    def draw(self, screen: pygame.Surface):
        """Draw the obelisk - 2001 monolith style."""
        half_w = self.width / 2
        half_h = self.height / 2

        # Pulse effect when hit
        if self.hit_timer > 0:
            pulse = 1 + (self.hit_timer / 15) * 0.1
            draw_w = int(self.width * pulse)
            draw_h = int(self.height * pulse)
            color = self.glow_color
        else:
            draw_w = self.width
            draw_h = self.height
            color = self.color

        # Shadow
        shadow_rect = pygame.Rect(
            self.x - draw_w // 2 + 4,
            self.y - draw_h // 2 + 4,
            draw_w, draw_h
        )
        pygame.draw.rect(screen, (10, 10, 15), shadow_rect)

        # Main body
        main_rect = pygame.Rect(
            self.x - draw_w // 2,
            self.y - draw_h // 2,
            draw_w, draw_h
        )
        pygame.draw.rect(screen, color, main_rect)

        # Subtle edge highlight (left and top)
        pygame.draw.line(screen, (40, 40, 50),
                         (main_rect.left, main_rect.bottom),
                         (main_rect.left, main_rect.top), 2)
        pygame.draw.line(screen, (40, 40, 50),
                         (main_rect.left, main_rect.top),
                         (main_rect.right, main_rect.top), 2)

        # Outer border
        pygame.draw.rect(screen, (50, 50, 60), main_rect, 1)


class Arena:
    def __init__(self):
        self.center_x, self.center_y = ARENA_CENTER
        self.base_radius = ARENA_RADIUS
        self.radius = ARENA_RADIUS
        self.finals_mode = False
        self.bumpers: list[Bumper] = []

        # Rectangle dimensions for finals (calculated from radius)
        self._update_rect_dimensions()

    def _update_rect_dimensions(self):
        """Update rectangle dimensions based on current radius."""
        # Height matches circle diameter, width is 1.8x wider
        self.rect_height = self.radius * 2
        self.rect_width = int(self.rect_height * 1.8)
        self.rect_left = self.center_x - self.rect_width // 2
        self.rect_right = self.center_x + self.rect_width // 2
        self.rect_top = self.center_y - self.rect_height // 2
        self.rect_bottom = self.center_y + self.rect_height // 2

    def set_finals_mode(self, enabled: bool):
        """Enable or disable finals rectangle mode."""
        self.finals_mode = enabled
        if enabled:
            self._create_bumpers()
        else:
            self.bumpers.clear()

    def _create_bumpers(self):
        """Create pinball bumpers for finals arena."""
        self.bumpers.clear()

        # Calculate bumper positions based on arena dimensions
        cx, cy = self.center_x, self.center_y
        w = self.rect_width
        h = self.rect_height

        # Bumper radius scales with arena size
        bumper_r = max(25, min(40, h // 15))

        # Create a pinball-style layout:
        # - Two bumpers in upper area (left and right of center)
        # - Two bumpers in lower area (left and right of center)
        # - One bumper in the center

        spread_x = w * 0.25  # Horizontal spread from center
        spread_y = h * 0.25  # Vertical spread from center

        # Upper bumpers
        self.bumpers.append(Bumper(int(cx - spread_x), int(cy - spread_y), bumper_r))
        self.bumpers.append(Bumper(int(cx + spread_x), int(cy - spread_y), bumper_r))

        # Lower bumpers
        self.bumpers.append(Bumper(int(cx - spread_x), int(cy + spread_y), bumper_r))
        self.bumpers.append(Bumper(int(cx + spread_x), int(cy + spread_y), bumper_r))

    def update_center(self, window_width: int, window_height: int) -> tuple:
        """Update arena center and radius based on window size. Returns (dx, dy) offset."""
        old_center_x, old_center_y = self.center_x, self.center_y
        self.center_x = window_width // 2
        self.center_y = window_height // 2
        # Scale radius to fit window (use smaller dimension, leave margin)
        max_radius = min(window_width, window_height) // 2 - 80
        self.radius = max(200, max_radius)
        self._update_rect_dimensions()
        # Recreate bumpers if in finals mode
        if self.finals_mode:
            self._create_bumpers()
        return (self.center_x - old_center_x, self.center_y - old_center_y)

    def update(self):
        """Update arena state (bumper animations)."""
        for bumper in self.bumpers:
            bumper.update()

    def apply_boundary(self, beyblade: Beyblade) -> bool:
        """Apply arena boundary physics. Returns True if bumper was hit."""
        bumper_hit = False

        if self.finals_mode:
            self._apply_rectangle_boundary(beyblade)
            # Check bumper collisions
            for bumper in self.bumpers:
                if bumper.check_collision(beyblade):
                    bumper.apply_bounce(beyblade)
                    bumper_hit = True
        else:
            self._apply_circle_boundary(beyblade)

        return bumper_hit

    def _apply_circle_boundary(self, beyblade: Beyblade):
        """Circle arena - bowl shape with ring-out on all edges."""
        dx = beyblade.x - self.center_x
        dy = beyblade.y - self.center_y
        dist_from_center = math.sqrt(dx**2 + dy**2)

        if dist_from_center == 0:
            return

        # Normalize direction from center
        nx = dx / dist_from_center
        ny = dy / dist_from_center

        # Bowl physics: slope force toward center (Flash has 3x stronger pull)
        edge_proximity = dist_from_center / self.radius
        slope_mult = 3.0 if beyblade.ability == 'flash' else 1.0
        slope_force = ARENA_SLOPE_STRENGTH * (edge_proximity ** 1.5) * slope_mult

        beyblade.vx -= nx * slope_force
        beyblade.vy -= ny * slope_force

        # Tangential force for orbital motion
        if beyblade.speed > 0.5:
            tx = -ny
            ty = nx
            cross = beyblade.vx * ty - beyblade.vy * tx
            spin_dir = 1 if cross > 0 else -1
            tangent_force = 0.02 * edge_proximity * spin_dir
            beyblade.vx += tx * tangent_force
            beyblade.vy += ty * tangent_force

        # Ring-out (Luffy gets 2 saves, Amadeus survives while rival lives)
        if dist_from_center > self.radius:
            if beyblade.ability == 'luffy' and beyblade.luffy_edge_saves > 0:
                # Bounce back into arena
                beyblade.luffy_edge_saves -= 1
                beyblade.x = self.center_x + nx * (self.radius - beyblade.radius - 10)
                beyblade.y = self.center_y + ny * (self.radius - beyblade.radius - 10)
                # Reverse velocity and boost back in
                beyblade.vx = -nx * 10
                beyblade.vy = -ny * 10
            elif beyblade.ability == 'amadeus' and beyblade.amadeus_rival_alive:
                # Amadeus refuses to die while rival lives - bounce at 1hp
                beyblade.stamina = max(1, beyblade.stamina)
                beyblade.x = self.center_x + nx * (self.radius - beyblade.radius - 10)
                beyblade.y = self.center_y + ny * (self.radius - beyblade.radius - 10)
                beyblade.vx = -nx * 8
                beyblade.vy = -ny * 8
            else:
                beyblade.die()

    def _apply_rectangle_boundary(self, beyblade: Beyblade):
        """Rectangle arena - bounce on top/bottom, ring-out on left/right."""
        # Gravity toward center for more dynamic movement
        dx = beyblade.x - self.center_x
        dy = beyblade.y - self.center_y
        dist = math.sqrt(dx**2 + dy**2)
        if dist > 0:
            beyblade.vx -= (dx / dist) * 0.08
            beyblade.vy -= (dy / dist) * 0.08

        # Top wall bounce
        if beyblade.y - beyblade.radius < self.rect_top:
            beyblade.y = self.rect_top + beyblade.radius
            beyblade.vy = abs(beyblade.vy) * 0.8  # Bounce down

        # Bottom wall bounce
        if beyblade.y + beyblade.radius > self.rect_bottom:
            beyblade.y = self.rect_bottom - beyblade.radius
            beyblade.vy = -abs(beyblade.vy) * 0.8  # Bounce up

        # Left side ring-out (Luffy gets saves, Amadeus survives while rival lives)
        if beyblade.x < self.rect_left:
            if beyblade.ability == 'luffy' and beyblade.luffy_edge_saves > 0:
                beyblade.luffy_edge_saves -= 1
                beyblade.x = self.rect_left + beyblade.radius + 10
                beyblade.vx = abs(beyblade.vx) + 8  # Bounce right
            elif beyblade.ability == 'amadeus' and beyblade.amadeus_rival_alive:
                beyblade.stamina = max(1, beyblade.stamina)
                beyblade.x = self.rect_left + beyblade.radius + 10
                beyblade.vx = abs(beyblade.vx) + 6  # Bounce right
            else:
                beyblade.die()

        # Right side ring-out (Luffy gets saves, Amadeus survives while rival lives)
        if beyblade.x > self.rect_right:
            if beyblade.ability == 'luffy' and beyblade.luffy_edge_saves > 0:
                beyblade.luffy_edge_saves -= 1
                beyblade.x = self.rect_right - beyblade.radius - 10
                beyblade.vx = -abs(beyblade.vx) - 8  # Bounce left
            elif beyblade.ability == 'amadeus' and beyblade.amadeus_rival_alive:
                beyblade.stamina = max(1, beyblade.stamina)
                beyblade.x = self.rect_right - beyblade.radius - 10
                beyblade.vx = -abs(beyblade.vx) - 6  # Bounce left
            else:
                beyblade.die()

    def draw(self, screen: pygame.Surface):
        """Draw the arena."""
        if self.finals_mode:
            self._draw_rectangle(screen)
            # Draw bumpers on top of arena floor
            for bumper in self.bumpers:
                bumper.draw(screen)
        else:
            self._draw_circle(screen)

    def _draw_circle(self, screen: pygame.Surface):
        """Draw circular arena."""
        cx, cy = self.center_x, self.center_y

        # Outer rim shadow
        pygame.draw.circle(screen, DARK_GRAY, (cx + 5, cy + 5), self.radius + 15)

        # Outer rim
        pygame.draw.circle(screen, ARENA_RIM, (cx, cy), self.radius + 15)

        # Edge ring
        pygame.draw.circle(screen, ARENA_EDGE, (cx, cy), self.radius + 5)

        # Main floor
        pygame.draw.circle(screen, ARENA_FLOOR, (cx, cy), self.radius)

        # Floor detail rings
        for i in range(1, 6):
            ring_radius = self.radius * (i / 6)
            alpha = 30 + i * 5
            ring_color = tuple(min(255, c + alpha) for c in ARENA_FLOOR)
            pygame.draw.circle(screen, ring_color, (cx, cy), int(ring_radius), 1)

        # Center mark
        pygame.draw.circle(screen, ARENA_EDGE, (cx, cy), 20)
        pygame.draw.circle(screen, ARENA_RIM, (cx, cy), 10)

        # Highlight on rim
        highlight_rect = pygame.Rect(
            cx - self.radius - 10,
            cy - self.radius - 10,
            (self.radius + 10) * 2,
            (self.radius + 10) * 2
        )
        pygame.draw.arc(screen, WHITE, highlight_rect, math.radians(200), math.radians(340), 3)

    def _draw_rectangle(self, screen: pygame.Surface):
        """Draw rectangular finals arena."""
        # Main floor rect
        floor_rect = pygame.Rect(
            self.rect_left, self.rect_top,
            self.rect_width, self.rect_height
        )

        # Shadow
        shadow_rect = floor_rect.inflate(30, 30).move(5, 5)
        pygame.draw.rect(screen, DARK_GRAY, shadow_rect, border_radius=10)

        # Outer rim
        rim_rect = floor_rect.inflate(30, 30)
        pygame.draw.rect(screen, ARENA_RIM, rim_rect, border_radius=10)

        # Edge
        edge_rect = floor_rect.inflate(10, 10)
        pygame.draw.rect(screen, ARENA_EDGE, edge_rect, border_radius=5)

        # Main floor
        pygame.draw.rect(screen, ARENA_FLOOR, floor_rect, border_radius=3)

        # Floor detail lines (horizontal)
        for i in range(1, 6):
            y = self.rect_top + int(self.rect_height * (i / 6))
            alpha = 30 + i * 5
            line_color = tuple(min(255, c + alpha) for c in ARENA_FLOOR)
            pygame.draw.line(screen, line_color, (self.rect_left + 5, y), (self.rect_right - 5, y), 1)

        # Center line (vertical)
        pygame.draw.line(screen, ARENA_EDGE,
                         (self.center_x, self.rect_top + 10),
                         (self.center_x, self.rect_bottom - 10), 2)

        # Center mark
        pygame.draw.circle(screen, ARENA_EDGE, (self.center_x, self.center_y), 20)
        pygame.draw.circle(screen, ARENA_RIM, (self.center_x, self.center_y), 10)

        # Danger zones on left/right (red tint for elimination sides)
        danger_color = (80, 40, 40)
        danger_width = 30

        # Left danger zone
        left_danger = pygame.Rect(self.rect_left, self.rect_top, danger_width, self.rect_height)
        pygame.draw.rect(screen, danger_color, left_danger)

        # Right danger zone
        right_danger = pygame.Rect(self.rect_right - danger_width, self.rect_top, danger_width, self.rect_height)
        pygame.draw.rect(screen, danger_color, right_danger)

        # Wall indicators on top/bottom (highlighted to show they're walls)
        wall_color = (100, 100, 120)
        pygame.draw.line(screen, wall_color,
                         (self.rect_left, self.rect_top),
                         (self.rect_right, self.rect_top), 4)
        pygame.draw.line(screen, wall_color,
                         (self.rect_left, self.rect_bottom),
                         (self.rect_right, self.rect_bottom), 4)

        # "FINALS" text in center
        font = pygame.font.Font(None, 36)
        text = font.render("FINALS", True, (80, 80, 100))
        text_rect = text.get_rect(center=(self.center_x, self.center_y + 50))
        screen.blit(text, text_rect)

    def get_spawn_positions(self, count: int) -> list:
        """Generate spawn positions."""
        if self.finals_mode:
            return self._get_rectangle_spawns(count)
        else:
            return self._get_circle_spawns(count)

    def _get_circle_spawns(self, count: int) -> list:
        """Spawn positions for circular arena."""
        spawns = []
        spawn_radius = self.radius * 0.6

        for i in range(count):
            angle = (2 * math.pi * i / count) + (math.pi / 4)
            dist = spawn_radius * (0.5 + 0.5 * ((i % 3) / 2))
            x = self.center_x + math.cos(angle) * dist
            y = self.center_y + math.sin(angle) * dist

            speed = 8 + (i % 4) * 1.5
            # Mix of tangential and inward velocity (60% tangent, 40% toward center)
            tangent_x = -math.sin(angle)
            tangent_y = math.cos(angle)
            inward_x = -math.cos(angle)
            inward_y = -math.sin(angle)
            vx = (tangent_x * 0.6 + inward_x * 0.4) * speed
            vy = (tangent_y * 0.6 + inward_y * 0.4) * speed

            spawns.append((x, y, vx, vy))

        return spawns

    def _get_rectangle_spawns(self, count: int) -> list:
        """Spawn positions for rectangle arena - spread across the field."""
        spawns = []

        # Spawn in two columns, left and right of center
        left_x = self.center_x - self.rect_width * 0.25
        right_x = self.center_x + self.rect_width * 0.25

        for i in range(count):
            # Alternate between left and right sides
            if i % 2 == 0:
                x = left_x + (i % 4) * 20
                vx = 7 + (i % 3) * 2  # Moving right
            else:
                x = right_x - (i % 4) * 20
                vx = -(7 + (i % 3) * 2)  # Moving left

            # Distribute vertically
            y_offset = ((i // 2) - (count // 4)) * 60
            y = self.center_y + y_offset
            # Keep within bounds
            y = max(self.rect_top + 50, min(self.rect_bottom - 50, y))

            vy = ((i % 5) - 2) * 3  # Some vertical variation

            spawns.append((x, y, vx, vy))

        return spawns

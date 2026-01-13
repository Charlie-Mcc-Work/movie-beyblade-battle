import pygame
import random
import math
from enum import Enum, auto
from .constants import AVATAR_DISTANCE_FROM_ARENA, AVATAR_ELIMINATED_DIM


class AvatarState(Enum):
    IDLE = auto()
    LAUNCHING = auto()
    CHEERING = auto()
    ELIMINATED = auto()
    VICTORY = auto()


class AvatarTraits:
    """Defines the unique visual characteristics of a stick figure."""

    HEAD_SHAPES = ['circle', 'oval_tall', 'oval_wide', 'square', 'triangle']
    ACCESSORIES = [
        None, 'hat', 'cap', 'bow', 'antenna', 'horns', 'halo', 'headphones'
    ]

    def __init__(self, color: tuple, seed: int = None):
        if seed is not None:
            rng = random.Random(seed)
        else:
            rng = random.Random()

        self.color = color
        self.head_shape = rng.choice(self.HEAD_SHAPES)
        self.accessory = rng.choice(self.ACCESSORIES)

        # Body proportions (multipliers)
        self.head_size = rng.uniform(0.8, 1.2)
        self.body_length = rng.uniform(0.85, 1.15)
        self.arm_length = rng.uniform(0.8, 1.2)
        self.leg_length = rng.uniform(0.85, 1.15)
        self.thickness = rng.randint(2, 4)
        self.leg_spread = rng.uniform(0.8, 1.2)


class Avatar:
    """A stick figure avatar linked to a beyblade."""

    BASE_HEAD_RADIUS = 12
    BASE_BODY_LENGTH = 30
    BASE_ARM_LENGTH = 22
    BASE_LEG_LENGTH = 24

    def __init__(self, beyblade_name: str, color: tuple, index: int, total_count: int):
        self.beyblade_name = beyblade_name
        self.index = index
        self.total_count = total_count

        # Generate unique traits using name hash as seed
        seed = hash(beyblade_name) & 0xFFFFFFFF
        self.traits = AvatarTraits(color, seed)

        # Position
        self.x = 0
        self.y = 0
        self.base_y = 0  # For bounce animations
        self.angle = 0  # Facing direction

        # Animation state
        self.state = AvatarState.IDLE
        self.anim_timer = 0
        self.launch_progress = 0.0
        self.cheer_phase = random.uniform(0, 2 * math.pi)
        self.victory_intensity = 0.0
        self.elim_transition = 0.0

    def update_position(self, arena_cx: int, arena_cy: int, arena_radius: int):
        """Calculate position around arena perimeter."""
        angle = (2 * math.pi * self.index / self.total_count) - (math.pi / 2)
        distance = arena_radius + AVATAR_DISTANCE_FROM_ARENA

        self.x = arena_cx + math.cos(angle) * distance
        self.base_y = arena_cy + math.sin(angle) * distance
        self.y = self.base_y
        self.angle = angle + math.pi  # Face toward center

    def set_state(self, new_state: AvatarState):
        """Change animation state."""
        if new_state != self.state:
            self.state = new_state
            self.anim_timer = 0
            if new_state == AvatarState.LAUNCHING:
                self.launch_progress = 0.0
            elif new_state == AvatarState.VICTORY:
                self.victory_intensity = 0.0
            elif new_state == AvatarState.ELIMINATED:
                self.elim_transition = 0.0

    def update(self, dt: float = 1.0):
        """Update animation state."""
        self.anim_timer += dt

        if self.state == AvatarState.LAUNCHING:
            self.launch_progress = min(1.0, self.launch_progress + 0.025 * dt)
            if self.launch_progress >= 1.0:
                self.set_state(AvatarState.CHEERING)

        elif self.state == AvatarState.CHEERING:
            # Bounce effect
            t = self.anim_timer + self.cheer_phase
            self.y = self.base_y + math.sin(t * 0.25) * 3

        elif self.state == AvatarState.ELIMINATED:
            self.elim_transition = min(1.0, self.elim_transition + 0.05 * dt)

        elif self.state == AvatarState.VICTORY:
            self.victory_intensity = min(1.0, self.victory_intensity + 0.03 * dt)
            # Jump effect
            t = self.anim_timer
            jump_cycle = (t * 0.4) % (2 * math.pi)
            if jump_cycle < math.pi:
                self.y = self.base_y - math.sin(jump_cycle) * 15 * self.victory_intensity
            else:
                self.y = self.base_y

    def draw(self, screen: pygame.Surface):
        """Draw the avatar."""
        # Calculate dimensions with traits
        head_r = int(self.BASE_HEAD_RADIUS * self.traits.head_size)
        body_len = int(self.BASE_BODY_LENGTH * self.traits.body_length)
        arm_len = int(self.BASE_ARM_LENGTH * self.traits.arm_length)
        leg_len = int(self.BASE_LEG_LENGTH * self.traits.leg_length)
        thick = self.traits.thickness

        # Get color (dim if eliminated)
        if self.state == AvatarState.ELIMINATED:
            dim = AVATAR_ELIMINATED_DIM + (1 - AVATAR_ELIMINATED_DIM) * (1 - self.elim_transition)
            color = tuple(int(c * dim) for c in self.traits.color)
        else:
            color = self.traits.color

        # Calculate body positions
        head_offset, left_arm, right_arm, left_leg, right_leg = self._get_pose()

        # Head position (adjusted for animation)
        head_x = int(self.x)
        head_y = int(self.y - body_len - head_r + head_offset)

        # Shoulder position
        shoulder_x = int(self.x)
        shoulder_y = int(self.y - body_len + head_offset * 0.5)

        # Hip position
        hip_x = int(self.x)
        hip_y = int(self.y)

        # Draw legs
        self._draw_legs(screen, hip_x, hip_y, left_leg, right_leg, leg_len, thick, color)

        # Draw body
        pygame.draw.line(screen, color, (shoulder_x, shoulder_y), (hip_x, hip_y), thick)

        # Draw arms
        self._draw_arms(screen, shoulder_x, shoulder_y, left_arm, right_arm, arm_len, thick, color)

        # Draw head
        self._draw_head(screen, head_x, head_y, head_r, thick, color)

        # Draw accessory
        self._draw_accessory(screen, head_x, head_y, head_r, color)

    def _get_pose(self) -> tuple:
        """Get pose based on current animation state."""
        # Default pose
        head_offset = 0
        left_arm = math.pi * 0.6  # Down-left
        right_arm = math.pi * 0.4  # Down-right
        left_leg = math.pi * 0.55
        right_leg = math.pi * 0.45

        if self.state == AvatarState.LAUNCHING:
            head_offset, left_arm, right_arm = self._get_launch_pose()

        elif self.state == AvatarState.CHEERING:
            head_offset, left_arm, right_arm = self._get_cheer_pose()

        elif self.state == AvatarState.ELIMINATED:
            head_offset, left_arm, right_arm = self._get_dejected_pose()

        elif self.state == AvatarState.VICTORY:
            head_offset, left_arm, right_arm, left_leg, right_leg = self._get_victory_pose()

        return head_offset, left_arm, right_arm, left_leg, right_leg

    def _get_launch_pose(self) -> tuple:
        """Arms spin like pulling a ripcord."""
        p = self.launch_progress

        # Arm rotation during pull
        spin = p * 6 * math.pi  # 3 full rotations

        # Head bob
        head_offset = math.sin(p * math.pi) * 5

        # Arms spin in opposite directions
        left_arm = spin + math.pi * 0.5
        right_arm = -spin + math.pi * 0.5

        return head_offset, left_arm, right_arm

    def _get_cheer_pose(self) -> tuple:
        """Arms pump up and down."""
        t = self.anim_timer + self.cheer_phase

        # Head stays still
        head_offset = 0

        # Arms wave
        wave = math.sin(t * 0.4) * 0.4
        left_arm = -math.pi * 0.3 + wave  # Upper left
        right_arm = -math.pi * 0.7 - wave  # Upper right

        return head_offset, left_arm, right_arm

    def _get_dejected_pose(self) -> tuple:
        """Head down, arms drooping."""
        t = self.elim_transition

        # Head droops
        head_offset = 8 * t

        # Arms hang limp
        left_arm = math.pi * 0.55 + t * 0.15
        right_arm = math.pi * 0.45 - t * 0.15

        return head_offset, left_arm, right_arm

    def _get_victory_pose(self) -> tuple:
        """Big celebration."""
        t = self.anim_timer
        intensity = self.victory_intensity

        # Head bob with jump
        head_offset = -3 * intensity

        # Arms thrust up
        pump = math.sin(t * 0.6) * 0.2 * intensity
        left_arm = -math.pi * 0.15 + pump
        right_arm = -math.pi * 0.85 - pump

        # Legs spread on landing
        jump_cycle = (t * 0.4) % (2 * math.pi)
        if jump_cycle >= math.pi:
            spread = 0.15 * intensity
        else:
            spread = 0

        left_leg = math.pi * 0.5 + spread
        right_leg = math.pi * 0.5 - spread

        return head_offset, left_arm, right_arm, left_leg, right_leg

    def _draw_head(self, screen: pygame.Surface, x: int, y: int, radius: int, thickness: int, color: tuple):
        """Draw head based on shape trait."""
        shape = self.traits.head_shape

        if shape == 'circle':
            pygame.draw.circle(screen, color, (x, y), radius, thickness)
        elif shape == 'oval_tall':
            rect = pygame.Rect(x - radius, y - int(radius * 1.3), radius * 2, int(radius * 2.6))
            pygame.draw.ellipse(screen, color, rect, thickness)
        elif shape == 'oval_wide':
            rect = pygame.Rect(x - int(radius * 1.3), y - radius, int(radius * 2.6), radius * 2)
            pygame.draw.ellipse(screen, color, rect, thickness)
        elif shape == 'square':
            rect = pygame.Rect(x - radius, y - radius, radius * 2, radius * 2)
            pygame.draw.rect(screen, color, rect, thickness)
        elif shape == 'triangle':
            points = [
                (x, y - radius),
                (x - radius, y + radius),
                (x + radius, y + radius)
            ]
            pygame.draw.polygon(screen, color, points, thickness)

    def _draw_accessory(self, screen: pygame.Surface, x: int, y: int, head_r: int, color: tuple):
        """Draw accessory on head."""
        acc = self.traits.accessory
        if acc is None:
            return

        if acc == 'hat':
            pygame.draw.rect(screen, color, (x - head_r + 2, y - head_r - 10, (head_r - 2) * 2, 10), 2)
            pygame.draw.line(screen, color, (x - head_r - 2, y - head_r), (x + head_r + 2, y - head_r), 2)
        elif acc == 'cap':
            pygame.draw.line(screen, color, (x - head_r, y - head_r + 2), (x + head_r + 6, y - head_r + 4), 3)
        elif acc == 'bow':
            pygame.draw.circle(screen, color, (x, y - head_r - 2), 3, 2)
            pygame.draw.line(screen, color, (x - 6, y - head_r - 2), (x - 2, y - head_r - 2), 2)
            pygame.draw.line(screen, color, (x + 2, y - head_r - 2), (x + 6, y - head_r - 2), 2)
        elif acc == 'antenna':
            pygame.draw.line(screen, color, (x, y - head_r), (x, y - head_r - 12), 2)
            pygame.draw.circle(screen, color, (x, y - head_r - 12), 3)
        elif acc == 'horns':
            pygame.draw.line(screen, color, (x - 5, y - head_r + 2), (x - 8, y - head_r - 8), 2)
            pygame.draw.line(screen, color, (x + 5, y - head_r + 2), (x + 8, y - head_r - 8), 2)
        elif acc == 'halo':
            pygame.draw.ellipse(screen, (255, 255, 150), (x - 10, y - head_r - 10, 20, 6), 2)
        elif acc == 'headphones':
            pygame.draw.arc(screen, color, (x - head_r - 1, y - head_r - 3, head_r * 2 + 2, head_r),
                            math.pi, 2 * math.pi, 2)
            pygame.draw.circle(screen, color, (x - head_r, y), 4, 2)
            pygame.draw.circle(screen, color, (x + head_r, y), 4, 2)

    def _draw_arms(self, screen: pygame.Surface, sx: int, sy: int,
                   left_angle: float, right_angle: float, arm_len: int, thickness: int, color: tuple):
        """Draw both arms."""
        left_end = (
            int(sx + math.cos(left_angle) * arm_len),
            int(sy + math.sin(left_angle) * arm_len)
        )
        right_end = (
            int(sx + math.cos(right_angle) * arm_len),
            int(sy + math.sin(right_angle) * arm_len)
        )

        pygame.draw.line(screen, color, (sx, sy), left_end, thickness)
        pygame.draw.line(screen, color, (sx, sy), right_end, thickness)

    def _draw_legs(self, screen: pygame.Surface, hx: int, hy: int,
                   left_angle: float, right_angle: float, leg_len: int, thickness: int, color: tuple):
        """Draw both legs."""
        spread = self.traits.leg_spread

        left_end = (
            int(hx + math.cos(left_angle) * leg_len * spread),
            int(hy + math.sin(left_angle) * leg_len)
        )
        right_end = (
            int(hx + math.cos(right_angle) * leg_len * spread),
            int(hy + math.sin(right_angle) * leg_len)
        )

        pygame.draw.line(screen, color, (hx, hy), left_end, thickness)
        pygame.draw.line(screen, color, (hx, hy), right_end, thickness)


class AvatarManager:
    """Manages all avatars for a battle."""

    def __init__(self):
        self.avatars: dict[str, Avatar] = {}

    def create_avatars(self, beyblades: list, arena):
        """Create avatars for all beyblades."""
        self.avatars.clear()

        for i, beyblade in enumerate(beyblades):
            avatar = Avatar(
                beyblade_name=beyblade.name,
                color=beyblade.color,
                index=i,
                total_count=len(beyblades)
            )
            avatar.update_position(arena.center_x, arena.center_y, arena.radius)
            avatar.set_state(AvatarState.LAUNCHING)
            self.avatars[beyblade.name] = avatar

    def update_positions(self, arena):
        """Update all avatar positions (for window resize)."""
        for avatar in self.avatars.values():
            avatar.update_position(arena.center_x, arena.center_y, arena.radius)

    def sync_with_beyblades(self, beyblades: list, winner_name: str = None):
        """Update avatar states based on beyblade status."""
        for beyblade in beyblades:
            if beyblade.name in self.avatars:
                avatar = self.avatars[beyblade.name]

                if winner_name and beyblade.name == winner_name:
                    avatar.set_state(AvatarState.VICTORY)
                elif not beyblade.alive:
                    avatar.set_state(AvatarState.ELIMINATED)
                elif avatar.state not in (AvatarState.LAUNCHING,):
                    avatar.set_state(AvatarState.CHEERING)

    def update(self, dt: float = 1.0):
        """Update all avatar animations."""
        for avatar in self.avatars.values():
            avatar.update(dt)

    def draw(self, screen: pygame.Surface):
        """Draw all avatars."""
        # Draw eliminated first (behind)
        for avatar in self.avatars.values():
            if avatar.state == AvatarState.ELIMINATED:
                avatar.draw(screen)

        # Draw active avatars
        for avatar in self.avatars.values():
            if avatar.state not in (AvatarState.ELIMINATED, AvatarState.VICTORY):
                avatar.draw(screen)

        # Draw victory avatar last (on top)
        for avatar in self.avatars.values():
            if avatar.state == AvatarState.VICTORY:
                avatar.draw(screen)

    def clear(self):
        """Remove all avatars."""
        self.avatars.clear()

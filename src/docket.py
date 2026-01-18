import pygame
import math
import random
from .constants import (
    DOCKET_GOLDEN, DOCKET_GOLDEN_DARK,
    DOCKET_DIAMOND, DOCKET_DIAMOND_DARK,
    DOCKET_SHIT, DOCKET_SHIT_DARK,
    DOCKET_UPGRADE_SLIVER,
    DOCKET_SPIN_MIN, DOCKET_SPIN_MAX,
    DOCKET_FRICTION, DOCKET_FLAP_DRAG, DOCKET_STOP_THRESHOLD,
    DOCKET_PEG_COUNT,
    UI_TEXT, UI_TEXT_DIM, UI_BG, UI_PANEL,
    GOLDEN_SEGMENT_COLORS, DIAMOND_SEGMENT_COLORS, SHIT_SEGMENT_COLORS
)


class DocketWheel:
    """Spinning wheel for the docket system with nested tiers."""

    GOLDEN = 'golden'
    DIAMOND = 'diamond'
    SHIT = 'shit'
    FINAL = 'final'

    def __init__(self, entries, docket_type, fonts, center, radius, sound_manager=None, next_tier_entries=None):
        """
        entries: list of (name, movie) tuples for participants
        docket_type: 'golden', 'diamond', or 'shit'
        fonts: dict of pygame fonts
        center: (x, y) center of wheel
        radius: radius of the wheel
        sound_manager: optional SoundManager for playing wheel sounds
        next_tier_entries: optional list of entries for the next tier (for preview)
        """
        self.entries = entries
        self.docket_type = docket_type
        self.fonts = fonts
        self.center = center
        self.radius = radius
        self.sound_manager = sound_manager
        self.next_tier_entries = next_tier_entries

        self.angular_velocity = 0
        self.angle = random.uniform(0, 2 * math.pi)  # Current rotation
        self.spinning = False
        self.stopped = False

        # Flap animation
        self.flap_angle = 0  # Current flap deflection
        self.flap_velocity = 0
        self.last_peg_index = -1

        # Build segments
        self._build_segments()

        # Colors based on docket type
        self.colors = self._get_colors()

    def _get_colors(self):
        """Get color scheme based on docket type."""
        if self.docket_type == self.GOLDEN:
            return {
                'primary': DOCKET_GOLDEN,
                'dark': DOCKET_GOLDEN_DARK,
                'next_primary': DOCKET_DIAMOND,
                'next_dark': DOCKET_DIAMOND_DARK,
                'segments': GOLDEN_SEGMENT_COLORS,
                'next_segments': DIAMOND_SEGMENT_COLORS,
            }
        elif self.docket_type == self.DIAMOND:
            return {
                'primary': DOCKET_DIAMOND,
                'dark': DOCKET_DIAMOND_DARK,
                'next_primary': DOCKET_SHIT,
                'next_dark': DOCKET_SHIT_DARK,
                'segments': DIAMOND_SEGMENT_COLORS,
                'next_segments': SHIT_SEGMENT_COLORS,
            }
        elif self.docket_type == self.SHIT:
            return {
                'primary': DOCKET_SHIT,
                'dark': DOCKET_SHIT_DARK,
                'next_primary': (255, 200, 50),  # Gold for final wheel center
                'next_dark': (180, 140, 30),
                'segments': SHIT_SEGMENT_COLORS,
                'next_segments': None,  # Final uses generated colors
            }
        else:  # final
            # Generate basic colors for final wheel (like original beyblade colors)
            basic_colors = [
                (255, 87, 87),    # Red
                (87, 167, 255),   # Blue
                (87, 255, 137),   # Green
                (255, 215, 87),   # Gold
                (215, 87, 255),   # Purple
                (255, 147, 87),   # Orange
                (87, 255, 255),   # Cyan
                (255, 87, 200),   # Pink
                (167, 255, 87),   # Lime
                (255, 167, 167),  # Light red
                (167, 200, 255),  # Light blue
                (200, 167, 255),  # Lavender
            ]
            return {
                'primary': (255, 200, 50),  # Gold
                'dark': (180, 140, 30),
                'next_primary': None,
                'next_dark': None,
                'segments': basic_colors,
                'next_segments': None,
            }

    def _build_segments(self):
        """Build wheel segments with entries and upgrade slivers."""
        self.segments = []
        self.sliver_percents = []  # Store for reference

        n_entries = len(self.entries)
        if n_entries == 0:
            return

        # Final wheel has no slivers - just entries
        if self.docket_type == self.FINAL:
            entry_percent = 1.0 / n_entries
            current_angle = 0
            for i in range(n_entries):
                angle_size = entry_percent * 2 * math.pi
                self.segments.append({
                    'type': 'entry',
                    'start_angle': current_angle,
                    'end_angle': current_angle + angle_size,
                    'entry': self.entries[i],
                    'color_index': i,
                })
                current_angle += angle_size
            return

        # Shit wheel has only ONE 1% sliver (sparkling gold)
        if self.docket_type == self.SHIT:
            self.sliver_percents = [0.01]  # Single 1% sliver
            total_upgrade = 0.01
            entry_percent = (1.0 - total_upgrade) / n_entries
            current_angle = 0

            # Place the single sliver after a random entry
            sliver_after_index = random.randint(0, n_entries - 1)

            for i in range(n_entries):
                # Add entry segment
                angle_size = entry_percent * 2 * math.pi
                self.segments.append({
                    'type': 'entry',
                    'start_angle': current_angle,
                    'end_angle': current_angle + angle_size,
                    'entry': self.entries[i],
                    'color_index': i,
                })
                current_angle += angle_size

                # Add the single sliver after the chosen entry
                if i == sliver_after_index:
                    sliver_angle = 0.01 * 2 * math.pi
                    self.segments.append({
                        'type': 'upgrade',
                        'start_angle': current_angle,
                        'end_angle': current_angle + sliver_angle,
                    })
                    current_angle += sliver_angle
            return

        # Golden and Diamond: One upgrade sliver after each entry, with random size
        # Min: 1%, Max: 40/n_slivers % (so with 5 slivers, max is 8% each)
        n_slivers = n_entries
        min_sliver = 0.01  # 1%
        max_sliver = 0.4 / n_slivers  # 40/n %

        # Generate random size for each sliver
        for _ in range(n_slivers):
            sliver_pct = random.uniform(min_sliver, max_sliver)
            self.sliver_percents.append(sliver_pct)

        total_upgrade = sum(self.sliver_percents)

        # Distribute remaining space among entries
        remaining = 1.0 - total_upgrade
        if remaining < 0.1:
            # If slivers took too much space, scale them down
            scale = (1.0 - 0.1 * n_entries) / total_upgrade
            self.sliver_percents = [p * scale for p in self.sliver_percents]
            total_upgrade = sum(self.sliver_percents)
            remaining = 1.0 - total_upgrade

        entry_percent = remaining / n_entries

        current_angle = 0

        # Add entry followed by sliver for each participant
        for i in range(n_entries):
            # Add entry segment
            angle_size = entry_percent * 2 * math.pi
            self.segments.append({
                'type': 'entry',
                'start_angle': current_angle,
                'end_angle': current_angle + angle_size,
                'entry': self.entries[i],
                'color_index': i,
            })
            current_angle += angle_size

            # Add sliver after this entry with its random size
            sliver_angle = self.sliver_percents[i] * 2 * math.pi
            self.segments.append({
                'type': 'upgrade',
                'start_angle': current_angle,
                'end_angle': current_angle + sliver_angle,
            })
            current_angle += sliver_angle

    def spin(self):
        """Start the wheel spinning."""
        # Randomize starting position each spin for more unpredictable results
        self.angle = random.uniform(0, 2 * math.pi)
        # Add more variability to spin speed - wider range and random multiplier
        base_velocity = random.uniform(DOCKET_SPIN_MIN, DOCKET_SPIN_MAX)
        velocity_multiplier = random.uniform(0.8, 1.3)  # Additional 20% variance either way
        self.angular_velocity = base_velocity * velocity_multiplier
        self.spinning = True
        self.stopped = False
        if self.sound_manager:
            self.sound_manager.play('wheel_spin')

    def update(self):
        """Update wheel physics each frame."""
        if not self.spinning:
            return

        # Apply friction
        self.angular_velocity *= DOCKET_FRICTION

        # Check for peg hits (flap resistance)
        peg_angle = 2 * math.pi / DOCKET_PEG_COUNT
        current_peg = int(self.angle / peg_angle) % DOCKET_PEG_COUNT

        if current_peg != self.last_peg_index and self.angular_velocity > 0.5:
            # Hit a peg - add drag and flap animation
            self.angular_velocity -= DOCKET_FLAP_DRAG * self.angular_velocity
            self.flap_velocity = min(0.5, self.angular_velocity * 0.1)
            self.last_peg_index = current_peg
            if self.sound_manager:
                self.sound_manager.play('wheel_tick')

        # Update flap animation (spring back)
        self.flap_angle += self.flap_velocity
        self.flap_velocity *= 0.85  # Damping
        self.flap_angle *= 0.9  # Return to center

        # Update wheel angle
        self.angle += self.angular_velocity * (1/60)  # Assuming 60 FPS
        self.angle = self.angle % (2 * math.pi)

        # Check if stopped
        if self.angular_velocity < DOCKET_STOP_THRESHOLD:
            self.angular_velocity = 0
            self.spinning = False
            self.stopped = True
            if self.sound_manager:
                self.sound_manager.play('wheel_stop')

    def force_upgrade(self):
        """Force the wheel to land on an upgrade sliver (debug function)."""
        # Find first upgrade segment
        for segment in self.segments:
            if segment['type'] == 'upgrade':
                # Calculate angle to land on middle of this sliver
                mid_pointer = (segment['start_angle'] + segment['end_angle']) / 2
                # pointer_angle = (3π/2 - angle) % 2π, so angle = (3π/2 - pointer_angle) % 2π
                self.angle = (3 * math.pi / 2 - mid_pointer) % (2 * math.pi)
                self.angular_velocity = 0
                self.spinning = False
                self.stopped = True
                if self.sound_manager:
                    self.sound_manager.play('wheel_stop')
                return

    def get_result(self):
        """Get the result when wheel has stopped. Returns (type, data)."""
        if not self.stopped:
            return None

        # The pointer is at the top (angle 0 points right, so top is -pi/2)
        # We need to find which segment is at the pointer position
        # Pointer is at top, wheel rotates clockwise
        pointer_angle = (3 * math.pi / 2 - self.angle) % (2 * math.pi)

        for segment in self.segments:
            start = segment['start_angle']
            end = segment['end_angle']
            if start <= pointer_angle < end:
                if segment['type'] == 'upgrade':
                    return ('upgrade', None)
                else:
                    return ('entry', segment['entry'])

        # Fallback to first entry
        if self.segments:
            for seg in self.segments:
                if seg['type'] == 'entry':
                    return ('entry', seg['entry'])
        return None

    def draw(self, screen, scale=1.0, show_next_tier=True):
        """Draw the wheel with optional scaling for zoom effect."""
        cx, cy = self.center
        r = int(self.radius * scale)

        # Draw outer ring
        pygame.draw.circle(screen, self.colors['dark'], (cx, cy), r + 8)
        pygame.draw.circle(screen, self.colors['primary'], (cx, cy), r + 4)

        # Draw segments with themed colors
        segment_colors = self.colors['segments']
        for segment in self.segments:
            start = segment['start_angle'] + self.angle
            end = segment['end_angle'] + self.angle

            if segment['type'] == 'upgrade':
                if self.docket_type == self.SHIT:
                    # Solid gold sliver for shit wheel
                    color = (255, 215, 50)
                else:
                    color = DOCKET_UPGRADE_SLIVER
            else:
                # Use themed segment colors
                idx = segment['color_index'] % len(segment_colors)
                color = segment_colors[idx]

            self._draw_segment(screen, cx, cy, r, start, end, color)

        # Draw extra sparkle effect on shit wheel's gold sliver
        if self.docket_type == self.SHIT:
            for segment in self.segments:
                if segment['type'] == 'upgrade':
                    mid_angle = (segment['start_angle'] + segment['end_angle']) / 2 + self.angle
                    # Draw stationary sparkle particles that blink
                    t = pygame.time.get_ticks() * 0.008
                    for i in range(3):
                        # Fixed positions along the sliver (inner, middle, outer)
                        sparkle_r = r * (0.5 + i * 0.2)
                        sx = cx + int(sparkle_r * math.cos(mid_angle))
                        sy = cy + int(sparkle_r * math.sin(mid_angle))
                        # Blinking size effect (staggered timing for each particle)
                        blink = abs(math.sin(t * 4 + i * 2.1))
                        if blink > 0.3:  # Only draw when "on"
                            size = 2 + int(blink * 3)
                            pygame.draw.circle(screen, (255, 255, 200), (sx, sy), size)

        # Draw themed decorations
        self._draw_decorations(screen, cx, cy, r)

        # Draw segment dividers (pegs)
        for i in range(len(self.segments)):
            seg = self.segments[i]
            angle = seg['start_angle'] + self.angle
            x1 = cx + int((r - 20) * math.cos(angle))
            y1 = cy + int((r - 20) * math.sin(angle))
            x2 = cx + int(r * math.cos(angle))
            y2 = cy + int(r * math.sin(angle))
            pygame.draw.line(screen, UI_BG, (x1, y1), (x2, y2), 3)

        # Draw pegs around the edge
        for i in range(DOCKET_PEG_COUNT):
            peg_angle = i * 2 * math.pi / DOCKET_PEG_COUNT + self.angle
            px = cx + int((r + 2) * math.cos(peg_angle))
            py = cy + int((r + 2) * math.sin(peg_angle))
            pygame.draw.circle(screen, self.colors['dark'], (px, py), 4)

        # Draw center circle with next tier preview
        center_radius = int(r * 0.25)
        if show_next_tier and self.colors['next_primary'] and self.next_tier_entries:
            # Draw mini preview wheel with actual segments
            self._draw_mini_wheel(screen, cx, cy, center_radius)
        elif show_next_tier and self.colors['next_primary']:
            pygame.draw.circle(screen, self.colors['next_dark'], (cx, cy), center_radius + 3)
            pygame.draw.circle(screen, self.colors['next_primary'], (cx, cy), center_radius)
            # Label for next tier
            next_label = "DIAMOND" if self.docket_type == self.GOLDEN else "SHIT"
            font = self.fonts['tiny']
            text = font.render(next_label, True, UI_BG)
            text_rect = text.get_rect(center=(cx, cy))
            screen.blit(text, text_rect)
        else:
            pygame.draw.circle(screen, self.colors['dark'], (cx, cy), center_radius + 3)
            pygame.draw.circle(screen, self.colors['primary'], (cx, cy), center_radius)

        # Draw text labels on segments
        self._draw_labels(screen, cx, cy, r, scale)

        # Draw pointer/flap at top
        self._draw_flap(screen, cx, cy - r - 15, scale)

    def _draw_segment(self, screen, cx, cy, r, start_angle, end_angle, color):
        """Draw a pie segment."""
        # Create points for polygon
        points = [(cx, cy)]
        steps = max(3, int((end_angle - start_angle) * 20))
        for i in range(steps + 1):
            angle = start_angle + (end_angle - start_angle) * i / steps
            x = cx + int(r * math.cos(angle))
            y = cy + int(r * math.sin(angle))
            points.append((x, y))

        if len(points) > 2:
            pygame.draw.polygon(screen, color, points)

    def _draw_mini_wheel(self, screen, cx, cy, radius):
        """Draw a mini preview of the next tier wheel in the center."""
        if not self.next_tier_entries:
            return

        # Determine next tier colors and type
        next_segment_colors = self.colors.get('next_segments')
        next_type = None
        if self.docket_type == self.GOLDEN:
            next_colors = {'primary': DOCKET_DIAMOND, 'dark': DOCKET_DIAMOND_DARK}
            next_type = self.DIAMOND
            if not next_segment_colors:
                next_segment_colors = DIAMOND_SEGMENT_COLORS
        elif self.docket_type == self.DIAMOND:
            next_colors = {'primary': DOCKET_SHIT, 'dark': DOCKET_SHIT_DARK}
            next_type = self.SHIT
            if not next_segment_colors:
                next_segment_colors = SHIT_SEGMENT_COLORS
        else:
            return  # No preview for shit->final or final

        # Draw outer ring
        pygame.draw.circle(screen, next_colors['dark'], (cx, cy), radius + 2)

        # Calculate segments for next tier
        n_entries = len(self.next_tier_entries)
        if n_entries == 0:
            pygame.draw.circle(screen, next_colors['primary'], (cx, cy), radius)
            return

        # Shit wheel preview: only ONE 1% sliver
        if next_type == self.SHIT:
            total_upgrade = 0.01
            entry_percent = (1.0 - total_upgrade) / n_entries
            current_angle = 0

            # Place the single sliver after a deterministic entry (based on count)
            sliver_after_index = n_entries // 2

            for i in range(n_entries):
                angle_size = entry_percent * 2 * math.pi
                idx = i % len(next_segment_colors)
                color = next_segment_colors[idx]
                self._draw_segment(screen, cx, cy, radius, current_angle, current_angle + angle_size, color)
                current_angle += angle_size

                if i == sliver_after_index:
                    sliver_angle = 0.01 * 2 * math.pi
                    # Solid gold for shit wheel sliver preview
                    gold_color = (255, 215, 50)
                    self._draw_segment(screen, cx, cy, radius, current_angle, current_angle + sliver_angle, gold_color)
                    current_angle += sliver_angle
        else:
            # Golden/Diamond: Generate random sliver sizes
            preview_random = random.Random(len(self.next_tier_entries) * 17 + 42)
            n_slivers = n_entries
            min_sliver = 0.01
            max_sliver = 0.4 / n_slivers  # 40/n %

            sliver_percents = [preview_random.uniform(min_sliver, max_sliver) for _ in range(n_slivers)]
            total_upgrade = sum(sliver_percents)

            # Scale down if needed
            remaining = 1.0 - total_upgrade
            if remaining < 0.1 * n_entries:
                scale = (1.0 - 0.1 * n_entries) / total_upgrade
                sliver_percents = [p * scale for p in sliver_percents]
                total_upgrade = sum(sliver_percents)
                remaining = 1.0 - total_upgrade

            entry_percent = remaining / n_entries

            current_angle = 0
            for i in range(n_entries):
                # Draw entry segment with themed colors
                angle_size = entry_percent * 2 * math.pi
                idx = i % len(next_segment_colors)
                color = next_segment_colors[idx]
                self._draw_segment(screen, cx, cy, radius, current_angle, current_angle + angle_size, color)
                current_angle += angle_size

                # Draw upgrade sliver with random size
                sliver_angle = sliver_percents[i] * 2 * math.pi
                self._draw_segment(screen, cx, cy, radius, current_angle, current_angle + sliver_angle, DOCKET_UPGRADE_SLIVER)
                current_angle += sliver_angle

        # Draw small center dot
        inner_radius = max(3, radius // 5)
        pygame.draw.circle(screen, next_colors['dark'], (cx, cy), inner_radius)

    def _draw_decorations(self, screen, cx, cy, r):
        """Draw themed decorations around the wheel."""
        if self.docket_type == self.GOLDEN:
            # Golden sparkles around the wheel
            for i in range(12):
                angle = i * math.pi / 6 + self.angle * 0.5
                dist = r + 20 + math.sin(pygame.time.get_ticks() * 0.005 + i) * 5
                x = cx + int(dist * math.cos(angle))
                y = cy + int(dist * math.sin(angle))
                # Draw star/sparkle
                size = 4 + int(math.sin(pygame.time.get_ticks() * 0.008 + i * 0.5) * 2)
                pygame.draw.circle(screen, (255, 230, 100), (x, y), size)
                pygame.draw.circle(screen, (255, 255, 200), (x, y), size - 2)

        elif self.docket_type == self.DIAMOND:
            # Diamond glints/sparkles
            for i in range(8):
                angle = i * math.pi / 4 + self.angle * 0.3
                dist = r + 15 + math.sin(pygame.time.get_ticks() * 0.006 + i) * 8
                x = cx + int(dist * math.cos(angle))
                y = cy + int(dist * math.sin(angle))
                # Draw diamond shape
                size = 5 + int(math.sin(pygame.time.get_ticks() * 0.01 + i) * 3)
                points = [
                    (x, y - size),
                    (x + size, y),
                    (x, y + size),
                    (x - size, y)
                ]
                pygame.draw.polygon(screen, (200, 230, 255), points)
                pygame.draw.polygon(screen, (255, 255, 255), points, 1)

        elif self.docket_type == self.SHIT:
            # Mud splatters
            random.seed(42)  # Consistent positions
            for i in range(10):
                angle = random.uniform(0, 2 * math.pi)
                dist = r + random.randint(10, 25)
                x = cx + int(dist * math.cos(angle))
                y = cy + int(dist * math.sin(angle))
                size = random.randint(3, 7)
                # Brown splatter
                pygame.draw.circle(screen, (80, 60, 40), (x, y), size)
                pygame.draw.circle(screen, (60, 45, 30), (x + 2, y + 1), size - 1)

        else:  # final
            # Simple gold sparkles for final wheel
            for i in range(8):
                angle = i * math.pi / 4 + self.angle * 0.2
                dist = r + 15 + math.sin(pygame.time.get_ticks() * 0.004 + i) * 5
                x = cx + int(dist * math.cos(angle))
                y = cy + int(dist * math.sin(angle))
                size = 3 + int(abs(math.sin(pygame.time.get_ticks() * 0.006 + i)) * 3)
                pygame.draw.circle(screen, (255, 215, 50), (x, y), size)
                pygame.draw.circle(screen, (255, 255, 200), (x, y), max(1, size - 2))

    def _draw_labels(self, screen, cx, cy, r, scale):
        """Draw movie/name labels on segments."""
        font = self.fonts['small']
        tiny_font = self.fonts['tiny']

        for segment in self.segments:
            if segment['type'] != 'entry':
                continue

            mid_angle = (segment['start_angle'] + segment['end_angle']) / 2 + self.angle

            # Position text at 60% radius
            text_r = r * 0.65
            tx = cx + int(text_r * math.cos(mid_angle))
            ty = cy + int(text_r * math.sin(mid_angle))

            name, movie = segment['entry']

            # Truncate long names
            display_name = name if len(name) <= 12 else name[:10] + ".."
            display_movie = movie if len(movie) <= 18 else movie[:16] + ".."

            # Rotate text to align with segment
            # For readability, show text roughly horizontal
            name_surf = tiny_font.render(display_name, True, UI_BG)
            movie_surf = tiny_font.render(display_movie, True, (0, 0, 0))  # Black for readability

            # Simple blit without rotation for readability
            name_rect = name_surf.get_rect(center=(tx, ty - 8))
            movie_rect = movie_surf.get_rect(center=(tx, ty + 8))

            screen.blit(name_surf, name_rect)
            screen.blit(movie_surf, movie_rect)

    def _draw_flap(self, screen, x, y, scale):
        """Draw the pointer/flap that hits pegs."""
        # Triangle pointer pointing down
        flap_offset = self.flap_angle * 20  # Visual deflection

        points = [
            (x + flap_offset, y + 25),  # Bottom point
            (x - 15 + flap_offset * 0.5, y - 10),  # Top left
            (x + 15 + flap_offset * 0.5, y - 10),  # Top right
        ]

        pygame.draw.polygon(screen, self.colors['primary'], points)
        pygame.draw.polygon(screen, self.colors['dark'], points, 3)

        # Small circle at pivot
        pygame.draw.circle(screen, self.colors['dark'], (x, y - 10), 6)


class DocketZoomTransition:
    """Handles the zoom animation when transitioning between docket tiers."""

    def __init__(self, from_wheel, to_type, entries, fonts, center, target_radius, duration=60, sound_manager=None, next_tier_entries=None):
        self.from_wheel = from_wheel
        self.to_type = to_type
        self.entries = entries
        self.fonts = fonts
        self.center = center
        self.target_radius = target_radius
        self.duration = duration
        self.frame = 0
        self.complete = False
        self.to_wheel = None
        self.sound_manager = sound_manager
        self.next_tier_entries = next_tier_entries  # For the wheel we're creating

        # Pre-generate sliver sizes for the transition animation
        n_entries = len(entries)
        self.sliver_percents = []
        self.sliver_after_index = None  # For shit wheel's single sliver

        if n_entries > 0:
            if to_type == DocketWheel.FINAL:
                # Final wheel has no slivers
                self.sliver_percents = []
            elif to_type == DocketWheel.SHIT:
                # Shit wheel has only ONE 1% sliver
                self.sliver_percents = [0.01]
                self.sliver_after_index = n_entries // 2  # Place in middle
            else:
                # Golden/Diamond: random sliver sizes
                n_slivers = n_entries
                min_sliver = 0.01
                max_sliver = 0.4 / n_slivers  # 40/n %
                self.sliver_percents = [random.uniform(min_sliver, max_sliver) for _ in range(n_slivers)]
                total_upgrade = sum(self.sliver_percents)

                # Scale down if needed
                remaining = 1.0 - total_upgrade
                if remaining < 0.1 * n_entries:
                    scale = (1.0 - 0.1 * n_entries) / total_upgrade
                    self.sliver_percents = [p * scale for p in self.sliver_percents]

        # Play upgrade sound when transition starts
        if self.sound_manager:
            self.sound_manager.play('wheel_upgrade')

    def update(self):
        """Update zoom animation."""
        self.frame += 1
        if self.frame >= self.duration:
            self.complete = True
            # Create the new wheel at full size
            self.to_wheel = DocketWheel(
                self.entries, self.to_type, self.fonts,
                self.center, self.target_radius, self.sound_manager,
                next_tier_entries=self.next_tier_entries
            )

    def draw(self, screen):
        """Draw the zoom transition - looks like zooming into the center wheel."""
        progress = self.frame / self.duration
        # Ease out cubic for smooth deceleration
        eased = 1 - (1 - progress) ** 3

        cx, cy = self.center

        # Determine colors for the next tier
        if self.to_type == DocketWheel.DIAMOND:
            next_colors = {'primary': DOCKET_DIAMOND, 'dark': DOCKET_DIAMOND_DARK}
            segment_colors = DIAMOND_SEGMENT_COLORS
        elif self.to_type == DocketWheel.SHIT:
            next_colors = {'primary': DOCKET_SHIT, 'dark': DOCKET_SHIT_DARK}
            segment_colors = SHIT_SEGMENT_COLORS
        else:  # final
            next_colors = {'primary': (255, 200, 50), 'dark': (180, 140, 30)}
            # Basic generated colors for final wheel
            segment_colors = [
                (255, 87, 87), (87, 167, 255), (87, 255, 137), (255, 215, 87),
                (215, 87, 255), (255, 147, 87), (87, 255, 255), (255, 87, 200),
                (167, 255, 87), (255, 167, 167), (167, 200, 255), (200, 167, 255),
            ]

        # Start from center circle size, expand to full wheel size
        start_r = int(self.from_wheel.radius * 0.25)
        end_r = self.target_radius
        current_r = int(start_r + (end_r - start_r) * eased)

        # Draw outer ring
        pygame.draw.circle(screen, next_colors['dark'], (cx, cy), current_r + 4)

        # Draw the expanding wheel with actual segments
        n_entries = len(self.entries)
        if n_entries > 0:
            if self.to_type == DocketWheel.FINAL:
                # Final wheel: no slivers, just evenly distributed entries
                entry_percent = 1.0 / n_entries
                current_angle = 0
                for i in range(n_entries):
                    angle_size = entry_percent * 2 * math.pi
                    idx = i % len(segment_colors)
                    color = segment_colors[idx]
                    self._draw_segment(screen, cx, cy, current_r, current_angle, current_angle + angle_size, color)
                    current_angle += angle_size
            elif self.to_type == DocketWheel.SHIT:
                # Shit wheel: only ONE 1% gold sliver after the middle entry
                total_upgrade = 0.01
                entry_percent = (1.0 - total_upgrade) / n_entries
                current_angle = 0

                for i in range(n_entries):
                    angle_size = entry_percent * 2 * math.pi
                    idx = i % len(segment_colors)
                    color = segment_colors[idx]
                    self._draw_segment(screen, cx, cy, current_r, current_angle, current_angle + angle_size, color)
                    current_angle += angle_size

                    if i == self.sliver_after_index:
                        sliver_angle = 0.01 * 2 * math.pi
                        # Solid gold sliver
                        gold_color = (255, 215, 50)
                        self._draw_segment(screen, cx, cy, current_r, current_angle, current_angle + sliver_angle, gold_color)
                        current_angle += sliver_angle
            else:
                # Golden/Diamond: Use pre-generated random sliver sizes
                total_upgrade = sum(self.sliver_percents)
                entry_percent = (1.0 - total_upgrade) / n_entries

                current_angle = 0
                for i in range(n_entries):
                    # Draw entry segment with themed colors
                    angle_size = entry_percent * 2 * math.pi
                    idx = i % len(segment_colors)
                    color = segment_colors[idx]
                    self._draw_segment(screen, cx, cy, current_r, current_angle, current_angle + angle_size, color)
                    current_angle += angle_size

                    # Draw upgrade sliver with its random size
                    sliver_angle = self.sliver_percents[i] * 2 * math.pi
                    self._draw_segment(screen, cx, cy, current_r, current_angle, current_angle + sliver_angle, DOCKET_UPGRADE_SLIVER)
                    current_angle += sliver_angle

        # Draw center circle
        inner_r = max(5, int(current_r * 0.25))
        pygame.draw.circle(screen, next_colors['dark'], (cx, cy), inner_r + 2)
        pygame.draw.circle(screen, next_colors['primary'], (cx, cy), inner_r)

        # Draw label that fades in
        if self.to_type == DocketWheel.DIAMOND:
            label = "DIAMOND DOCKET"
        elif self.to_type == DocketWheel.SHIT:
            label = "SHIT DOCKET"
        else:
            label = "FINAL WHEEL"

        # Only show label in later part of animation
        if progress > 0.3:
            label_alpha = min(255, int(255 * (progress - 0.3) / 0.7))
            font = self.fonts['large']
            text = font.render(label, True, (255, 255, 255))
            text.set_alpha(label_alpha)
            text_rect = text.get_rect(center=(cx, cy - current_r - 40))
            screen.blit(text, text_rect)

    def _draw_segment(self, screen, cx, cy, r, start_angle, end_angle, color):
        """Draw a pie segment for the zoom transition."""
        points = [(cx, cy)]
        steps = max(3, int((end_angle - start_angle) * 20))
        for i in range(steps + 1):
            angle = start_angle + (end_angle - start_angle) * i / steps
            x = cx + int(r * math.cos(angle))
            y = cy + int(r * math.sin(angle))
            points.append((x, y))

        if len(points) > 2:
            pygame.draw.polygon(screen, color, points)

    def get_new_wheel(self):
        """Get the newly created wheel after transition completes."""
        return self.to_wheel

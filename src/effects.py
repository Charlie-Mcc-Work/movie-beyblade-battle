import pygame
import random
import math
import array
from .constants import SPARK_COLORS, SPARK_LIFETIME, SPARK_COUNT

# Fun notification colors
NOTIFICATION_COLORS = [
    (255, 100, 100),  # Red
    (100, 255, 100),  # Green
    (100, 200, 255),  # Blue
    (255, 200, 100),  # Orange
    (255, 100, 255),  # Pink
    (100, 255, 255),  # Cyan
    (255, 255, 100),  # Yellow
    (200, 150, 255),  # Purple
]


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


class SoundManager:
    def __init__(self):
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        self.muted = False
        self.sounds = {}
        self._generate_sounds()

    def _generate_sounds(self):
        """Generate fun retro sound effects programmatically."""
        # Collision - short punchy hit
        self.sounds['hit'] = self._make_sound(freq=300, duration=0.08, freq_end=150, volume=0.3)
        # Big hit
        self.sounds['big_hit'] = self._make_sound(freq=200, duration=0.15, freq_end=80, volume=0.5)
        # Ability trigger - rising tone
        self.sounds['ability'] = self._make_sound(freq=400, duration=0.12, freq_end=800, volume=0.25)
        # Knockout - descending sad tone
        self.sounds['knockout'] = self._make_sound(freq=500, duration=0.3, freq_end=100, volume=0.35)
        # Bouncy save - boing!
        self.sounds['bouncy'] = self._make_sound(freq=200, duration=0.2, freq_end=600, volume=0.3)
        # Victory fanfare
        self.sounds['victory'] = self._make_victory_sound()
        # New round
        self.sounds['round'] = self._make_sound(freq=600, duration=0.15, freq_end=800, volume=0.3)
        # Burst
        self.sounds['burst'] = self._make_sound(freq=150, duration=0.2, freq_end=400, volume=0.4)
        # Dodge
        self.sounds['dodge'] = self._make_sound(freq=800, duration=0.1, freq_end=1200, volume=0.2)
        # Counter
        self.sounds['counter'] = self._make_sound(freq=400, duration=0.15, freq_end=200, volume=0.35)
        # Vampire
        self.sounds['vampire'] = self._make_sound(freq=200, duration=0.2, freq_end=300, volume=0.25)
        # Gambler win
        self.sounds['gambler_win'] = self._make_sound(freq=500, duration=0.15, freq_end=1000, volume=0.3)
        # Gambler lose
        self.sounds['gambler_lose'] = self._make_sound(freq=400, duration=0.2, freq_end=150, volume=0.25)
        # Countdown beep (3, 2, 1)
        self.sounds['countdown_beep'] = self._make_sound(freq=440, duration=0.15, freq_end=440, volume=0.4)
        # Countdown GO! (higher, more exciting)
        self.sounds['countdown_go'] = self._make_countdown_go()
        # Bumper hit - pinball-style ding
        self.sounds['bumper'] = self._make_sound(freq=800, duration=0.08, freq_end=1200, volume=0.35)

    def _make_sound(self, freq=440, duration=0.1, freq_end=None, volume=0.3):
        """Generate a simple synthesized sound."""
        sample_rate = 22050
        n_samples = int(sample_rate * duration)
        if freq_end is None:
            freq_end = freq

        buf = array.array('h', [0] * n_samples)
        for i in range(n_samples):
            t = i / sample_rate
            progress = i / n_samples
            # Linear frequency sweep
            current_freq = freq + (freq_end - freq) * progress
            # Envelope: quick attack, decay
            envelope = min(1.0, (1 - progress) * 3) * min(1.0, i / (sample_rate * 0.01))
            value = int(32767 * volume * envelope * math.sin(2 * math.pi * current_freq * t))
            buf[i] = max(-32767, min(32767, value))

        sound = pygame.mixer.Sound(buffer=buf)
        return sound

    def _make_victory_sound(self):
        """Generate a victory fanfare."""
        sample_rate = 22050
        duration = 0.6
        n_samples = int(sample_rate * duration)
        buf = array.array('h', [0] * n_samples)

        # Three note fanfare: C-E-G
        notes = [(523, 0.0, 0.2), (659, 0.2, 0.2), (784, 0.4, 0.2)]
        for note_freq, start_time, note_dur in notes:
            start_sample = int(start_time * sample_rate)
            end_sample = int((start_time + note_dur) * sample_rate)
            for i in range(start_sample, min(end_sample, n_samples)):
                t = (i - start_sample) / sample_rate
                progress = (i - start_sample) / (end_sample - start_sample)
                envelope = min(1.0, (1 - progress) * 2) * min(1.0, (i - start_sample) / (sample_rate * 0.01))
                value = int(32767 * 0.3 * envelope * math.sin(2 * math.pi * note_freq * t))
                buf[i] = max(-32767, min(32767, buf[i] + value))

        return pygame.mixer.Sound(buffer=buf)

    def _make_countdown_go(self):
        """Generate an exciting GO! sound - quick ascending burst."""
        sample_rate = 22050
        duration = 0.25
        n_samples = int(sample_rate * duration)
        buf = array.array('h', [0] * n_samples)

        # Two-tone burst: low to high
        for i in range(n_samples):
            t = i / sample_rate
            progress = i / n_samples
            # Quick sweep from 400 to 800 Hz
            freq = 400 + 600 * progress
            # Sharp attack, medium decay
            envelope = min(1.0, (1 - progress) * 2) * min(1.0, i / (sample_rate * 0.005))
            value = int(32767 * 0.45 * envelope * math.sin(2 * math.pi * freq * t))
            # Add a harmonic for richness
            value += int(32767 * 0.2 * envelope * math.sin(2 * math.pi * freq * 2 * t))
            buf[i] = max(-32767, min(32767, value))

        return pygame.mixer.Sound(buffer=buf)

    def play(self, sound_name: str):
        """Play a sound if not muted."""
        if not self.muted and sound_name in self.sounds:
            self.sounds[sound_name].play()

    def toggle_mute(self):
        self.muted = not self.muted
        return self.muted


class EffectsManager:
    def __init__(self):
        self.particles: list[Particle] = []
        self.knockout_effects: list[dict] = []
        self.event_log: list[dict] = []  # Scrolling log on the side
        self.max_log_entries = 30  # Entries persist until heat ends
        self.sound = SoundManager()

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

    def spawn_ability_notification(self, beyblade_name: str, ability_text: str, color: tuple, sound_name: str = 'ability', ability_name: str = None):
        """Add a notification to the scrolling log."""
        # Use a random fun color instead of the passed color for variety
        log_color = random.choice(NOTIFICATION_COLORS)

        self.event_log.append({
            'name': beyblade_name,
            'text': ability_text,
            'color': log_color,
            'age': 0,  # Frames since added
            'ability_name': ability_name,  # The name of the ability that triggered this
        })

        # Keep log trimmed
        if len(self.event_log) > self.max_log_entries:
            self.event_log.pop(0)

        # Play sound
        self.sound.play(sound_name)

    def add_log_entry(self, text: str, color: tuple = None, sound_name: str = None):
        """Add a generic log entry."""
        if color is None:
            color = random.choice(NOTIFICATION_COLORS)

        self.event_log.append({
            'name': '',
            'text': text,
            'color': color,
            'age': 0,
        })

        if len(self.event_log) > self.max_log_entries:
            self.event_log.pop(0)

        if sound_name:
            self.sound.play(sound_name)

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

        # Age log entries
        for entry in self.event_log:
            entry['age'] += dt

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

        # Draw scrolling event log on left side
        log_x = 10
        log_y_start = 60
        line_height = 22

        for i, entry in enumerate(self.event_log):
            y = log_y_start + i * line_height

            # Fade in new entries, then stay solid (cleared when heat ends)
            alpha = min(1.0, entry['age'] / 15)

            # Build text - only truncate names over 25 chars
            if entry['name']:
                name_display = entry['name'][:22] + '...' if len(entry['name']) > 25 else entry['name']
                ability_prefix = f"[{entry.get('ability_name', '')}] " if entry.get('ability_name') else ""
                text = f"{name_display}: {ability_prefix}{entry['text']}"
            else:
                text = entry['text']

            text_color = tuple(int(c * alpha) for c in entry['color'])
            text_surface = font.render(text, True, text_color)

            # Solid background for readability
            bg_surface = pygame.Surface((text_surface.get_width() + 10, line_height - 2), pygame.SRCALPHA)
            bg_surface.fill((20, 20, 30, int(230 * alpha)))
            screen.blit(bg_surface, (log_x - 5, y))

            screen.blit(text_surface, (log_x, y + 2))

    def clear(self):
        self.particles.clear()
        self.knockout_effects.clear()
        self.event_log.clear()

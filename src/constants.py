# Window settings
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
FPS = 60

# Arena settings
ARENA_CENTER = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
ARENA_RADIUS = 350

# Beyblade settings
BEYBLADE_RADIUS = 25
BEYBLADE_MIN_RADIUS = 20
BEYBLADE_MAX_RADIUS = 35

# Stats ranges (random generation)
STAT_RANGES = {
    'spin_power': (50, 100),      # Visual spin speed + slight damage bonus
    'attack': (10, 30),            # Damage dealt on collision
    'defense': (5, 20),            # Damage reduction
    'stamina': (100, 200),         # Health pool
    'weight': (0.5, 1.5),          # Mass multiplier (affects knockback)
}

# Physics
MAX_SPEED = 10
FRICTION = 0.99
COLLISION_ELASTICITY = 0.8
BASE_DAMAGE_MULTIPLIER = 0.5
KNOCKBACK_FORCE = 2.0
ARENA_SLOPE_STRENGTH = 0.15  # Bowl slope - creates orbital motion

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (40, 40, 40)
LIGHT_GRAY = (200, 200, 200)

# Arena colors
ARENA_FLOOR = (50, 50, 60)
ARENA_EDGE = (80, 80, 90)
ARENA_RIM = (100, 100, 110)

# UI Colors
UI_BG = (25, 25, 35)
UI_PANEL = (40, 40, 55)
UI_ACCENT = (100, 150, 255)
UI_ACCENT_HOVER = (130, 180, 255)
UI_TEXT = (230, 230, 240)
UI_TEXT_DIM = (150, 150, 160)

# Victory colors
VICTORY_GOLD = (255, 215, 0)
VICTORY_GLOW = (255, 235, 100)

# Beyblade color palette (will cycle through these)
BEYBLADE_COLORS = [
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
    (255, 200, 100),  # Peach
    (100, 255, 200),  # Mint
    (255, 100, 150),  # Rose
]

# Particle effects
SPARK_COLORS = [
    (255, 255, 200),
    (255, 230, 150),
    (255, 200, 100),
    (255, 170, 50),
]
SPARK_LIFETIME = 20
SPARK_COUNT = 8

# Knockout effect
KNOCKOUT_DURATION = 45
KNOCKOUT_FLASH_SPEED = 4

# Speed multipliers
SPEED_OPTIONS = [1, 2, 4]

# Text
FONT_SIZES = {
    'tiny': 12,
    'small': 16,
    'medium': 24,
    'large': 36,
    'huge': 72,
    'title': 48,
}

# Game states
STATE_INPUT = 'input'
STATE_BATTLE = 'battle'
STATE_VICTORY = 'victory'

# File loading
MOVIE_LIST_FILE = "movies.txt"

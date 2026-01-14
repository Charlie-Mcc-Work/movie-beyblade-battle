# Window settings
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
FPS = 60

# Arena settings
ARENA_CENTER = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
ARENA_RADIUS = 525

# Beyblade settings
BEYBLADE_RADIUS = 25
BEYBLADE_MIN_RADIUS = 20
BEYBLADE_MAX_RADIUS = 35

# Stats ranges (random generation)
STAT_RANGES = {
    'spin_power': (50, 100),      # Visual spin speed + slight damage bonus
    'attack': (10, 30),            # Damage dealt on collision
    'defense': (5, 20),            # Damage reduction
    'stamina': (18, 40),           # Health pool - 20% higher for longer fights
    'weight': (0.5, 1.5),          # Mass multiplier (affects knockback)
}

# Avatar abilities - these are cast from the avatar, not the beyblade
# They continue even after the beyblade is eliminated
AVATAR_ABILITIES = ['fireball', 'ice', 'grenade', 'kamehameha', 'water', 'john_wick']

# Physics
MAX_SPEED = 15
FRICTION = 0.995
COLLISION_ELASTICITY = 0.6
BASE_DAMAGE_MULTIPLIER = 0.5
KNOCKBACK_FORCE = 1.2
ARENA_SLOPE_STRENGTH = 0.20  # Bowl slope - creates orbital motion

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
    'tiny': 16,
    'small': 20,
    'medium': 28,
    'large': 42,
    'huge': 84,
    'title': 56,
}

# Game states
STATE_INPUT = 'input'
STATE_BATTLE = 'battle'
STATE_HEAT_TRANSITION = 'heat_transition'
STATE_VICTORY = 'victory'
STATE_LEADERBOARD = 'leaderboard'

# File loading
MOVIE_LIST_FILE = "movies.txt"
QUEUE_FILE = "queue.txt"
WATCHED_FILE = "watched.txt"

# Avatar settings
AVATAR_DISTANCE_FROM_ARENA = 60  # Pixels outside arena edge
AVATAR_ELIMINATED_DIM = 0.5  # Color multiplier when eliminated

# Abilities
ABILITY_CHANCE = 1.0  # 100% chance to have an ability

ABILITIES = {
    'glass_cannon': {
        'name': 'Glass Cannon',
        'color': (255, 100, 100),
        'type': 'passive',
        'description': '+50% knockback dealt & received',
    },
    'vampire': {
        'name': 'Vampire',
        'color': (150, 0, 50),
        'type': 'passive',
        'description': 'Steal stamina on hit',
    },
    'giant': {
        'name': 'Giant',
        'color': (200, 150, 100),
        'type': 'passive',
        'description': '40% larger size',
    },
    'tiny': {
        'name': 'Tiny',
        'color': (150, 200, 255),
        'type': 'passive',
        'description': '30% smaller size',
    },
    'burst': {
        'name': 'Burst',
        'color': (255, 200, 0),
        'type': 'triggered',
        'description': 'Chance for 2.5x knockback',
        'trigger_chance': 0.15,
    },
    'dodge': {
        'name': 'Dodge',
        'color': (100, 255, 200),
        'type': 'triggered',
        'description': 'Chance to ignore knockback',
        'trigger_chance': 0.20,
    },
    'vengeance': {
        'name': 'Vengeance',
        'color': (128, 0, 128),
        'type': 'triggered',
        'description': 'Stores damage, releases on next hit',
    },
    'reversal': {
        'name': 'Reversal',
        'color': (0, 200, 200),
        'type': 'triggered',
        'description': '10% chance to swap positions',
        'trigger_chance': 0.10,
    },
    'parasite': {
        'name': 'Parasite',
        'color': (100, 150, 50),
        'type': 'triggered',
        'description': 'Latches to enemy, share damage',
    },
    'timebomb': {
        'name': 'Timebomb',
        'color': (50, 50, 50),
        'type': 'triggered',
        'description': 'Huge explosion after 20 seconds',
    },
    'counter': {
        'name': 'Counter',
        'color': (255, 50, 150),
        'type': 'triggered',
        'description': 'Chance to reflect knockback',
        'trigger_chance': 0.15,
    },
    'rage': {
        'name': 'Rage',
        'color': (255, 50, 0),
        'type': 'triggered',
        'description': 'Next hit 2x after taking big hit',
    },
    'brutal': {
        'name': 'Brutal',
        'color': (200, 50, 50),
        'type': 'passive',
        'description': '+40% damage dealt',
    },
    'gambler': {
        'name': 'Gambler',
        'color': (255, 215, 0),
        'type': 'passive',
        'description': 'Hits randomly 2x or 0.5x',
    },
    'mirror': {
        'name': 'Mirror',
        'color': (200, 200, 255),
        'type': 'triggered',
        'description': 'Copy ability on hit',
        'trigger_chance': 0.25,
    },
    'momentum': {
        'name': 'Momentum',
        'color': (100, 200, 255),
        'type': 'passive',
        'description': 'More damage at high speed',
    },
    'berserker': {
        'name': 'Berserker',
        'color': (180, 0, 0),
        'type': 'passive',
        'description': 'More damage at low HP',
    },
    'explosive': {
        'name': 'Explosive',
        'color': (255, 100, 0),
        'type': 'triggered',
        'description': 'Explodes on death',
    },
    'copycat': {
        'name': 'Copycat',
        'color': (180, 180, 180),
        'type': 'triggered',
        'description': 'Copies first ability hit',
    },
    'fireball': {
        'name': 'Fireball',
        'color': (255, 100, 0),
        'type': 'active',
        'description': 'Shoots fireballs toward center',
    },
    'portal': {
        'name': 'Portal',
        'color': (150, 50, 255),
        'type': 'active',
        'description': 'Creates linked portals on the field',
    },
    'zombie': {
        'name': 'Zombie',
        'color': (100, 150, 50),
        'type': 'triggered',
        'description': 'Revives once with 50% HP',
    },
    'last_stand': {
        'name': 'Last Stand',
        'color': (255, 215, 0),
        'type': 'triggered',
        'description': 'Invincible for 5s at low HP',
    },
    'earthquake': {
        'name': 'Earthquake',
        'color': (139, 90, 43),
        'type': 'active',
        'description': 'Shakes arena every 15 seconds',
    },
    'lightning_storm': {
        'name': 'Lightning',
        'color': (255, 255, 100),
        'type': 'active',
        'description': 'Strikes 3 random enemies periodically',
    },
    'inflation': {
        'name': 'Inflation',
        'color': (255, 150, 200),
        'type': 'passive',
        'description': 'Grows 5% larger per hit taken',
    },
    'shrinking': {
        'name': 'Shrinking',
        'color': (150, 200, 255),
        'type': 'passive',
        'description': 'Shrink 10% when hit (harder to hit)',
    },
    'mutually_assured': {
        'name': 'M.A.D.',
        'color': (200, 0, 0),
        'type': 'triggered',
        'description': 'On death, all lose 50% current HP',
    },
    'doomsday': {
        'name': 'Doomsday',
        'color': (50, 50, 50),
        'type': 'active',
        'description': 'After 30s, eliminates 2 nearest edge',
    },
    'swamp_thing': {
        'name': 'Swamp Thing',
        'color': (50, 120, 50),
        'type': 'triggered',
        'description': 'Stops all momentum once when fast',
    },
    'ice': {
        'name': 'Ice',
        'color': (150, 220, 255),
        'type': 'active',
        'description': 'Shoots ice that freezes and leaves slippery trails',
    },
    'grenade': {
        'name': 'Grenade',
        'color': (80, 100, 50),
        'type': 'active',
        'description': 'Throws grenades that explode on landing',
    },
    'kamehameha': {
        'name': 'Kamehameha',
        'color': (100, 180, 255),
        'type': 'active',
        'description': 'Charges and fires a powerful beam',
    },
    'water': {
        'name': 'Water',
        'color': (50, 150, 255),
        'type': 'active',
        'description': 'Splashes waves that push everything',
    },
    'venom': {
        'name': 'Venom',
        'color': (100, 0, 150),
        'type': 'passive',
        'description': '200% damage dealt over time',
    },
    'naruto': {
        'name': 'Naruto',
        'color': (255, 150, 50),
        'type': 'triggered',
        'description': 'Creates 2 clones, each with 1/3 HP',
    },
    'goku': {
        'name': 'Goku',
        'color': (255, 200, 50),
        'type': 'active',
        'description': 'Teleports behind random enemy',
    },
    'batman': {
        'name': 'Batman',
        'color': (30, 30, 30),
        'type': 'passive',
        'description': 'Immune to all ability effects',
    },
    'flash': {
        'name': 'Flash',
        'color': (255, 50, 50),
        'type': 'passive',
        'description': '100% faster with strong center pull',
    },
    'zoro': {
        'name': 'Zoro',
        'color': (50, 150, 50),
        'type': 'triggered',
        'description': '25% chance to slice through enemies',
        'trigger_chance': 0.25,
    },
    'luffy': {
        'name': 'Luffy',
        'color': (200, 50, 50),
        'type': 'passive',
        'description': '2x bounce, survives 2 edge hits',
    },
    'andy_dufresne': {
        'name': 'Andy Dufresne',
        'color': (100, 80, 60),
        'type': 'triggered',
        'description': 'Respawns after 20s dead if heat continues',
    },
    'shelob': {
        'name': 'Shelob',
        'color': (40, 40, 40),
        'type': 'passive',
        'description': 'Crawls on 8 legs after 3s without being hit',
    },
    'the_prestige': {
        'name': 'The Prestige',
        'color': (80, 60, 100),
        'type': 'triggered',
        'description': 'Enters tournament twice as two copies',
    },
    'the_obelisk': {
        'name': 'The Obelisk',
        'color': (60, 60, 80),
        'type': 'active',
        'description': 'Spawns a bumper on the arena',
    },
    'kill_bill': {
        'name': 'Kill Bill',
        'color': (255, 220, 0),
        'type': 'passive',
        'description': '5x damage vs one random target per heat',
    },
    'american_psycho': {
        'name': 'American Psycho',
        'color': (180, 50, 50),
        'type': 'passive',
        'description': 'Damage resets after 20 seconds',
    },
    'little_miss_sunshine': {
        'name': 'Little Miss Sunshine',
        'color': (255, 255, 150),
        'type': 'passive',
        'description': 'Immune to damage from red/green beyblades',
    },
    'barry_lyndon': {
        'name': 'Barry Lyndon',
        'color': (180, 150, 100),
        'type': 'triggered',
        'description': 'Once per game: duel (90% win)',
    },
    'kevin_mcallister': {
        'name': 'Kevin McAllister',
        'color': (255, 200, 100),
        'type': 'active',
        'description': 'Leaves traps: nails & banana peels',
    },
    'ferris_bueller': {
        'name': 'Ferris Bueller',
        'color': (200, 50, 50),
        'type': 'triggered',
        'description': 'Joins 5 seconds late',
    },
    'alien': {
        'name': 'Alien',
        'color': (50, 80, 50),
        'type': 'triggered',
        'description': 'Juvenile infects host, adult +10% stats',
    },
    'amadeus': {
        'name': 'Amadeus',
        'color': (200, 180, 150),
        'type': 'passive',
        'description': 'Cannot die while rival lives',
    },
    'terminator': {
        'name': 'Terminator',
        'color': (150, 150, 180),
        'type': 'passive',
        'description': 'Hunts target after 3s without hit',
    },
    'oppenheimer': {
        'name': 'Oppenheimer',
        'color': (255, 150, 50),
        'type': 'triggered',
        'description': '1/200 chance to nuke half the field',
    },
    'john_wick': {
        'name': 'John Wick',
        'color': (50, 50, 50),
        'type': 'active',
        'description': 'Avatar shoots pistol bursts',
    },
}

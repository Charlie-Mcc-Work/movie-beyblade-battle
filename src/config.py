# Mode configuration for different user groups

class ModeConfig:
    """Configuration for different game modes."""

    def __init__(self, mode='default'):
        self.mode = mode
        self._setup_mode()

    def _setup_mode(self):
        if self.mode == 'girlfriend':
            self._setup_girlfriend_mode()
        else:
            self._setup_default_mode()

    def _setup_default_mode(self):
        """Default mode - full features for movie group."""
        # File paths
        self.movie_file = "movies.txt"
        self.queue_file = "queue.txt"
        self.watched_file = "watched.txt"
        self.sequel_file = "sequels.txt"
        self.golden_docket_file = "goldendocket.txt"
        self.diamond_docket_file = "diamonddocket.txt"
        self.shit_docket_file = "shitdocket.txt"
        self.permanent_people_file = "permenantpeople.txt"
        self.people_counter_file = "peoplecounter.txt"
        self.ability_wins_file = "abilitywins.txt"
        self.ability_stats_file = "abilitystats.txt"

        # UI Colors
        self.ui_bg = (25, 25, 35)
        self.ui_panel = (40, 40, 55)
        self.ui_accent = (100, 150, 255)
        self.ui_accent_hover = (130, 180, 255)

        # Arena colors
        self.arena_floor = (50, 50, 60)
        self.arena_edge = (80, 80, 90)
        self.arena_rim = (100, 100, 110)

        # Features
        self.has_shit_docket = True
        self.can_add_members = True
        self.permanent_members = None  # Load from file
        self.diamond_sliver_to_final_wheel = False

        # Mode label
        self.mode_label = None

    def _setup_girlfriend_mode(self):
        """Girlfriend mode - Charlie & Hanan only, purple theme."""
        # File paths (prefixed with gf_)
        self.movie_file = "gf_movies.txt"
        self.queue_file = "gf_queue.txt"
        self.watched_file = "gf_watched.txt"
        self.sequel_file = "gf_sequels.txt"
        self.golden_docket_file = "gf_goldendocket.txt"
        self.diamond_docket_file = "gf_diamonddocket.txt"
        self.shit_docket_file = None  # No shit docket
        self.permanent_people_file = None  # Fixed members
        self.people_counter_file = "gf_peoplecounter.txt"
        self.ability_wins_file = "gf_abilitywins.txt"
        self.ability_stats_file = "gf_abilitystats.txt"

        # UI Colors - Purple theme
        self.ui_bg = (35, 25, 45)  # Dark purple
        self.ui_panel = (55, 40, 70)  # Purple panel
        self.ui_accent = (180, 100, 255)  # Bright purple accent
        self.ui_accent_hover = (210, 130, 255)  # Lighter purple hover

        # Arena colors - Purple tinted
        self.arena_floor = (50, 40, 65)
        self.arena_edge = (80, 60, 100)
        self.arena_rim = (100, 80, 120)

        # Features
        self.has_shit_docket = False
        self.can_add_members = False
        self.permanent_members = ['Charlie', 'Hanan']  # Fixed members
        self.diamond_sliver_to_final_wheel = True

        # Mode label
        self.mode_label = "Charlie & Hanan"


# Global config instance (set by main.py)
current_config = None

def get_config():
    """Get current mode configuration."""
    global current_config
    if current_config is None:
        current_config = ModeConfig('default')
    return current_config

def set_mode(mode):
    """Set the game mode."""
    global current_config
    current_config = ModeConfig(mode)
    return current_config

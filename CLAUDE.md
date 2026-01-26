# Movie Beyblade Battle - Project Context

## What This Is
A Pygame-based battle royale simulator for picking movie night selections. Users paste movie titles, each becomes a spinning "beyblade" with random stats and special abilities, they fight in an arena, and the last one standing wins.

## How to Run
```bash
pip install -r requirements.txt
python main.py              # Default mode (movie group)
python main.py -g           # Girlfriend mode (Charlie & Hanan)
python main.py --girlfriend # Same as -g
```

## Game Modes

### Default Mode
Full-featured mode for the movie group with all docket types and member management.

**Docket Flow:**
1. Click Golden Docket → Participant selection screen
2. Select/add participants, manage counters
3. Golden docket spin → Diamond docket (on sliver) → Shit docket (on sliver) → Final wheel

### Girlfriend Mode (-g)
Simplified mode for Charlie & Hanan with:
- Purple-themed UI
- Fixed members (Charlie & Hanan only, no add member option)
- No participant selection screen - goes straight to docket spin
- No shit docket - diamond slivers go directly to final wheel
- No people counting or graduation system
- Separate data files (prefixed with `gf_`)

**Docket Flow (simplified):**
1. Click Golden Docket → Immediately starts golden docket spin
2. Golden docket spin → Diamond docket (on sliver) → Final wheel (on sliver)

## Project Structure
```
├── main.py           # Entry point with mode flag parsing
├── requirements.txt  # pygame>=2.5.0
├── src/
│   ├── game.py       # Main game loop & state machine
│   ├── config.py     # Mode configuration (default vs girlfriend)
│   ├── beyblade.py   # Beyblade class with stats, physics, abilities
│   ├── arena.py      # Circular stadium with slope physics
│   ├── effects.py    # Spark particles, knockout animations
│   ├── ui.py         # All UI screens and components
│   └── constants.py  # Tunable values (colors, physics, abilities)
│
├── # Default mode data files:
├── movies.txt        # Main movie list
├── queue.txt         # Queue of movies to watch
├── sequels.txt       # Sequel movies list
├── watched.txt       # Watch history
├── abilitystats.txt  # Ability statistics
├── abilitywins.txt   # Ability win counts
├── goldendocket.txt  # Golden docket picks
├── diamonddocket.txt # Diamond docket picks
├── shitdocket.txt    # Shit docket picks
├── permenantpeople.txt # Permanent group members
├── peoplecounter.txt # Member participation counts
│
└── # Girlfriend mode data files (gf_ prefix):
    gf_movies.txt, gf_queue.txt, gf_sequels.txt, gf_watched.txt,
    gf_goldendocket.txt, gf_diamonddocket.txt, gf_abilitystats.txt,
    gf_abilitywins.txt, gf_peoplecounter.txt
```

## Key Features

### Battle System
- **Battle Royale format**: All movies fight at once (handles 30-80 movies)
- **Random stats each run**: spin_power, attack, defense, stamina, weight
- **Special Abilities**: Each beyblade gets a random ability with unique effects
- **Speed controls**: 1x/2x/4x buttons during battle
- **Physics**: Circular collision, arena slope pushes toward center, momentum-based knockback

### Movie Selection Priority System (weakest to strongest)
6. **Battle!** - Regular battle, winner can be sent to queue
5. **Queue** - Manual queue management
4. **Queue Battle** - Battle with queue movies, winner must be watched
3. **Sequels** - Manual sequel list management
2. **Sequel Battle** - Battle with sequel movies, winner must be watched
1. **Golden Docket** - Special picks, winner must be watched

### Home Screen Elements
- **Movie Input Box** - Paste/type movie list (center)
- **Queue Panel** - Shows queued movies (right side)
- **Sequel Panel** - Shows sequel list with add input (right of queue)
- **Docket Picks Panel** - Shows golden/diamond/shit docket entries (left side)
- **Priority Breakdown** - Shows selection hierarchy (left of center)
- **Battle Wheel** - Spinnable wheel to suggest which battle type to do (below buttons)
- **Mode Label** - Shows "Charlie & Hanan" in girlfriend mode (top left)

### Battle Types
- **Regular Battle**: From main movie list, winner can be added to queue
- **Queue Battle**: From queue.txt, forces winner selection (no play again/quit)
- **Sequel Battle**: From sequels.txt, forces winner selection (no play again/quit)

### Post-Battle
- **Leaderboard Screen**: Shows final rankings with ability stats
- **Choose Button**: Marks winner as watched, removes from source list
- **Add to Queue**: Available for regular battles only

## Data Files
- All text files use simple newline-separated format
- Docket files use "Name - Movie" format
- Ability stats track wins, total damage, and battles per ability
- Girlfriend mode uses separate files with `gf_` prefix

## Configuration (src/config.py)
The `ModeConfig` class handles mode-specific settings:
- `movie_file`, `queue_file`, etc. - File paths for all data files
- `ui_bg`, `ui_accent`, etc. - UI colors (purple theme for girlfriend mode)
- `has_shit_docket` - Whether shit docket exists (False in girlfriend mode)
- `can_add_members` - Whether new members can be added (False in girlfriend mode)
- `permanent_members` - Fixed member list (['Charlie', 'Hanan'] in girlfriend mode)
- `diamond_sliver_to_final_wheel` - Skip shit docket (True in girlfriend mode)

## Status
- All core features implemented
- Queue and sequel battle modes working
- Battle wheel for random battle type suggestion
- Ability system with stats tracking
- Girlfriend mode with purple theme, simplified docket flow, and separate data

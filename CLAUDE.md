# Movie Beyblade Battle - Project Context

## What This Is
A Pygame-based battle royale simulator for picking movie night selections. Users paste movie titles, each becomes a spinning "beyblade" with random stats and special abilities, they fight in an arena, and the last one standing wins.

## How to Run
```bash
pip install -r requirements.txt
python main.py
```

## Project Structure
```
├── main.py           # Entry point
├── requirements.txt  # pygame>=2.5.0
├── src/
│   ├── game.py       # Main game loop & state machine (INPUT -> BATTLE -> VICTORY)
│   ├── beyblade.py   # Beyblade class with stats, physics, collision detection, abilities
│   ├── arena.py      # Circular stadium with slope physics pushing toward center
│   ├── effects.py    # Spark particles on collision, knockout animations
│   ├── ui.py         # InputScreen, BattleHUD, VictoryScreen, LeaderboardScreen, Button, TextBox
│   └── constants.py  # All tunable values (colors, physics, sizes, abilities)
├── movies.txt        # Main movie list (auto-saved)
├── queue.txt         # Queue of movies to watch
├── sequels.txt       # List of sequel movies to watch
├── watched.txt       # History of watched movies
├── abilitystats.txt  # Ability win/loss statistics
├── abilitywins.txt   # Ability leaderboard data
├── golden_docket.txt # Golden docket picks (Name - Movie format)
├── diamond_docket.txt # Diamond docket picks
└── shit_docket.txt   # Shit docket picks
```

## Key Features

### Battle System
- **Battle Royale format**: All movies fight at once (handles 30-80 movies)
- **Random stats each run**: spin_power, attack, defense, stamina, weight
- **Special Abilities**: Each beyblade gets a random ability with unique effects
- **Speed controls**: 1x/2x/4x buttons during battle
- **Physics**: Circular collision, arena slope pushes toward center, momentum-based knockback

### Movie Selection Priority System (weakest to strongest)
1. **Battle!** - Regular battle, winner can be sent to queue
2. **Queue** - Manual queue management
3. **Queue Battle** - Battle with queue movies, winner must be watched
4. **Sequels** - Manual sequel list management
5. **Sequel Battle** - Battle with sequel movies, winner must be watched
6. **Golden Docket** - Special picks, winner must be watched

### Home Screen Elements
- **Movie Input Box** - Paste/type movie list (center)
- **Queue Panel** - Shows queued movies (right side)
- **Sequel Panel** - Shows sequel list with add input (right of queue)
- **Docket Picks Panel** - Shows golden/diamond/shit docket entries (left side)
- **Priority Breakdown** - Shows selection hierarchy (left of center)
- **Battle Wheel** - Spinnable wheel to suggest which battle type to do (below buttons)

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

## Status
- All core features implemented
- Queue and sequel battle modes working
- Battle wheel for random battle type suggestion
- Ability system with stats tracking

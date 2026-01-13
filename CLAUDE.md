# Movie Beyblade Battle - Project Context

## What This Is
A Pygame-based battle royale simulator for picking movie night selections. Users paste movie titles, each becomes a spinning "beyblade" with random stats, they fight in an arena, and the last one standing wins.

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
│   ├── beyblade.py   # Beyblade class with stats, physics, collision detection
│   ├── arena.py      # Circular stadium with slope physics pushing toward center
│   ├── effects.py    # Spark particles on collision, knockout animations
│   ├── ui.py         # InputScreen, BattleHUD, VictoryScreen, Button, TextBox
│   └── constants.py  # All tunable values (colors, physics, sizes)
```

## Key Design Decisions
- **Battle Royale format**: All movies fight at once (handles 30-80 movies in ~2 min)
- **Random stats each run**: spin_power, attack, defense, stamina, weight
- **Speed controls**: 1x/2x/4x buttons during battle
- **Physics**: Circular collision, arena slope pushes toward center, momentum-based knockback

## Status
- All core features implemented and ready to test
- Git repo initialized and pushed to GitHub

## Potential Enhancements (if requested)
- Sound effects
- Tournament bracket mode (alternative to battle royale)
- Save/load movie lists
- Custom color themes

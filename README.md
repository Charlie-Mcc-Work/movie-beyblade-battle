# Movie Beyblade Battle

A fun way to pick your movie night selection! Enter movie titles and watch them battle it out as spinning beyblades in an arena. The last one standing is your pick!

## How It Works

1. Enter your list of movie titles (one per line)
2. Click "BATTLE!" to start the showdown
3. Watch as each movie becomes a beyblade with random stats
4. Movies collide, deal damage, and get eliminated
5. The last movie standing wins!

## Features

- **Battle Royale Format**: All movies fight at once in a circular arena
- **Random Stats**: Each movie gets randomized attack, defense, stamina, weight, and spin power
- **Speed Controls**: 1x, 2x, or 4x speed to fit your time constraints
- **Visual Effects**: Spark particles on collision, knockout animations
- **Handles 30-80+ Movies**: Designed for large lists, battles typically last ~2 minutes

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/movie-beyblade-battle.git
cd movie-beyblade-battle

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

Then:
1. Paste or type your movie list into the text box
2. Click "BATTLE!"
3. Enjoy the chaos
4. Watch your winner get announced

## Controls

- **Text Box**: Click to focus, type or paste (Ctrl+V) movie titles
- **Speed Buttons**: Click 1x/2x/4x during battle to change simulation speed
- **Play Again**: Return to input screen after victory

## Requirements

- Python 3.8+
- Pygame 2.5+

## Stats System

Each movie beyblade gets random stats:

| Stat | Effect |
|------|--------|
| Spin Power | Visual spin speed + slight damage bonus |
| Attack | Damage dealt on collision |
| Defense | Reduces incoming damage |
| Stamina | Health pool - reach 0 and you're out |
| Weight | Affects knockback (heavier = harder to push) |

## License

MIT License - do whatever you want with it!

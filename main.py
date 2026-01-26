#!/usr/bin/env python3
"""
Movie Beyblade Battle
A fun way to pick your movie night selection!

Enter movie titles and watch them battle it out as spinning beyblades.
The last one standing wins!

Usage:
    python main.py              # Default mode (movie group)
    python main.py --girlfriend # Girlfriend mode (Charlie & Hanan)
    python main.py -g           # Short flag for girlfriend mode
"""

import argparse
from src.config import set_mode
from src.game import Game


def main():
    parser = argparse.ArgumentParser(description='Movie Beyblade Battle')
    parser.add_argument('-g', '--girlfriend', action='store_true',
                        help='Run in girlfriend mode (Charlie & Hanan)')
    args = parser.parse_args()

    # Set mode based on flag
    if args.girlfriend:
        config = set_mode('girlfriend')
        print("Running in Girlfriend Mode (Charlie & Hanan)")
    else:
        config = set_mode('default')

    game = Game(config)
    game.run()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Movie Beyblade Battle
A fun way to pick your movie night selection!

Enter movie titles and watch them battle it out as spinning beyblades.
The last one standing wins!
"""

from src.game import Game


def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()

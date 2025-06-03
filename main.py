"""Entry point for the Heroes-like game."""

from heroes import Game


def main() -> None:
    game = Game()
    game.run()


if __name__ == "__main__":
    main()

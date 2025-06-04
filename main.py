"""Entry point for the Heroes-like game."""

from heroes import Game, Menu


def main() -> None:
    menu = Menu()
    if menu.run():
        game = Game()
        game.run()


if __name__ == "__main__":
    main()

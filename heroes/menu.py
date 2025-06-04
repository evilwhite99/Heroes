import pygame
from .game import Game


class Menu:
    """Simple start menu for the game."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((Game.WINDOW_SIZE, Game.WINDOW_SIZE))
        pygame.display.set_caption("Heroes Python - Menu")
        self.clock = pygame.time.Clock()
        self.options = ["Start Game", "Quit"]
        self.selected = 0
        self.font = pygame.font.Font(None, 48)
        self.running = True

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self.selected = (self.selected - 1) % len(self.options)
                elif event.key == pygame.K_DOWN:
                    self.selected = (self.selected + 1) % len(self.options)
                elif event.key == pygame.K_RETURN:
                    if self.selected == 0:
                        return "start"
                    else:
                        return "quit"
        return None

    def draw(self):
        self.screen.fill((0, 0, 0))
        for index, option in enumerate(self.options):
            color = (255, 255, 0) if index == self.selected else (255, 255, 255)
            text = self.font.render(option, True, color)
            rect = text.get_rect(center=(Game.WINDOW_SIZE // 2, Game.WINDOW_SIZE // 2 + index * 60))
            self.screen.blit(text, rect)
        pygame.display.flip()

    def run(self):
        while self.running:
            action = self.handle_events()
            if action == "start":
                pygame.quit()
                return True
            if action == "quit":
                pygame.quit()
                return False
            self.draw()
            self.clock.tick(30)
        pygame.quit()
        return False

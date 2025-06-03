import pygame
from .hero import Hero


class Game:
    """Basic game logic and rendering."""

    GRID_SIZE = 10
    CELL_SIZE = 64
    WINDOW_SIZE = GRID_SIZE * CELL_SIZE

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((self.WINDOW_SIZE, self.WINDOW_SIZE))
        pygame.display.set_caption("Heroes Python")
        self.clock = pygame.time.Clock()
        self.hero = Hero("Player")
        self.running = True

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_LEFT]:
            dx = -1
        if keys[pygame.K_RIGHT]:
            dx = 1
        if keys[pygame.K_UP]:
            dy = -1
        if keys[pygame.K_DOWN]:
            dy = 1
        if dx or dy:
            self.hero.move(dx, dy, self.GRID_SIZE, self.GRID_SIZE)

    def draw_grid(self):
        for x in range(self.GRID_SIZE):
            for y in range(self.GRID_SIZE):
                rect = pygame.Rect(x * self.CELL_SIZE, y * self.CELL_SIZE, self.CELL_SIZE, self.CELL_SIZE)
                color = (180, 180, 180) if (x + y) % 2 == 0 else (160, 160, 160)
                pygame.draw.rect(self.screen, color, rect)

    def draw_hero(self):
        rect = pygame.Rect(
            self.hero.x * self.CELL_SIZE,
            self.hero.y * self.CELL_SIZE,
            self.CELL_SIZE,
            self.CELL_SIZE,
        )
        pygame.draw.rect(self.screen, self.hero.color, rect)

    def run(self):
        while self.running:
            self.handle_events()
            self.screen.fill((0, 0, 0))
            self.draw_grid()
            self.draw_hero()
            pygame.display.flip()
            self.clock.tick(30)

        pygame.quit()

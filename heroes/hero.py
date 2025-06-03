class Hero:
    """Simple hero representation."""

    def __init__(self, name: str, x: int = 0, y: int = 0, color: tuple = (0, 0, 255)):
        self.name = name
        self.x = x
        self.y = y
        self.color = color
        self.speed = 5

    def move(self, dx: int, dy: int, grid_width: int, grid_height: int):
        """Move hero by dx, dy within grid boundaries."""
        new_x = min(max(self.x + dx, 0), grid_width - 1)
        new_y = min(max(self.y + dy, 0), grid_height - 1)
        self.x = new_x
        self.y = new_y

    @property
    def pos(self):
        return self.x, self.y

import pygame
import math

class GameScreen:
    def __init__(self, screen, hex_grid, hex_size=30):
        """
        Initializes the game screen.

        Args:
            screen: The main Pygame screen surface.
            hex_grid: An instance of the HexGrid class from game_logic.hex_grid.
            hex_size (int): The radius of a hexagon (distance from center to a vertex).
        """
        self.screen = screen
        self.hex_grid = hex_grid
        self.hex_size = hex_size
        self.font = pygame.font.Font(None, 20) # For drawing coordinates

        # Calculate derived hex dimensions
        self.hex_width = math.sqrt(3) * self.hex_size
        self.hex_height = 2 * self.hex_size
        
        self.colors = {
            "white": (255, 255, 255),
            "black": (0, 0, 0),
            "grey": (150, 150, 150), # For hex outlines
            "red": (200, 50, 50) 
        }
        
        # Optional: Add camera/viewport offsets if map is larger than screen
        self.camera_offset_x = 20
        self.camera_offset_y = 20

    def _hex_to_pixel(self, hexagon):
        """Converts odd-r offset hex coordinates to pixel coordinates (center of hex)."""
        # For pointy-topped hexagons with "odd-r" offset
        center_x = self.camera_offset_x + self.hex_size * math.sqrt(3) * (hexagon.col + 0.5 * (hexagon.row % 2))
        center_y = self.camera_offset_y + self.hex_size * 3/2 * hexagon.row + self.hex_size # Add self.hex_size to y for better top padding
        return center_x, center_y

    def _get_hex_vertices(self, center_x, center_y):
        """Calculates the 6 vertices for a pointy-topped hexagon given its center."""
        vertices = []
        for i in range(6):
            angle_deg = 60 * i - 30 # -30 degrees to make top pointy
            angle_rad = math.pi / 180 * angle_deg
            point_x = center_x + self.hex_size * math.cos(angle_rad)
            point_y = center_y + self.hex_size * math.sin(angle_rad)
            vertices.append((point_x, point_y))
        return vertices

    def draw(self, screen_surface):
        """Draws the game screen, primarily the hex grid."""
        screen_surface.fill(self.colors["white"])

        for hexagon in self.hex_grid: # Iterate through all hexagons in the grid
            center_x, center_y = self._hex_to_pixel(hexagon)
            vertices = self._get_hex_vertices(center_x, center_y)
            
            # Draw the hexagon outline
            pygame.draw.polygon(screen_surface, self.colors["grey"], vertices, 1) 
            
            # Optional: Draw coordinates on the hex
            coord_text = f"{hexagon.col},{hexagon.row}"
            text_surf = self.font.render(coord_text, True, self.colors["black"])
            text_rect = text_surf.get_rect(center=(center_x, center_y))
            screen_surface.blit(text_surf, text_rect)

    def handle_event(self, event):
        """Handles events for the game screen (e.g., quitting)."""
        if event.type == pygame.QUIT:
            return "quit_game" # Or some other signal to main.py
        # Add other game screen specific event handling here (mouse clicks on hexes, etc.)
        return None

if __name__ == '__main__':
    # Example Usage (requires HexGrid from game_logic.hex_grid)
    # This example won't run standalone without HexGrid being importable
    # and may need adjustment of paths if game_logic is not in PYTHONPATH.
    
    # To run this example:
    # 1. Make sure game_logic/hex_grid.py exists.
    # 2. You might need to adjust sys.path if running this file directly, e.g.:
    # import sys
    # import os
    # sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    
    from game_logic.hex_grid import HexGrid # Assuming direct run from gui folder or path setup

    pygame.init()
    screen_width_example = 800
    screen_height_example = 600
    example_screen = pygame.display.set_mode((screen_width_example, screen_height_example))
    pygame.display.set_caption("Game Screen Hex Grid Test")

    example_grid = HexGrid(cols=15, rows=10) # Example grid size
    game_screen_instance = GameScreen(example_screen, example_grid, hex_size=25)

    running_example = True
    while running_example:
        for event_example in pygame.event.get():
            if event_example.type == pygame.QUIT:
                running_example = False
            action = game_screen_instance.handle_event(event_example)
            if action == "quit_game":
                running_example = False
        
        game_screen_instance.draw(example_screen)
        pygame.display.flip()

    pygame.quit()

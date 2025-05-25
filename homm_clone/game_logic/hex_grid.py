import math
from collections import namedtuple

# Using namedtuple for lightweight Hexagon objects
# Stores grid coordinates (column, row) - using offset coordinates "odd-r"
# (odd rows are shifted to the right relative to even rows)
Hexagon = namedtuple("Hexagon", ["col", "row"])

class HexGrid:
    def __init__(self, cols, rows):
        """
        Initializes a hex grid with the given number of columns and rows.
        Uses offset coordinates ("odd-r" convention).
        Example:
        (0,0) (1,0) (2,0)
          (0,1) (1,1) (2,1)
        (0,2) (1,2) (2,2)

        Args:
            cols (int): Number of columns in the grid.
            rows (int): Number of rows in the grid.
        """
        if not isinstance(cols, int) or not isinstance(rows, int) or cols <= 0 or rows <= 0:
            raise ValueError("Columns and rows must be positive integers.")

        self.cols = cols
        self.rows = rows
        
        self.grid = []
        for r in range(self.rows):
            current_row = []
            for c in range(self.cols):
                current_row.append(Hexagon(c, r))
            self.grid.append(current_row)

    def get_hexagon(self, col, row):
        """
        Retrieves the Hexagon object at the given column and row.

        Args:
            col (int): The column index.
            row (int): The row index.

        Returns:
            Hexagon: The Hexagon object if coordinates are valid, else None.
        """
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.grid[row][col]
        return None

    def __iter__(self):
        """Allows iteration over all hexagons in the grid."""
        for r in range(self.rows):
            for c in range(self.cols):
                yield self.grid[r][c]
    
    def __len__(self):
        """Returns the total number of hexagons in the grid."""
        return self.cols * self.rows

if __name__ == '__main__':
    # Example Usage:
    grid = HexGrid(cols=10, rows=8)
    
    print(f"Created a grid of {grid.cols}x{grid.rows} hexagons.")
    print(f"Total hexagons: {len(grid)}")

    hex_2_3 = grid.get_hexagon(col=2, row=3)
    if hex_2_3:
        print(f"Hexagon at (2,3): {hex_2_3}") # Output: Hexagon at (2,3): Hexagon(col=2, row=3)

    hex_invalid = grid.get_hexagon(col=10, row=8)
    print(f"Hexagon at (10,8): {hex_invalid}") # Output: Hexagon at (10,8): None

    print("\nIterating through some hexagons:")
    count = 0
    for h in grid:
        if count < 5: # Print first 5
            print(h)
        count +=1
        if count == 5: break

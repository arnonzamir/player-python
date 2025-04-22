import random

class TetrisStrategy:
    """Strategy class for Tetris gameplay focused on line completion"""
    
    def __init__(self, debug=False):
        self.debug = debug
        self.matrix_width = 10
        self.matrix_height = 20
        self.last_matrix = None
        self.current_action_sequence = []
        
    def decide_move(self, matrix):
        """Determine the next move based on the current matrix state"""
        if not matrix:
            return self._random_move()
            
        # Store matrix for comparison in subsequent calls
        previous_matrix = self.last_matrix
        self.last_matrix = matrix
        
        # If we have an action sequence in progress, continue with it
        if self.current_action_sequence:
            next_action = self.current_action_sequence.pop(0)
            if self.debug:
                print(f"Following action sequence: {next_action}")
            return next_action
            
        # Analyze the board state
        heights = self._get_column_heights(matrix)
        holes = self._count_holes(matrix)
        bumpiness = self._calculate_bumpiness(heights)
        active_piece = self._identify_active_piece(matrix, previous_matrix)
        
        if self.debug:
            print(f"Column heights: {heights}")
            print(f"Holes: {holes}, Bumpiness: {bumpiness:.2f}")
            if active_piece:
                print(f"Active piece cells: {active_piece}")
        
        # Evaluate possible moves and create an action sequence
        self._plan_action_sequence(matrix, heights, holes, bumpiness, active_piece)
        
        # If we created an action sequence, return the first action
        if self.current_action_sequence:
            next_action = self.current_action_sequence.pop(0)
            if self.debug:
                print(f"Starting new action sequence with: {next_action}")
            return next_action
            
        # Fallback to basic strategy
        return self._basic_strategy(matrix, heights, holes, bumpiness, active_piece)
    
    def _random_move(self):
        """Return a random move (fallback)"""
        return random.choice(['LEFT', 'RIGHT', 'DOWN', 'ROTATE_CW'])
    
    def _get_column_heights(self, matrix):
        """Get the height of each column in the matrix"""
        heights = [0] * self.matrix_width
        
        # Find the highest block in each column
        for col in range(self.matrix_width):
            for row_idx, row in enumerate(matrix):
                if "cells" in row and col < len(row["cells"]) and row["cells"][col] > 0:
                    heights[col] = self.matrix_height - row["line"]
                    break
        
        return heights
    
    def _count_holes(self, matrix):
        """Count empty cells with blocks above them"""
        holes = 0
        column_tops = [self.matrix_height] * self.matrix_width  # Start with max height
        
        # Find the top piece in each column
        for row in matrix:
            if "cells" in row:
                line_num = row["line"]
                cells = row["cells"]
                for col in range(min(len(cells), self.matrix_width)):
                    if cells[col] > 0:
                        column_tops[col] = min(column_tops[col], line_num)
        
        # Count holes (empty cells below the top block in each column)
        for row in matrix:
            if "cells" in row:
                line_num = row["line"]
                cells = row["cells"]
                for col in range(min(len(cells), self.matrix_width)):
                    if cells[col] == 0 and line_num > column_tops[col]:
                        holes += 1
        
        return holes
    
    def _calculate_bumpiness(self, heights):
        """Calculate the sum of differences between adjacent columns"""
        if not heights:
            return 0
            
        bumpiness = 0
        for i in range(len(heights) - 1):
            bumpiness += abs(heights[i] - heights[i+1])
            
        return bumpiness
    
    def _identify_active_piece(self, matrix, previous_matrix):
        """Identify the active piece by comparing current and previous matrices"""
        if not previous_matrix:
            return None
            
        # Find cells that are different between current and last matrix
        active_cells = []
        
        for row in matrix:
            if "cells" in row:
                line_num = row["line"]
                cells = row["cells"]
                
                # Find matching row in previous matrix
                last_row = None
                for lr in previous_matrix:
                    if "line" in lr and lr["line"] == line_num and "cells" in lr:
                        last_row = lr
                        break
                
                if last_row:
                    last_cells = last_row.get("cells", [])
                    for col in range(min(len(cells), len(last_cells))):
                        # Cell has a piece now but was empty before
                        if cells[col] > 0 and col < len(last_cells) and last_cells[col] == 0:
                            active_cells.append((line_num, col))
        
        return active_cells if active_cells else None
    
    def _plan_action_sequence(self, matrix, heights, holes, bumpiness, active_piece):
        """Create a sequence of actions to complete lines"""
        # Reset current action sequence
        self.current_action_sequence = []
        
        # If we can't identify the active piece, we can't plan effectively
        if not active_piece or len(active_piece) == 0:
            return
            
        # Analyze the board to find potential line completions
        potential_lines = self._identify_potential_lines(matrix)
        
        if potential_lines:
            # Find the most promising line to complete (closest to being complete)
            target_line = max(potential_lines, key=lambda x: x[1])
            target_row = target_line[0]
            
            # Check if active piece is near the target row
            piece_rows = [cell[0] for cell in active_piece]
            piece_cols = [cell[1] for cell in active_piece]
            avg_row = sum(piece_rows) / len(piece_rows)
            avg_col = sum(piece_cols) / len(piece_cols)
            
            # Calculate moves to get to the target position
            actions = []
            
            # First focus on horizontal positioning
            if avg_col < self._get_target_column(matrix, target_row):
                actions.extend(['RIGHT'] * min(3, int(self._get_target_column(matrix, target_row) - avg_col)))
            else:
                actions.extend(['LEFT'] * min(3, int(avg_col - self._get_target_column(matrix, target_row))))
                
            # Add some rotations if needed to fit better
            if random.random() < 0.3:
                actions.append('ROTATE_CW')
                
            # Drop when in position
            actions.append('DROP')
            
            # Limit sequence length to avoid getting stuck
            self.current_action_sequence = actions[:5]
        else:
            # No potential lines identified, try to keep the stack low and even
            self._plan_minimal_height_sequence(matrix, heights, active_piece)
    
    def _identify_potential_lines(self, matrix):
        """Identify rows that are close to being complete"""
        potential_lines = []
        
        for row in matrix:
            if "cells" in row:
                line_num = row["line"]
                cells = row["cells"]
                filled_cells = sum(1 for cell in cells if cell > 0)
                
                # If the row is at least 70% filled, consider it a potential completion
                if filled_cells >= 7:  # 70% of a 10-column board
                    potential_lines.append((line_num, filled_cells))
        
        return potential_lines
    
    def _get_target_column(self, matrix, target_row):
        """Find the best column to place a piece for completing the target row"""
        # Look for gaps in the target row
        for row in matrix:
            if "line" in row and row["line"] == target_row and "cells" in row:
                cells = row["cells"]
                for col, cell in enumerate(cells):
                    if cell == 0:
                        return col
                        
        # If no gaps found, aim for the middle
        return self.matrix_width / 2
    
    def _plan_minimal_height_sequence(self, matrix, heights, active_piece):
        """Plan a sequence that minimizes stack height and creates a flat surface"""
        # Target the lowest column
        lowest_col = heights.index(min(heights))
        
        # Check position of active piece
        piece_cols = [cell[1] for cell in active_piece]
        avg_col = sum(piece_cols) / len(piece_cols) if piece_cols else 5
        
        actions = []
        
        # Move towards the lowest column
        if avg_col < lowest_col:
            actions.extend(['RIGHT'] * min(3, int(lowest_col - avg_col)))
        else:
            actions.extend(['LEFT'] * min(3, int(avg_col - lowest_col)))
            
        # Add rotation for variety
        if random.random() < 0.4:
            actions.append(random.choice(['ROTATE_CW', 'ROTATE_CCW']))
            
        # Drop to place the piece
        actions.append('DROP')
        
        # Limit sequence length
        self.current_action_sequence = actions[:4]
    
    def _basic_strategy(self, matrix, heights, holes, bumpiness, active_piece):
        """Basic strategy when planning fails"""
        # 1. If we have too many holes, try to fill them by moving towards lower columns
        if holes > 3:
            min_height_col = heights.index(min(heights))
            # Move toward the lowest column
            if active_piece and len(active_piece) > 0:
                active_col = active_piece[0][1]  # Column of first active cell
                if active_col < min_height_col:
                    return 'RIGHT'
                elif active_col > min_height_col:
                    return 'LEFT'
                else:
                    return 'DROP'  # Drop if we're above the target column
        
        # 2. If the surface is very uneven, try to make it more even
        if bumpiness > 5:
            # Find the highest column
            max_height_col = heights.index(max(heights))
            
            # Try to avoid placing pieces on the highest column
            if active_piece and len(active_piece) > 0:
                active_col = active_piece[0][1]
                if active_col == max_height_col:
                    # Move away from the highest column
                    return 'LEFT' if max_height_col > self.matrix_width/2 else 'RIGHT'
        
        # 3. Occasionally rotate for better positioning
        if random.random() < 0.3:
            return random.choice(['ROTATE_CW', 'ROTATE_CCW'])
            
        # 4. Drop if we've found a good position
        if random.random() < 0.15:
            return 'DROP'
            
        # 5. Otherwise, make a semi-random move with bias toward moving down
        return random.choices(
            ['LEFT', 'RIGHT', 'DOWN', 'ROTATE_CW'], 
            weights=[0.2, 0.2, 0.5, 0.1]
        )[0] 
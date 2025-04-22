import requests
import time
import random
import signal
import sys
import argparse
import json
from tetris_strategy import TetrisStrategy

class TetrisBot:
    def __init__(self, session_id, server_url='tetris-server.example.com', port=3001):
        self.session_id = session_id
        self.base_url = f"https://{server_url}:{port}/api/tetris/{session_id}"
        self.running = False
        self.matrix_width = 10  # Standard Tetris width
        self.matrix_height = 20  # Standard Tetris height
        self.debug = False
        self.game_paused = False  # Track if the game is currently paused
        self.pause_start_time = 0  # Track when the game was paused
        self.last_resume_attempt = 0  # Track when we last tried to resume
        self.game_over = False  # Track if the game is in GAME_OVER state
        self.last_restart_attempt = 0  # Track when we last tried to restart
        self.strategy = None  # Will be initialized in start()
    
    def start(self):
        """Start the bot and the game loop"""
        print(f"Starting bot for session: {self.session_id}")
        print(f"Using API URL: {self.base_url}")
        self.running = True
        
        # Initialize the strategy
        self.strategy = TetrisStrategy(debug=self.debug)
        
        # Check initial game status
        status = self.get_status()
        if status and status.get('state') == 'PAUSED':
            self.game_paused = True
            self.pause_start_time = time.time()
            print("Game is paused. Will auto-resume after 3 seconds.")
        
        # Send restart command to start the game
        response = self.send_command('RESTART')
        if not response:
            print("Failed to restart game. Checking API connection...")
            self.check_api_connection()
        
        # Start the game loop
        self.game_loop()
    
    def stop(self):
        """Stop the bot"""
        self.running = False
        print(f"Stopping bot for session: {self.session_id}")
    
    def get_status(self):
        """Get the current game status using the status endpoint"""
        try:
            url = f"{self.base_url}/status"
            response = requests.get(url, timeout=3)
            
            if response.status_code == 200:
                try:
                    if response.text.strip():
                        data = response.json()
                        if self.debug:
                            print(f"Game status: {data}")
                        return data
                    else:
                        print(f"Received empty response from status endpoint")
                        return None
                except json.JSONDecodeError as e:
                    print(f"Error parsing status JSON: {e}")
                    print(f"Response text: {response.text[:100]}")
                    return None
            else:
                print(f"Error getting status: Status code {response.status_code}")
                print(f"Response text: {response.text[:100]}")
                return None
        except Exception as e:
            print(f"Error getting status: {e}")
            return None
    
    def check_api_connection(self):
        """Check if we can connect to the API"""
        try:
            # Try to access the base URL for the session
            print(f"Testing connection to: {self.base_url}")
            response = requests.get(f"{self.base_url}")
            print(f"Response status code: {response.status_code}")
            try:
                content = response.text[:100] + ("..." if len(response.text) > 100 else "")
                print(f"Response content (truncated): {content}")
            except:
                print("Couldn't display response content")
            
            # Maybe the correct URL doesn't include the /tetris part
            test_url = self.base_url.replace('/tetris/', '/')
            print(f"Testing alternative URL: {test_url}")
            response = requests.get(test_url)
            print(f"Response status code: {response.status_code}")
            
            # Try accessing /api directly
            base_parts = self.base_url.split('/api/')
            if len(base_parts) > 1:
                api_url = f"{base_parts[0]}/api"
                print(f"Testing API root: {api_url}")
                response = requests.get(api_url)
                print(f"Response status code: {response.status_code}")
                
        except Exception as e:
            print(f"Connection test failed: {e}")
    
    def game_loop(self):
        """Main game loop that continuously gets state and sends commands"""
        connection_errors = 0
        max_connection_errors = 5
        last_status_check = 0
        
        while self.running:
            try:
                current_time = time.time()
                
                # Check game status every second
                if current_time - last_status_check > 1:
                    status = self.get_status()
                    last_status_check = current_time
                    
                    if status and 'state' in status:
                        is_currently_paused = status['state'] == 'PAUSED'
                        is_game_over = status['state'] == 'GAME_OVER'
                        
                        # Game just became paused
                        if is_currently_paused and not self.game_paused:
                            print("Game is now paused. Will auto-resume after 3 seconds.")
                            self.game_paused = True
                            self.pause_start_time = current_time
                        
                        # Game was paused but now is playing
                        elif not is_currently_paused and self.game_paused:
                            print("Game has been resumed.")
                            self.game_paused = False
                            
                        # Game just entered GAME_OVER state
                        if is_game_over and not self.game_over:
                            print("Game is now in GAME_OVER state. Will auto-restart every 5 seconds.")
                            self.game_over = True
                            
                        # Game was over but now is playing
                        elif not is_game_over and self.game_over:
                            print("Game has been restarted.")
                            self.game_over = False
                
                # If the game is in GAME_OVER state
                if self.game_over:
                    # Auto-restart if game over for more than 5 seconds since last attempt
                    if current_time - self.last_restart_attempt > 5:
                        print("Auto-restarting game after game over...")
                        self.send_command('RESTART')
                        self.last_restart_attempt = current_time
                        print("Will attempt to restart again in 5 seconds if still game over.")
                        
                    # Skip the rest of the loop while in game over state
                    time.sleep(0.2)
                    continue
                
                # If the game is paused
                if self.game_paused:
                    # Auto-resume if paused for more than 3 seconds
                    if current_time - self.pause_start_time > 3 and current_time - self.last_resume_attempt > 3:
                        print("Auto-resuming game after 3 seconds...")
                        self.send_command('RESUME')
                        self.last_resume_attempt = current_time
                        print("Will wait 3 seconds before trying to resume again if needed.")
                        
                    # Skip the rest of the loop while paused
                    time.sleep(0.2)
                    continue
                
                # Only execute this section when the game is not paused or game over
                matrix = self.get_matrix()
                
                if matrix:
                    # Reset error counter if we got valid data
                    connection_errors = 0
                    
                    if self.debug:
                        self.print_matrix(matrix)
                    
                    # Analyze the matrix and decide next move
                    next_move = self.decide_next_move(matrix)
                    
                    # Send the command
                    self.send_command(next_move)
                else:
                    connection_errors += 1
                    print(f"No valid matrix data received ({connection_errors}/{max_connection_errors})")
                    
                    if connection_errors >= max_connection_errors:
                        print("Too many connection errors. Checking API connection...")
                        self.check_api_connection()
                        connection_errors = 0  # Reset counter after check
                
                # Wait before next iteration
                time.sleep(0.2)
                
            except Exception as e:
                print(f"Error in game loop: {e}")
                time.sleep(1)  # Wait a bit longer if there's an error
    
    def print_matrix(self, matrix):
        """Print the matrix in a readable format for debugging"""
        print("\nCurrent Matrix:")
        for row in matrix:
            line_num = row.get("line", 0)
            cells = row.get("cells", [0] * self.matrix_width)
            print(f"Line {line_num:2d}: {cells}")
        print()
    
    def send_command(self, command):
        """Send a command to the Tetris game"""
        try:
            url = f"{self.base_url}/command?command={command}"
            print(f"Sending command: {command} to URL: {url}")
            response = requests.get(url, timeout=3)
            
            if response.status_code == 200:
                print(f"Sent command: {command}")
                try:
                    if response.text.strip():
                        return response.json()
                    else:
                        print(f"Command sent, but received empty response")
                        return None
                except json.JSONDecodeError as e:
                    print(f"Command sent, but received invalid JSON: {e}")
                    print(f"Response text: {response.text[:100]}")
                    return None
            else:
                print(f"Error sending command {command}: Status code {response.status_code}")
                print(f"Response text: {response.text[:100]}")
                return None
        except requests.exceptions.Timeout:
            print(f"Timeout sending command {command}")
            return None
        except requests.exceptions.ConnectionError:
            print(f"Connection error sending command {command}")
            return None
        except Exception as e:
            print(f"Error sending command {command}: {e}")
            return None
    
    def get_matrix(self):
        """Get the current game matrix state"""
        try:
            url = f"{self.base_url}/matrix"
            response = requests.get(url, timeout=3)
            
            if response.status_code == 200:
                try:
                    if response.text.strip():
                        data = response.json()
                        return data.get('matrix', [])
                    else:
                        print(f"Received empty response from matrix endpoint")
                        return []
                except json.JSONDecodeError as e:
                    print(f"Error parsing matrix JSON: {e}")
                    print(f"Response text: {response.text[:100]}")
                    return []
            else:
                print(f"Error getting matrix: Status code {response.status_code}")
                print(f"Response text: {response.text[:100]}")
                return []
        except requests.exceptions.Timeout:
            print(f"Timeout getting matrix")
            return []
        except requests.exceptions.ConnectionError:
            print(f"Connection error getting matrix")
            return []
        except Exception as e:
            print(f"Error getting matrix: {e}")
            return []
    
    def decide_next_move(self, matrix):
        """Delegate move decision to the strategy class"""
        return self.strategy.decide_move(matrix)


def signal_handler(sig, frame):
    """Handle Ctrl+C to stop the bot gracefully"""
    print("Ctrl+C detected. Shutting down...")
    if 'bot' in globals():
        bot.stop()
    sys.exit(0)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Tetris Bot using HTTP API')
    
    parser.add_argument('-s', '--server', type=str, default='tetris-server.example.com',
                        help='Tetris server hostname (default: tetris-server.example.com)')
    parser.add_argument('-p', '--port', type=int, default=3001,
                        help='HTTP API port (default: 3001)')
    parser.add_argument('-i', '--session-id', type=str, default='my-bot-session',
                        help='Game session ID (default: my-bot-session)')
    parser.add_argument('--http-protocol', type=str, choices=['http', 'https'], default='https',
                        help='HTTP protocol to use (default: https)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug output')
    parser.add_argument('--api-path', type=str, default='/api/tetris/',
                        help='API path (default: /api/tetris/)')
    
    return parser.parse_args()

if __name__ == "__main__":
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Update the base URL based on the protocol
    TetrisBot.__init__ = lambda self, session_id, server_url=args.server, port=args.port: (
        setattr(self, 'session_id', session_id),
        setattr(self, 'base_url', f"{args.http_protocol}://{server_url}:{port}{args.api_path}{session_id}"),
        setattr(self, 'running', False),
        setattr(self, 'matrix_width', 10),
        setattr(self, 'matrix_height', 20),
        setattr(self, 'debug', args.debug),
        setattr(self, 'game_paused', False),
        setattr(self, 'pause_start_time', 0),
        setattr(self, 'last_resume_attempt', 0),
        setattr(self, 'game_over', False),
        setattr(self, 'last_restart_attempt', 0),
        setattr(self, 'strategy', None)
    )[-1]
    
    # Create and start the bot
    print(f"Starting Tetris bot with settings:")
    print(f"  Server: {args.http_protocol}://{args.server}:{args.port}")
    print(f"  API Path: {args.api_path}")
    print(f"  Session ID: {args.session_id}")
    
    bot = TetrisBot(args.session_id, args.server, args.port)
    bot.start() 
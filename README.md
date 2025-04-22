# Tetris Bot (HTTP API)

A Python-based bot that can play Tetris automatically using the HTTP API.

## Features

- Connects to a Tetris server using HTTP API
- Analyzes game board to make intelligent moves
- Tries to maintain a balanced stack and minimize holes
- Customizable server, port and session ID via command-line arguments

## Requirements

- Python 3.6 or higher
- `requests` library for HTTP communication

Install dependencies:
```bash
pip install requests
```

## Usage

Basic usage:
```bash
python tetris_bot_http.py
```

This will connect to the default server (`tetris-server.example.com`) and session (`my-bot-session`). 

### Command-line Options

Customize the bot behavior with these command-line arguments:

```bash
python tetris_bot_http.py -s your-server.com -p 3001 -i your-session-id
```

Available options:
- `-s, --server`: Specify the Tetris server hostname (default: tetris-server.example.com)
- `-p, --port`: Specify the HTTP API port (default: 3001)
- `-i, --session-id`: Specify the game session ID (default: my-bot-session)
- `--http-protocol`: Choose between `http` or `https` protocol (default: https)

Example with all options:
```bash
python tetris_bot_http.py --server tetris.example.com --port 3001 --session-id player1 --http-protocol http
```

## Algorithm

The bot uses a simple but effective algorithm to play Tetris:

1. Analyzes the heights of each column in the game board
2. Counts holes (empty cells with blocks above them) 
3. Tries to keep the surface as even as possible
4. Identifies the active piece by comparing the current and previous board state
5. Makes decisions based on the board state:
   - Tries to fill holes
   - Avoids piling pieces on already tall columns
   - Occasionally rotates pieces for better positioning
   - Drops pieces when well-positioned

## Extending the Bot

You can improve the bot by enhancing the `decide_next_move()` method with more sophisticated algorithms such as:

- Implementing proper piece recognition logic
- Adding look-ahead to evaluate potential future moves
- Using reinforcement learning to improve decision making
- Implementing a more sophisticated evaluation function

## Troubleshooting

If you encounter issues:

1. Make sure the Tetris server is running and accessible
2. Check if the port and protocol (http/https) are correct
3. Verify that your session ID is valid
4. Check for any network-related issues (firewalls, proxy settings, etc.)

## License

This code is available under the MIT License. 
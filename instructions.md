# Programmatic Tetris Control Guide

This document provides comprehensive instructions for developers who want to create programs that can automatically play the Tetris game using the available APIs.

## Overview

The Multi-Session MQTT Tetris application exposes two APIs for programmatic control:

1. **MQTT API** - Real-time messaging using MQTT over WebSockets
2. **HTTP REST API** - Simple HTTP endpoints for commands and game state

Each game session has a unique session ID, with its own independent game state and control channels. This allows running multiple automated games simultaneously or creating competitive scenarios between different algorithms.

## Connecting to an Existing Deployment

If you've been provided with a link to an already running Tetris server, you'll need:

1. **Base URL** - The hostname where the application is hosted (replace `tetris-server.example.com` in examples with your actual server URL)
2. **WebSocket MQTT Port** - Usually port 9001 for WebSocket connections
3. **HTTP API Port** - Usually port 3001 for HTTP API

## Getting Started

1. Create a new game session by accessing:
   ```
   https://tetris-server.example.com/#/session/my-bot-session
   ```
   Replace `tetris-server.example.com` with your server address and `my-bot-session` with your desired session name.

2. Send a command to move right:
   ```bash
   curl "https://tetris-server.example.com:3001/api/tetris/my-bot-session/command?command=RIGHT"
   ```

3. Get the current game state:
   ```bash
   curl "https://tetris-server.example.com:3001/api/tetris/my-bot-session/matrix"
   ```

## Available Commands

The following commands can be sent to control the game:

| Command | Description |
|---------|-------------|
| RIGHT | Move the piece right |
| LEFT | Move the piece left |
| DOWN | Move the piece down |
| DROP | Hard drop the piece |
| ROTATE_CW | Rotate piece clockwise |
| ROTATE_CCW | Rotate piece counter-clockwise |
| HOLD | Hold the current piece |
| PAUSE | Pause the game |
| RESUME | Resume the game |
| RESTART | Restart the game |

## Understanding the Game Matrix

The game board is represented as a matrix of cells. Each cell can be empty (0) or contain a piece (1-7). The matrix is published whenever the game state changes.

Matrix data format:
```json
[
  {"line": 0},
  {"line": 1, "cells": [0,0,1,1,0,0,0,0,0,0]},
  {"line": 2, "cells": [0,0,1,1,0,0,0,0,0,0]},
  {"line": 3},
  // ... more lines
]
```

Where:
- Lines without a `cells` property are empty rows
- `0` represents an empty cell
- Values `1-7` represent different tetromino pieces:
  - `1`: I-piece (cyan)
  - `2`: J-piece (blue)
  - `3`: L-piece (orange)
  - `4`: O-piece (yellow) 
  - `5`: S-piece (green)
  - `6`: T-piece (purple)
  - `7`: Z-piece (red)

## API Reference

### HTTP API

#### Send Commands

Send a command to control the game:
```
GET https://tetris-server.example.com:3001/api/tetris/{sessionId}/command?command={COMMAND}
```

Example:
```bash
curl "https://tetris-server.example.com:3001/api/tetris/my-bot-session/command?command=RIGHT"
```

Response:
```json
{
  "success": true,
  "message": "Command \"RIGHT\" sent to session \"my-bot-session\""
}
```

#### Get Matrix Data

Get the current game board state:
```
GET https://tetris-server.example.com:3001/api/tetris/{sessionId}/matrix
```

Example:
```bash
curl "https://tetris-server.example.com:3001/api/tetris/my-bot-session/matrix"
```

Response:
```json
{
  "success": true,
  "sessionId": "my-bot-session",
  "matrix": [
    {"line": 0},
    {"line": 1, "cells": [0,0,1,1,0,0,0,0,0,0]},
    {"line": 2, "cells": [0,0,1,1,0,0,0,0,0,0]},
    // ... more lines
  ]
}
```

#### Get Game Status

Get the current status of a game session:
```
GET https://tetris-server.example.com:3001/api/tetris/{sessionId}/status
```

Example:
```bash
curl "https://tetris-server.example.com:3001/api/tetris/my-bot-session/status"
```

Response:
```json
{
  "success": true,
  "sessionId": "my-bot-session",
  "exists": true,
  "state": "PLAYING",
  "lastUpdated": "2023-06-22T14:35:27.123Z"
}
```

#### List All Active Sessions

Get a list of all active game sessions:
```
GET https://tetris-server.example.com:3001/api/tetris/sessions
```

Example:
```bash
curl "https://tetris-server.example.com:3001/api/tetris/sessions"
```

Response:
```json
{
  "success": true,
  "count": 2,
  "sessions": [
    {
      "sessionId": "session1",
      "state": "PLAYING",
      "lastUpdated": "2023-06-22T14:35:27.123Z"
    },
    {
      "sessionId": "session2",
      "state": "PAUSED",
      "lastUpdated": "2023-06-22T14:33:12.456Z"
    }
  ]
}
```

### MQTT API

#### Connect to MQTT Broker

Connect to the MQTT broker using WebSockets:
```
ws://tetris-server.example.com:9001
```

#### Send Commands

Publish a command to the control topic:
```
tetris/{sessionId}/control
```

Example (using mosquitto_pub):
```bash
mosquitto_pub -h tetris-server.example.com -p 9001 -t tetris/my-bot-session/control -m "RIGHT"
```

#### Receive Matrix Updates

Subscribe to the matrix topic to receive game state updates:
```
tetris/{sessionId}/matrix
```

Example (using mosquitto_sub):
```bash
mosquitto_sub -h tetris-server.example.com -p 9001 -t tetris/my-bot-session/matrix -v
```

#### Receive Heartbeat Updates

Subscribe to the heartbeat topic to receive real-time game status updates:
```
tetris/{sessionId}/heartbeat
```

Example (using mosquitto_sub):
```bash
mosquitto_sub -h tetris-server.example.com -p 9001 -t tetris/my-bot-session/heartbeat -v
```

The heartbeat payload contains:
```json
{
  "state": "PLAYING",
  "points": 1200,
  "lines": 12,
  "timestamp": "2023-06-22T14:35:27.123Z"
}
```

Heartbeats are published every 5 seconds while a session is active.

## Implementing an Automated Player

Below is a simple example of how to create an automated player using Node.js and the HTTP API:

```javascript
const axios = require('axios');

class TetrisBot {
  constructor(sessionId, serverUrl = 'tetris-server.example.com') {
    this.sessionId = sessionId;
    this.baseUrl = `https://${serverUrl}:3001/api/tetris/${sessionId}`;
    this.running = false;
  }

  async start() {
    console.log(`Starting bot for session: ${this.sessionId}`);
    this.running = true;
    
    // Send restart command to start the game
    await this.sendCommand('RESTART');
    
    // Start the game loop
    this.gameLoop();
  }
  
  stop() {
    this.running = false;
    console.log(`Stopping bot for session: ${this.sessionId}`);
  }
  
  async gameLoop() {
    while (this.running) {
      try {
        // 1. Check game status first
        const status = await this.getStatus();
        
        // Only process moves if the game is in a PLAYING state
        if (status.state === 'PLAYING') {
          // 2. Get current game state
          const matrix = await this.getMatrix();
          
          // 3. Analyze the matrix and decide next move
          const nextMove = this.decideNextMove(matrix);
          
          // 4. Send the command
          await this.sendCommand(nextMove);
        } else {
          // If game is paused or ended, try to resume it
          console.log(`Game is in ${status.state} state, attempting to resume...`);
          await this.sendCommand('RESUME');
        }
        
        // 5. Wait a bit before next iteration
        await this.sleep(100);
      } catch (error) {
        console.error('Error in game loop:', error.message);
        await this.sleep(1000);
      }
    }
  }
  
  async sendCommand(command) {
    try {
      const response = await axios.get(`${this.baseUrl}/command?command=${command}`);
      console.log(`Sent command: ${command}, response:`, response.data);
      return response.data;
    } catch (error) {
      console.error(`Error sending command ${command}:`, error.message);
      throw error;
    }
  }
  
  async getMatrix() {
    try {
      const response = await axios.get(`${this.baseUrl}/matrix`);
      return response.data.matrix;
    } catch (error) {
      console.error('Error getting matrix:', error.message);
      throw error;
    }
  }
  
  async getStatus() {
    try {
      const response = await axios.get(`${this.baseUrl}/status`);
      return response.data;
    } catch (error) {
      console.error('Error getting status:', error.message);
      throw error;
    }
  }
  
  decideNextMove(matrix) {
    // This is where your game logic goes
    // Analyze the matrix and decide the best move
    
    // For this example, just randomly choose a move
    const moves = ['LEFT', 'RIGHT', 'DOWN', 'ROTATE_CW', 'DROP'];
    const randomIndex = Math.floor(Math.random() * moves.length);
    return moves[randomIndex];
  }
  
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// Usage
const bot = new TetrisBot('my-bot-session', 'tetris-server.example.com');
bot.start();

// Handle graceful shutdown
process.on('SIGINT', () => {
  bot.stop();
  process.exit(0);
});
```

## Tips for Advanced Algorithms

When implementing a Tetris-playing algorithm, consider these strategies:

1. **Piece Recognition**: Extract the current piece from the matrix by comparing consecutive frames
2. **Next Piece Planning**: Consider all possible placements of the current piece
3. **Evaluation Functions**: Score potential moves based on criteria like:
   - Height of the stack
   - Number of complete lines
   - Number of "holes" (empty cells with blocks above them)
   - Smoothness of the surface
4. **Look-ahead**: Plan multiple moves in advance
5. **Pattern Recognition**: Identify common patterns like tetris-ready formations

## Performance Considerations

1. **Polling Rate**: Don't overwhelm the API with too many requests; aim for 5-10 requests per second at most
2. **MQTT vs HTTP**: For real-time monitoring, MQTT is more efficient as it pushes updates; for sending commands, either API works well
3. **Error Handling**: Implement robust error handling to recover from network issues or API errors
4. **Game State Tracking**: Maintain your own local copy of the game state to reduce API calls

## Monitoring Multiple Sessions

The heartbeat system and status endpoints make it easy to monitor multiple game sessions simultaneously. This is useful for:

1. **Tournament Scenarios**: Run multiple bots against each other and track their progress
2. **Performance Metrics**: Compare different algorithms under the same conditions
3. **Session Management**: Identify inactive or stuck sessions that need attention

### Example: Session Monitor

Here's a simple Node.js script that monitors all active sessions:

```javascript
const axios = require('axios');
const mqtt = require('mqtt');

class SessionMonitor {
  constructor(serverUrl = 'tetris-server.example.com') {
    this.serverUrl = serverUrl;
    this.apiBaseUrl = `https://${serverUrl}:3001/api`;
    this.activeSessions = new Map();
    this.mqttClient = null;
  }
  
  async start() {
    console.log('Starting Tetris session monitor...');
    
    // Connect to MQTT
    this.mqttClient = mqtt.connect(`ws://${this.serverUrl}:9001`);
    
    this.mqttClient.on('connect', () => {
      console.log('Connected to MQTT broker');
      // Subscribe to all heartbeats using wildcard
      this.mqttClient.subscribe('tetris/+/heartbeat');
    });
    
    this.mqttClient.on('message', (topic, message) => {
      // Extract session ID from topic (format: tetris/{sessionId}/heartbeat)
      const sessionId = topic.split('/')[1];
      try {
        const data = JSON.parse(message.toString());
        this.updateSessionData(sessionId, data);
      } catch (err) {
        console.error(`Error parsing message from ${topic}:`, err);
      }
    });
    
    // Also poll HTTP API periodically to catch sessions that aren't sending heartbeats
    this.startPolling();
  }
  
  updateSessionData(sessionId, data) {
    // Update our local map of active sessions
    this.activeSessions.set(sessionId, {
      ...data,
      lastUpdated: data.timestamp || new Date().toISOString()
    });
    
    console.log(`Session ${sessionId} update: ${data.state}, points: ${data.points}, lines: ${data.lines}`);
  }
  
  async startPolling() {
    setInterval(async () => {
      try {
        // Get all sessions from the API
        const response = await axios.get(`${this.apiBaseUrl}/tetris/sessions`);
        if (response.data && response.data.sessions) {
          response.data.sessions.forEach(session => {
            // Add any sessions we're not already tracking via MQTT
            if (!this.activeSessions.has(session.sessionId)) {
              this.activeSessions.set(session.sessionId, session);
            }
          });
        }
        
        // Check for inactive sessions (no heartbeat for > 30 seconds)
        const now = new Date();
        this.activeSessions.forEach((data, sessionId) => {
          const lastUpdated = new Date(data.lastUpdated);
          const secondsSinceUpdate = (now - lastUpdated) / 1000;
          
          if (secondsSinceUpdate > 30) {
            console.log(`Warning: Session ${sessionId} hasn't sent a heartbeat in ${Math.round(secondsSinceUpdate)} seconds`);
          }
        });
      } catch (err) {
        console.error('Error polling sessions API:', err);
      }
    }, 15000); // Poll every 15 seconds
  }
  
  stop() {
    if (this.mqttClient) {
      this.mqttClient.end();
    }
    console.log('Session monitor stopped');
  }
}

// Usage
const monitor = new SessionMonitor('tetris-server.example.com');
monitor.start();

// Handle graceful shutdown
process.on('SIGINT', () => {
  monitor.stop();
  process.exit(0);
});
```

This monitor provides a real-time overview of all game sessions, helping you track progress and identify issues.

## Advanced Example: Python MQTT Client

Here's an example of a Python client using MQTT for real-time updates:

```python
import paho.mqtt.client as mqtt
import json
import time
import requests
import random

class TetrisBotMQTT:
    def __init__(self, session_id, server_url='tetris-server.example.com'):
        self.session_id = session_id
        self.server_url = server_url
        self.mqtt_client = mqtt.Client(transport="websockets")
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.http_base_url = f"https://{server_url}:3001/api/tetris/{session_id}"
        self.current_matrix = None
        self.running = False
    
    def start(self):
        print(f"Starting MQTT bot for session: {self.session_id}")
        self.running = True
        
        # Connect to MQTT broker
        self.mqtt_client.connect(self.server_url, 9001, 60)
        self.mqtt_client.loop_start()
        
        # Start the game via HTTP
        self.send_command("RESTART")
        
        # Start decision loop
        self.decision_loop()
    
    def stop(self):
        self.running = False
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
        print(f"Stopped MQTT bot for session: {self.session_id}")
    
    def on_connect(self, client, userdata, flags, rc):
        print(f"Connected to MQTT broker with result code {rc}")
        # Subscribe to matrix updates
        client.subscribe(f"tetris/{self.session_id}/matrix")
        # Subscribe to heartbeat updates
        client.subscribe(f"tetris/{self.session_id}/heartbeat")
    
    def on_message(self, client, userdata, msg):
        if msg.topic == f"tetris/{self.session_id}/matrix":
            try:
                self.current_matrix = json.loads(msg.payload.decode())
                # Matrix updated, we could trigger analysis here
            except Exception as e:
                print(f"Error parsing matrix data: {e}")
        elif msg.topic == f"tetris/{self.session_id}/heartbeat":
            try:
                heartbeat = json.loads(msg.payload.decode())
                print(f"Heartbeat: state={heartbeat['state']}, points={heartbeat['points']}, lines={heartbeat['lines']}")
                # Use heartbeat data for game status monitoring
            except Exception as e:
                print(f"Error parsing heartbeat data: {e}")
    
    def send_command(self, command):
        try:
            response = requests.get(f"{self.http_base_url}/command?command={command}")
            print(f"Sent command: {command}")
            return response.json()
        except Exception as e:
            print(f"Error sending command {command}: {e}")
    
    def decision_loop(self):
        while self.running:
            if self.current_matrix:
                # Analyze the matrix and decide move
                move = self.decide_next_move()
                self.send_command(move)
            time.sleep(0.2)  # Sleep to avoid overwhelming the API
    
    def decide_next_move(self):
        # Implement your game logic here
        moves = ['LEFT', 'RIGHT', 'DOWN', 'ROTATE_CW', 'DROP']
        return random.choice(moves)

# Usage
bot = TetrisBotMQTT("my-bot-session", "tetris-server.example.com")
bot.start()

try:
    # Keep the main thread running
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    bot.stop()
```

## Conclusion

This guide provides the fundamentals for creating programs that can play Tetris through the provided API. The multi-session nature of the application makes it ideal for running competitions between different algorithms or testing various strategies.

Make sure to check the game interface at your provided server URL for additional information about session performance and to visually monitor your bot's gameplay.

For further assistance or questions, refer to the [MQTT Command Reference](mqtt-command-reference.md) or open an issue on the project's GitHub repository. 

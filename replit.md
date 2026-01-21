# Multiplayer Trading Game

## Overview
A real-time multiplayer trading game built with FastAPI and WebSockets. Players join lobbies to trade virtual assets (oil, gold, electronics, rice, plumber) with simulated market volatility and price movements.

## Project Architecture

### Backend (Python/FastAPI)
- **main.py**: FastAPI application entry point, serves UI and coordinates routes
- **config.py**: Global configuration constants (assets, tick intervals, starting capital)
- **state.py**: Global state management (websocket connections, lobbies, ID generators)

### Domain Logic
- **domain/models.py**: Core data models (PlayerState, LobbyState)
- **domain/execution.py**: Order execution engine (buy/sell market orders)
- **domain/pricing.py**: Price simulation with volatility modeling
- **domain/portfolio.py**: Portfolio calculations, P&L tracking, leaderboard

### WebSocket System
- **websockets/endpoints.py**: Main WebSocket handler for client messages
- **websockets/utils.py**: Helper functions for broadcasting and message sending
- **websockets/ticker.py**: Game loop that updates prices and broadcasts to all players

### Frontend
- **ui/index.html**: Single-page application with Chart.js for price visualization

## Technology Stack
- Python 3.11
- FastAPI (web framework)
- Uvicorn (ASGI server)
- WebSockets (real-time communication)
- Chart.js (frontend charting)

## Key Features
- Real-time multiplayer trading via WebSockets
- Lobby creation/joining with invite codes
- Dynamic price simulation with volatility
- Position tracking (long/short)
- Realized/unrealized P&L calculations
- Live leaderboard
- Trade history tracking

## Development Setup
- Frontend runs on port 5000
- Server binds to 0.0.0.0 to support Replit's proxy
- No-cache headers ensure UI updates are visible

## Recent Changes (Nov 15, 2025)
- Imported from GitHub
- Fixed missing imports across all Python modules
- Configured for Replit environment (port 5000)
- Added proper type hints with TYPE_CHECKING to avoid circular imports
- Set up development workflow
- Configured WebSocket support using wsproto (avoids websockets library compatibility issues)
- Updated requirements.txt to explicitly list uvicorn dependencies without [standard] extra
- Configured deployment to use wsproto for production WebSocket handling

## Game Flow
1. Players connect via WebSocket
2. Host creates a lobby with custom rules (starting capital, tick interval, duration)
3. Players join via invite code and mark themselves ready
4. Host starts the game
5. Prices tick automatically, players execute market orders
6. Game ends after duration expires, showing final leaderboard

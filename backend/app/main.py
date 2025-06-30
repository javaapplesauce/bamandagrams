# backend/app/main.py
import os
import asyncio
import secrets
from typing import Dict, List, Optional
from datetime import datetime, timedelta

import socketio
from fastapi import FastAPI, WebSocketException, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app import models, schemas, crud  # import ORM models, Pydantic schemas, DB CRUD ops (defined in other modules)

# Environment configuration
WEB_ORIGIN = os.environ.get("WEB_ORIGIN", "*")  # Allowed front-end origin (use '*' for dev)
ENABLE_FX = os.environ.get("ENABLE_FX", "0") == "1"  # Feature flag: enable animations/sounds
JWT_SECRET = os.environ.get("JWT_SECRET", "super-secret")  # JWT signing key (set via env in prod)
JWT_ALGORITHM = "HS256"
TURN_TIMEOUT = 30  # seconds for turn timeout
NO_MOVE_ROUNDS_TO_END = 3  # end after 3 full rounds of no moves

# FastAPI app and Socket.IO server initialization
fastapi_app = FastAPI(title="BamandaGrams API", version="1.0.0")
# Enable CORS for the front-end origin (and allow WebSocket upgrades)
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=[WEB_ORIGIN] if WEB_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create Socket.IO Async server
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins=[WEB_ORIGIN] if WEB_ORIGIN != "*" else "*")
# Wrap FastAPI app with Socket.IO ASGI app
app = socketio.ASGIApp(sio, fastapi_app)  # 'app' is the ASGI application Uvicorn will run

# In-memory game session store
games: Dict[str, "GameState"] = {}

class GameState:
    """In-memory state of an active game."""
    def __init__(self, code: str):
        self.code = code
        # Generate a shuffled bag of 144 tiles (same distribution as Bananagrams)
        tile_counts = {
            'A': 13, 'B': 3, 'C': 3, 'D': 6, 'E': 18, 'F': 3, 'G': 4, 'H': 3,
            'I': 12, 'J': 2, 'K': 2, 'L': 5, 'M': 3, 'N': 8, 'O': 11, 'P': 3,
            'Q': 2, 'R': 9, 'S': 6, 'T': 9, 'U': 6, 'V': 3, 'W': 3, 'X': 2,
            'Y': 3, 'Z': 2
        }
        # Create the tile bag as a list of letters and shuffle it
        self.tile_bag: List[str] = [letter for letter, count in tile_counts.items() for _ in range(count)]
        secrets.SystemRandom().shuffle(self.tile_bag)
        self.players: Dict[str, "PlayerState"] = {}  # key: sid (socket id), value: player state
        self.turn_order: List[str] = []              # list of player sids in turn sequence
        self.current_turn_index: int = 0
        self.no_move_turns: int = 0                  # count of consecutive turns with no action
        self.last_action_time: datetime = datetime.utcnow()
        self.game_active: bool = True

class PlayerState:
    def __init__(self, sid: str, name: str, user_id: Optional[int] = None):
        self.sid = sid
        self.name = name
        self.user_id = user_id  # user id if logged in, else None (guest)
        self.letters: List[str] = []   # letters in hand (not yet used in placed words)
        self.words: Dict[str, str] = {} # word_id -> word text for words this player has on the board

# Helper: Get current game from code
def get_game(code: str) -> GameState:
    game = games.get(code)
    if not game:
        raise WebSocketException(message=f"Game {code} not found")
    return game

# Background task to enforce turn timeout
async def turn_timer_task(game_code: str, turn_index: int, start_time: datetime):
    await asyncio.sleep(TURN_TIMEOUT)
    game = games.get(game_code)
    if not game or not game.game_active:
        return
    # If the turn has not advanced since start_time, force advance (timeout)
    if game.current_turn_index == turn_index and game.last_action_time <= start_time:
        # Skip the current player's turn due to timeout
        current_sid = game.turn_order[game.current_turn_index]
        await sio.emit("turn_timeout", {"sid": current_sid}, room=f"room/{game_code}")
        # Advance to next player's turn
        await advance_turn(game_code, action_taken=False)

async def advance_turn(game_code: str, action_taken: bool):
    """Advance to the next player's turn. If no action was taken, increment no-move count."""
    game = get_game(game_code)
    # If game already ended, do nothing
    if not game.game_active:
        return
    if action_taken:
        game.no_move_turns = 0
    else:
        game.no_move_turns += 1
    # Check for game end condition: no moves by anyone for 3 full rounds
    if game.no_move_turns >= len(game.turn_order) * NO_MOVE_ROUNDS_TO_END:
        await end_game(game_code)
        return
    # Advance turn index
    game.current_turn_index = (game.current_turn_index + 1) % len(game.turn_order)
    game.last_action_time = datetime.utcnow()
    next_sid = game.turn_order[game.current_turn_index]
    # Notify the next player it's their turn
    await sio.emit("your_turn", {}, room=next_sid)
    # Start a new turn timer
    asyncio.create_task(turn_timer_task(game_code, game.current_turn_index, game.last_action_time))

async def end_game(game_code: str):
    """End the game, calculate scores, persist results, and notify players."""
    game = get_game(game_code)
    game.game_active = False
    # Calculate final scores: sum of (length^2) for each word a player has
    results = []
    for sid, pstate in game.players.items():
        score = sum(len(word)**2 for word in pstate.words.values())
        results.append({"name": pstate.name, "score": score})
    # Rank the results by score (simple sorting, higher is better)
    results.sort(key=lambda r: r["score"], reverse=True)
    # Persist match results to DB (async)
    try:
        async with models.SessionLocal() as db_sess:  # AsyncSession from models.py
            match = await crud.save_match_results(db_sess, game, results)
    except Exception as e:
        print(f"DB Error saving results: {e}")
    # Broadcast game over event with scoreboard
    await sio.emit("game_over", {"results": results}, room=f"room/{game_code}")
    # Remove game from memory
    games.pop(game_code, None)

# Socket.IO Event Handlers
@sio.event
async def connect(sid, environ, auth):
    """New socket connection established."""
    # Basic origin check (prevent unknown origins if WebSocket sends it)
    origin = environ.get('HTTP_ORIGIN', '')
    if WEB_ORIGIN != "*" and WEB_ORIGIN not in origin:
        print(f"Rejecting connection from origin: {origin}")
        return False  # reject connection
    print(f"Socket connected: {sid}")
    return True

@sio.event
async def disconnect(sid):
    """Socket disconnected. If player was in a game, notify others."""
    # Find if this sid was in any game
    for game in list(games.values()):
        if sid in game.players:
            player = game.players.pop(sid)
            game.turn_order = [s for s in game.turn_order if s != sid]
            # Notify remaining players
            await sio.emit("player_left", {"sid": sid, "name": player.name}, room=f"room/{game.code}")
            # If game still active but only one or zero players remain, end it early
            if game.game_active and len(game.turn_order) < 2:
                await end_game(game.code)
    print(f"Socket disconnected: {sid}")

@sio.on("create_game")
async def handle_create_game(sid, data):
    """Create a new game lobby and join the creator to it."""
    name = data.get("name", "Player")
    # Generate a unique 5-letter lobby code
    code = None
    for _ in range(5):
        code = ''.join(secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ') for _ in range(5))
        if code not in games:
            break
    if not code or code in games:
        return {"error": "Could not generate lobby code"}
    # Create game state and add creator
    game = GameState(code=code)
    games[code] = game
    # Create player state for lobby creator
    player = PlayerState(sid=sid, name=name)
    game.players[sid] = player
    game.turn_order.append(sid)
    # Join the socket.io room for this game
    sio.enter_room(sid, f"room/{code}")
    print(f"Game created: {code} by {name} ({sid})")
    # Notify creator with the lobby code and initial state
    return {"code": code, "player": {"sid": sid, "name": name}}

@sio.on("join_game")
async def handle_join_game(sid, data):
    """Join an existing game lobby via code."""
    code = data.get("code")
    name = data.get("name", "Player")
    game = games.get(code)
    if not game or not game.game_active or len(game.players) >= 5:
        return {"error": "Cannot join game (invalid code or game full/started)"}
    # Add new player
    player = PlayerState(sid=sid, name=name)
    game.players[sid] = player
    game.turn_order.append(sid)
    sio.enter_room(sid, f"room/{code}")
    # Broadcast to lobby that a new player joined
    await sio.emit("player_joined", {"sid": sid, "name": name}, room=f"room/{code}")
    print(f"Player {name} joined game {code}")
    return {"code": code, "player": {"sid": sid, "name": name}, "players": [
        {"sid": pid, "name": pstate.name} for pid, pstate in game.players.items()
    ]}

@sio.on("start_game")
async def handle_start_game(sid, data):
    """Start the game (initial turn assignment and tile distribution)."""
    code = data.get("code")
    game = get_game(code)
    if game.current_turn_index != 0 or not game.game_active:
        return  # already started or ended
    # If less than 2 players, cannot start
    if len(game.players) < 2:
        await sio.emit("error_message", {"error": "Need at least 2 players to start."}, to=sid)
        return
    # Deal initial letters to players (optional: could start with none, here give each 1 letter to start)
    for pid, pstate in game.players.items():
        if game.tile_bag:
            letter = game.tile_bag.pop()
            pstate.letters.append(letter)
            # Notify that player got a starting letter
            await sio.emit("tile_flipped", {"sid": pid, "letter": letter}, room=f"room/{code}")
    # Notify all players that the game is starting
    await sio.emit("game_started", {}, room=f"room/{code}")
    # Emit first turn
    game.last_action_time = datetime.utcnow()
    first_sid = game.turn_order[game.current_turn_index]
    await sio.emit("your_turn", {}, room=first_sid)
    # Start turn timer
    asyncio.create_task(turn_timer_task(code, game.current_turn_index, game.last_action_time))
    print(f"Game {code} started with players: {[p.name for p in game.players.values()]}")

@sio.on("flip_tile")
async def handle_flip_tile(sid, data):
    """Flip a new tile from the communal pile (active player's turn)."""
    code = data.get("code")
    game = get_game(code)
    # Ensure it's the requesting player's turn
    if game.turn_order[game.current_turn_index] != sid:
        return {"error": "Not your turn"}
    if not game.tile_bag:
        return {"error": "No tiles left"}
    # Draw a tile
    letter = game.tile_bag.pop()
    game.players[sid].letters.append(letter)
    # Broadcast the flipped tile to all players
    await sio.emit("tile_flipped", {"sid": sid, "letter": letter}, room=f"room/{code}")
    print(f"Player {sid} flipped tile {letter} in game {code}")
    # End turn (no word formed, but flip counts as an action?)
    game.last_action_time = datetime.utcnow()
    await advance_turn(code, action_taken=True)
    return {"letter": letter}

@sio.on("form_word")
async def handle_form_word(sid, data):
    """Form a new word from the current player's available letters."""
    code = data.get("code")
    game = get_game(code)
    if game.turn_order[game.current_turn_index] != sid:
        return {"error": "Not your turn"}
    word_str = data.get("word", "")
    tiles = data.get("tiles", [])  # letters used from player's hand
    word = word_str.upper()
    # Validate that the player indeed has the tiles claimed
    player_state = game.players[sid]
    tiles_available = player_state.letters.copy()
    for t in tiles:
        if t not in tiles_available:
            return {"error": "Tiles not available"}
        tiles_available.remove(t)
    # Validate the word against dictionary (using wordfreq's word list)
    from wordfreq import zipf_frequency
    if zipf_frequency(word, "en", wordlist="large") == 0.0:
        return {"error": f"'{word}' is not a valid English word"}
    # Word is valid: remove used tiles from hand and add word to player's list
    for t in tiles:
        player_state.letters.remove(t)
    word_id = secrets.token_hex(4)  # generate a short ID for the word
    player_state.words[word_id] = word
    # Broadcast to all players that a new word is placed
    await sio.emit("word_placed", {"sid": sid, "word": word, "word_id": word_id}, room=f"room/{code}")
    print(f"Player {player_state.name} formed word '{word}'")
    # End turn (successful action)
    game.last_action_time = datetime.utcnow()
    await advance_turn(code, action_taken=True)
    return {"word_id": word_id, "word": word}

@sio.on("steal_word")
async def handle_steal_word(sid, data):
    """Steal another player's word by extending it with new letters."""
    code = data.get("code")
    game = get_game(code)
    if game.turn_order[game.current_turn_index] != sid:
        return {"error": "Not your turn"}
    target_sid = data.get("targetPlayerId")
    base_word_id = data.get("baseWordId")
    new_word_str = data.get("newWord", "")
    if not target_sid or not base_word_id or not new_word_str:
        return {"error": "Missing data"}
    target_player = game.players.get(target_sid)
    stealing_player = game.players[sid]
    if not target_player or base_word_id not in target_player.words:
        return {"error": "Base word not found"}
    base_word = target_player.words[base_word_id]
    new_word = new_word_str.upper()
    # Check that new_word contains all letters of base_word plus at least one from stealer's hand
    base_letters = list(base_word)
    added_letters = []
    temp_letters = stealing_player.letters.copy()
    # Remove each letter of base_word from new_word's letters
    new_word_letters = list(new_word)
    for letter in base_letters:
        if letter in new_word_letters:
            new_word_letters.remove(letter)
    # Now new_word_letters should be exactly the letters added
    added_letters = new_word_letters
    # Verify the stealing player has those added letters
    for letter in added_letters:
        if letter not in temp_letters:
            return {"error": "You do not have the required letters to form that word"}
        temp_letters.remove(letter)
    # Verify new word is valid English word
    from wordfreq import zipf_frequency
    if zipf_frequency(new_word, "en", wordlist="large") == 0.0:
        return {"error": f"'{new_word}' is not a valid word"}
    # Steal is valid: remove base word from target, remove added letters from stealer, and add new word to stealer
    del target_player.words[base_word_id]
    for letter in added_letters:
        stealing_player.letters.remove(letter)
    new_word_id = secrets.token_hex(4)
    stealing_player.words[new_word_id] = new_word
    # Broadcast word stolen event
    await sio.emit("word_stolen", {
        "thief_sid": sid, "victim_sid": target_sid,
        "old_word_id": base_word_id, "new_word": new_word, "new_word_id": new_word_id
    }, room=f"room/{code}")
    print(f"Player {stealing_player.name} stole word '{base_word}' and formed '{new_word}'")
    # End turn
    game.last_action_time = datetime.utcnow()
    await advance_turn(code, action_taken=True)
    return {"new_word": new_word, "new_word_id": new_word_id}

@sio.on("send_chat")
async def handle_chat(sid, data):
    """Handle a chat message sent by a player."""
    code = data.get("code")
    text = data.get("text", "")
    game = get_game(code)
    player = game.players.get(sid)
    if player and text:
        # Simple rate-limit: no more than 3 messages in 5 seconds (not implemented fully here, just a placeholder)
        # Broadcast chat message to the room
        await sio.emit("chat_message", {"sid": sid, "name": player.name, "text": text}, room=f"room/{code}")
        print(f"[{code}] {player.name}: {text}")

# FastAPI API endpoints (Auth and health-check)
@fastapi_app.get("/", response_class=HTMLResponse)
async def index():
    return "<h3>BamandaGrams API is running</h3>"

@fastapi_app.get("/health")
async def health():
    return {"status": "ok"}

# Auth scaffolding
@fastapi_app.post("/auth/signup", response_model=schemas.UserOut)
async def signup(user_in: schemas.UserCreate):
    """Create a new user account (sign up)."""
    async with models.SessionLocal() as session:
        # Check if username is taken
        if await crud.get_user_by_username(session, user_in.username):
            raise HTTPException(status_code=400, detail="Username already taken")
        user = await crud.create_user(session, user_in)
        return user

@fastapi_app.post("/auth/login", response_model=schemas.Token)
async def login(form: schemas.LoginRequest):
    """Authenticate user and return JWT token."""
    async with models.SessionLocal() as session:
        user = await crud.get_user_by_username(session, form.username)
        if not user or not crud.verify_password(form.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        # Create JWT token
        import jwt
        payload = {"sub": str(user.id), "exp": datetime.utcnow() + timedelta(hours=24)}
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return {"access_token": token, "token_type": "bearer"}

@fastapi_app.get("/auth/me", response_model=schemas.UserOut)
async def get_current_user(current_user: models.User = Depends(crud.get_current_user)):
    """Get details of the current logged-in user (via JWT)."""
    return current_user

// frontend/src/context/GameContext.tsx
import React, { createContext, useReducer } from 'react';
import { io, Socket } from 'socket.io-client';

interface PlayerInfo { sid: string; name: string; score?: number; }
interface WordInfo { word: string; word_id: string; owner: string; }
interface Message { from: string; text: string; }

interface GameState {
  socket: Socket | null;
  code: string | null;
  players: PlayerInfo[];
  words: WordInfo[];     // all current words on the board
  messages: Message[];
  darkMode: boolean;
}

const initialState: GameState = {
  socket: null,
  code: null,
  players: [],
  words: [],
  messages: [],
  darkMode: false
};

type Action =
  | { type: 'SET_CODE', code: string }
  | { type: 'SET_PLAYERS', players: PlayerInfo[] }
  | { type: 'PLAYER_JOINED', player: PlayerInfo }
  | { type: 'PLAYER_LEFT', sid: string }
  | { type: 'WORD_PLACED', word: WordInfo }
  | { type: 'WORD_STOLEN', victim_sid: string, old_word_id: string, new_word: WordInfo }
  | { type: 'TILE_FLIPPED', sid: string, letter: string }
  | { type: 'NEW_MESSAGE', message: Message }
  | { type: 'SET_DARK_MODE', enabled: boolean }
  | { type: 'RESET_GAME' }
  ;

const GameContext = createContext<{
  state: GameState;
  dispatch: React.Dispatch<Action>;
  connectSocket: () => void;
  disconnectSocket: () => void;
}>({ state: initialState, dispatch: () => null, connectSocket: () => {}, disconnectSocket: () => {} });

const gameReducer = (state: GameState, action: Action): GameState => {
  switch (action.type) {
    case 'SET_CODE':
      return { ...state, code: action.code };
    case 'SET_PLAYERS':
      return { ...state, players: action.players };
    case 'PLAYER_JOINED':
      return { ...state, players: [...state.players, action.player] };
    case 'PLAYER_LEFT':
      return { ...state, players: state.players.filter(p => p.sid !== action.sid) };
    case 'WORD_PLACED':
      return { ...state, words: [...state.words, action.word] };
    case 'WORD_STOLEN':
      // Remove old word and add new word
      return {
        ...state,
        words: state.words.filter(w => w.word_id !== action.old_word_id)
                          .concat(action.new_word)
      };
    case 'TILE_FLIPPED':
      // We could track each player's letters, but for UI, maybe display a quick animation or just log it.
      return state;
    case 'NEW_MESSAGE':
      return { ...state, messages: [...state.messages, action.message] };
    case 'SET_DARK_MODE':
      return { ...state, darkMode: action.enabled };
    case 'RESET_GAME':
      return { ...state, code: null, players: [], words: [], messages: [] };
    default:
      return state;
  }
};

const GameProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(gameReducer, initialState);

  const connectSocket = () => {
    if (!state.socket) {
      const socketUrl = import.meta.env.VITE_API_URL || window.location.origin;
      const socket = io(socketUrl, { transports: ['websocket'] });
      dispatch({ type: 'RESET_GAME' });
      // Register Socket.IO event listeners
      socket.on('connect', () => {
        console.log('Socket connected');
      });
      socket.on('player_joined', (data: any) => {
        dispatch({ type: 'PLAYER_JOINED', player: { sid: data.sid, name: data.name } });
      });
      socket.on('player_left', (data: any) => {
        dispatch({ type: 'PLAYER_LEFT', sid: data.sid });
      });
      socket.on('game_started', () => {
        console.log('Game started!');
      });
      socket.on('your_turn', () => {
        alert('Your turn! Make a move.');
      });
      socket.on('turn_timeout', (data: any) => {
        console.log(`Player ${data.sid} timed out.`);
      });
      socket.on('tile_flipped', (data: any) => {
        // Optionally show the letter flip to all players
        console.log(`Tile flipped by ${data.sid}: ${data.letter}`);
        dispatch({ type: 'TILE_FLIPPED', sid: data.sid, letter: data.letter });
      });
      socket.on('word_placed', (data: any) => {
        dispatch({
          type: 'WORD_PLACED',
          word: { word: data.word, word_id: data.word_id, owner: data.sid }
        });
      });
      socket.on('word_stolen', (data: any) => {
        dispatch({
          type: 'WORD_STOLEN',
          victim_sid: data.victim_sid,
          old_word_id: data.old_word_id,
          new_word: { word: data.new_word, word_id: data.new_word_id, owner: data.thief_sid }
        });
      });
      socket.on('chat_message', (msg: any) => {
        dispatch({ type: 'NEW_MESSAGE', message: { from: msg.name, text: msg.text } });
      });
      socket.on('game_over', (data: any) => {
        alert("Game Over! Final Scores:\n" + data.results.map((r: any, i: number) =>
          `${i+1}. ${r.name}: ${r.score}`).join("\n"));
      });
      dispatch({ type: 'SET_PLAYERS', players: [] }); // reset players list
      dispatch({ type: 'SET_CODE', code: '' });       // code will be set upon join/create response
      state.socket = socket;
      state.socket.connect();
    }
  };

  const disconnectSocket = () => {
    state.socket?.disconnect();
    dispatch({ type: 'RESET_GAME' });
  };

  return (
    <GameContext.Provider value={{ state, dispatch, connectSocket, disconnectSocket }}>
      {children}
    </GameContext.Provider>
  );
};

export { GameContext, GameProvider };

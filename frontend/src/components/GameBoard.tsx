// frontend/src/components/GameBoard.tsx
import React, { useContext, useState } from 'react';
import { GameContext } from '../context/GameContext';
import PlayerList from './PlayerList';
import ChatPanel from './ChatPanel';
import { SunIcon, MoonIcon } from '@heroicons/react/24/outline';

const GameBoard: React.FC = () => {
  const { state, dispatch } = useContext(GameContext);
  const [newWord, setNewWord] = useState("");
  const [stealDetails, setStealDetails] = useState({ baseWordId: "", targetSid: "" });

  const flipTile = () => {
    state.socket?.emit("flip_tile", { code: state.code });
  };
  const formWord = () => {
    if (newWord) {
      state.socket?.emit("form_word", { code: state.code, word: newWord, tiles: newWord.toUpperCase().split("") }, (res: any) => {
        if (res.error) alert(res.error);
        else setNewWord("");
      });
    }
  };
  const stealWord = () => {
    const { baseWordId, targetSid } = stealDetails;
    if (baseWordId && targetSid && newWord) {
      state.socket?.emit("steal_word", {
        code: state.code,
        targetPlayerId: targetSid,
        baseWordId: baseWordId,
        newWord: newWord
      }, (res: any) => {
        if (res.error) alert(res.error);
        else {
          setNewWord("");
          setStealDetails({ baseWordId: "", targetSid: "" });
        }
      });
    }
  };
  const toggleDarkMode = () => {
    dispatch({ type: 'SET_DARK_MODE', enabled: !state.darkMode });
  };

  return (
    <div className="flex h-screen">
      {/* Left side: Board and controls */}
      <div className="flex-1 flex flex-col p-4">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xl font-semibold">Lobby Code: {state.code || "(loading)"}</h2>
          <button onClick={toggleDarkMode} className="p-2">
            {state.darkMode ? <SunIcon className="h-6 w-6"/> : <MoonIcon className="h-6 w-6"/>}
          </button>
        </div>
        <div className="flex-1 bg-green-50 dark:bg-gray-800 rounded p-4 overflow-y-auto">
          {/* Display words on the board */}
          {state.words.length === 0 ? (
            <p className="text-gray-500">No words on board yet.</p>
          ) : (
            <ul>
              {state.words.map((w) => (
                <li key={w.word_id} className="mb-1">
                  <span className="font-bold">{w.word}</span> 
                  <span className="text-sm text-gray-600 dark:text-gray-400">({w.owner === state.socket?.id ? "You" : state.players.find(p => p.sid === w.owner)?.name})</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="mt-3 flex space-x-2">
          <button onClick={flipTile} className="bg-yellow-500 hover:bg-yellow-600 text-white px-4 py-2 rounded">Flip Tile</button>
          <input 
            type="text" 
            placeholder="Enter word or new word" 
            value={newWord} 
            onChange={e => setNewWord(e.target.value)} 
            className="flex-1 p-2 border rounded text-gray-900"
          />
          <button onClick={formWord} className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded">Place Word</button>
          <button onClick={stealWord} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded">Steal Word</button>
        </div>
        {/* Instructions or status */}
        <p className="text-sm text-gray-700 dark:text-gray-300 mt-1">Use "Place Word" for new words from your letters, or fill in a word and select a target word to "Steal Word".</p>
      </div>
      {/* Right side: Player list and chat */}
      <div className="w-1/3 bg-gray-100 dark:bg-gray-900 border-l border-gray-300 dark:border-gray-700 flex flex-col">
        <PlayerList players={state.players} />
        <ChatPanel messages={state.messages} onSend={(msg) => {
          state.socket?.emit("send_chat", { code: state.code, text: msg });
        }}/>
      </div>
    </div>
  );
};

export default GameBoard;

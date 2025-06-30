// frontend/src/App.tsx
import React, { useState, useEffect, useContext } from 'react';
import { GameContext } from './context/GameContext';
import JoinLobby from './components/JoinLobby';
import GameBoard from './components/GameBoard';

const App: React.FC = () => {
  const { state, connectSocket, disconnectSocket } = useContext(GameContext);
  const [joined, setJoined] = useState(false);

  useEffect(() => {
    // On unmount, disconnect socket to leave any rooms
    return () => {
      disconnectSocket();
    };
  }, []);

  const handleJoin = (name: string, code?: string) => {
    connectSocket();  // establish socket connection
    // If code provided, join existing; otherwise create new
    if (code) {
      state.socket?.emit('join_game', { code, name }, (res: any) => {
        if (res.error) {
          alert(res.error);
        } else {
          setJoined(true);
        }
      });
    } else {
      state.socket?.emit('create_game', { name }, (res: any) => {
        if (res.error) {
          alert(res.error);
        } else {
          setJoined(true);
        }
      });
    }
  };

  return (
    <div className={`min-h-screen bg-gray-100 text-gray-900 ${state.darkMode ? 'dark bg-gray-900 text-gray-100' : ''}`}>
      {!joined ? (
        <JoinLobby onSubmit={handleJoin} />
      ) : (
        <GameBoard />
      )}
    </div>
  );
};

export default App;

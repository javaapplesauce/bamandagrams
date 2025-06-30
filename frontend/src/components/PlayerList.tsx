// frontend/src/components/PlayerList.tsx
import React from 'react';

interface Player { sid: string; name: string; score?: number; }

const PlayerList: React.FC<{ players: Player[] }> = ({ players }) => {
  return (
    <div className="p-4 flex-1 overflow-y-auto">
      <h3 className="text-lg font-semibold mb-2">Players</h3>
      {players.map(p => (
        <div key={p.sid} className="flex justify-between items-center mb-1">
          <span>{p.name}</span>
          {p.score !== undefined && <span className="text-sm text-gray-600 dark:text-gray-400">{p.score}</span>}
        </div>
      ))}
      {players.length === 0 && <p className="text-gray-500">Waiting for players...</p>}
    </div>
  );
};

export default PlayerList;

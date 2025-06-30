// frontend/src/components/JoinLobby.tsx
import React, { useState } from 'react';

interface Props {
  onSubmit: (name: string, code?: string) => void;
}

const JoinLobby: React.FC<Props> = ({ onSubmit }) => {
  const [name, setName] = useState("");
  const [code, setCode] = useState("");

  const handleCreate = () => {
    if (!name) {
      alert("Please enter your name");
      return;
    }
    onSubmit(name.trim());
  };
  const handleJoin = () => {
    if (!name || !code) {
      alert("Please enter your name and lobby code");
      return;
    }
    onSubmit(name.trim(), code.trim().toUpperCase());
  };

  return (
    <div className="flex flex-col items-center justify-center h-screen p-4 bg-gradient-to-br from-yellow-100 to-green-100 dark:from-gray-800 dark:to-gray-700">
      <h1 className="text-3xl font-bold mb-6">🍌 BamandaGrams</h1>
      <input 
        type="text" 
        placeholder="Your Name" 
        value={name} 
        onChange={e => setName(e.target.value)} 
        className="mb-3 p-2 border rounded w-64 text-gray-900"
      />
      <input 
        type="text" 
        placeholder="Lobby Code (if joining)" 
        value={code} 
        onChange={e => setCode(e.target.value)} 
        className="mb-6 p-2 border rounded w-64 text-gray-900"
      />
      <div className="space-x-4">
        <button onClick={handleCreate} className="px-4 py-2 bg-green-600 text-white rounded shadow">Create Game</button>
        <button onClick={handleJoin} className="px-4 py-2 bg-blue-600 text-white rounded shadow">Join Game</button>
      </div>
    </div>
  );
};

export default JoinLobby;

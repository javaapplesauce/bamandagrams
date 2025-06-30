// frontend/src/components/ChatPanel.tsx
import React, { useState, useRef, useEffect } from 'react';

interface Message { from: string; text: string; }

const ChatPanel: React.FC<{ messages: Message[]; onSend: (msg: string) => void }> = ({ messages, onSend }) => {
  const [draft, setDraft] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const sendMessage = () => {
    if (draft.trim()) {
      onSend(draft);
      setDraft("");
    }
  };

  useEffect(() => {
    // Scroll to bottom on new message
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="border-t border-gray-300 dark:border-gray-700 p-2">
      <div className="h-32 overflow-y-auto mb-2 bg-white dark:bg-gray-800 p-2 rounded">
        {messages.map((msg, idx) => (
          <div key={idx} className="text-sm"><b>{msg.from}:</b> {msg.text}</div>
        ))}
        <div ref={bottomRef}></div>
      </div>
      <div className="flex space-x-2">
        <input 
          type="text" 
          placeholder="Type a message..." 
          value={draft} 
          onChange={e => setDraft(e.target.value)} 
          onKeyDown={e => { if(e.key==='Enter') sendMessage(); }} 
          className="flex-1 p-1 border rounded text-gray-900 text-sm"
        />
        <button onClick={sendMessage} className="bg-gray-700 text-white px-3 py-1 text-sm rounded">Send</button>
      </div>
    </div>
  );
};

export default ChatPanel;

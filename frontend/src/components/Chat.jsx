import React, { useState } from 'react';

const Chat = () => {
  const [messages, setMessages] = useState([
    { type: 'agent', content: 'Hello! Your financial data is ready. Ask me anything about your spending.' }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg = input.trim();
    setMessages(prev => [...prev, { type: 'user', content: userMsg }]);
    setInput('');
    setIsTyping(true);

    try {
      const response = await fetch('http://localhost:5000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg })
      });
      const data = await response.json();
      
      // Add agent narrations
      if (data.narrations && data.narrations.length > 0) {
        data.narrations.forEach(narration => {
          setMessages(prev => [...prev, { type: 'narration', content: narration }]);
        });
      }

      // Add actual reply
      if (data.reply) {
         setMessages(prev => [...prev, { type: 'agent', content: data.reply }]);
      }

      // Render chart if generated
      if (data.chart) {
         setMessages(prev => [...prev, { type: 'agent', isImage: true, content: data.chart }]);
      }

    } catch (err) {
      setMessages(prev => [...prev, { type: 'agent', content: 'Error communicating with agent.' }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="card chat-container">
      <div className="chat-history">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.type}`}>
             {msg.isImage ? <img src={msg.content} alt="Chart" style={{ maxWidth: '100%', borderRadius: '4px' }} /> : msg.content}
          </div>
        ))}
        {isTyping && <div className="message narration">Agent is thinking...</div>}
      </div>
      <div className="chat-input-area">
        <input 
          type="text" 
          className="chat-input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSend()}
          placeholder="Ask a financial question..."
        />
        <button className="btn" onClick={handleSend}>Send</button>
      </div>
    </div>
  );
};

export default Chat;

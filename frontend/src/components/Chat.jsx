import React, { useState, useRef, useEffect } from 'react';

const Chat = () => {
  const [messages, setMessages] = useState([
    {
      type: 'agent',
      content: 'Hello! Your financial data is ready. Ask me anything about your spending.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const handleSend = async () => {
    if (!input.trim() || isTyping) return;

    const userMsg = input.trim();
    const timestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setMessages(prev => [...prev, { type: 'user', content: userMsg, timestamp }]);
    setInput('');
    setIsTyping(true);

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || ''}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg })
      });
      const data = await response.json();
      const agentTimestamp = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      if (data.narrations && data.narrations.length > 0) {
        data.narrations.forEach(narration => {
          setMessages(prev => [...prev, { type: 'narration', content: narration }]);
        });
      }

      if (data.reply) {
        const isRateLimit = data.reply.includes('rate limit') || data.reply.includes('quota') || data.reply.includes('AI is busy');
        setMessages(prev => [...prev, {
          type: 'agent',
          content: data.reply,
          timestamp: agentTimestamp,
          isRateLimit
        }]);
      }

      if (data.chart) {
        setMessages(prev => [...prev, {
          type: 'agent', isImage: true, content: data.chart, timestamp: agentTimestamp
        }]);
      }

    } catch (_err) {
      setMessages(prev => [...prev, {
        type: 'agent',
        content: 'Error communicating with agent. Is the backend running?',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <span className="chat-header-title">💬 AI Chat</span>
        <span style={{ fontSize: '11px', color: '#00E676', marginLeft: '8px' }}>
          ⚡ Ready
        </span>
      </div>

      <div className="chat-messages">
        {messages.map((msg, idx) => {
          if (msg.type === 'narration') {
            return <div key={idx} className="chat-narration">{msg.content}</div>;
          }
          return (
            <div key={idx} className={`chat-bubble-wrap ${msg.type}`}>
              <div className={`chat-bubble ${msg.type}`} style={
                msg.isRateLimit ? { background: '#1A1400', color: '#FFB300', border: '1px solid #FFB30040' } : {}
              }>
                {msg.isImage
                  ? <img src={msg.content} alt="Chart" style={{ maxWidth: '100%', borderRadius: '6px', display: 'block' }} />
                  : msg.content
                }
              </div>
              {msg.timestamp && <span className="chat-timestamp">{msg.timestamp}</span>}
            </div>
          );
        })}

        {isTyping && (
          <div className="chat-bubble-wrap agent">
            <div className="chat-bubble agent" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div className="status-dot pulsing" />
              Agent is thinking...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-bar">
        <input
          className="chat-input"
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSend()}
          placeholder="Ask a financial question..."
          disabled={isTyping}
        />
        <button className="btn" onClick={handleSend} disabled={isTyping}
          style={{ minWidth: '90px' }}>
          Send
          <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        </button>
      </div>
    </div>
  );
};

export default Chat;

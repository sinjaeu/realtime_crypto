import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import './AIAssistant.css';

const AIAssistant = () => {
  const { user } = useAuth();
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ 
        behavior: "smooth", 
        block: "end",
        inline: "nearest"
      });
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // 인증 테스트 및 초기 환영 메시지
    const initializeAI = async () => {
      const token = localStorage.getItem('token');
      if (!token) {
        const errorMessage = {
          id: Date.now(),
          type: 'ai',
          content: '🔐 로그인이 필요합니다. 다시 로그인해주세요.',
          timestamp: new Date().toLocaleTimeString('ko-KR'),
          suggestions: ['다시 로그인하기']
        };
        setMessages([errorMessage]);
        return;
      }

      try {
        // AI 인증 테스트
        const response = await axios.get('http://localhost:8000/api/ai/test', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          timeout: 10000
        });

        if (response.data.success) {
          const welcomeMessage = {
            id: Date.now(),
            type: 'ai',
            content: `안녕하세요 ${user?.username}님! 🤖\n\nXGBoost 머신러닝 모델을 활용한 AI 투자 어시스턴트입니다.\n\n인증이 완료되었습니다. 어떤 도움이 필요하신가요?`,
            timestamp: new Date().toLocaleTimeString('ko-KR'),
            suggestions: [
              "내 포트폴리오 분석해줘",
              "코인 가격 예측해줘",
              "투자 추천해줘",
              "시장 동향 분석해줘"
            ]
          };
          setMessages([welcomeMessage]);
          setSuggestions(welcomeMessage.suggestions);
        }
      } catch (error) {
        console.error('AI 인증 테스트 실패:', error);
        const errorMessage = {
          id: Date.now(),
          type: 'ai',
          content: '🔐 인증에 실패했습니다. 다시 로그인해주세요.',
          timestamp: new Date().toLocaleTimeString('ko-KR'),
          suggestions: ['다시 로그인하기', '새로고침 후 재시도']
        };
        setMessages([errorMessage]);
      }
    };

    initializeAI();
  }, [user?.username]);

  const sendMessage = async (messageText = null) => {
    const message = messageText || inputMessage.trim();
    if (!message) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: message,
      timestamp: new Date().toLocaleTimeString('ko-KR')
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const token = localStorage.getItem('token');
      if (!token) {
        throw new Error('로그인이 필요합니다.');
      }

      console.log('AI 요청 전송:', { message, token: token ? 'exists' : 'missing' });

      const response = await axios.post('http://localhost:8000/api/ai/assistant', {
        message: message,
        context: null
      }, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        timeout: 30000
      });

      if (response.data.success) {
        const aiMessage = {
          id: Date.now() + 1,
          type: 'ai',
          content: response.data.response,
          timestamp: new Date().toLocaleTimeString('ko-KR'),
          suggestions: response.data.suggestions || []
        };

        setMessages(prev => [...prev, aiMessage]);
        setSuggestions(response.data.suggestions || []);
      } else {
        throw new Error(response.data.response || 'AI 응답 실패');
      }
    } catch (error) {
      console.error('AI 어시스턴트 오류:', error);
      
      let errorContent = '죄송합니다. AI 서비스에 일시적인 문제가 발생했습니다.';
      
      if (error.response?.status === 401) {
        errorContent = '🔐 로그인이 만료되었습니다. 다시 로그인해주세요.';
      } else if (error.response?.status === 500) {
        errorContent = '🤖 AI 서버에 문제가 발생했습니다. 잠시 후 다시 시도해주세요.';
      } else if (error.message === '로그인이 필요합니다.') {
        errorContent = '🔐 로그인이 필요합니다. 다시 로그인해주세요.';
      } else if (error.code === 'ECONNABORTED') {
        errorContent = '⏰ 요청 시간이 초과되었습니다. 다시 시도해주세요.';
      }
      
      const errorMessage = {
        id: Date.now() + 1,
        type: 'ai',
        content: errorContent,
        timestamp: new Date().toLocaleTimeString('ko-KR'),
        suggestions: ['다시 로그인하기', '새로고침 후 재시도']
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage();
  };

  const handleSuggestionClick = (suggestion) => {
    sendMessage(suggestion);
  };

  const clearChat = () => {
    setMessages([]);
    setSuggestions([]);
    
    // 초기 환영 메시지 다시 설정
    const welcomeMessage = {
      id: Date.now(),
      type: 'ai',
      content: `새로운 대화를 시작합니다! 🤖\n\n무엇을 도와드릴까요?`,
      timestamp: new Date().toLocaleTimeString('ko-KR'),
      suggestions: [
        "내 포트폴리오 분석해줘",
        "코인 가격 예측해줘",
        "투자 추천해줘",
        "시장 동향 분석해줘"
      ]
    };
    setMessages([welcomeMessage]);
    setSuggestions(welcomeMessage.suggestions);
  };

  return (
    <div className="ai-assistant">
      <div className="ai-assistant-header">
        <div className="header-content">
          <div className="header-title">
            <h1>🤖 AI 투자 어시스턴트</h1>
            <p>XGBoost 머신러닝 모델 기반 암호화폐 투자 분석</p>
          </div>
          <button onClick={clearChat} className="clear-chat-btn">
            🗑️ 대화 초기화
          </button>
        </div>
      </div>

      <div className="chat-container">
        <div className="messages-container">
          {messages.map((message) => (
            <div key={message.id} className={`message ${message.type}`}>
              <div className="message-content">
                <div className="message-text">
                  {message.content.split('\n').map((line, index) => (
                    <React.Fragment key={index}>
                      {line}
                      {index < message.content.split('\n').length - 1 && <br />}
                    </React.Fragment>
                  ))}
                </div>
                <div className="message-time">{message.timestamp}</div>
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div className="message ai">
              <div className="message-content">
                <div className="typing-indicator">
                  <div className="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                  <span className="typing-text">AI가 분석 중입니다...</span>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {suggestions.length > 0 && (
          <div className="suggestions-container">
            <div className="suggestions-title">💡 추천 질문</div>
            <div className="suggestions-grid">
              {suggestions.map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => handleSuggestionClick(suggestion)}
                  className="suggestion-btn"
                  disabled={isLoading}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="input-container">
          <div className="input-wrapper">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="AI에게 투자 관련 질문을 해보세요..."
              className="message-input"
              disabled={isLoading}
            />
            <button 
              type="submit" 
              className="send-btn"
              disabled={isLoading || !inputMessage.trim()}
            >
              {isLoading ? '⏳' : '📤'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AIAssistant;

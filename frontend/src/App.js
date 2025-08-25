import React, { useState } from 'react';
import './App.css';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import AuthWrapper from './components/Auth/AuthWrapper';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import Settings from './pages/Settings';
import Trading from './pages/Trading';
import Portfolio from './pages/Portfolio';
import History from './pages/History';

// 임시 페이지 컴포넌트들
const AIAssistant = () => <div className="page-content"><h1>🤖 AI 어시스턴트</h1><p>투자 조언 및 채팅이 여기에 구현됩니다.</p></div>;

// 로딩 컴포넌트
const LoadingScreen = () => (
  <div className="loading-screen">
    <div className="loading-spinner">
      <div className="spinner"></div>
      <p>CryptoTrader 로딩 중...</p>
    </div>
  </div>
);

// 메인 애플리케이션 컴포넌트
const MainApp = () => {
  const { isAuthenticated, loading, login } = useAuth();
  const [activeTab, setActiveTab] = useState('dashboard');

  // 로딩 중일 때
  if (loading) {
    return <LoadingScreen />;
  }

  // 인증되지 않은 경우 로그인 화면
  if (!isAuthenticated) {
    return <AuthWrapper onLogin={login} />;
  }

  // 인증된 경우 메인 앱
  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard />;
      case 'trading':
        return <Trading />;
      case 'portfolio':
        return <Portfolio />;
      case 'ai-assistant':
        return <AIAssistant />;
      case 'history':
        return <History />;
      case 'settings':
        return <Settings />;
      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="app">
      <Header />
      <div className="app-body">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />
        <main className="main-content">
          {renderContent()}
        </main>
      </div>
    </div>
  );
};

// 최상위 App 컴포넌트 (AuthProvider로 감싸기)
function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
}

export default App;

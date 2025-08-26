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
import AIAssistant from './pages/AIAssistant';
import History from './pages/History';
import TopGainers from './pages/TopGainers';

// LiveTracker 임시 컴포넌트
const LiveTracker = () => <div className="page-content"><h1>📊 실시간 추적</h1><p>실시간 가격 추적 기능이 여기에 구현됩니다.</p></div>;

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
  const [tradingParams, setTradingParams] = useState({ symbol: null, tradeType: null });

  // 커스텀 이벤트 리스너들
  React.useEffect(() => {
    const handleNavigateToTrading = (event) => {
      setActiveTab('trading');
      // 선택된 코인과 거래 타입 정보 저장
      if (event.detail) {
        setTradingParams({
          symbol: event.detail.symbol,
          tradeType: event.detail.tradeType
        });
      } else {
        setTradingParams({ symbol: null, tradeType: null });
      }
    };
    
    const handleNavigateToTopGainers = () => {
      setActiveTab('top-gainers');
    };
    
    const handleNavigateToLiveTracker = () => {
      setActiveTab('live-tracker');
    };
    
      const handleNavigateToPortfolio = () => {
    setActiveTab('portfolio');
  };

  const handleNavigateToAI = () => {
    setActiveTab('ai-assistant');
  };

    window.addEventListener('navigateToTrading', handleNavigateToTrading);
    window.addEventListener('navigateToTopGainers', handleNavigateToTopGainers);
    window.addEventListener('navigateToLiveTracker', handleNavigateToLiveTracker);
    window.addEventListener('navigateToPortfolio', handleNavigateToPortfolio);
    window.addEventListener('navigateToAI', handleNavigateToAI);
    
    return () => {
      window.removeEventListener('navigateToTrading', handleNavigateToTrading);
      window.removeEventListener('navigateToTopGainers', handleNavigateToTopGainers);
      window.removeEventListener('navigateToLiveTracker', handleNavigateToLiveTracker);
      window.removeEventListener('navigateToPortfolio', handleNavigateToPortfolio);
      window.removeEventListener('navigateToAI', handleNavigateToAI);
    };
  }, []);

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
        return <Trading selectedSymbol={tradingParams.symbol} tradeType={tradingParams.tradeType} />;
      case 'portfolio':
        return <Portfolio />;
      case 'ai-assistant':
        return <AIAssistant />;
      case 'history':
        return <History />;
              case 'top-gainers':
          return <TopGainers />;
        case 'live-tracker':
          return <TopGainers />; // 실시간 추적 → 상승률 TOP으로 연결
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

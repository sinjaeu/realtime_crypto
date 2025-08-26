import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import './Dashboard.css';

const Dashboard = () => {
  const { token } = useAuth();
  const [marketData, setMarketData] = useState([]);
  const [portfolioData, setPortfolioData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [systemStatus, setSystemStatus] = useState({
    api: 'checking',
    redis: 'checking', 
    data_available: false
  });
  const [aiRecommendations, setAiRecommendations] = useState([]);

  useEffect(() => {
    const fetchMarketData = async () => {
      try {
        console.log('🔄 시장 데이터 요청 중...');
        const response = await axios.get('http://localhost:8000/api/market/prices');
        
        if (response.data.success && response.data.data) {
          console.log('✅ 시장 데이터 수신:', response.data.data.length, '개 코인');
          
          // 상위 10개 코인만 표시
          const topCoins = response.data.data.slice(0, 10).map(coin => ({
            symbol: coin.symbol,
            price: coin.formatted_price,
            change: coin.change,
            changeClass: coin.change_class,
            rawPrice: coin.price,
            lastUpdate: coin.last_update
          }));
          
          setMarketData(topCoins);
        } else {
          console.warn('⚠️ 데이터 없음:', response.data.message);
          // 데이터가 없을 때 빈 배열 설정
          setMarketData([]);
        }
        
        setLoading(false);
      } catch (error) {
        console.error('❌ 데이터 로딩 실패:', error);
        
        // 에러 시 임시 데이터 표시
        const fallbackData = [
          { symbol: 'API 연결 실패', price: '0.0000', change: '0.00%', changeClass: 'negative' }
        ];
        
        setMarketData(fallbackData);
        setLoading(false);
      }
    };

    // 포트폴리오 데이터 가져오기
    const fetchPortfolioData = async () => {
      if (!token) return;
      
      try {
        const response = await axios.get('http://localhost:8000/api/portfolio', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        if (response.data.success) {
          setPortfolioData(response.data.data);
        }
      } catch (error) {
        console.error('포트폴리오 데이터 조회 실패:', error);
        setPortfolioData(null);
      }
    };

    // 시스템 상태 확인
    const checkSystemStatus = async () => {
      try {
        const response = await axios.get('http://localhost:8000/api/status');
        setSystemStatus(response.data);
      } catch (error) {
        console.error('시스템 상태 확인 실패:', error);
        setSystemStatus({
          api: 'error',
          redis: 'disconnected',
          data_available: false
        });
      }
    };

    const fetchAiRecommendations = async () => {
      if (!token) return;
      
      try {
        const response = await axios.post('http://localhost:8000/api/ai/assistant', {
          message: '투자 추천해줘'
        }, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        
        // AI 응답에서 추천 데이터 파싱
        const aiResponse = response.data.response;
        const recommendations = parseAiRecommendations(aiResponse);
        setAiRecommendations(recommendations);
      } catch (error) {
        console.error('AI 추천 가져오기 실패:', error);
        // 기본 추천 데이터 설정
        setAiRecommendations([
          { type: 'buy', coin: 'BTCUSDC', reason: '상승 추세 예상' },
          { type: 'hold', coin: 'ETHUSDC', reason: '횡보 예상' },
          { type: 'sell', coin: 'ADAUSDC', reason: '조정 가능성' }
        ]);
      }
    };

    const parseAiRecommendations = (aiResponse) => {
      // AI 응답에서 추천 정보를 파싱하는 간단한 로직
      const recommendations = [];
      
      if (aiResponse.includes('상승') || aiResponse.includes('매수')) {
        recommendations.push({ type: 'buy', coin: 'BTCUSDC', reason: 'AI 상승 예측' });
      }
      if (aiResponse.includes('보합') || aiResponse.includes('유지')) {
        recommendations.push({ type: 'hold', coin: 'ETHUSDC', reason: 'AI 보합 예측' });
      }
      if (aiResponse.includes('하락') || aiResponse.includes('매도')) {
        recommendations.push({ type: 'sell', coin: 'ADAUSDC', reason: 'AI 하락 예측' });
      }
      
      // 기본값 반환
      if (recommendations.length === 0) {
        return [
          { type: 'buy', coin: 'BTCUSDC', reason: 'AI 분석 중...' },
          { type: 'hold', coin: 'ETHUSDC', reason: 'AI 분석 중...' },
          { type: 'sell', coin: 'ADAUSDC', reason: 'AI 분석 중...' }
        ];
      }
      
      return recommendations.slice(0, 3); // 최대 3개
    };

    fetchMarketData();
    fetchPortfolioData();
    checkSystemStatus();
    fetchAiRecommendations();
    
    // 5초마다 데이터 업데이트 (더 실시간)
    const interval = setInterval(() => {
      fetchMarketData();
      fetchPortfolioData();
      checkSystemStatus();
    }, 5000);
    
    // 30초마다 AI 추천 업데이트 (덜 빈번하게)
    const aiInterval = setInterval(() => {
      fetchAiRecommendations();
    }, 30000);
    
    // 포트폴리오 업데이트 이벤트 리스너
    const handlePortfolioUpdate = () => {
      fetchPortfolioData();
    };
    
    window.addEventListener('portfolioUpdated', handlePortfolioUpdate);
    
    return () => {
      clearInterval(interval);
      clearInterval(aiInterval);
      window.removeEventListener('portfolioUpdated', handlePortfolioUpdate);
    };
  }, [token]);

  if (loading) {
    return (
      <div className="dashboard">
        <div className="loading">
          <div className="spinner"></div>
          <p>시장 데이터 로딩 중...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>📊 시장 대시보드</h1>
        <div className="header-info">
          <div className="system-status">
            <span className={`status-dot ${systemStatus.api === 'running' ? 'green' : 'red'}`}></span>
            <span>API: {systemStatus.api}</span>
            <span className={`status-dot ${systemStatus.redis === 'connected' ? 'green' : 'red'}`}></span>
            <span>Redis: {systemStatus.redis}</span>
            {systemStatus.total_symbols && (
              <span className="symbol-count">📊 {systemStatus.total_symbols}개 코인</span>
            )}
          </div>
          <div className="last-updated">
            마지막 업데이트: {new Date().toLocaleTimeString('ko-KR')}
          </div>
        </div>
      </div>

      <div className="dashboard-grid">
        {/* 포트폴리오 요약 */}
        <div className="card portfolio-summary">
          <h3>💼 내 포트폴리오</h3>
          <div className="portfolio-stats">
            <div className="stat-item">
              <span className="stat-label">총 자산</span>
              <span className="stat-value">
                ${portfolioData ? portfolioData.total_assets.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0.00'}
              </span>
            </div>
            <div className="stat-item">
              <span className="stat-label">총 수익</span>
              <span className={`stat-value ${portfolioData && portfolioData.total_profit_loss >= 0 ? 'positive' : 'negative'}`}>
                {portfolioData ? (
                  `${portfolioData.total_profit_loss >= 0 ? '+' : ''}$${portfolioData.total_profit_loss.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} (${portfolioData.total_profit_loss_pct >= 0 ? '+' : ''}${portfolioData.total_profit_loss_pct.toFixed(2)}%)`
                ) : (
                  '$0.00 (0.00%)'
                )}
              </span>
            </div>
            <div className="stat-item">
              <span className="stat-label">보유 코인</span>
              <span className="stat-value">
                {portfolioData ? portfolioData.holding_count : 0}개
              </span>
            </div>
          </div>
        </div>

        {/* 상위 코인 */}
        <div className="card top-coins">
          <h3>🚀 주요 코인</h3>
          <div className="coin-list">
            {marketData.map((coin, index) => (
              <div key={coin.symbol} className="coin-item">
                <div className="coin-info">
                  <span className="coin-symbol">{coin.symbol}</span>
                  <span className="coin-price">${coin.price}</span>
                </div>
                <span className={`coin-change ${coin.changeClass}`}>
                  {coin.change}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* 빠른 액세스 메뉴 */}
        <div className="card quick-access">
          <h3>⚡ 빠른 액세스</h3>
          <div className="quick-actions">
            <div className="quick-action-item" onClick={() => window.dispatchEvent(new CustomEvent('navigateToTrading'))}>
              <div className="action-icon">💹</div>
              <div className="action-content">
                <div className="action-title">거래하기</div>
                <div className="action-desc">암호화폐 매수/매도</div>
              </div>
            </div>
            
            <div className="quick-action-item" onClick={() => window.dispatchEvent(new CustomEvent('navigateToTopGainers'))}>
              <div className="action-icon">🚀</div>
              <div className="action-content">
                <div className="action-title">상승률 TOP</div>
                <div className="action-desc">인기 코인 차트</div>
              </div>
            </div>
            
            <div className="quick-action-item" onClick={() => window.dispatchEvent(new CustomEvent('navigateToAI'))}>
              <div className="action-icon">🤖</div>
              <div className="action-content">
                <div className="action-title">AI 어시스턴트</div>
                <div className="action-desc">투자 분석 & 조언</div>
              </div>
            </div>
            
            <div className="quick-action-item" onClick={() => window.dispatchEvent(new CustomEvent('navigateToPortfolio'))}>
              <div className="action-icon">💼</div>
              <div className="action-content">
                <div className="action-title">포트폴리오</div>
                <div className="action-desc">보유 현황 확인</div>
              </div>
            </div>
          </div>
        </div>

        {/* AI 추천 */}
        <div className="card ai-recommendations">
          <h3>🤖 AI 투자 조언</h3>
          <div className="recommendations">
            {aiRecommendations.length > 0 ? (
              aiRecommendations.map((rec, index) => (
                <div key={index} className="recommendation-item">
                  <span className={`rec-type ${rec.type}`}>
                    {rec.type === 'buy' ? '매수 추천' : 
                     rec.type === 'hold' ? '보유 유지' : '매도 고려'}
                  </span>
                  <span className="rec-coin">{rec.coin}</span>
                  <span className="rec-reason">{rec.reason}</span>
                </div>
              ))
            ) : (
              <div className="recommendation-item">
                <span className="rec-type loading">🤖 AI 분석 중...</span>
                <span className="rec-coin">-</span>
                <span className="rec-reason">잠시만 기다려주세요</span>
              </div>
            )}
            
            {/* AI 어시스턴트로 이동하는 버튼 */}
            <div className="ai-assistant-link" 
                 onClick={() => window.dispatchEvent(new CustomEvent('navigateToAI'))}>
              <span className="ai-link-text">🤖 더 자세한 AI 분석 받기</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;

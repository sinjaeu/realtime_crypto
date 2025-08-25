import React, { useEffect, useState } from 'react';
import axios from 'axios';
import './Dashboard.css';

const Dashboard = () => {
  const [marketData, setMarketData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [systemStatus, setSystemStatus] = useState({
    api: 'checking',
    redis: 'checking', 
    data_available: false
  });

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

    fetchMarketData();
    checkSystemStatus();
    
    // 5초마다 데이터 업데이트 (더 실시간)
    const interval = setInterval(() => {
      fetchMarketData();
      checkSystemStatus();
    }, 5000);
    
    return () => clearInterval(interval);
  }, []);

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
              <span className="stat-value">$100,000</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">오늘 수익</span>
              <span className="stat-value positive">+$1,234 (+1.23%)</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">보유 코인</span>
              <span className="stat-value">5개</span>
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

        {/* 차트 영역 (임시) */}
        <div className="card chart-area">
          <h3>📈 가격 차트</h3>
          <div className="chart-placeholder">
            <div className="chart-mock">
              <p>📊 실시간 차트가 여기에 표시됩니다</p>
              <p>Chart.js 또는 TradingView 위젯 예정</p>
            </div>
          </div>
        </div>

        {/* AI 추천 */}
        <div className="card ai-recommendations">
          <h3>🤖 AI 투자 조언</h3>
          <div className="recommendations">
            <div className="recommendation-item">
              <span className="rec-type buy">매수 추천</span>
              <span className="rec-coin">BTCUSDC</span>
              <span className="rec-reason">상승 추세 예상</span>
            </div>
            <div className="recommendation-item">
              <span className="rec-type hold">보유 유지</span>
              <span className="rec-coin">ETHUSDC</span>
              <span className="rec-reason">횡보 예상</span>
            </div>
            <div className="recommendation-item">
              <span className="rec-type sell">매도 고려</span>
              <span className="rec-coin">ADAUSDC</span>
              <span className="rec-reason">조정 가능성</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;

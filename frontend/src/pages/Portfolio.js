import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import './Portfolio.css';

const Portfolio = () => {
  const { user } = useAuth();
  const [portfolioData, setPortfolioData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // 포트폴리오 데이터 가져오기
  const fetchPortfolioData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      if (!token) {
        setError('로그인이 필요합니다.');
        setLoading(false);
        return;
      }

      console.log('포트폴리오 API 호출 시작, 토큰:', token ? '있음' : '없음');
      
      const response = await axios.get('http://localhost:8000/api/portfolio', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        timeout: 10000
      });

      console.log('포트폴리오 데이터:', response.data);
      
      // 포트폴리오 데이터 구조 확인 및 기본값 설정
      const portfolioData = {
        balance: response.data.balance || 0,
        total_invested: response.data.total_invested || 0,
        total_value: response.data.total_value || 0,
        total_profit_loss: response.data.total_profit_loss || 0,
        total_profit_loss_pct: response.data.total_profit_loss_pct || 0,
        total_assets: response.data.total_assets || response.data.balance || 0,
        portfolios: response.data.portfolios || []
      };
      
      setPortfolioData(portfolioData);
      setError('');
    } catch (error) {
      console.error('포트폴리오 조회 실패:', error);
      
      if (error.response?.status === 401) {
        setError('로그인이 만료되었습니다. 다시 로그인해주세요.');
        // 토큰이 만료된 경우 로그아웃 처리할 수 있음
        // logout();
      } else if (error.response?.status === 404) {
        setError('포트폴리오 API를 찾을 수 없습니다.');
      } else if (error.code === 'ECONNABORTED') {
        setError('서버 응답 시간이 초과되었습니다.');
      } else {
        setError(`포트폴리오 데이터를 불러올 수 없습니다: ${error.response?.data?.detail || error.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPortfolioData();
    // 30초마다 업데이트
    const interval = setInterval(fetchPortfolioData, 30000);
    return () => clearInterval(interval);
  }, []);

  // 수익률 색상 결정
  const getProfitColor = (profit) => {
    if (profit > 0) return 'positive';
    if (profit < 0) return 'negative';
    return 'neutral';
  };

  // 포트폴리오 차트 데이터 (간단한 도넛 차트용)
  const getPortfolioDistribution = () => {
    if (!portfolioData || !portfolioData.portfolios) return [];
    
    return portfolioData.portfolios.map(coin => ({
      symbol: coin.symbol,
      value: coin.current_value,
      percentage: ((coin.current_value / portfolioData.total_value) * 100).toFixed(1)
    }));
  };

  if (loading) {
    return (
      <div className="portfolio">
        <div className="portfolio-header">
          <h1>💼 포트폴리오</h1>
        </div>
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>포트폴리오 데이터를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="portfolio">
        <div className="portfolio-header">
          <h1>💼 포트폴리오</h1>
        </div>
        <div className="error-container">
          <div className="error-icon">⚠️</div>
          <p className="error-message">{error}</p>
          <div className="error-actions">
            <button onClick={fetchPortfolioData} className="retry-button">
              다시 시도
            </button>
            {error.includes('로그인') && (
              <button 
                onClick={() => window.location.reload()} 
                className="login-button"
              >
                로그인 페이지로
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (!portfolioData || portfolioData.portfolios.length === 0) {
    return (
      <div className="portfolio">
        <div className="portfolio-header">
          <h1>💼 포트폴리오</h1>
          <p>보유 중인 암호화폐 현황을 확인하세요</p>
        </div>
        <div className="empty-portfolio">
          <div className="empty-icon">📊</div>
          <h3>보유 중인 암호화폐가 없습니다</h3>
          <p>거래 페이지에서 첫 번째 투자를 시작해보세요!</p>
          <button 
            className="start-trading-button"
            onClick={() => window.location.href = '#trading'}
          >
            거래 시작하기
          </button>
        </div>
      </div>
    );
  }

  const distribution = getPortfolioDistribution();

  return (
    <div className="portfolio">
      <div className="portfolio-header">
        <h1>💼 포트폴리오</h1>
        <p>보유 중인 암호화폐 현황을 확인하세요</p>
      </div>

      {/* 포트폴리오 요약 */}
      <div className="portfolio-summary">
        <div className="summary-card">
          <div className="summary-title">💰 총 자산</div>
          <div className="summary-value">
            ${portfolioData.total_assets?.toLocaleString() || '0'}
          </div>
          <div className="summary-subtitle">
            현금: ${portfolioData.balance?.toLocaleString() || '0'} | 
            투자: ${portfolioData.total_value?.toLocaleString() || '0'}
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-title">📈 총 수익/손실</div>
          <div className={`summary-value ${getProfitColor(portfolioData.total_profit_loss)}`}>
            ${portfolioData.total_profit_loss?.toLocaleString() || '0'}
          </div>
          <div className={`summary-subtitle ${getProfitColor(portfolioData.total_profit_loss)}`}>
            {portfolioData.total_profit_loss_pct >= 0 ? '+' : ''}
            {portfolioData.total_profit_loss_pct?.toFixed(2) || '0.00'}%
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-title">💎 보유 종목</div>
          <div className="summary-value">
            {portfolioData.portfolios?.length || 0}개
          </div>
          <div className="summary-subtitle">
            총 투자금: ${portfolioData.total_invested?.toLocaleString() || '0'}
          </div>
        </div>
      </div>

      {/* 포트폴리오 분포 */}
      <div className="portfolio-content">
        <div className="portfolio-distribution">
          <h3>📊 포트폴리오 분포</h3>
          <div className="distribution-list">
            {distribution.map(item => (
              <div key={item.symbol} className="distribution-item">
                <div className="distribution-info">
                  <span className="distribution-symbol">{item.symbol}</span>
                  <span className="distribution-percentage">{item.percentage}%</span>
                </div>
                <div className="distribution-bar">
                  <div 
                    className="distribution-fill"
                    style={{ width: `${item.percentage}%` }}
                  ></div>
                </div>
                <div className="distribution-value">
                  ${item.value?.toLocaleString()}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 보유 코인 상세 */}
        <div className="portfolio-details">
          <h3>💰 보유 코인 상세</h3>
          <div className="portfolio-table">
            <div className="table-header">
              <div className="col-symbol">코인</div>
              <div className="col-quantity">보유량</div>
              <div className="col-avg-price">평균단가</div>
              <div className="col-current-price">현재가</div>
              <div className="col-value">평가금액</div>
              <div className="col-profit">수익/손실</div>
            </div>

            {portfolioData.portfolios.map(coin => (
              <div key={coin.symbol} className="table-row">
                <div className="col-symbol">
                  <span className="coin-symbol">{coin.symbol}</span>
                </div>
                <div className="col-quantity">
                  {coin.quantity?.toFixed(8)}
                </div>
                <div className="col-avg-price">
                  ${coin.avg_price?.toFixed(4)}
                </div>
                <div className="col-current-price">
                  ${coin.current_price?.toFixed(4)}
                </div>
                <div className="col-value">
                  ${coin.current_value?.toLocaleString()}
                </div>
                <div className={`col-profit ${getProfitColor(coin.profit_loss)}`}>
                  <div className="profit-amount">
                    {coin.profit_loss >= 0 ? '+' : ''}${coin.profit_loss?.toLocaleString()}
                  </div>
                  <div className="profit-percentage">
                    ({coin.profit_loss_pct >= 0 ? '+' : ''}{coin.profit_loss_pct?.toFixed(2)}%)
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Portfolio;

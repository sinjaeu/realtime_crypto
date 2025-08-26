import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import PriceChart from '../components/PriceChart';
import { useAuth } from '../contexts/AuthContext';
import './LiveTracker.css';

const LiveTracker = () => {
  const { user } = useAuth();
  const [allCoins, setAllCoins] = useState([]);
  const [selectedCoin, setSelectedCoin] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredCoins, setFilteredCoins] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [watchlist, setWatchlist] = useState(['BTCUSDC', 'ETHUSDC', 'ADAUSDC']); // 기본 관심 목록
  const [portfolioData, setPortfolioData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const searchInputRef = useRef(null);

  // 모든 코인 데이터 가져오기
  const fetchAllCoins = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/market/prices', {
        timeout: 10000,
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (response.data.success) {
        setAllCoins(response.data.data);
        setError('');
        
        // 첫 번째 코인을 기본 선택 (BTCUSDC 우선)
        if (!selectedCoin && response.data.data.length > 0) {
          const btc = response.data.data.find(coin => coin.symbol === 'BTCUSDC');
          setSelectedCoin(btc || response.data.data[0]);
        }
      } else {
        setError('시장 데이터를 불러올 수 없습니다.');
      }
    } catch (error) {
      console.error('시장 데이터 조회 실패:', error);
      setError('서버 연결에 실패했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 포트폴리오 데이터 가져오기 (보유 수량 확인용)
  const fetchPortfolioData = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;

      const response = await axios.get('http://localhost:8000/api/portfolio', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        timeout: 10000
      });

      if (response.data.success) {
        setPortfolioData(response.data.data);
      }
    } catch (error) {
      console.error('포트폴리오 데이터 조회 실패:', error);
    }
  };

  useEffect(() => {
    fetchAllCoins();
    fetchPortfolioData();
    
    // 5초마다 데이터 업데이트
    const interval = setInterval(() => {
      fetchAllCoins();
      fetchPortfolioData();
    }, 5000);
    
    return () => clearInterval(interval);
  }, []);

  // 검색 필터링
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredCoins([]);
      setShowSuggestions(false);
      return;
    }

    const filtered = allCoins.filter(coin =>
      coin.symbol.toLowerCase().includes(searchQuery.toLowerCase())
    ).slice(0, 10); // 상위 10개만 표시

    setFilteredCoins(filtered);
    setShowSuggestions(true);
  }, [searchQuery, allCoins]);

  // 코인 선택
  const handleCoinSelect = (coin) => {
    setSelectedCoin(coin);
    setSearchQuery('');
    setShowSuggestions(false);
    
    // 관심 목록에 추가 (중복 제거)
    if (!watchlist.includes(coin.symbol)) {
      setWatchlist(prev => [coin.symbol, ...prev].slice(0, 6)); // 최대 6개
    }
  };

  // 관심 목록에서 코인 선택
  const handleWatchlistSelect = (symbol) => {
    const coin = allCoins.find(c => c.symbol === symbol);
    if (coin) {
      setSelectedCoin(coin);
    }
  };

  // 관심 목록에서 제거
  const removeFromWatchlist = (symbol) => {
    setWatchlist(prev => prev.filter(s => s !== symbol));
  };

  // 보유 수량 조회
  const getHoldingQuantity = (symbol) => {
    if (!portfolioData || !portfolioData.portfolios) return 0;
    const holding = portfolioData.portfolios.find(p => p.symbol === symbol);
    return holding ? holding.quantity : 0;
  };

  // 거래 페이지로 이동
  const navigateToTrading = (symbol, type = 'BUY') => {
    // 거래 페이지로 이동하면서 선택된 코인 정보 전달
    window.dispatchEvent(new CustomEvent('navigateToTradingWithSymbol', {
      detail: { symbol, type }
    }));
  };

  // 외부 클릭 시 검색 제안 닫기
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (searchInputRef.current && !searchInputRef.current.contains(event.target)) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (loading) {
    return (
      <div className="live-tracker">
        <div className="tracker-header">
          <h1>📈 실시간 가격 추적</h1>
        </div>
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>실시간 데이터를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="live-tracker">
        <div className="tracker-header">
          <h1>📈 실시간 가격 추적</h1>
        </div>
        <div className="error-container">
          <div className="error-icon">⚠️</div>
          <p className="error-message">{error}</p>
          <button onClick={fetchAllCoins} className="retry-button">
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="live-tracker">
      <div className="tracker-header">
        <h1>📈 실시간 가격 추적</h1>
        <p>원하는 코인을 검색하여 실시간 가격 변동을 추적하세요</p>
        
        {/* 검색 바 */}
        <div className="search-section" ref={searchInputRef}>
          <div className="search-container">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="코인 검색 (예: BTC, ETH, ADA...)"
              className="search-input"
            />
            <div className="search-icon">🔍</div>
          </div>
          
          {/* 검색 제안 */}
          {showSuggestions && filteredCoins.length > 0 && (
            <div className="search-suggestions">
              {filteredCoins.map(coin => (
                <div
                  key={coin.symbol}
                  className="suggestion-item"
                  onClick={() => handleCoinSelect(coin)}
                >
                  <div className="suggestion-info">
                    <span className="suggestion-symbol">{coin.symbol}</span>
                    <span className="suggestion-price">${coin.formatted_price}</span>
                  </div>
                  <div className={`suggestion-change ${coin.change_class}`}>
                    {coin.change}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="tracker-content">
        {/* 좌측: 관심 목록 & 선택된 코인 정보 */}
        <div className="sidebar-panel">
          {/* 관심 목록 */}
          <div className="watchlist-section">
            <h3>⭐ 관심 목록</h3>
            <div className="watchlist">
              {watchlist.map(symbol => {
                const coin = allCoins.find(c => c.symbol === symbol);
                if (!coin) return null;
                
                return (
                  <div
                    key={symbol}
                    className={`watchlist-item ${selectedCoin?.symbol === symbol ? 'active' : ''}`}
                    onClick={() => handleWatchlistSelect(symbol)}
                  >
                    <div className="watchlist-info">
                      <div className="watchlist-symbol">{symbol}</div>
                      <div className="watchlist-price">${coin.formatted_price}</div>
                    </div>
                    <div className={`watchlist-change ${coin.change_class}`}>
                      {coin.change}
                    </div>
                    <button
                      className="remove-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        removeFromWatchlist(symbol);
                      }}
                    >
                      ✕
                    </button>
                  </div>
                );
              })}
            </div>
          </div>

          {/* 선택된 코인 정보 */}
          {selectedCoin && (
            <div className="coin-info-section">
              <h3>📊 코인 정보</h3>
              <div className="coin-details">
                <div className="coin-header">
                  <h4>{selectedCoin.symbol}</h4>
                  <div className={`coin-change ${selectedCoin.change_class}`}>
                    {selectedCoin.change}
                  </div>
                </div>
                
                <div className="coin-stats">
                  <div className="stat-row">
                    <span className="stat-label">현재가</span>
                    <span className="stat-value">${selectedCoin.formatted_price}</span>
                  </div>
                  <div className="stat-row">
                    <span className="stat-label">24분 변동</span>
                    <span className={`stat-value ${selectedCoin.change_class}`}>
                      {selectedCoin.change_percent?.toFixed(2)}%
                    </span>
                  </div>
                  <div className="stat-row">
                    <span className="stat-label">보유 수량</span>
                    <span className="stat-value">
                      {getHoldingQuantity(selectedCoin.symbol).toFixed(8)}
                    </span>
                  </div>
                </div>

                {/* 빠른 거래 버튼 */}
                <div className="quick-trade-buttons">
                  <button
                    className="trade-btn buy-btn"
                    onClick={() => navigateToTrading(selectedCoin.symbol, 'BUY')}
                  >
                    💰 매수
                  </button>
                  <button
                    className="trade-btn sell-btn"
                    onClick={() => navigateToTrading(selectedCoin.symbol, 'SELL')}
                    disabled={getHoldingQuantity(selectedCoin.symbol) === 0}
                  >
                    💸 매도
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 우측: 실시간 차트 */}
        <div className="chart-panel">
          {selectedCoin ? (
            <div className="chart-section">
              <div className="chart-header">
                <div className="chart-title">
                  <h3>{selectedCoin.symbol} 실시간 차트</h3>
                  <div className="chart-price">
                    <span className="current-price">${selectedCoin.formatted_price}</span>
                    <span className={`price-change ${selectedCoin.change_class}`}>
                      {selectedCoin.change}
                    </span>
                  </div>
                </div>
                
                <div className="chart-info">
                  <span className="update-time">
                    업데이트: {new Date().toLocaleTimeString('ko-KR')}
                  </span>
                </div>
              </div>
              
              <div className="chart-container">
                <PriceChart
                  symbol={selectedCoin.symbol}
                  priceHistory={selectedCoin.price_history || []}
                  currentPrice={selectedCoin.price}
                  changePercent={selectedCoin.change_percent || 0}
                  height={500}
                />
              </div>
            </div>
          ) : (
            <div className="chart-placeholder">
              <div className="placeholder-content">
                <div className="placeholder-icon">📈</div>
                <h3>코인을 선택하세요</h3>
                <p>검색하거나 관심 목록에서 코인을 선택하면<br/>실시간 가격 차트를 확인할 수 있습니다.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default LiveTracker;

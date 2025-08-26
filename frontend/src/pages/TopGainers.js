import React, { useState, useEffect } from 'react';
import axios from 'axios';
import PriceChart from '../components/PriceChart';
import './TopGainers.css';

const TopGainers = () => {
  const [topGainers, setTopGainers] = useState([]);
  const [allCoins, setAllCoins] = useState([]);
  const [filteredGainers, setFilteredGainers] = useState([]);
  const [selectedCoin, setSelectedCoin] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [limit, setLimit] = useState(10);
  const [searchQuery, setSearchQuery] = useState('');

  // 전체 코인 데이터 가져오기 (검색용)
  const fetchAllCoins = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/market/prices', {
        timeout: 10000,
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (response.data.success) {
        const coinsData = response.data.data.map(coin => ({
          ...coin,
          change_percent: coin.change_percent || 0,
          change: coin.change || '0.00%',
          change_class: coin.change_class || 'neutral'
        }));
        setAllCoins(coinsData);
        console.log(`전체 코인 ${coinsData.length}개 로드됨 (검색용)`);
      }
    } catch (error) {
      console.error('전체 코인 데이터 조회 실패:', error);
    }
  };

  // 상위 상승률 코인 데이터 가져오기
  const fetchTopGainers = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`http://localhost:8000/api/market/top-gainers?limit=${limit}`, {
        timeout: 10000,
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (response.data.success) {
        const gainersData = response.data.data
          .map(coin => ({
            ...coin,
            change_percent: coin.change_percent || 0,
            change: coin.change || '0.00%',
            change_class: coin.change_class || 'neutral'
          }))
          .filter(coin => coin.change_percent > 0.01); // 프론트엔드에서도 추가 필터링
        
        console.log(`상승 코인 ${gainersData.length}개 로드됨:`, gainersData.map(c => `${c.symbol}: ${c.change_percent.toFixed(2)}%`));
        
        setTopGainers(gainersData);
        setFilteredGainers(gainersData);
        
        // 첫 번째 코인을 기본 선택
        if (gainersData.length > 0 && !selectedCoin) {
          setSelectedCoin(gainersData[0]);
        }
        
        setError('');
      } else {
        setError(response.data.message || '데이터를 불러올 수 없습니다.');
        setTopGainers([]);
        setFilteredGainers([]);
      }
    } catch (error) {
      console.error('상위 상승률 코인 조회 실패:', error);
      setError('서버 연결에 실패했습니다.');
      setTopGainers([]);
    } finally {
      setLoading(false);
    }
  };

  // 검색 필터링
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredGainers(topGainers);
      return;
    }

    // 검색할 때는 전체 코인 데이터에서 검색
    const searchData = allCoins.length > 0 ? allCoins : topGainers;
    const filtered = searchData.filter(coin =>
      coin.symbol.toLowerCase().includes(searchQuery.toLowerCase())
    );
    setFilteredGainers(filtered);
    
    // 검색 결과가 있으면 첫 번째 코인 선택
    if (filtered.length > 0) {
      setSelectedCoin(filtered[0]);
    }
    
    console.log(`검색 "${searchQuery}": ${filtered.length}개 결과 (전체 ${searchData.length}개 중)`);
  }, [searchQuery, topGainers, allCoins]);

  useEffect(() => {
    fetchTopGainers();
    fetchAllCoins(); // 검색용 전체 코인 데이터 로드
    
    // 30초마다 데이터 업데이트
    const interval = setInterval(() => {
      fetchTopGainers();
      fetchAllCoins();
    }, 30000);
    return () => clearInterval(interval);
  }, [limit]);

  const handleCoinSelect = (coin) => {
    setSelectedCoin(coin);
  };

  const handleLimitChange = (newLimit) => {
    setLimit(newLimit);
    setSelectedCoin(null); // 선택 초기화
    setSearchQuery(''); // 검색어 초기화
  };

  const handleTradeNavigation = (symbol, tradeType) => {
    // 커스텀 이벤트로 거래 페이지 이동 및 코인 선택
    window.dispatchEvent(new CustomEvent('navigateToTrading', {
      detail: { symbol, tradeType }
    }));
  };

  if (loading && topGainers.length === 0) {
    return (
      <div className="top-gainers">
        <div className="top-gainers-header">
          <h1>🚀 상승률 TOP 코인</h1>
        </div>
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>상승률 데이터를 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="top-gainers">
        <div className="top-gainers-header">
          <h1>🚀 상승률 TOP 코인</h1>
        </div>
        <div className="error-container">
          <div className="error-icon">⚠️</div>
          <p className="error-message">{error}</p>
          <button onClick={fetchTopGainers} className="retry-button">
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  // 상승 코인이 없을 때
  if (!loading && topGainers.length === 0) {
    return (
      <div className="top-gainers">
        <div className="top-gainers-header">
          <h1>🚀 상승률 TOP 코인</h1>
          <p>5분간 가격 변동률 기준 상위 코인</p>
        </div>
        <div className="no-gainers">
          <div className="no-gainers-content">
            <div className="no-gainers-icon">📉</div>
            <h3>현재 상승하는 코인이 없습니다</h3>
            <p>시장이 조정 중이거나 하락세입니다.</p>
            <p>잠시 후 다시 확인해보세요.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="top-gainers">
      <div className="top-gainers-header">
        <h1>🚀 상승률 TOP 코인</h1>
        <p>5분간 가격 변동률 기준 상위 코인</p>
        
        <div className="controls">
          <div className="control-left">
            <div className="limit-selector">
              <label>표시 개수:</label>
              <select value={limit} onChange={(e) => handleLimitChange(Number(e.target.value))}>
                <option value={5}>TOP 5</option>
                <option value={10}>TOP 10</option>
                <option value={15}>TOP 15</option>
                <option value={20}>TOP 20</option>
              </select>
            </div>
            
            <div className="search-container">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="코인 검색 (예: BTC, ETH...)"
                className="search-input"
              />
              <div className="search-icon">🔍</div>
            </div>
          </div>
          
          <div className="last-updated">
            마지막 업데이트: {new Date().toLocaleTimeString('ko-KR')}
          </div>
        </div>
      </div>

      <div className="top-gainers-content">
        {/* 좌측: 코인 순위 리스트 */}
        <div className="gainers-list">
          <div className="list-header">
            <h3>📈 상승률 순위</h3>
          </div>
          
          <div className="gainers-table">
            <div className="table-header">
              <div className="col-rank">순위</div>
              <div className="col-symbol">코인</div>
              <div className="col-price">가격</div>
              <div className="col-change">변동률</div>
            </div>
            
            {filteredGainers.length > 0 ? (
              filteredGainers.map((coin, index) => (
                <div 
                  key={coin.symbol} 
                  className={`table-row ${selectedCoin?.symbol === coin.symbol ? 'selected' : ''}`}
                  onClick={() => handleCoinSelect(coin)}
                >
                  <div className="col-rank">
                    <span className="rank-number">#{index + 1}</span>
                  </div>
                  <div className="col-symbol">
                    <span className="symbol-name">{coin.symbol}</span>
                  </div>
                  <div className="col-price">
                    <span className="price-value">${coin.formatted_price}</span>
                  </div>
                  <div className={`col-change ${coin.change_class}`}>
                    <span className="change-value">{coin.change}</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="no-results">
                <div className="no-results-content">
                  <div className="no-results-icon">🔍</div>
                  <p>검색 결과가 없습니다.</p>
                  <p>다른 키워드로 검색해보세요.</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 우측: 선택된 코인 차트 */}
        <div className="chart-section">
          {selectedCoin ? (
            <>
              <div className="chart-header">
                <div className="coin-info">
                  <h3>{selectedCoin.symbol}</h3>
                  <div className="price-info">
                    <span className="current-price">${selectedCoin.formatted_price}</span>
                    <span className={`price-change ${selectedCoin.change_class}`}>
                      {selectedCoin.change}
                    </span>
                  </div>
                </div>
                
                <div className="chart-stats">
                  <div className="stat-item">
                    <span className="stat-label">5분 변동</span>
                    <span className={`stat-value ${selectedCoin.change_class}`}>
                      {selectedCoin.change_percent ? selectedCoin.change_percent.toFixed(2) : '0.00'}%
                    </span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">데이터 포인트</span>
                    <span className="stat-value">{selectedCoin.price_history?.length || 0}개</span>
                  </div>
                  <div className="stat-item">
                    <span className="stat-label">순위</span>
                    <span className="stat-value">#{filteredGainers.findIndex(c => c.symbol === selectedCoin.symbol) + 1}</span>
                  </div>
                </div>
                
                <div className="trade-actions">
                  <button 
                    className="trade-button buy-button"
                    onClick={() => handleTradeNavigation(selectedCoin.symbol, 'buy')}
                  >
                    🚀 매수하기
                  </button>
                  <button 
                    className="trade-button sell-button"
                    onClick={() => handleTradeNavigation(selectedCoin.symbol, 'sell')}
                  >
                    💰 매도하기
                  </button>
                </div>
              </div>
              
              <div className="chart-container">
                <PriceChart
                  symbol={selectedCoin.symbol}
                  priceHistory={selectedCoin.price_history}
                  currentPrice={selectedCoin.price}
                  changePercent={selectedCoin.change_percent}
                  height={400}
                />
              </div>
            </>
          ) : (
            <div className="chart-placeholder">
              <div className="placeholder-content">
                <div className="placeholder-icon">📊</div>
                <h3>코인을 선택하세요</h3>
                <p>좌측 리스트에서 코인을 클릭하면<br/>가격 차트를 확인할 수 있습니다.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TopGainers;

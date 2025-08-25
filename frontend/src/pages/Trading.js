import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import './Trading.css';

const Trading = () => {
  const { user, updateUserBalance } = useAuth();
  const [selectedSymbol, setSelectedSymbol] = useState('BTCUSDC');
  const [tradeType, setTradeType] = useState('BUY');
  const [quantity, setQuantity] = useState('');
  const [marketData, setMarketData] = useState([]);
  const [filteredMarketData, setFilteredMarketData] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [symbolSearchQuery, setSymbolSearchQuery] = useState('');
  const [showSymbolDropdown, setShowSymbolDropdown] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [currentPrice, setCurrentPrice] = useState(111077.01); // BTCUSDC 기본값
  
  // 거래 계산 상태
  const [totalAmount, setTotalAmount] = useState(0);
  const [fee, setFee] = useState(0);
  const [finalAmount, setFinalAmount] = useState(0);

  const showMessage = (type, text) => {
    setMessage({ type, text });
    setTimeout(() => setMessage({ type: '', text: '' }), 5000);
  };

  // 검색 필터링 함수
  const filterMarketData = (data, query) => {
    if (!query) return data;
    
    const searchTerm = query.toLowerCase();
    return data.filter(coin => 
      coin.symbol.toLowerCase().includes(searchTerm)
    );
  };

  // 마켓 데이터 가져오기
  const fetchMarketData = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/market/prices', {
        timeout: 10000,
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      console.log('마켓 데이터 응답:', response.data);
      
      if (response.data && response.data.success && response.data.data) {
        // 가격이 0보다 큰 거래쌍만 필터링
        const validPrices = response.data.data.filter(coin => coin.price > 0);
        setMarketData(validPrices);
        
        // 검색 필터 적용
        const filtered = filterMarketData(validPrices, searchQuery);
        setFilteredMarketData(filtered);
        
        // 선택된 심볼의 현재 가격 업데이트
        const selectedCoin = validPrices.find(coin => coin.symbol === selectedSymbol);
        if (selectedCoin) {
          setCurrentPrice(selectedCoin.price);
        }
      } else {
        console.warn('마켓 데이터 형식이 예상과 다릅니다:', response.data);
        showMessage('warning', '마켓 데이터를 불러오는 중 문제가 발생했습니다.');
      }
    } catch (error) {
      console.error('마켓 데이터 조회 실패:', error);
      showMessage('error', '마켓 데이터를 불러올 수 없습니다. 잠시 후 다시 시도해주세요.');
      
      // 기본 데이터 설정 (오류 시 대체)
      setMarketData([
        { symbol: 'BTCUSDC', price: 111077.01, change: 0 },
        { symbol: 'ETHUSDC', price: 4522.83, change: 0 },
        { symbol: 'BNBUSDC', price: 850.84, change: 0 }
      ]);
    }
  };

  // 거래 금액 계산
  const calculateTrade = () => {
    if (!quantity || !currentPrice) {
      setTotalAmount(0);
      setFee(0);
      setFinalAmount(0);
      return;
    }

    const qty = parseFloat(quantity);
    const price = parseFloat(currentPrice);
    const total = qty * price;
    const tradeFee = total * 0.001; // 0.1% 수수료
    
    setTotalAmount(total);
    setFee(tradeFee);
    
    if (tradeType === 'BUY') {
      setFinalAmount(total + tradeFee); // 매수 시 수수료 추가
    } else {
      setFinalAmount(total - tradeFee); // 매도 시 수수료 차감
    }
  };

  // 거래 실행
  const executeTrade = async () => {
    if (!quantity || parseFloat(quantity) <= 0) {
      showMessage('error', '올바른 수량을 입력해주세요.');
      return;
    }

    if (tradeType === 'BUY' && finalAmount > user.balance) {
      showMessage('error', '잔고가 부족합니다.');
      return;
    }

    setLoading(true);

    try {
      const endpoint = tradeType === 'BUY' ? '/api/trade/buy' : '/api/trade/sell';
      const token = localStorage.getItem('token');
      
      if (!token) {
        showMessage('error', '로그인이 필요합니다.');
        return;
      }

      const response = await axios.post(`http://localhost:8000${endpoint}`, {
        symbol: selectedSymbol,
        quantity: parseFloat(quantity),
        trade_type: tradeType
      }, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.data.success) {
        showMessage('success', response.data.message);
        updateUserBalance(response.data.new_balance);
        setQuantity('');
        calculateTrade();
      }
    } catch (error) {
      console.error('거래 실행 실패:', error);
      const errorMessage = error.response?.data?.detail || '거래 실행에 실패했습니다.';
      showMessage('error', errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // 빠른 수량 설정
  const setQuickQuantity = (percentage) => {
    if (tradeType === 'BUY' && currentPrice > 0) {
      const availableAmount = user.balance * (percentage / 100);
      const qty = (availableAmount / (currentPrice * 1.001)).toFixed(8); // 수수료 고려
      setQuantity(qty);
    }
    // 매도의 경우 포트폴리오 데이터가 필요하므로 나중에 구현
  };

  // 검색 입력 핸들러
  const handleSearchChange = (e) => {
    const query = e.target.value;
    setSearchQuery(query);
    
    // 실시간 필터링
    const filtered = filterMarketData(marketData, query);
    setFilteredMarketData(filtered);
  };

  // 심볼 검색 핸들러
  const handleSymbolSearch = (e) => {
    setSymbolSearchQuery(e.target.value);
  };

  // 심볼 선택 핸들러
  const handleSymbolSelect = (symbol) => {
    setSelectedSymbol(symbol);
    setSymbolSearchQuery('');
    setShowSymbolDropdown(false);
    
    // 선택된 심볼의 가격 업데이트
    const selectedCoin = marketData.find(coin => coin.symbol === symbol);
    if (selectedCoin) {
      setCurrentPrice(selectedCoin.price);
    }
  };

  // 필터된 심볼 목록
  const getFilteredSymbols = () => {
    if (!symbolSearchQuery) return marketData.slice(0, 10); // 기본적으로 상위 10개만 표시
    
    return marketData.filter(coin => 
      coin.symbol.toLowerCase().includes(symbolSearchQuery.toLowerCase())
    ).slice(0, 20); // 검색 시 상위 20개까지 표시
  };

  useEffect(() => {
    fetchMarketData();
    const interval = setInterval(fetchMarketData, 5000); // 5초마다 업데이트
    return () => clearInterval(interval);
  }, []);

  // 검색어 변경 시 필터링
  useEffect(() => {
    const filtered = filterMarketData(marketData, searchQuery);
    setFilteredMarketData(filtered);
  }, [marketData, searchQuery]);

  useEffect(() => {
    calculateTrade();
  }, [quantity, currentPrice, tradeType]);

  useEffect(() => {
    // 선택된 심볼이 변경될 때 현재 가격 업데이트
    const selectedCoin = marketData.find(coin => coin.symbol === selectedSymbol);
    if (selectedCoin) {
      setCurrentPrice(selectedCoin.price);
    }
  }, [selectedSymbol, marketData]);

  // 외부 클릭 시 드롭다운 닫기
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (!event.target.closest('.symbol-search-container')) {
        setShowSymbolDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="trading">
      <div className="trading-header">
        <h1>💹 거래</h1>
        <p>실시간 암호화폐 거래를 시작하세요</p>
      </div>

      {message.text && (
        <div className={`message ${message.type}`}>
          {message.text}
        </div>
      )}

      <div className="trading-content">
        {/* 좌측: 거래 패널 */}
        <div className="trading-panel">
          <div className="trade-form">
            <div className="trade-header">
              <div className="trade-tabs">
                <button 
                  className={`tab ${tradeType === 'BUY' ? 'active buy' : ''}`}
                  onClick={() => setTradeType('BUY')}
                >
                  매수
                </button>
                <button 
                  className={`tab ${tradeType === 'SELL' ? 'active sell' : ''}`}
                  onClick={() => setTradeType('SELL')}
                >
                  매도
                </button>
              </div>
            </div>

            <div className="form-group">
              <label>거래 쌍</label>
              <div className="symbol-search-container">
                <input
                  type="text"
                  value={symbolSearchQuery || selectedSymbol}
                  onChange={handleSymbolSearch}
                  onFocus={() => setShowSymbolDropdown(true)}
                  placeholder="코인 검색 또는 선택..."
                  className="symbol-search-input"
                />
                
                {showSymbolDropdown && (
                  <div className="symbol-dropdown">
                    {getFilteredSymbols().map(coin => (
                      <div
                        key={coin.symbol}
                        className={`symbol-option ${selectedSymbol === coin.symbol ? 'selected' : ''}`}
                        onClick={() => handleSymbolSelect(coin.symbol)}
                      >
                        <div className="symbol-info">
                          <span className="symbol-name">{coin.symbol}</span>
                          <span className="symbol-price">${coin.price?.toFixed(4)}</span>
                        </div>
                        <div className={`symbol-change ${coin.change_percent >= 0 ? 'positive' : 'negative'}`}>
                          {coin.change || '0.00%'}
                        </div>
                      </div>
                    ))}
                    
                    {getFilteredSymbols().length === 0 && (
                      <div className="no-results">
                        검색 결과가 없습니다.
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            <div className="form-group">
              <label>현재 가격</label>
              <div className="current-price">
                ${currentPrice.toFixed(4)}
              </div>
            </div>

            <div className="form-group">
              <label>수량</label>
              <input
                type="number"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                placeholder="거래할 수량을 입력하세요"
                step="0.00000001"
                min="0"
              />
              
              {tradeType === 'BUY' && (
                <div className="quick-amounts">
                  <button onClick={() => setQuickQuantity(25)}>25%</button>
                  <button onClick={() => setQuickQuantity(50)}>50%</button>
                  <button onClick={() => setQuickQuantity(75)}>75%</button>
                  <button onClick={() => setQuickQuantity(100)}>100%</button>
                </div>
              )}
            </div>

            {/* 거래 계산 정보 */}
            {quantity && currentPrice > 0 && (
              <div className="trade-calculation">
                <div className="calc-row">
                  <span>거래 금액:</span>
                  <span>${totalAmount.toFixed(2)}</span>
                </div>
                <div className="calc-row">
                  <span>수수료 (0.1%):</span>
                  <span>${fee.toFixed(2)}</span>
                </div>
                <div className="calc-row total">
                  <span>{tradeType === 'BUY' ? '총 필요 금액:' : '받을 금액:'}</span>
                  <span>${finalAmount.toFixed(2)}</span>
                </div>
              </div>
            )}

            <div className="balance-info">
              <span>사용 가능 잔고: ${user?.balance?.toLocaleString() || '0'}</span>
            </div>

            <button 
              className={`trade-button ${tradeType.toLowerCase()}`}
              onClick={executeTrade}
              disabled={loading || !quantity || parseFloat(quantity) <= 0}
            >
              {loading ? '처리 중...' : `${tradeType === 'BUY' ? '매수' : '매도'} 주문`}
            </button>
          </div>
        </div>

        {/* 우측: 마켓 데이터 */}
        <div className="market-panel">
          <h3>📊 실시간 시세</h3>
          
          {/* 검색 입력 */}
          <div className="search-container">
            <input
              type="text"
              placeholder="코인 검색 (예: BTC, ETH, SOL...)"
              value={searchQuery}
              onChange={handleSearchChange}
              className="search-input"
            />
            <div className="search-info">
              {searchQuery ? `${filteredMarketData.length}개 결과` : `${marketData.length}개 코인`}
            </div>
          </div>

          <div className="market-list">
            {filteredMarketData.map(coin => (
              <div 
                key={coin.symbol} 
                className={`market-item ${selectedSymbol === coin.symbol ? 'selected' : ''}`}
                onClick={() => setSelectedSymbol(coin.symbol)}
              >
                <div className="coin-info">
                  <span className="symbol">{coin.symbol}</span>
                  <span className="price">${coin.price?.toFixed(4)}</span>
                </div>
                <div className={`change ${coin.change_percent >= 0 ? 'positive' : 'negative'}`}>
                  {coin.change || '0.00%'}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Trading;

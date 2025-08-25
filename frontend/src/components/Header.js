import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import './Header.css';

const Header = () => {
  const { user, logout } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [showSearchResults, setShowSearchResults] = useState(false);
  const [marketData, setMarketData] = useState([]);

  const handleLogout = () => {
    if (window.confirm('로그아웃하시겠습니까?')) {
      logout();
    }
  };

  const handleSwitchAccount = () => {
    if (window.confirm('다른 계정으로 로그인하시겠습니까?')) {
      logout();
    }
  };

  const formatBalance = (balance) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(balance);
  };

  // 마켓 데이터 가져오기
  const fetchMarketData = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/market/prices');
      if (response.data && response.data.success && response.data.data) {
        const validPrices = response.data.data.filter(coin => coin.price > 0);
        setMarketData(validPrices);
      }
    } catch (error) {
      console.error('마켓 데이터 조회 실패:', error);
    }
  };

  // 검색 처리
  const handleSearchChange = (e) => {
    const query = e.target.value;
    setSearchQuery(query);

    if (!query.trim()) {
      setSearchResults([]);
      setShowSearchResults(false);
      return;
    }

    // 검색 필터링
    const filtered = marketData.filter(coin =>
      coin.symbol.toLowerCase().includes(query.toLowerCase())
    ).slice(0, 10); // 상위 10개만 표시

    setSearchResults(filtered);
    setShowSearchResults(true);
  };

  // 검색 결과 선택
  const handleSearchSelect = (symbol) => {
    setSearchQuery(symbol);
    setShowSearchResults(false);
    
    // 거래 페이지로 이동하는 로직을 여기에 추가할 수 있습니다
    console.log(`${symbol} 선택됨`);
  };

  // 검색창 포커스 아웃
  const handleSearchBlur = () => {
    // 약간의 지연을 두어 클릭 이벤트가 먼저 처리되도록 함
    setTimeout(() => setShowSearchResults(false), 200);
  };

  // 컴포넌트 마운트 시 마켓 데이터 로드
  useEffect(() => {
    fetchMarketData();
  }, []);

  return (
    <header className="header">
      <div className="header-left">
        <div className="logo">
          <h2>🚀 CryptoTrader</h2>
        </div>
      </div>
      
      <div className="header-center">
        <div className="search-bar">
          <input 
            type="text" 
            placeholder="코인 검색 (예: BTCUSDC)" 
            className="search-input"
            value={searchQuery}
            onChange={handleSearchChange}
            onBlur={handleSearchBlur}
            onFocus={() => searchQuery && setShowSearchResults(true)}
          />
          
          {/* 검색 결과 드롭다운 */}
          {showSearchResults && searchResults.length > 0 && (
            <div className="search-results">
              {searchResults.map(coin => (
                <div
                  key={coin.symbol}
                  className="search-result-item"
                  onClick={() => handleSearchSelect(coin.symbol)}
                >
                  <div className="search-coin-info">
                    <span className="search-symbol">{coin.symbol}</span>
                    <span className="search-price">${coin.price?.toFixed(4)}</span>
                  </div>
                  <div className={`search-change ${coin.change_percent >= 0 ? 'positive' : 'negative'}`}>
                    {coin.change || '0.00%'}
                  </div>
                </div>
              ))}
            </div>
          )}
          
          {/* 검색 결과가 없을 때 */}
          {showSearchResults && searchResults.length === 0 && searchQuery && (
            <div className="search-results">
              <div className="no-search-results">
                '{searchQuery}'에 대한 검색 결과가 없습니다.
              </div>
            </div>
          )}
        </div>
      </div>
      
      <div className="header-right">
        <div className="user-info">
          <span className="balance">💰 {formatBalance(user?.balance || 0)}</span>
          <span className="username">{user?.username || '사용자'}</span>
          <div className="avatar-dropdown">
            <div className="avatar">👤</div>
            <div className="dropdown-menu">
              <div className="dropdown-item">
                <span>👤 {user?.username}</span>
              </div>
              <div className="dropdown-item">
                <span>📧 {user?.email}</span>
              </div>
              <div className="dropdown-divider"></div>
              <button className="dropdown-item switch-account-btn" onClick={handleSwitchAccount}>
                🔄 계정 전환
              </button>
              <button className="dropdown-item logout-btn" onClick={handleLogout}>
                🚪 로그아웃
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;

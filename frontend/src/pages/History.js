import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import './History.css';

const History = () => {
  const { user } = useAuth();
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('ALL'); // ALL, BUY, SELL
  const [searchQuery, setSearchQuery] = useState('');

  // 거래 내역 가져오기
  const fetchTransactions = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      if (!token) {
        setError('로그인이 필요합니다.');
        setLoading(false);
        return;
      }

      const response = await axios.get('http://localhost:8000/api/transactions?limit=100', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        timeout: 10000
      });

      console.log('거래 내역:', response.data);
      setTransactions(response.data.transactions || []);
      setError('');
    } catch (error) {
      console.error('거래 내역 조회 실패:', error);
      setError('거래 내역을 불러올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTransactions();
  }, []);

  // 필터링된 거래 내역
  const getFilteredTransactions = () => {
    let filtered = transactions;

    // 타입 필터
    if (filter !== 'ALL') {
      filtered = filtered.filter(tx => tx.type === filter);
    }

    // 검색 필터
    if (searchQuery) {
      filtered = filtered.filter(tx => 
        tx.symbol.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    return filtered;
  };

  // 거래 타입별 스타일
  const getTransactionStyle = (type) => {
    return type === 'BUY' ? 'buy' : 'sell';
  };

  // 날짜 포맷팅
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // 거래 통계 계산
  const getTransactionStats = () => {
    const filtered = getFilteredTransactions();
    const buyTransactions = filtered.filter(tx => tx.type === 'BUY');
    const sellTransactions = filtered.filter(tx => tx.type === 'SELL');
    
    const totalBuyAmount = buyTransactions.reduce((sum, tx) => sum + tx.total_amount, 0);
    const totalSellAmount = sellTransactions.reduce((sum, tx) => sum + tx.total_amount, 0);
    const totalFees = filtered.reduce((sum, tx) => sum + tx.fee, 0);

    return {
      totalTransactions: filtered.length,
      buyCount: buyTransactions.length,
      sellCount: sellTransactions.length,
      totalBuyAmount,
      totalSellAmount,
      totalFees
    };
  };

  const filteredTransactions = getFilteredTransactions();
  const stats = getTransactionStats();

  if (loading) {
    return (
      <div className="history">
        <div className="history-header">
          <h1>📈 거래 내역</h1>
        </div>
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>거래 내역을 불러오는 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="history">
        <div className="history-header">
          <h1>📈 거래 내역</h1>
        </div>
        <div className="error-container">
          <p className="error-message">{error}</p>
          <button onClick={fetchTransactions} className="retry-button">
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="history">
      <div className="history-header">
        <h1>📈 거래 내역</h1>
        <p>모든 거래 기록을 확인하고 분석하세요</p>
      </div>

      {/* 거래 통계 */}
      <div className="transaction-stats">
        <div className="stat-card">
          <div className="stat-title">📊 총 거래</div>
          <div className="stat-value">{stats.totalTransactions}건</div>
          <div className="stat-subtitle">
            매수 {stats.buyCount}건 | 매도 {stats.sellCount}건
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-title">💰 총 거래금액</div>
          <div className="stat-value">
            ${(stats.totalBuyAmount + stats.totalSellAmount).toLocaleString()}
          </div>
          <div className="stat-subtitle">
            매수: ${stats.totalBuyAmount.toLocaleString()} | 
            매도: ${stats.totalSellAmount.toLocaleString()}
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-title">💸 총 수수료</div>
          <div className="stat-value text-warning">
            ${stats.totalFees.toLocaleString()}
          </div>
          <div className="stat-subtitle">
            전체 거래의 0.1% 수수료
          </div>
        </div>
      </div>

      {/* 필터 및 검색 */}
      <div className="history-controls">
        <div className="filter-buttons">
          <button 
            className={`filter-btn ${filter === 'ALL' ? 'active' : ''}`}
            onClick={() => setFilter('ALL')}
          >
            전체
          </button>
          <button 
            className={`filter-btn buy ${filter === 'BUY' ? 'active' : ''}`}
            onClick={() => setFilter('BUY')}
          >
            매수
          </button>
          <button 
            className={`filter-btn sell ${filter === 'SELL' ? 'active' : ''}`}
            onClick={() => setFilter('SELL')}
          >
            매도
          </button>
        </div>

        <div className="search-container">
          <input
            type="text"
            placeholder="코인 검색..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
        </div>
      </div>

      {/* 거래 내역 테이블 */}
      {filteredTransactions.length === 0 ? (
        <div className="empty-history">
          <div className="empty-icon">📋</div>
          <h3>
            {searchQuery || filter !== 'ALL' 
              ? '검색 결과가 없습니다' 
              : '거래 내역이 없습니다'}
          </h3>
          <p>
            {searchQuery || filter !== 'ALL'
              ? '다른 검색어나 필터를 시도해보세요'
              : '거래 페이지에서 첫 번째 거래를 시작해보세요!'}
          </p>
        </div>
      ) : (
        <div className="history-table">
          <div className="table-header">
            <div className="col-date">날짜</div>
            <div className="col-type">구분</div>
            <div className="col-symbol">코인</div>
            <div className="col-quantity">수량</div>
            <div className="col-price">가격</div>
            <div className="col-amount">금액</div>
            <div className="col-fee">수수료</div>
            <div className="col-status">상태</div>
          </div>

          {filteredTransactions.map(transaction => (
            <div key={transaction.id} className="table-row">
              <div className="col-date">
                {formatDate(transaction.created_at)}
              </div>
              <div className={`col-type ${getTransactionStyle(transaction.type)}`}>
                <span className="type-badge">
                  {transaction.type === 'BUY' ? '매수' : '매도'}
                </span>
              </div>
              <div className="col-symbol">
                <span className="symbol-name">{transaction.symbol}</span>
              </div>
              <div className="col-quantity">
                {transaction.quantity?.toFixed(8)}
              </div>
              <div className="col-price">
                ${transaction.price?.toFixed(4)}
              </div>
              <div className="col-amount">
                ${transaction.total_amount?.toLocaleString()}
              </div>
              <div className="col-fee">
                ${transaction.fee?.toFixed(2)}
              </div>
              <div className="col-status">
                <span className={`status-badge ${transaction.status.toLowerCase()}`}>
                  {transaction.status === 'COMPLETED' ? '완료' : transaction.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default History;

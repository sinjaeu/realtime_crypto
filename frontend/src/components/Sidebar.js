import React, { useState } from 'react';
import './Sidebar.css';

const Sidebar = ({ activeTab, setActiveTab }) => {
  const menuItems = [
    { id: 'dashboard', icon: '📊', label: '대시보드', description: '시장 현황' },
    { id: 'trading', icon: '💹', label: '거래', description: '매수/매도' },
    { id: 'portfolio', icon: '💼', label: '포트폴리오', description: '보유 현황' },
    { id: 'ai-assistant', icon: '🤖', label: 'AI 어시스턴트', description: '투자 조언' },
    { id: 'history', icon: '📈', label: '거래 내역', description: '과거 거래' },
    { id: 'settings', icon: '⚙️', label: '설정', description: '계정 설정' },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-content">
        <nav className="sidebar-nav">
          {menuItems.map((item) => (
            <div
              key={item.id}
              className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
              onClick={() => setActiveTab(item.id)}
            >
              <div className="nav-icon">{item.icon}</div>
              <div className="nav-text">
                <div className="nav-label">{item.label}</div>
                <div className="nav-description">{item.description}</div>
              </div>
            </div>
          ))}
        </nav>
        
        <div className="sidebar-footer">
          <div className="market-status">
            <div className="status-indicator online"></div>
            <span>시장 연결됨</span>
          </div>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;

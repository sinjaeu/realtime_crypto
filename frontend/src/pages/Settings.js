import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';
import './Settings.css';

const Settings = () => {
  const { user, logout, updateUserBalance } = useAuth();
  const [activeSection, setActiveSection] = useState('profile');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  // 프로필 수정 상태
  const [profileData, setProfileData] = useState({
    username: user?.username || '',
    email: user?.email || ''
  });

  // 비밀번호 변경 상태
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });

  const showMessage = (type, text) => {
    setMessage({ type, text });
    setTimeout(() => setMessage({ type: '', text: '' }), 3000);
  };

  const handleProfileUpdate = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      // 실제로는 백엔드 API 호출
      // const response = await axios.put('/api/auth/profile', profileData);
      
      // 임시로 성공 메시지만 표시
      showMessage('success', '프로필이 업데이트되었습니다.');
      console.log('프로필 업데이트:', profileData);
    } catch (error) {
      showMessage('error', '프로필 업데이트에 실패했습니다.');
      console.error('프로필 업데이트 오류:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();

    if (passwordData.newPassword !== passwordData.confirmPassword) {
      showMessage('error', '새 비밀번호가 일치하지 않습니다.');
      return;
    }

    if (passwordData.newPassword.length < 6) {
      showMessage('error', '새 비밀번호는 최소 6자 이상이어야 합니다.');
      return;
    }

    setLoading(true);

    try {
      // 실제로는 백엔드 API 호출
      // const response = await axios.put('/api/auth/password', {
      //   current_password: passwordData.currentPassword,
      //   new_password: passwordData.newPassword
      // });

      showMessage('success', '비밀번호가 변경되었습니다.');
      setPasswordData({
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      });
    } catch (error) {
      showMessage('error', '비밀번호 변경에 실패했습니다.');
      console.error('비밀번호 변경 오류:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleResetBalance = () => {
    if (window.confirm('잔고를 초기값($100,000)으로 재설정하시겠습니까?')) {
      updateUserBalance(100000);
      showMessage('success', '잔고가 재설정되었습니다.');
    }
  };

  const handleDeleteAccount = () => {
    if (window.confirm('정말로 계정을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) {
      if (window.confirm('모든 데이터가 삭제됩니다. 정말 진행하시겠습니까?')) {
        // 실제로는 백엔드 API 호출 후 로그아웃
        showMessage('success', '계정이 삭제되었습니다.');
        setTimeout(() => logout(), 2000);
      }
    }
  };

  const renderProfileSection = () => (
    <div className="settings-section">
      <h3>👤 프로필 정보</h3>
      <form onSubmit={handleProfileUpdate} className="settings-form">
        <div className="form-group">
          <label>사용자명</label>
          <input
            type="text"
            value={profileData.username}
            onChange={(e) => setProfileData({...profileData, username: e.target.value})}
            required
          />
        </div>
        
        <div className="form-group">
          <label>이메일</label>
          <input
            type="email"
            value={profileData.email}
            onChange={(e) => setProfileData({...profileData, email: e.target.value})}
            required
          />
        </div>

        <div className="form-group">
          <label>가입일</label>
          <input
            type="text"
            value={user?.created_at ? new Date(user.created_at).toLocaleDateString('ko-KR') : '알 수 없음'}
            readOnly
            className="readonly-input"
          />
        </div>

        <button type="submit" className="settings-button" disabled={loading}>
          {loading ? '업데이트 중...' : '프로필 업데이트'}
        </button>
      </form>
    </div>
  );

  const renderSecuritySection = () => (
    <div className="settings-section">
      <h3>🔒 보안 설정</h3>
      <form onSubmit={handlePasswordChange} className="settings-form">
        <div className="form-group">
          <label>현재 비밀번호</label>
          <input
            type="password"
            value={passwordData.currentPassword}
            onChange={(e) => setPasswordData({...passwordData, currentPassword: e.target.value})}
            required
          />
        </div>

        <div className="form-group">
          <label>새 비밀번호</label>
          <input
            type="password"
            value={passwordData.newPassword}
            onChange={(e) => setPasswordData({...passwordData, newPassword: e.target.value})}
            required
          />
        </div>

        <div className="form-group">
          <label>새 비밀번호 확인</label>
          <input
            type="password"
            value={passwordData.confirmPassword}
            onChange={(e) => setPasswordData({...passwordData, confirmPassword: e.target.value})}
            required
          />
        </div>

        <button type="submit" className="settings-button" disabled={loading}>
          {loading ? '변경 중...' : '비밀번호 변경'}
        </button>
      </form>
    </div>
  );

  const renderAccountSection = () => (
    <div className="settings-section">
      <h3>💰 계정 관리</h3>
      
      <div className="account-info">
        <div className="info-item">
          <span className="info-label">현재 잔고:</span>
          <span className="info-value balance">
            ${user?.balance?.toLocaleString() || '0'}
          </span>
        </div>
        
        <div className="info-item">
          <span className="info-label">계정 상태:</span>
          <span className="info-value status active">활성</span>
        </div>
      </div>

      <div className="account-actions">
        <button 
          className="settings-button reset-button"
          onClick={handleResetBalance}
        >
          💰 잔고 재설정
        </button>

        <button 
          className="settings-button danger-button"
          onClick={handleDeleteAccount}
        >
          🗑️ 계정 삭제
        </button>
      </div>
    </div>
  );

  const menuItems = [
    { id: 'profile', icon: '👤', label: '프로필' },
    { id: 'security', icon: '🔒', label: '보안' },
    { id: 'account', icon: '💰', label: '계정' }
  ];

  return (
    <div className="settings">
      <div className="settings-header">
        <h1>⚙️ 설정</h1>
        <p>계정 정보를 관리하고 보안 설정을 변경하세요</p>
      </div>

      {message.text && (
        <div className={`message ${message.type}`}>
          {message.text}
        </div>
      )}

      <div className="settings-content">
        <div className="settings-sidebar">
          <nav className="settings-nav">
            {menuItems.map(item => (
              <button
                key={item.id}
                className={`nav-item ${activeSection === item.id ? 'active' : ''}`}
                onClick={() => setActiveSection(item.id)}
              >
                <span className="nav-icon">{item.icon}</span>
                <span className="nav-label">{item.label}</span>
              </button>
            ))}
          </nav>
        </div>

        <div className="settings-main">
          {activeSection === 'profile' && renderProfileSection()}
          {activeSection === 'security' && renderSecuritySection()}
          {activeSection === 'account' && renderAccountSection()}
        </div>
      </div>
    </div>
  );
};

export default Settings;

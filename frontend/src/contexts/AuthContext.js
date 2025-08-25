import React, { createContext, useState, useContext, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  // 페이지 로드 시 저장된 인증 정보 복원
  useEffect(() => {
    const initAuth = async () => {
      const savedToken = localStorage.getItem('token');
      const savedUser = localStorage.getItem('user');

      if (savedToken && savedUser) {
        try {
          // 토큰 유효성 검증
          axios.defaults.headers.common['Authorization'] = `Bearer ${savedToken}`;
          const response = await axios.get('http://localhost:8000/api/auth/me');
          
          setToken(savedToken);
          setUser(JSON.parse(savedUser));
          console.log('✅ 인증 상태 복원 성공');
        } catch (error) {
          console.error('❌ 토큰 검증 실패:', error);
          // 유효하지 않은 토큰 제거
          localStorage.removeItem('token');
          localStorage.removeItem('user');
          delete axios.defaults.headers.common['Authorization'];
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const login = async (userData, accessToken) => {
    try {
      // 토큰을 axios 기본 헤더에 설정
      axios.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`;
      
      // 상태 업데이트
      setUser(userData);
      setToken(accessToken);
      
      // localStorage에 저장 (호환성을 위해 두 키 모두 저장)
      localStorage.setItem('token', accessToken);
      localStorage.setItem('access_token', accessToken);
      localStorage.setItem('user', JSON.stringify(userData));
      
      console.log('✅ 로그인 상태 설정 완료');
      return true;
    } catch (error) {
      console.error('❌ 로그인 상태 설정 실패:', error);
      return false;
    }
  };

  const logout = () => {
    // 상태 초기화
    setUser(null);
    setToken(null);
    
    // localStorage 정리
    localStorage.removeItem('token');
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    
    // axios 헤더 제거
    delete axios.defaults.headers.common['Authorization'];
    
    console.log('✅ 로그아웃 완료');
  };

  const updateUserBalance = (newBalance) => {
    if (user) {
      const updatedUser = { ...user, balance: newBalance };
      setUser(updatedUser);
      localStorage.setItem('user', JSON.stringify(updatedUser));
    }
  };

  const value = {
    user,
    token,
    loading,
    login,
    logout,
    updateUserBalance,
    isAuthenticated: !!user && !!token
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

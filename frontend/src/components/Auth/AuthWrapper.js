import React, { useState } from 'react';
import Login from './Login';
import Register from './Register';

const AuthWrapper = ({ onLogin }) => {
  const [isLogin, setIsLogin] = useState(true);

  const switchToRegister = () => setIsLogin(false);
  const switchToLogin = () => setIsLogin(true);

  return (
    <div>
      {isLogin ? (
        <Login 
          onLogin={onLogin} 
          switchToRegister={switchToRegister} 
        />
      ) : (
        <Register 
          switchToLogin={switchToLogin} 
        />
      )}
    </div>
  );
};

export default AuthWrapper;

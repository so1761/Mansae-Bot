import React, { createContext, useContext, useState, useEffect } from "react";
const baseUrl = process.env.REACT_APP_API_BASE_URL;

console.log(baseUrl)
// Context 생성
const AuthContext = createContext();

// useAuth 훅으로 로그인 상태와 유저 정보 사용
export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [user, setUser] = useState(null);
  
    useEffect(() => {
      fetch(`${baseUrl}/api/user/`, { credentials: "include" })
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (data) {
            setIsLoggedIn(true);
            setUser(data);
          }
        });
    }, []);
  
    const handleLogin = () => {
      window.location.href = `${baseUrl}/login/`;
    };
  
    const handleLogout = () => {
      fetch(`${baseUrl}/logout/`, { credentials: "include" })
        .then((res) => {
          if (res.ok) {
            setIsLoggedIn(false);
            setUser(null);
          }
        });
    };
  
    return (
      <AuthContext.Provider
        value={{ isLoggedIn, user, setIsLoggedIn, setUser, handleLogin, handleLogout }}
      >
        {children}
      </AuthContext.Provider>
    );
  };
import React, { createContext, useContext, useState, useEffect } from "react";
const baseUrl = process.env.REACT_APP_API_BASE_URL;

console.log(baseUrl)
// Context 생성
const AuthContext = createContext();

// useAuth 훅으로 로그인 상태와 유저 정보 사용
export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [user, setUser] = useState(null); // 유저 정보 (디스코드 프로필 이미지 등)

    useEffect(() => {
        // 로그인 상태와 유저 정보를 확인하는 API 요청
        fetch(`${baseUrl}/api/user/`, { credentials: "include" })
            .then((res) => {
                if (!res.ok) {
                    console.warn("Failed to fetch user info");
                    return null;
                }
                return res.json();
            })
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
        fetch(`${baseUrl}/logout/`, {
            credentials: "include"
        })
        .then((res) => {
            if (res.ok) {
                // 로그아웃 성공 시 클라이언트 상태 초기화
                setIsLoggedIn(false);
                setUser(null);
            } else {
                console.error("로그아웃 실패");
            }
        })
        .catch((error) => {
            console.error("로그아웃 중 오류 발생:", error);
        });
    };

    return (
        <AuthContext.Provider value={{ isLoggedIn, user, handleLogin, handleLogout }}>
            {children}
        </AuthContext.Provider>
    );
};
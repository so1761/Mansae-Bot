import React from "react";
import { Outlet, Link, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";  // useAuth 훅 import

function Layout() {
    const location = useLocation();
    const { isLoggedIn, user, handleLogin, handleLogout } = useAuth();  // Context에서 로그인 상태와 유저 정보 가져오기

    const isActive = (path) => location.pathname.startsWith(path);

    return (
        <div className="min-h-screen flex bg-gradient-to-br from-indigo-100 to-purple-200">
            {/* 사이드바 */}
            <aside className="w-64 min-h-screen bg-white shadow-lg p-6 space-y-4">
                <h2 className="text-xl font-bold text-indigo-600 mb-4">메뉴</h2>
                <ul className="space-y-2 text-lg font-medium">
                    <li>
                        <Link
                            to="/"
                            className={`block px-3 py-2 rounded ${
                                isActive("/") && location.pathname === "/" ? "bg-indigo-100 text-indigo-700" : "hover:bg-indigo-50"
                            }`}
                        >
                            홈
                        </Link>
                    </li>
                    <li>
                        <div className="text-indigo-600 font-semibold px-3 mt-4">확률</div>
                        <ul className="pl-4 space-y-1">
                            <li>
                                <Link
                                    to="/probability/randombox"
                                    className={`block px-3 py-2 rounded ${
                                        isActive("/probability/randombox") ? "bg-indigo-100 text-indigo-700" : "hover:bg-indigo-50"
                                    }`}
                                >
                                    랜덤박스
                                </Link>
                            </li>
                            <li>
                                <Link
                                    to="/probability/enhancement"
                                    className={`block px-3 py-2 rounded ${
                                        isActive("/probability/enhancement") ? "bg-indigo-100 text-indigo-700" : "hover:bg-indigo-50"
                                    }`}
                                >
                                    강화 확률
                                </Link>
                            </li>
                            <li>
                                <Link
                                    to="/probability/inheritance"
                                    className={`block px-3 py-2 rounded ${
                                        isActive("/probability/inheritance") ? "bg-indigo-100 text-indigo-700" : "hover:bg-indigo-50"
                                    }`}
                                >
                                    계승 확률
                                </Link>
                            </li>
                        </ul>
                    </li>
                        <li>
                            <div className="text-indigo-600 font-semibold px-3 mt-4">무기</div>
                            <ul className="pl-4 space-y-1">
                                <li>
                                <Link
                                    to="/weapon"
                                    className={`block px-3 py-2 rounded ${
                                    isActive("/weapon") && location.pathname === "/weapon" ? "bg-indigo-100 text-indigo-700" : "hover:bg-indigo-50"
                                    }`}
                                >
                                    무기 정보
                                </Link>
                                </li>
                                <li>
                                <Link
                                    to="/weapon/enhancement_values"
                                    className={`block px-3 py-2 rounded ${
                                        isActive("/weapon/enhancement_values") ? "bg-indigo-100 text-indigo-700" : "hover:bg-indigo-50"
                                    }`}
                                    >
                                    강화 수치 보기
                                    </Link>
                                </li>
                            </ul>
                        </li>
                </ul>
            </aside>

            {/* 메인 영역 */}
            <div className="flex-1 flex flex-col">
                {/* 상단 바 */}
                <header className="flex justify-end items-center p-4 bg-transparent gap-4">
                    {isLoggedIn && user ? (
                        <>
                            <img
                                src={
                                    user.avatar_url ??
                                    (user.avatar
                                        ? `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}${user.avatar.startsWith("a_") ? ".gif" : ".png"}`
                                        : `https://cdn.discordapp.com/embed/avatars/${user.id % 5}.png`)
                                }
                                alt="프로필"
                                className="w-10 h-10 rounded-full shadow"
                            />
                            <button
                                onClick={handleLogout}
                                className="text-sm px-4 py-2 rounded-md bg-red-500 text-white hover:bg-red-600 transition"
                            >
                                로그아웃
                            </button>
                        </>
                    ) : (
                        <button
                            onClick={handleLogin}
                            className="text-sm px-4 py-2 rounded-md bg-indigo-600 text-white hover:bg-indigo-700 transition"
                        >
                            로그인
                        </button>
                    )}
                </header>

                {/* 페이지 콘텐츠 */}
                <main className="flex-1 flex justify-center items-start p-10">
                    <Outlet />
                </main>
            </div>
        </div>
    );
}

export default Layout;
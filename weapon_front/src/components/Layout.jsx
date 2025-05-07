import React, { useState } from "react";
import { Outlet, Link, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function Layout() {
    const location = useLocation();
    const { isLoggedIn, user, handleLogin, handleLogout } = useAuth();
    const [isSidebarOpen, setIsSidebarOpen] = useState(false);

    const isActive = (path) => location.pathname === path;

    return (
        <div className="min-h-screen flex bg-gradient-to-br from-indigo-100 to-purple-200">
            {/* 모바일 오버레이 */}
            {isSidebarOpen && (
                <div
                    className="fixed inset-0 bg-black bg-opacity-30 z-40 xl:hidden"
                    onClick={() => setIsSidebarOpen(false)}
                />
            )}

            {/* 사이드바 */}
            <aside
                className={`
                    bg-white shadow-xl p-6 space-y-4 w-64
                    fixed z-50 top-0 left-0 transform transition-transform duration-300
                    h-screen overflow-y-auto
                    ${isSidebarOpen ? "translate-x-0" : "-translate-x-full"}
                    xl:translate-x-0 xl:block xl:z-auto
                `}
            >
                <h2 className="text-xl font-bold text-indigo-600 mb-4">메뉴</h2>
                <ul className="space-y-2 text-lg font-medium">
                    <li>
                        <Link
                            to="/"
                            className={`block px-3 py-2 rounded ${
                                isActive("/") && location.pathname === "/" ? "bg-indigo-100 text-indigo-700" : "hover:bg-indigo-50"
                            }`}
                            onClick={() => setIsSidebarOpen(false)}
                        >
                            홈
                        </Link>
                    </li>

                    {/* 확률 섹션 */}
                    <li>
                        <div className="text-indigo-600 font-semibold px-3 mt-4">확률</div>
                        <ul className="pl-4 space-y-1">
                            <li>
                                <Link
                                    to="/probability/randombox"
                                    className={`block px-3 py-2 rounded ${
                                        isActive("/probability/randombox") ? "bg-indigo-100 text-indigo-700" : "hover:bg-indigo-50"
                                    }`}
                                    onClick={() => setIsSidebarOpen(false)}
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
                                    onClick={() => setIsSidebarOpen(false)}
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
                                    onClick={() => setIsSidebarOpen(false)}
                                >
                                    계승 확률
                                </Link>
                            </li>
                        </ul>
                    </li>

                    {/* 무기 섹션 */}
                    <li>
                        <div className="text-indigo-600 font-semibold px-3 mt-4">무기</div>
                        <ul className="pl-4 space-y-1">
                            <li>
                                <Link
                                    to="/weapon"
                                    className={`block px-3 py-2 rounded ${
                                        isActive("/weapon") && location.pathname === "/weapon" ? "bg-indigo-100 text-indigo-700" : "hover:bg-indigo-50"
                                    }`}
                                    onClick={() => setIsSidebarOpen(false)}
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
                                    onClick={() => setIsSidebarOpen(false)}
                                >
                                    강화 수치 보기
                                </Link>
                            </li>
                            <li>
                                <Link
                                    to="/weapon/enhance"
                                    className={`block px-3 py-2 rounded ${
                                        isActive("/weapon/enhance") ? "bg-indigo-100 text-indigo-700" : "hover:bg-indigo-50"
                                    }`}
                                    onClick={() => setIsSidebarOpen(false)}
                                >
                                    강화하기
                                </Link>
                            </li>
                            <li>
                                <Link
                                    to="/weapon/skills"
                                    className={`block px-3 py-2 rounded ${
                                    isActive("/weapon/skills") ? "bg-indigo-100 text-indigo-700" : "hover:bg-indigo-50"
                                    }`}
                                    onClick={() => setIsSidebarOpen(false)}
                                >
                                    스킬 정보
                                </Link>
                            </li>
                        </ul>
                    </li>
                    <li>
                        <Link
                            to="https://www.notion.so/1dff1cca1de280c69c1fc82bd171d5bb"
                            target="_blank"   // 새 탭에서 열기
                            rel="noopener noreferrer"   // 보안 강화
                            className={`block px-3 py-2 rounded hover:bg-indigo-50`}
                        >
                            패치 노트
                        </Link>
                    </li>
                </ul>
            </aside>

            {/* 우측 메인 영역 */}
            <div className="flex-1 flex flex-col">
                {/* 상단 바 */}
                <header className="flex justify-between items-center p-4 bg-transparent sticky top-0 z-30">
                    {/* 햄버거 버튼 */}
                    <button
                        className="xl:hidden text-2xl text-indigo-700"
                        onClick={() => setIsSidebarOpen(!isSidebarOpen)}
                    >
                        ☰
                    </button>

                    {/* 로그인 / 로그아웃 */}
                    <div className="flex items-center gap-4 ml-auto">
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
                    </div>
                </header>

                {/* 페이지 콘텐츠 */}
                <main className="flex-1 flex justify-center items-start p-4 sm:p-10">
                    <Outlet />
                </main>
            </div>
        </div>
    );
}

export default Layout;
import React from "react";
import { Routes, Route } from "react-router-dom";
import OAuthRedirect from "./pages/OAuthRedirect";
import Layout from "./components/Layout"; // 메뉴 + Outlet 포함
import { AuthProvider } from "./context/AuthContext";  // AuthContext import
import Home from "./pages/Home";
import RandomBox from "./pages/RandomBox";
import Enhancement from "./pages/Enhancement";
import EnhancementInfoPage from "./pages/EnhancementInfo";
import EnhanceWeaponPage  from "./pages/EnhanceWeaponPage";
import Inheritance from "./pages/Inheritance";
import WeaponInfo from "./pages/WeaponInfo";
import TooltipList from "./pages/TooltipList"; // 경로는 실제 위치에 맞게 수정

function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* 로그인 외 전체 페이지는 Layout을 공통 부모로 */}
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="probability/randombox" element={<RandomBox />} />
          <Route path="probability/enhancement" element={<Enhancement />} />
          <Route path="probability/inheritance" element={<Inheritance />} />
          <Route path="weapon" element={<WeaponInfo />} />
          <Route path="weapon/enhancement_values" element={<EnhancementInfoPage />} />
          <Route path="weapon/enhance" element={<EnhanceWeaponPage />} />
          <Route path="weapon/skills" element={<TooltipList />} />
        </Route>
        {/* OAuth 리디렉션 전용 페이지는 Layout 밖에 둠 */}
        <Route path="/oauth/redirect" element={<OAuthRedirect />} />
      </Routes>
    </AuthProvider>
  );
}

export default App;
import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

export default function OAuthRedirect() {
  const navigate = useNavigate();
  const hasFetchedRef = useRef(false); // ✅ 중복 요청 방지용 ref

  useEffect(() => {
    if (hasFetchedRef.current) return; // 이미 요청했으면 무시
    hasFetchedRef.current = true;

    const code = new URLSearchParams(window.location.search).get("code");

    if (code) {
      fetch("http://localhost:8000/api/discord/callback/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include", // ✅ 세션 쿠키 포함
        body: JSON.stringify({ code }),
      })
        .then((res) => res.json())
        .then((data) => {
          console.log("✅ 로그인 성공:", data);
          navigate("/"); // 홈으로 이동
        })
        .catch((err) => {
          console.error("❌ 로그인 실패:", err);
        });
    }
  }, [navigate]);

  return <div>로그인 중입니다... 잠시만 기다려주세요.</div>;
}
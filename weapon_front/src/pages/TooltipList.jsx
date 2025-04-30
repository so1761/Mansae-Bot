import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { tooltipTemplates } from "../lib/tooltipTemplates"; // named import 방식으로 수정
import { useAuth } from "../context/AuthContext"; // AuthContext에서 로그인 상태와 사용자 정보를 가져옵니다.
import { Tooltip } from "react-tooltip"; // Tooltip으로 변경
import 'react-tooltip/dist/react-tooltip.css';

const baseUrl = process.env.REACT_APP_API_BASE_URL;

export default function AllTooltips() {
  const [skills, setSkills] = useState([]);
  const [level, setLevel] = useState(1); // ✅ 레벨 상태 추가
  const { user } = useAuth();

  // 툴팁을 위한 API 호출
  useEffect(() => {
    const fetchSkillsAndParams = async () => {
      if (!user?.discord_username) return;

      const discordUsername = user.discord_username;

      try {
        const res = await fetch(`${baseUrl}/api/get_skills_with_tooltips`);
        const skillList = await res.json();

        const sortedSkillList = skillList.sort((a, b) => {
          const aNum = parseInt(a.tooltip_key.replace(/\D/g, ""), 10); // 숫자만 추출
          const bNum = parseInt(b.tooltip_key.replace(/\D/g, ""), 10);
          return aNum - bNum;
        });

        const enriched = await Promise.all(
          sortedSkillList.map(async (skill) => {
            const res = await fetch(
              `${baseUrl}/api/get_skill_params/${discordUsername}/?key=${skill.skill_name}`
            );
            const params = await res.json();
            return { ...skill, params };
          })
        );

        setSkills(enriched);
      } catch (err) {
        console.error("스킬/파라미터 로딩 실패:", err);
      }
    };

    fetchSkillsAndParams();
  }, [user]);

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-8">
      <h1 className="text-3xl font-bold text-center text-indigo-700">🎓 모든 스킬 툴팁 보기</h1>

      {/* ✅ 레벨 선택 UI */}
      <div className="flex justify-center items-center gap-4 mb-6">
        <label htmlFor="level" className="font-medium text-indigo-600">레벨: {level}</label>
        <input
          type="range"
          id="level"
          min={1}
          max={20}
          value={level}
          onChange={(e) => setLevel(parseInt(e.target.value))}
          className="w-64 accent-indigo-500"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {skills.map((skill, idx) => {
        const Component = tooltipTemplates[skill.tooltip_key];
        if (!Component) return null;

        const cooldown = skill.params;
        const initialCooldown = cooldown["현재 쿨타임"];
        const totalCooldown = cooldown["전체 쿨타임"];
        
        console.log(cooldown)
        return (
          <motion.div
            key={skill.tooltip_key}
            className="bg-white p-6 rounded-2xl shadow-xl border border-gray-200 space-y-4"
            initial={{ opacity: 0, y: 0 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.1, duration: 0.4 }}
          >
            <h2 className="text-xl font-semibold text-indigo-600">{skill.skill_name}</h2>

            {/* ✅ 쿨타임 정보 출력 */}
            {(initialCooldown !== undefined || totalCooldown !== undefined) && (
              <div className="text-gray-600 text-sm space-y-1">
                {initialCooldown !== undefined && (
                  <p>🕒 초기 쿨타임: <strong>{initialCooldown}</strong>턴</p>
                )}
                {totalCooldown !== undefined && (
                  <p>♻️ 전체 쿨타임: <strong>{totalCooldown}</strong>턴</p>
                )}
              </div>
            )}

            <div className="prose max-w-none text-sm">
              <Component {...skill.params} 레벨={level} />
            </div>
          </motion.div>
        );
      })}
        {/* 툴팁을 전역적으로 추가 */}
      <Tooltip id="tooltip-hit" place="right" effect="solid"/>
      </div>

      
    </div>
    
  );
}
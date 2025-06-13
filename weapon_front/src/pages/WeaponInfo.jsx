import React, { useState, useEffect, useCallback } from "react";
import { Tooltip } from 'react-tooltip';
import 'react-tooltip/dist/react-tooltip.css';
import { tooltipTemplates } from "../lib/tooltipTemplates"; // 경로는 상황에 맞게 조정
import { skillDescriptions } from "../lib/descriptions";
import { useAuth } from "../context/AuthContext"; // AuthContext에서 로그인 상태와 사용자 정보를 가져옵니다.
import {
  Sword,
  Shield,
  WandSparkles,
  Zap,
  Target,
  Flame,
  Heart,
  Sparkles,
  Scale,
  DiamondPlus,
  Star,
  CirclePlus,
  RotateCcw,
  Search // 검색 아이콘 추가
} from "lucide-react"; // 필요한 아이콘만 쓰기

const baseUrl = process.env.REACT_APP_API_BASE_URL;

// enhancementIcons와 enhancementLabels 객체는 기존과 동일하게 유지합니다.
const enhancementIcons = {
    attack_enhance: <Sword size={16} />,
    durability_enhance: <Heart size={16} />,
    accuracy_enhance: <Target size={16} />,
    speed_enhance: <Zap size={16} />,
    defense_enhance: <Shield size={16} />,
    skill_enhance: <WandSparkles size={16} />,
    critical_damage_enhance: <Flame size={16} />,
    critical_hit_chance_enhance: <Sparkles size={16} />,
    balance_enhance: <Scale size={16} />,
};
  
const enhancementLabels = {
    attack_enhance: "공격 강화",
    durability_enhance: "내구도 강화",
    accuracy_enhance: "명중 강화",
    speed_enhance: "속도 강화",
    defense_enhance: "방어 강화",
    skill_enhance: "스킬 강화",
    critical_damage_enhance: "치명타 대미지 강화",
    critical_hit_chance_enhance: "치명타 확률 강화",
    balance_enhance: "밸런스 강화",
};

function WeaponInfo() {
  const { isLoggedIn, user } = useAuth();
  const [weaponData, setWeaponData] = useState(null);
  const [activeTab, setActiveTab] = useState("weapon");
  const [isLoading, setIsLoading] = useState(false); // 로딩 상태 통합
  const [error, setError] = useState(null); // 에러 메시지 상태
  const [searchTerm, setSearchTerm] = useState(""); // 검색어 상태
  const [displayedUsername, setDisplayedUsername] = useState(null); // 현재 표시 중인 유저 이름

  // 무기 데이터를 가져오는 함수 (재사용을 위해 useCallback으로 감싸기)
  const fetchWeaponData = useCallback(async (username, isRefresh = false) => {
    if (!username) return;
    setIsLoading(true);
    setError(null);

    const cachedData = sessionStorage.getItem(`weaponData_${username}`);
    if (cachedData && !isRefresh) {
      setWeaponData(JSON.parse(cachedData));
      setDisplayedUsername(username);
      setIsLoading(false);
      return;
    }

    try {
      const res = await fetch(`${baseUrl}/api/weapon/${username}/`, {
        credentials: "include",
      });
      if (!res.ok) {
        throw new Error("유저를 찾을 수 없거나 데이터를 가져올 수 없습니다.");
      }
      const data = await res.json();
      setWeaponData(data);
      setDisplayedUsername(username);
      sessionStorage.setItem(`weaponData_${username}`, JSON.stringify(data));
    } catch (err) {
      console.error("Error fetching weapon data:", err);
      setError(err.message);
      setWeaponData(null); // 에러 발생 시 데이터 초기화
    } finally {
      setIsLoading(false);
    }
  }, []);

  // 로그인 상태가 변경되면 기본적으로 자신의 정보를 불러옴
  useEffect(() => {
    if (isLoggedIn && user) {
        // 다른 유저를 검색한 상태가 아닐 때만 자신의 정보를 불러옴
        if (!displayedUsername || displayedUsername === user.discord_username) {
            fetchWeaponData(user.discord_username);
        }
    } else {
        // 로그아웃 시 데이터 초기화 (검색된 정보는 유지할 수 있음)
    }
  }, [isLoggedIn, user, fetchWeaponData]);

  const handleRefresh = () => {
    if (displayedUsername) {
      fetchWeaponData(displayedUsername, true); // 현재 표시 중인 유저 정보 새로고침
    }
  };
  
  const handleSearch = (e) => {
    e.preventDefault();
    if (searchTerm.trim()) {
        setActiveTab("weapon"); // 검색 시 항상 기본 탭으로 이동
        fetchWeaponData(searchTerm.trim());
    }
  }

  // Stat, Damage Reduction, renderStat, WeaponInfo sub-component 등은 기존과 동일합니다.
  const statInfo = [
    { key: "attack_power", label: "공격력" },
    { key: "skill_enhance", label: "스킬 증폭" },
    { key: "durability", label: "내구도" },
    { key: "accuracy", label: "명중" },
    { key: "defense", label: "방어력" },
    { key: "speed", label: "스피드" },
    { key: "critical_damage", label: "치명타 대미지", isPercent: true },
    { key: "critical_hit_chance", label: "치명타 확률", isPercent: true },
  ];

  function calculateDamageReduction(defense) {
    return Math.min(0.99, 1 - (100 / (100 + defense)));
  }

  const renderStat = ({ key, label, isPercent }, w) => {
    const stat = w[key] || {};
    const base = stat.base ?? 0;
    const inheritance = stat.inheritance ?? 0;
    const enhancement = stat.enhancement ?? 0;
  
    const total = base + inheritance + enhancement;
    const displayValue = isPercent ? `${Math.round(total * 100)}%` : total;
    const inheritText =
      inheritance > 0
        ? ` (+${isPercent ? Math.round(inheritance * 100) + "%" : inheritance})`
        : "";
    const enhanceText =
      enhancement > 0
        ? ` (+${isPercent ? Math.round(enhancement * 100) + "%" : enhancement})`
        : "";

    if (key === "defense") {
      const tooltipId = `tooltip-${key}`;
      const reduction = Math.round(calculateDamageReduction(total) * 100);
      return (
        <p
          key={key}
          className="text-gray-700"
          data-tooltip-id={tooltipId}
          data-tooltip-content={`대미지 감소율: ${reduction}%`}
          data-tooltip-place="left"
        >
          {label}: {displayValue}
          {inheritText && <span className="text-orange-500">{inheritText}</span>}
          {enhanceText && <span className="text-blue-500">{enhanceText}</span>}
          <Tooltip id={tooltipId} />
        </p>
      );
    }

    if (key === "speed") {
      const tooltipId = `tooltip-${key}`;
      const accelerationChance = Math.floor(total / 5);
      const overdriveChance = Math.max(0, Math.floor((total - 200) / 5));
      const evasionScore = Math.floor(total / 5);
    
      return (
        <p
          key={key}
          className="text-gray-700"
          data-tooltip-id={tooltipId}
          data-tooltip-html={`
            가속 확률: ${accelerationChance}%<br/>
            초가속 확률: ${overdriveChance}%<br/>
            회피 수치: ${evasionScore}
          `}
          data-tooltip-place="left"
        >
          {label}: {displayValue}
          {inheritText && <span className="text-orange-500">{inheritText}</span>}
          {enhanceText && <span className="text-blue-500">{enhanceText}</span>}
          <Tooltip id={tooltipId} />
        </p>
      );
    }
    
    return (
      <p key={key} className="text-gray-700">
        {label}: {displayValue}
        {inheritText && <span className="text-orange-500">{inheritText}</span>}
        {enhanceText && <span className="text-blue-500">{enhanceText}</span>}
      </p>
    );
  };
  
  function WeaponStatInfo({ w }) {
    return (
      <div className="space-y-4">
        <h2 className="text-2xl font-semibold text-indigo-600">무기 이름: {w.name}</h2>
        <p className="text-gray-700">무기 유형: {w.weapon_type}</p>
        {statInfo.map((stat) => renderStat(stat, w))}
      </div>
    );
  }

  const renderTabContent = () => {
    // weaponData가 없을 경우 렌더링하지 않음
    if (!weaponData) return null;

    switch (activeTab) {
      case "weapon":
        return <WeaponStatInfo w={weaponData.weapon} />;
      // ... 나머지 case "enhancements", "inheritance", "skills"는 기존 코드와 동일 ...
      case "enhancements":
        const enhancementEntries = Object.entries(weaponData.enhancements || {}).filter(
          ([key, value]) => key !== "enhancement_level" && value > 0
        );
          
        const enhancements = enhancementEntries.map(([key, value]) => (
          <div
            key={key}
            className="flex items-center justify-between px-3 py-2 rounded-md bg-white shadow-sm border"
          >
            <div className="flex items-center gap-2 text-gray-700">
              {enhancementIcons[key]}
              <span>{enhancementLabels[key] || key}</span>
            </div>
            <span className="font-semibold text-indigo-600">+{value}</span>
          </div>
        ));

        const totalEnhancementLevel = enhancementEntries.reduce((sum, [_, value]) => sum + value, 0);

        return (
          <div className="space-y-4">
            <h3 className="text-xl font-semibold text-indigo-500">강화 정보</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {enhancements}
            </div>
            <div className="text-sm text-right text-gray-500">
              총 강화 레벨: +{totalEnhancementLevel}
            </div>
          </div>
        );
      case "inheritance":
        const inheritanceIcons = {
          "기본 스탯 증가": <DiamondPlus size={16} />,
          "기본 스킬 레벨 증가": <Star size={16} />,
          "공격 강화": <Sword size={16} />,
          "내구도 강화": <Heart size={16} />,
          "명중 강화": <Target size={16} />,
          "속도 강화": <Zap size={16} />,
          "방어 강화": <Shield size={16} />,
          "스킬 강화": <WandSparkles size={16} />,
          "치명타 대미지 강화": <Flame size={16} />,
          "치명타 확률 강화": <Sparkles size={16} />,
          "밸런스 강화": <Scale size={16} />,
        };
        const additionalEnhancements = Object.entries(
          weaponData.inheritance.additional_enhance || {}
        ).map(([key, value]) => (
          <div
            key={key}
            className="flex items-center justify-between px-3 py-2 rounded-md bg-white shadow-sm border"
          >
            <div className="flex items-center gap-2 text-gray-700">
              {inheritanceIcons[key] || <CirclePlus size={16} />}
              <span>{key}</span>
            </div>
            <span className="font-semibold text-indigo-600">+{value}</span>
          </div>
        ));

        return (
          <div className="space-y-4">
            <h3 className="text-xl font-semibold text-indigo-500">계승 정보</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {/* 기본 스탯 증가 */}
              <div className="flex items-center justify-between px-3 py-2 rounded-md bg-white shadow-sm border">
                <div className="flex items-center gap-2 text-gray-700">
                  {inheritanceIcons["기본 스탯 증가"]} {/* 기본 스탯 증가 아이콘 */}
                  <span>기본 스탯 증가</span>
                </div>
                <span
                  className="font-semibold text-indigo-600"
                  data-tooltip-id="tooltip-base-stat"
                  data-tooltip-content={`기본 스탯이 +${weaponData.inheritance.base_stat_increase * 30}% 증가합니다.`} // 툴팁 내용 추가
                  data-tooltip-place="top"
                >
                  +{weaponData.inheritance.base_stat_increase}
                </span>
                <Tooltip id="tooltip-base-stat" />
              </div>
      
              {/* 기본 스킬 레벨 증가 */}
              <div className="flex items-center justify-between px-3 py-2 rounded-md bg-white shadow-sm border">
                <div className="flex items-center gap-2 text-gray-700">
                  {inheritanceIcons["기본 스킬 레벨 증가"]} {/* 기본 스킬 레벨 증가 아이콘 */}
                  <span>기본 스킬 레벨 증가</span>
                </div>
                <span
                  className="font-semibold text-indigo-600"
                  data-tooltip-id="tooltip-base-skill"
                  data-tooltip-content={`기본 스킬 레벨이 +${weaponData.inheritance.base_skill_level_increase} 증가합니다.`} // 툴팁 내용 추가
                  data-tooltip-place="top"
                >
                  +{weaponData.inheritance.base_skill_level_increase}
                </span>
                <Tooltip id="tooltip-base-skill" />
              </div>
            </div>
      
            {/* 추가 강화 */}
            {additionalEnhancements.length > 0 && (
              <div>
                <h4 className="font-semibold text-indigo-600 mt-2">추가 강화</h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-2">
                  {additionalEnhancements}
                </div>
              </div>
            )}
      
            <div className="text-sm text-right text-gray-500">
              계승 레벨: {weaponData.inheritance.inheritance_level}
            </div>
          </div>
        );
      case "skills":
        return (
          <div className="space-y-4">
            <h3 className="text-xl font-semibold text-indigo-500">스킬</h3>
            {weaponData.skills.length === 0 ? (
              <p className="text-gray-700">스킬이 없습니다.</p>
            ) : (
              weaponData.skills.map((skill, index) => {

                const renderedNote =
                skill.skill_notes_key &&
                tooltipTemplates[skill.skill_notes_key] &&
                skill.skill_notes_params
                  ? tooltipTemplates[skill.skill_notes_key](skill.skill_notes_params)
                  : "";                
      
                return (
                  <div key={index} className="mb-4 p-4 border border-gray-200 rounded-xl shadow-sm bg-white">
                    <h4 className="text-lg font-semibold text-indigo-400">
                      {skill.skill_name} Lv.{skill.level}
                    </h4>
                    <div className="text-sm text-gray-600 mt-2">
                      <p className="text-gray-700">쿨타임: {skill.cooldown}턴</p>
                      <p className="text-gray-700">초기 쿨타임: {skill.current_cooldown}턴</p>
                    </div>
                    <div className="text-sm text-gray-600 mt-2">
                      <span className="font-semibold text-indigo-400 mb-1">📘 설명:</span>
                      <div
                        className="mt-1 text-gray-800"
                        dangerouslySetInnerHTML={{
                          __html: skillDescriptions[skill.skill_name] || "설명이 없습니다.",
                        }}
                      />
                    </div>
                    {renderedNote && (
                      <div className="text-sm text-gray-600 mt-2">
                        <h5 className="font-semibold text-indigo-400 mb-1">📌 상세 효과</h5>
                        {renderedNote}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        );
      default:
        return null;
    }
  };

  // UI 렌더링 부분
  return (
    <div className="p-6 max-w-4xl mx-auto bg-white shadow-lg rounded-md">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-3xl font-extrabold text-indigo-700">⚔️ 무기 정보</h1>
        <button
          onClick={handleRefresh}
          disabled={isLoading || !displayedUsername}
          className="ml-2 p-1 rounded-full hover:bg-indigo-100 text-indigo-600 transition disabled:text-gray-400 disabled:cursor-not-allowed"
          title="새로고침"
        >
          {isLoading ? (
            <svg
              className="animate-spin h-5 w-5 text-indigo-600"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              ></circle>
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v4l5-5-5-5v4a10 10 0 100 20v-2a8 8 0 01-8-8z"
              ></path>
            </svg>
          ) : (
            <RotateCcw className="h-5 w-5" />
          )}
        </button>
      </div>

      {/* 검색창 UI */}
      <form onSubmit={handleSearch} className="mb-6 flex gap-2">
        <input 
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Discord 유저네임을 검색하세요..."
            className="flex-grow px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
        />
        <button
            type="submit"
            disabled={isLoading}
            className="flex items-center justify-center px-4 py-2 bg-indigo-600 text-white font-semibold rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-indigo-300"
        >
            <Search size={18} />
            <span className="ml-2">검색</span>
        </button>
      </form>

      {/* 정보 표시 영역 */}
      <div>
        {isLoading && (
          <div className="text-center py-10">
            <h2 className="text-xl font-bold text-indigo-600">정보를 불러오는 중...</h2>
          </div>
        )}

        {!isLoading && error && (
            <div className="text-center py-10">
              <h2 className="text-xl font-bold text-red-500">{error}</h2>
            </div>
        )}
        
        {!isLoading && !error && weaponData && (
          <>
            <div className="mb-6 flex space-x-4 border-b-2 pb-2">
              <button
                className={`flex-1 px-2 py-2 rounded-md text-center text-lg font-medium sm:px-4 sm:py-2 sm:text-base sm:leading-5 break-keep ${activeTab === "weapon" ? "text-white bg-indigo-600" : "text-indigo-600 hover:bg-indigo-100"}`}
                onClick={() => setActiveTab("weapon")}
              >
                <span className="inline sm:hidden">무기</span>
                <span className="hidden sm:inline">무기 정보</span>
              </button>
              <button
                className={`flex-1 px-2 py-2 rounded-md text-center text-lg font-medium sm:px-4 sm:py-2 sm:text-base sm:leading-5 break-keep ${activeTab === "enhancements" ? "text-white bg-indigo-600" : "text-indigo-600 hover:bg-indigo-100"}`}
                onClick={() => setActiveTab("enhancements")}
              >
                <span className="inline sm:hidden">강화</span>
                <span className="hidden sm:inline">강화 정보</span>
              </button>
              <button
                className={`flex-1 px-2 py-2 rounded-md text-center text-lg font-medium sm:px-4 sm:py-2 sm:text-base sm:leading-5 break-keep ${activeTab === "inheritance" ? "text-white bg-indigo-600" : "text-indigo-600 hover:bg-indigo-100"}`}
                onClick={() => setActiveTab("inheritance")}
              >
                <span className="inline sm:hidden">계승</span>
                <span className="hidden sm:inline">계승 정보</span>
              </button>
              <button
                className={`flex-1 px-2 py-2 rounded-md text-center text-lg font-medium sm:px-4 sm:py-2 sm:text-base sm:leading-5 break-keep ${activeTab === "skills" ? "text-white bg-indigo-600" : "text-indigo-600 hover:bg-indigo-100"}`}
                onClick={() => setActiveTab("skills")}
              >
                <span className="inline sm:hidden">스킬</span>
                <span className="hidden sm:inline">스킬 정보</span>
              </button>
            </div>
            <div className="space-y-6">
              {renderTabContent()}
            </div>
          </>
        )}

        {!isLoading && !error && !weaponData && (
             <div className="text-center py-10">
                <h2 className="text-xl font-bold text-gray-500">
                    {isLoggedIn ? "내 무기 정보를 불러오는 중이거나, 다른 유저를 검색해보세요." : "로그인하여 내 정보를 보거나, 다른 유저를 검색하세요."}
                </h2>
             </div>
        )}
      </div>
      <Tooltip id="tooltip-hit" place="top" effect="solid"/>
    </div>
  );
}

export default WeaponInfo;
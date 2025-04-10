import React, { useState, useEffect } from "react";
import { Tooltip } from 'react-tooltip';
import 'react-tooltip/dist/react-tooltip.css';
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
  CirclePlus
} from "lucide-react"; // 필요한 아이콘만 쓰기

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
  const [weaponData, setWeaponData] = useState(null); // 무기 정보 상태
  const [activeTab, setActiveTab] = useState("weapon"); // 활성 탭 상태 (무기 정보, 스탯, 강화 등)

  useEffect(() => {
    if (isLoggedIn && user) {
      const discordUsername = user.discord_username;
      
      fetch(`http://localhost:8000/api/weapon/${discordUsername}/`, {
        credentials: "include", 
      })
        .then((res) => res.json())
        .then((data) => {
          setWeaponData(data); // 무기 정보 상태에 저장
        })
        .catch((error) => {
          console.error("Error fetching weapon data:", error);
        });
    }
  }, [isLoggedIn, user]);

  if (!isLoggedIn) {
    return (
      <div className="text-center">
        <h2 className="text-xl font-bold text-indigo-600">로그인 후 무기 정보를 확인할 수 있습니다.</h2>
      </div>
    );
  }

  if (!weaponData) {
    return (
      <div className="text-center">
        <h2 className="text-xl font-bold text-indigo-600">무기 정보 로딩 중...</h2>
      </div>
    );
  }

  // WeaponInfo 컴포넌트 정의 (밖에서 따로 분리)
  const statInfo = [
    { key: "attack_power", label: "공격력" },
    { key: "skill_enhance", label: "스킬 증폭" },
    { key: "durability", label: "내구도" },
    { key: "accuracy", label: "명중" },
    { key: "defense", label: "방어력" },
    { key: "speed", label: "스피드" },
    { key: "critical_damage", label: "치명타 대미지", isPercent: true },
    { key: "critical_hit_chance", label: "치명타 확률", isPercent: true },
    { key: "range", label: "사거리" },
  ];

  const calculateAccuracyRate = (accuracy) => {
    return Math.min(0.99, 1 - 50 / (50 + accuracy));
  };

  function calculateDamageReduction(defense) {
    return Math.min(0.99, 1 - (100 / (100 + defense)));
  }
  
  function calculateMoveChance(speed) {
    return Math.min(0.99, 1 - Math.exp(-speed / 70));
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

    if (key === "accuracy") {
      const tooltipId = `tooltip-${key}`;
      const accuracyRate = Math.round(calculateAccuracyRate(total) * 100);

      return (
        <p
          key={key}
          className="text-gray-700"
          data-tooltip-id={tooltipId}
          data-tooltip-content={`명중률: ${accuracyRate}%`}
          data-tooltip-place="left"
        >
          {label}: {displayValue}
          {inheritText && <span className="text-orange-500">{inheritText}</span>}
          {enhanceText && <span className="text-blue-500">{enhanceText}</span>}
          <Tooltip id={tooltipId} />
        </p>
      );
    }

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
      const moveChance = Math.round(calculateMoveChance(total) * 100);
    
      return (
        <p
          key={key}
          className="text-gray-700"
          data-tooltip-id={tooltipId}
          data-tooltip-content={`이동 확률: ${moveChance}%`}
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

  function WeaponInfo({ w }) {
    return (
      <div className="space-y-4">
        <h2 className="text-2xl font-semibold text-indigo-600">무기 이름: {w.name}</h2>
        <p className="text-gray-700">무기 유형: {w.weapon_type}</p>
        {statInfo.map((stat) => renderStat(stat, w))}
      </div>
    );
  }

  const renderTabContent = () => {
    switch (activeTab) {
      case "weapon":
        return <WeaponInfo w={weaponData.weapon} />;
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
                      data-tooltip-content={`기본 스탯이 +${weaponData.inheritance.base_stat_increase * 20}% 증가합니다.`} // 툴팁 내용 추가
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
                      data-tooltip-place="left"
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
              weaponData.skills.map((skill, index) => (
                <div key={index} className="mb-4">
                  <h4 className="text-lg font-semibold text-indigo-400">{skill.skill_name}</h4>
                  <p className="text-gray-700">레벨: {skill.level}</p>
                  <p className="text-gray-700">쿨타임: {skill.cooldown}턴</p>
                  <p className="text-gray-700">초기 쿨타임: {skill.current_cooldown}턴</p>
                </div>
              ))
            )}
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto bg-white shadow-lg rounded-md">
      <h1 className="text-3xl font-extrabold text-indigo-700 mb-6">⚔️ 나의 무기 정보</h1>

      {/* 탭 UI */}
      <div className="mb-6 flex space-x-4 border-b-2 pb-2">
        <button
          className={`px-6 py-2 rounded-md text-lg font-medium ${activeTab === "weapon" ? "text-white bg-indigo-600" : "text-indigo-600 hover:bg-indigo-100"}`}
          onClick={() => setActiveTab("weapon")}
        >
          무기 정보
        </button>
        <button
          className={`px-6 py-2 rounded-md text-lg font-medium ${activeTab === "enhancements" ? "text-white bg-indigo-600" : "text-indigo-600 hover:bg-indigo-100"}`}
          onClick={() => setActiveTab("enhancements")}
        >
          강화 정보
        </button>
        <button
          className={`px-6 py-2 rounded-md text-lg font-medium ${activeTab === "inheritance" ? "text-white bg-indigo-600" : "text-indigo-600 hover:bg-indigo-100"}`}
          onClick={() => setActiveTab("inheritance")}
        >
          계승 정보
        </button>
        <button
          className={`px-6 py-2 rounded-md text-lg font-medium ${activeTab === "skills" ? "text-white bg-indigo-600" : "text-indigo-600 hover:bg-indigo-100"}`}
          onClick={() => setActiveTab("skills")}
        >
          스킬 정보
        </button>
      </div>

      {/* 탭에 맞는 내용 렌더링 */}
      <div className="space-y-6">{renderTabContent()}</div>
    </div>
  );
}

export default WeaponInfo;

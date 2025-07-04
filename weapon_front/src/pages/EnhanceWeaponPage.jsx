import { useEffect, useState } from "react";
import ToggleSwitch from "../components/ui/ToggleSwitch";
import { useAuth } from "../context/AuthContext";
import { RotateCcw} from "lucide-react"; // 필요한 아이콘만 쓰기

const baseUrl = process.env.REACT_APP_API_BASE_URL;
export default function EnhanceWeaponPage() {
  const { isLoggedIn, user } = useAuth();
  const [weaponData, setWeaponData] = useState(null);
  const [itemData, setItemData] = useState(null);
  const [selectedStats, setSelectedStats] = useState([]);
  const [usePolish, setUsePolish] = useState(false); // 일반 연마제
  const [useHighPolish, setUseHighPolish] = useState(false); // 특수 연마제
  const [loading, setLoading] = useState(true);
  const [isEnhancing, setIsEnhancing] = useState(false);
  const [enhancementOptions, setEnhancementOptions] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false); // 새로고침 중인지
  const [enhanceResult, setEnhanceResult] = useState(null);
  const [enhanceResultBatch, setEnhanceResultBatch] = useState(null); // 연속 강화용
  const [targetEnhancement, setTargetEnhancement] = useState(1);
  const [showEnhanceBatchModal, setShowEnhanceBatchModal] = useState(false); // 연속 강화 모달을 띄움
  const [usePolishLimit, setUsePolishLimit] = useState(0);
  const [useHighPolishLimit, setUseHighPolishLimit] = useState(0);
  const [useWeaponPartsLimit, setUseWeaponPartsLimit] = useState(1);
    const enhancementChances = [
    100, 90, 90, 80, 80, 80, 70, 60, 60, 40,
    40, 30, 20, 20, 10, 10, 5, 5, 3, 1
  ];

  const EnhanceResultBatchModal = ({ resultData, onClose }) => {
    const handleOverlayClick = (event) => {
      if (event.target === event.currentTarget) {
        onClose();
      }
    };
  
    if (!resultData) return null;
  
    const { success, result, logs, used } = resultData;
  
    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60"
        onClick={handleOverlayClick}
      >
        <div className="bg-white rounded-2xl p-8 shadow-2xl text-center animate-fade-in-up w-[90%] max-w-2xl max-h-[90%] overflow-y-auto">
          <div className={`text-4xl font-extrabold mb-4 ${success ? 'text-green-500' : 'text-yellow-600'}`}>
            {success ? '🔥 연속 강화 완료!' : '🔁 연속 강화 진행'}
          </div>
  
          <div className="text-lg text-gray-800 font-semibold mb-2">{result}</div>
  
          {used && (
            <div className="text-sm text-gray-600 mb-4">
              사용된 재료:
              <ul className="list-disc list-inside">
                <li>강화재료: {used["강화재료"]}개</li>
                <li>연마제: {used["연마제"]}개</li>
                <li>특수 연마제: {used["특수 연마제"]}개</li>
              </ul>
            </div>
          )}
  
          <div className="text-sm text-left max-h-64 overflow-y-auto bg-gray-100 rounded-xl p-4 shadow-inner">
            <div className="font-bold mb-2">🔍 강화 로그</div>
            {logs && logs.length > 0 ? (
              logs.map((log, index) => (
                <div key={index} className="mb-2">
                  <div className="font-semibold">{log.message}</div>
                  {log.costs && (
                    <div className="text-xs text-gray-500 ml-2">
                      재료 사용 - 강화재료: {log.costs["강화재료"]}, 연마제: {log.costs["연마제"]}, 특수 연마제: {log.costs["특수 연마제"]}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="text-gray-500">로그가 없습니다.</div>
            )}
          </div>
  
          <div className="text-gray-500 text-sm mt-6">아무데나 클릭하여 닫기</div>
        </div>
      </div>
    );
  };
  
  const EnhanceResultModal = ({ result, onClose }) => {
    const handleOverlayClick = (event) => {
      // 모달 외부를 클릭하면 모달을 닫음
      if (event.target === event.currentTarget) {
        onClose();
      }
    };
    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60"
        onClick={handleOverlayClick} // 모달 외부 클릭 시 닫히도록 이벤트 처리
      >
        <div className="bg-white rounded-2xl p-8 shadow-2xl text-center animate-fade-in-up w-80 max-w-sm">
          {result === 'success' ? (
            <>
              <div className="text-green-500 text-4xl font-extrabold mb-4">🔥 강화 성공!</div>
              <div className="text-xl text-green-700 font-semibold mb-4">+1 강화에 성공했습니다!</div>
              <div className="bg-green-200 p-3 rounded-xl text-lg text-green-800 shadow-md">축하합니다! 강화가 성공적으로 완료되었습니다.</div>
            </>
          ) : result === 'failure' ? (
            <>
              <div className="text-red-500 text-4xl font-extrabold mb-4">😢 강화 실패...</div>
              <div className="text-xl text-red-700 font-semibold mb-4">아쉽게도 실패했습니다.</div>
              <div className="bg-red-200 p-3 rounded-xl text-lg text-red-800 shadow-md">다시 도전해보세요!</div>
            </>
          ) : (
            <>
              <div className="text-red-500 text-4xl font-extrabold mb-4">⚠️ 서버 오류</div>
              <div className="text-xl text-red-700 font-semibold mb-4">서버에서 문제가 발생했습니다. 다시 시도해 주세요.</div>
            </>
          )}
          <div className="text-gray-500 text-sm mt-6">아무데나 클릭하여 닫기</div>
        </div>
      </div>
    );
  };
  
  const fetchAllData = async (discordUsername) => {
    try {
      const now = Date.now();
      // 무기 데이터
      const weaponCacheKey = `weapon_${discordUsername}`;
      const weaponCacheTimeKey = `weapon_${discordUsername}_time`;
      const weaponTTL = 5 * 60 * 1000;
      const weaponCached = sessionStorage.getItem(weaponCacheKey);
      const weaponCachedTime = sessionStorage.getItem(weaponCacheTimeKey);

      if (weaponCached && weaponCachedTime && now - parseInt(weaponCachedTime) < weaponTTL) {
        setWeaponData(JSON.parse(weaponCached));
      } else {
        const weaponRes = await fetch(`${baseUrl}/api/weapon/${discordUsername}/`, {
          credentials: "include",
        });
        const weaponData = await weaponRes.json();
        setWeaponData(weaponData);
        sessionStorage.setItem(weaponCacheKey, JSON.stringify(weaponData));
        sessionStorage.setItem(weaponCacheTimeKey, now.toString());
      }

      // 아이템 데이터
      const itemCacheKey = `items_${discordUsername}`;
      const itemCacheTimeKey = `items_${discordUsername}_time`;
      const itemTTL = 5 * 60 * 1000;
      const itemCached = sessionStorage.getItem(itemCacheKey);
      const itemCachedTime = sessionStorage.getItem(itemCacheTimeKey);

      if (itemCached && itemCachedTime && now - parseInt(itemCachedTime) < itemTTL) {
        setItemData(JSON.parse(itemCached));
      } else {
        const itemRes = await fetch(`${baseUrl}/api/item/${discordUsername}/`, {
          credentials: "include",
        });
        const itemData = await itemRes.json();
        setItemData(itemData);
        sessionStorage.setItem(itemCacheKey, JSON.stringify(itemData));
        sessionStorage.setItem(itemCacheTimeKey, now.toString());
      }

      // 강화 수치 데이터
      const enhCacheKey = "enhancementOptions";
      const enhCacheTimeKey = "enhancementOptions_time";
      const enhTTL = 10 * 60 * 1000;
      const enhCached = sessionStorage.getItem(enhCacheKey);
      const enhCachedTime = sessionStorage.getItem(enhCacheTimeKey);

      if (enhCached && enhCachedTime && now - parseInt(enhCachedTime) < enhTTL) {
        setEnhancementOptions(JSON.parse(enhCached));
      } else {
        const enhRes = await fetch(`${baseUrl}/api/enhancement-info/`);
        const enhData = await enhRes.json();
        setEnhancementOptions(enhData);
        sessionStorage.setItem(enhCacheKey, JSON.stringify(enhData));
        sessionStorage.setItem(enhCacheTimeKey, now.toString());
      }

    } catch (err) {
      console.error("데이터 불러오기 실패:", err);
    } finally {
      setLoading(false); // 무기 불러오기 완료 기준으로 사용 중이라면 여기만 처리
    }
  };

  // 새로 고침 시 상태 복원
  useEffect(() => {
    const savedStats = JSON.parse(localStorage.getItem('selectedStats'));
    if (savedStats) {
      setSelectedStats(savedStats);
    }
  }, []);

  // 기본 강화 수치를 현재 강화 수치에 따라 변경
  useEffect(() => {
    if (weaponData && weaponData.enhancements) {
      setTargetEnhancement(weaponData.enhancements.enhancement_level + 1);
    }
  }, [weaponData]);

  // 선택된 강화 상태를 로컬 스토리지에 저장
  useEffect(() => {
    if (selectedStats.length > 0) {
      localStorage.setItem('selectedStats', JSON.stringify(selectedStats));
    }
  }, [selectedStats]);

  useEffect(() => {
    if (!isLoggedIn || !user) return;
    fetchAllData(user.discord_username);
  }, [isLoggedIn, user]);

  useEffect(() => {
    if (itemData) {
      if (itemData.연마제 <= 0 && usePolish) {
        setUsePolish(false);
      }
      if (itemData["특수 연마제"] <= 0 && useHighPolish) {
        setUseHighPolish(false);
      }
    }
  }, [itemData, usePolish, useHighPolish]);

  const handleRefresh = async () => {
    if (!user) return;
    const discordUsername = user.discord_username;
  
    try {
      setIsRefreshing(true);
  
      // 무기 정보
      const weaponRes = await fetch(`${baseUrl}/api/weapon/${discordUsername}/`, {
        credentials: "include",
      });
      const weaponData = await weaponRes.json();
      setWeaponData(weaponData);
      sessionStorage.setItem(`weapon_${discordUsername}`, JSON.stringify(weaponData));
      sessionStorage.setItem(`weapon_${discordUsername}_time`, Date.now().toString());
  
      // 아이템 정보
      const itemRes = await fetch(`${baseUrl}/api/item/${discordUsername}/`, {
        credentials: "include",
      });
      const itemData = await itemRes.json();
      setItemData(itemData);
      sessionStorage.setItem(`items_${discordUsername}`, JSON.stringify(itemData));
      sessionStorage.setItem(`items_${discordUsername}_time`, Date.now().toString());
  
      // 강화 수치 정보
      const enhancementRes = await fetch(`${baseUrl}/api/enhancement-info/`);
      const enhancementData = await enhancementRes.json();
      setEnhancementOptions(enhancementData);
      sessionStorage.setItem("enhancementOptions", JSON.stringify(enhancementData));
      sessionStorage.setItem("enhancementOptions_time", Date.now().toString());
  
    } catch (error) {
      console.error("데이터 새로고침 실패:", error);
      alert("데이터 새로고침 중 오류가 발생했습니다.");
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleEnhance = async () => {
    console.log('Selected Stats:', selectedStats);
    setIsEnhancing(true);
    
    if (!user) return;
    const discordUsername = user.discord_username;

    try {
      const res = await fetch(`${baseUrl}/api/enhance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          discord_username: discordUsername,
          enhanceType: selectedStats,
          usePolish: usePolish,
          useHighPolish: useHighPolish,
        }),
      });
  
      const data = await res.json();
      console.log("서버 응답 데이터:", data);
      
      if (res.ok) {
        if (data.success) {
          setEnhanceResult('success');
        } else {
          setEnhanceResult('failure');
        }
      } else {
        // 서버에서 명시적으로 에러를 보냈을 경우
        if (data.error) {
          alert(`에러: ${data.error}`); // 또는 setEnhanceError(data.error) 등으로 UI 표시
        } else {
          alert('알 수 없는 오류가 발생했습니다.');
        }
        setEnhanceResult('error');
      }
      
      // 강화 후 캐시 무효화 + 최신 데이터 반영
      sessionStorage.removeItem(`weapon_${discordUsername}`);
      sessionStorage.removeItem(`weapon_${discordUsername}_time`);
      sessionStorage.removeItem(`items_${discordUsername}`);
      sessionStorage.removeItem(`items_${discordUsername}_time`);
      fetchAllData(discordUsername);
    } catch (err) {
      console.error('강화 요청 실패:', err);
      setEnhanceResult('error'); // 오류 발생 시 상태 설정
    } finally {
      setIsEnhancing(false); // 강화 진행 상태 종료
    }
  };

  const handleEnhanceBatch = async () => {
    if (!user) return;

    const discordUsername = user.discord_username;

    // 아이템 재고 체크
    if (usePolish > itemData.연마제) {
      alert(`연마제 개수가 부족합니다. 현재: ${itemData.연마제}개`);
      return;
    }

    if (useHighPolish > itemData["특수 연마제"]) {
      alert(`특수 연마제 개수가 부족합니다. 현재: ${itemData["특수 연마제"]}개`);
      return;
    }

    if (useWeaponPartsLimit > itemData.강화재료) {
      alert(`강화재료 개수가 부족합니다. 현재: ${itemData.강화재료}개`);
      return;
    }

    // 강화 수치 체크
    if (targetEnhancement <= enhancementLevel) {
      alert(`목표 강화 수치는 현재 강화 수치(${enhancementLevel}강)보다 커야 합니다.`);
      return;
    }

    console.log('Selected Stats:', selectedStats);
    setIsEnhancing(true);
  
    try {
      const res = await fetch(`${baseUrl}/api/enhance_batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          discord_username: discordUsername,
          enhanceType: selectedStats,
          usePolishLimit: usePolish,          // 연마제 사용 수 제한
          useHighPolishLimit: useHighPolish,  // 특수 연마제 사용 수 제한
          targetEnhancement: targetEnhancement, // 목표 강화 수치
          useWeaponPartsLimit: useWeaponPartsLimit // 강화재료 사용 수 제한
        }),
      });
  
      const data = await res.json();
      console.log("서버 응답 데이터:", data);
  
      if (res.ok) {
          setEnhanceResultBatch(data);
      } else {
        if (data.error) {
          alert(`에러: ${data.error}`);
        } else {
          alert('알 수 없는 오류가 발생했습니다.');
        }
        setEnhanceResult('error');
      }
  
      // 캐시 무효화 및 데이터 갱신
      sessionStorage.removeItem(`weapon_${discordUsername}`);
      sessionStorage.removeItem(`weapon_${discordUsername}_time`);
      sessionStorage.removeItem(`items_${discordUsername}`);
      sessionStorage.removeItem(`items_${discordUsername}_time`);
      fetchAllData(discordUsername);
    } catch (err) {
      console.error('연속 강화 요청 실패:', err);
      setEnhanceResult('error');
    } finally {
      setIsEnhancing(false);
    }
  };
  
  // 모달 닫기 함수
  const closeModal = () => {
    setEnhanceResult(null); // 모달 닫을 때 결과 상태 초기화
  };

  if (!isLoggedIn) {
    return <p className="text-center text-indigo-600 font-semibold">로그인 후 이용 가능합니다.</p>;
  }

  if (loading || !weaponData) {
    return <p className="text-center text-gray-600">무기 정보 로딩 중...</p>;
  }

  const enhancementLevel = weaponData.enhancements.enhancement_level || 0;
  const polishBonus = usePolish ? 5 : 0;
  const highPolishBonus = useHighPolish ? 50 : 0;
  const currentChance = enhancementChances[enhancementLevel] ?? 0;
  const statLabels = {
    attack_power: "공격력",
    durability: "내구도",
    defense: "방어력",
    speed: "스피드",
    accuracy: "명중",
    critical_damage: "치명타 대미지",
    critical_hit_chance: "치명타 확률",
    skill_enhance: "스킬 증폭",
  };

  const maxWeaponParts = itemData.강화재료;
  const maxPolish = itemData.연마제;
  const maxHighPolish = itemData["특수 연마제"];
  return (
    <div className="px-6 py-0 max-w-3xl mx-auto">
      <h2 className="text-3xl font-bold text-indigo-600 mb-6 text-center">⚒️ 무기 강화</h2>
      {/* 새로고침 버튼 - 오른쪽 상단에 고정 */}
      {/* 새로고침 버튼 - 무기 강화 영역 오른쪽 하단 고정 */}
      <div className="relative mb-6">
  {/* 새로고침 버튼 */}
  <button
    onClick={handleRefresh}
    className="absolute -top-3 -right-3 p-2 bg-white rounded-full shadow-md hover:bg-indigo-50 text-indigo-600 transition z-10"
    title="새로고침"
  >
    {isRefreshing ? (
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
        <div className="bg-white shadow rounded-lg p-6 mb-6 relative">
          <div className="grid grid-cols-2 gap-2 text-sm">
          {Object.entries(weaponData.weapon).map(([stat, value]) => {
            if (
              stat === "range" ||
              typeof value !== "object" ||
              value === null ||
              !("base" in value && "inheritance" in value && "enhancement" in value)
            ) {
              return null;
            }

            const isPercentStat = stat === "critical_hit_chance" || stat === "critical_damage";
            const excludeInheritance = isPercentStat;

            const base = value.base;
            const enhancement = value.enhancement;
            const inheritance = excludeInheritance ? 0 : value.inheritance;

            const total = base + inheritance + enhancement;
            const displayValue = isPercentStat ? (total * 100).toFixed(0) + "%" : total;
            // 👇 미리보기 강화 수치 가져오기
            let previewBonus = 0;
            if (enhancementOptions && selectedStats.length > 0) {
              const selectedOption = enhancementOptions[selectedStats[0]];
              if (
                selectedOption &&
                selectedOption.stats &&
                stat in statLabels &&
                statLabels[stat] in selectedOption.stats
              ) {
                previewBonus = selectedOption.stats[statLabels[stat]];
              }
            }

            return (
              <div key={stat}>
                <span className="font-medium">{statLabels[stat] || stat}:</span>{" "}
                {displayValue}
                {previewBonus > 0 && (
                  <span className="ml-1 text-blue-600 font-semibold">
                    (+{isPercentStat
                      ? (previewBonus * 100).toFixed(0) + "%"
                      : previewBonus}
                    )
                  </span>
                )}
                <span className="text-xs text-gray-500 ml-2 max-[700px]:hidden">
                  (기본 {isPercentStat ? (base * 100).toFixed(0) + "%" : base}{" "}
                  {excludeInheritance ? "" : `+ 계승 ${inheritance}`} + 강화{" "}
                  {isPercentStat ? (enhancement * 100).toFixed(0) + "%" : enhancement})
                </span>
              </div>
            );
          })}
          </div>
        </div>
      </div>
      <div className="bg-white shadow rounded-lg p-6 mb-6">
        {/* 데스크탑용 버튼 UI */}
        <div className="hidden sm:grid grid-cols-2 sm:grid-cols-3 gap-3">
          {Object.keys(enhancementOptions).map((key) => (
            <button
              key={key}
              onClick={() => setSelectedStats([key])}
              className={`w-full px-4 py-2 rounded-lg border text-sm transition text-center
                ${
                  selectedStats.includes(key)
                    ? "bg-blue-600 text-white border-blue-700"
                    : "bg-white text-gray-800 border-gray-300 hover:bg-gray-100"
                }`}
            >
              {key}
            </button>
          ))}
        </div>

        {/* 모바일용 select UI */}
        <div className="sm:hidden">
          <select
            value={selectedStats[0] || ""}
            onChange={(e) => setSelectedStats([e.target.value])}
            className="w-full mt-2 px-4 py-2 border rounded-lg text-sm text-gray-800"
          >
            <option value="" disabled>스탯을 선택하세요</option>
            {Object.keys(enhancementOptions).map((key) => (
              <option key={key} value={key}>
                {key}
              </option>
            ))}
          </select>
        </div>
              
        {itemData && (
          <div className="mt-4 grid grid-cols-3 gap-4 text-center text-base font-medium">
            <div className="bg-indigo-50 rounded-md p-2">
              <div className="text-indigo-600 text-sm sm:text-base whitespace-nowrap">
                강화 재료
              </div>
              <div className="text-sm sm:text-base">{itemData.강화재료 || 0}</div>
            </div>
            <div className="bg-blue-50 rounded-md p-2">
              <div className="text-blue-600 text-sm sm:text-base whitespace-nowrap">
                연마제
              </div>
              <div className="text-sm sm:text-base">{itemData.연마제 || 0}</div>
            </div>
            <div className="bg-purple-50 rounded-md p-2">
              <div className="text-purple-600 text-sm sm:text-base whitespace-nowrap">
                특수 연마제
              </div>
              <div className="text-sm sm:text-base">{itemData["특수 연마제"] || 0}</div>
            </div>
          </div>
        )}
        
        <div className="mt-3 text-sm text-gray-800">
          <div className="mt-6 bg-blue-50 rounded-md py-3 px-4 shadow-sm">
            <div className="text-gray-700 font-semibold text-sm text-center mb-1">
              강화 성공 확률
            </div>

            <div className="text-2xl font-bold text-center text-blue-700 flex justify-center items-center space-x-1">
              {enhancementLevel === 20 ? (
                <span className="text-red-500">최대 강화 도달</span>
              ) : (
                <>
                  <span>{currentChance + polishBonus + highPolishBonus}%</span>
                  {(polishBonus + highPolishBonus > 0) && (
                    <span className="text-green-600 text-base">
                      (+{polishBonus + highPolishBonus}%)
                    </span>
                  )}
                </>
              )}
            </div>

            {enhancementLevel !== 20 && (
              <div className="text-gray-500 text-xs mt-2 text-center">
                +{enhancementLevel} → +{enhancementLevel + 1}
              </div>
            )}
          </div>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-4">
          <div className="flex flex-col items-start sm:flex-row sm:items-center sm:justify-start gap-1 sm:gap-2">
            <span className="text-[13px] sm:text-sm text-gray-700 whitespace-nowrap">
              연마제 사용 <span className="text-gray-500 text-xs">(+5%)</span>
            </span>
            <ToggleSwitch
              enabled={usePolish}
              setEnabled={setUsePolish}
              disabled={enhancementLevel === 20 || !itemData || !itemData.연마제 || itemData.연마제 <= 0}
            />
          </div>

          <div className="flex flex-col items-start sm:flex-row sm:items-center sm:justify-start gap-1 sm:gap-2">
            <span className="text-[13px] sm:text-sm text-gray-700 whitespace-nowrap">
              특수 연마제 사용 <span className="text-gray-500 text-xs">(+50%)</span>
            </span>
            <ToggleSwitch
              enabled={useHighPolish}
              setEnabled={setUseHighPolish}
              disabled={enhancementLevel === 20 || !itemData || !itemData["특수 연마제"] || itemData["특수 연마제"] <= 0}
            />
          </div>
        </div>
        </div>

        <div className="flex space-x-2">
          <button
            className={`flex-1 bg-blue-600 text-white px-4 py-2 rounded-xl transition
              ${
                isEnhancing ||
                enhancementLevel === 20 ||
                !selectedStats ||
                selectedStats.length === 0 ||
                !itemData.강화재료 ||
                itemData.강화재료 === 0 
                  ? 'bg-gray-400 cursor-not-allowed' 
                  : 'hover:bg-blue-700'
              }`}
            onClick={handleEnhance}
            disabled={
              isEnhancing ||
              enhancementLevel === 20 ||
              !selectedStats ||
              selectedStats.length === 0 ||
              !itemData.강화재료 ||
              itemData.강화재료 === 0 
            }
          >
            {enhancementLevel === 20
              ? '최대 강화입니다'
              : isEnhancing
              ? '강화 중...'
              : !selectedStats || selectedStats.length === 0
              ? '강화 항목을 선택하세요'
              : itemData.강화재료 === 0 || !itemData.강화재료
              ? '재료가 부족합니다'
              : '강화하기'}
          </button>

          <button
            className={`flex-1 bg-purple-600 text-white px-4 py-2 rounded-xl transition
            ${
              isEnhancing ||
              enhancementLevel === 20 ||
              !selectedStats ||
              selectedStats.length === 0 ||
              !itemData.강화재료 ||
              itemData.강화재료 === 0 
                ? 'bg-gray-400 cursor-not-allowed' 
                : 'hover:bg-purple-700'
            }`}
            onClick={() => setShowEnhanceBatchModal(true)}
            disabled={
              isEnhancing ||
              enhancementLevel === 20 ||
              !selectedStats ||
              selectedStats.length === 0 ||
              !itemData.강화재료 ||
              itemData.강화재료 === 0 
            }
          >
            {enhancementLevel === 20
              ? '최대 강화입니다'
              : isEnhancing
              ? '강화 중...'
              : !selectedStats || selectedStats.length === 0
              ? '강화 항목을 선택하세요'
              : itemData.강화재료 === 0 || !itemData.강화재료
              ? '재료가 부족합니다'
              : '연속 강화'}
          </button>
        </div>
        
        {showEnhanceBatchModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex justify-center items-center z-50">
            <div className="bg-white rounded-xl shadow-lg p-6 w-full max-w-md">
              <h2 className="text-xl font-bold mb-4">연속 강화 설정</h2>

              <div className="space-y-6">
                {/* 목표 강화 수치 */}
                <div>
                  <label className="block text-sm font-medium mb-1">목표 강화 수치</label>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setTargetEnhancement(enhancementLevel + 1)}
                      className="text-xs bg-gray-200 px-2 py-1 rounded"
                    >
                      min
                    </button>
                    <button
                      onClick={() => setTargetEnhancement((prev) => Math.max(prev - 10, enhancementLevel + 1))}
                      className="text-xs bg-gray-200 px-2 py-1 rounded"
                    >
                      -10
                    </button>
                    <button
                      onClick={() => setTargetEnhancement((prev) => Math.max(prev - 1, enhancementLevel + 1))}
                      className="text-xs bg-gray-200 px-2 py-1 rounded"
                    >
                      -1
                    </button>

                    <input
                      type="number"
                      min={enhancementLevel + 1}
                      max={20}
                      value={targetEnhancement}
                      onChange={(e) => {
                        let val = Number(e.target.value);
                        if (val < enhancementLevel + 1) val = enhancementLevel + 1;
                        if (val > 20) val = 20;
                        setTargetEnhancement(val);
                      }}
                      className="w-20 text-center border border-gray-300 rounded px-2 py-1 text-sm"
                    />

                    <button
                      onClick={() => setTargetEnhancement((prev) => Math.min(prev + 1, 20))}
                      className="text-xs bg-gray-200 px-2 py-1 rounded"
                    >
                      +1
                    </button>
                    <button
                      onClick={() => setTargetEnhancement((prev) => Math.min(prev + 10, 20))}
                      className="text-xs bg-gray-200 px-2 py-1 rounded"
                    >
                      +10
                    </button>
                    <button
                      onClick={() => setTargetEnhancement(20)}
                      className="text-xs bg-gray-200 px-2 py-1 rounded"
                    >
                      max
                    </button>
                  </div>
                </div>

                {/* 강화재료 */}
                <div>
                  <label className="block text-sm font-medium mb-1">강화재료 사용 제한</label>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setUseWeaponPartsLimit(1)}
                      className="text-xs bg-gray-200 px-2 py-1 rounded"
                    >
                      min
                    </button>
                    <button
                      onClick={() => setUseWeaponPartsLimit((prev) => Math.max(prev - 10, 1))}
                      className="text-xs bg-gray-200 px-2 py-1 rounded"
                    >
                      -10
                    </button>
                    <button
                      onClick={() => setUseWeaponPartsLimit((prev) => Math.max(prev - 1, 1))}
                      className="text-xs bg-gray-200 px-2 py-1 rounded"
                    >
                      -1
                    </button>

                    <input
                      type="number"
                      min={1}
                      max={maxWeaponParts}
                      value={useWeaponPartsLimit}
                      onChange={(e) => {
                        let val = Number(e.target.value);
                        if (val < 1) val = 1;
                        if (val > maxWeaponParts) val = maxWeaponParts;
                        setUseWeaponPartsLimit(val);
                      }}
                      className="w-20 text-center border border-gray-300 rounded px-2 py-1 text-sm"
                    />

                    <button
                      onClick={() => setUseWeaponPartsLimit((prev) => Math.min(prev + 1, maxWeaponParts))}
                      className="text-xs bg-gray-200 px-2 py-1 rounded"
                    >
                      +1
                    </button>
                    <button
                      onClick={() => setUseWeaponPartsLimit((prev) => Math.min(prev + 10, maxWeaponParts))}
                      className="text-xs bg-gray-200 px-2 py-1 rounded"
                    >
                      +10
                    </button>
                    <button
                      onClick={() => setUseWeaponPartsLimit(maxWeaponParts)}
                      className="text-xs bg-gray-200 px-2 py-1 rounded"
                    >
                      max
                    </button>
                  </div>
                </div>

                {/* 연마제 */}
                <div>
                  <label className="block text-sm font-medium mb-1">연마제 사용 수량</label>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setUsePolishLimit(0)}
                      className="text-xs bg-gray-200 px-2 py-1 rounded"
                    >
                      min
                    </button>
                    <button
                      onClick={() => setUsePolishLimit((prev) => Math.max(prev - 10, 0))}
                      className="text-xs bg-gray-200 px-2 py-1 rounded"
                    >
                      -10
                    </button>
                    <button
                      onClick={() => setUsePolishLimit((prev) => Math.max(prev - 1, 0))}
                      className="text-xs bg-gray-200 px-2 py-1 rounded"
                    >
                      -1
                    </button>

                    <input
                      type="number"
                      min={0}
                      max={maxPolish}
                      value={usePolishLimit}
                      onChange={(e) => {
                        let val = Number(e.target.value);
                        if (val < 0) val = 0;
                        if (val > maxPolish) val = maxPolish;
                        setUsePolishLimit(val);
                      }}
                      className="w-20 text-center border border-gray-300 rounded px-2 py-1 text-sm"
                    />

                    <button
                      onClick={() => setUsePolishLimit((prev) => Math.min(prev + 1, maxPolish))}
                      className="text-xs bg-gray-200 px-2 py-1 rounded"
                    >
                      +1
                    </button>
                    <button
                      onClick={() => setUsePolishLimit((prev) => Math.min(prev + 10, maxPolish))}
                      className="text-xs bg-gray-200 px-2 py-1 rounded"
                    >
                      +10
                    </button>
                    <button
                      onClick={() => setUsePolishLimit(maxPolish)}
                      className="text-xs bg-gray-200 px-2 py-1 rounded"
                    >
                      max
                    </button>
                  </div>
                </div>

                {/* 특수 연마제 */}
                <div>
                  <label className="block text-sm font-medium mb-1">특수 연마제 사용 수량</label>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setUseHighPolishLimit(0)}
                      className="text-xs bg-gray-200 px-2 py-1 rounded"
                    >
                      min
                    </button>
                    <button
                      onClick={() => setUseHighPolishLimit((prev) => Math.max(prev - 10, 0))}
                      className="text-xs bg-gray-200 px-2 py-1 rounded"
                    >
                      -10
                    </button>
                    <button
                      onClick={() => setUseHighPolishLimit((prev) => Math.max(prev - 1, 0))}
                      className="text-xs bg-gray-200 px-2 py-1 rounded"
                    >
                      -1
                    </button>

                    <input
                      type="number"
                      min={0}
                      max={maxHighPolish}
                      value={useHighPolishLimit}
                      onChange={(e) => {
                        let val = Number(e.target.value);
                        if (val < 0) val = 0;
                        if (val > maxHighPolish) val = maxHighPolish;
                        setUseHighPolishLimit(val);
                      }}
                      className="w-20 text-center border border-gray-300 rounded px-2 py-1 text-sm"
                    />

                    <button
                      onClick={() => setUseHighPolishLimit((prev) => Math.min(prev + 1, maxHighPolish))}
                      className="text-xs bg-gray-200 px-2 py-1 rounded"
                    >
                      +1
                    </button>
                    <button
                      onClick={() => setUseHighPolishLimit((prev) => Math.min(prev + 10, maxHighPolish))}
                      className="text-xs bg-gray-200 px-2 py-1 rounded"
                    >
                      +10
                    </button>
                    <button
                      onClick={() => setUseHighPolishLimit(maxHighPolish)}
                      className="text-xs bg-gray-200 px-2 py-1 rounded"
                    >
                      max
                    </button>
                  </div>
                </div>
              </div>

              <div className="mt-6 flex justify-end space-x-2">
                <button
                  onClick={() => setShowEnhanceBatchModal(false)}
                  className="px-4 py-2 rounded bg-gray-300 hover:bg-gray-400"
                >
                  취소
                </button>
                <button
                  onClick={handleEnhanceBatch}
                  disabled={isEnhancing}
                  className={`px-4 py-2 rounded text-white transition 
                    ${isEnhancing 
                      ? 'bg-gray-400 cursor-not-allowed' 
                      : 'bg-purple-600 hover:bg-purple-700'}
                  `}
                >
                  {isEnhancing ? '강화 중...' : '연속 강화 실행'}
                </button>
              </div>
            </div>
          </div>
        )}
      {enhanceResult && !enhanceResultBatch && (
        <EnhanceResultModal result={enhanceResult} onClose={closeModal} />
      )}
      {enhanceResultBatch && (
        <EnhanceResultBatchModal
          resultData={enhanceResultBatch}
          onClose={() => {
            setEnhanceResultBatch(null);       // 결과 모달 닫기
            setShowEnhanceBatchModal(false);   // 상위 모달도 함께 닫기
          }}
        />
      )}
    </div>
  );
}
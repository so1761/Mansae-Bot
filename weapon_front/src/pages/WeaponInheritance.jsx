import React, { useState, useEffect } from 'react';
import { useAuth } from "../context/AuthContext";
import { 
  ShieldAlert, 
  Sparkles, 
  ArrowRightLeft, 
  RefreshCw, 
  Gem, 
  Gift,
  ChevronsRight,
  X,
  RotateCcw
} from 'lucide-react';
const baseUrl = process.env.REACT_APP_API_BASE_URL;

// 드롭다운에 표시할 무기 목록
const weaponOptions = [
    { label: "활", description: "스피드를 통한 연사", value: "활" },
    { label: "대검", description: "높은 공격력과 보호막 파괴", value: "대검" },
    { label: "단검", description: "높은 회피와 암살 능력", value: "단검" },
    { label: "조총", description: "치명타를 통한 스킬 연속 사용", value: "조총" },
    { label: "창", description: "꿰뚫림 스택을 통한 누적 피해", value: "창" },
    { label: "낫", description: "흡혈을 통한 유지력", value: "낫" },
    { label: "스태프-화염", description: "강력한 화력과 지속적 화상 피해", value: "스태프-화염" },
    { label: "스태프-냉기", description: "얼음과 관련된 군중제어기 보유", value: "스태프-냉기" },
    { label: "스태프-신성", description: "치유 능력과 침묵 부여", value: "스태프-신성" },
    { label: "태도", description: "명중에 따른 공격 능력 증가, 출혈을 통한 피해", value: "태도" },
];

// 계승 불가 시 보여줄 컴포넌트
const EligibilityWarning = ({ enhancementLevel, handleRefresh, isRefreshing }) => (
  <div className="relative flex flex-col items-center justify-center text-center p-8 border-2 border-red-300 bg-red-50 rounded-lg shadow-md">
    {/* 오른쪽 상단 새로고침 버튼 */}
    <button
      onClick={handleRefresh}
      className="absolute top-2 right-2 p-2 bg-red-100 rounded-full shadow hover:bg-red-200 text-red-600 transition"
      title="새로고침"
    >
      {isRefreshing ? (
        <svg
          className="animate-spin h-5 w-5 text-red-600"
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

    <ShieldAlert className="w-16 h-16 text-red-500 mb-4" />
    <h2 className="text-2xl font-bold text-red-700">계승 불가!</h2>
    <p className="text-lg text-red-600 mt-2">
      무기 강화 단계가 15단계 이상일 때만 계승이 가능합니다.
    </p>
    <p className="text-md text-gray-500 mt-4">
      현재 강화 단계: <span className="font-bold text-red-500">+{enhancementLevel}</span>
    </p>
  </div>
);

// 계승 진행 모달 컴포넌트
const InheritanceModal = ({ selectedWeapon, onConfirm, onCancel, isSubmitting }) => {
    const [newWeaponName, setNewWeaponName] = useState("");

    const handleConfirm = () => {
        if (newWeaponName.trim()) {
            onConfirm(newWeaponName.trim());
        }
    };
    
    return (
        <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50 transition-opacity">
            <div className="bg-white rounded-lg shadow-2xl p-8 m-4 max-w-sm w-full transform transition-all scale-100">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-2xl font-bold text-indigo-600">새로운 무기 이름 결정</h2>
                    <button onClick={onCancel} className="p-1 rounded-full hover:bg-gray-200">
                        <X className="w-6 h-6 text-gray-500" />
                    </button>
                </div>
                <p className="text-gray-600 mb-4">
                    선택한 <span className="font-semibold text-indigo-500">{selectedWeapon}</span> 타입의 새로운 이름을 입력해주세요.
                </p>
                <input 
                    type="text"
                    value={newWeaponName}
                    onChange={(e) => setNewWeaponName(e.target.value)}
                    placeholder="예: 거대한 공포"
                    maxLength={10}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 mb-6"
                />
                <div className="flex justify-end gap-3">
                    <button 
                        onClick={onCancel}
                        className="px-4 py-2 bg-gray-200 text-gray-800 font-semibold rounded-md hover:bg-gray-300"
                    >
                        취소
                    </button>
                    <button
                        onClick={handleConfirm}
                        disabled={!newWeaponName.trim() || isSubmitting}
                        className="px-4 py-2 bg-indigo-600 text-white font-semibold rounded-md hover:bg-indigo-700 disabled:bg-indigo-300 disabled:cursor-not-allowed flex items-center gap-2"
                        >
                        <Sparkles className="w-5 h-5" />
                        {isSubmitting ? '처리 중...' : '계승 시작'}
                    </button>
                </div>
            </div>
        </div>
    );
};

const InheritResultModal = ({ newWeaponName, inheritReward, inheritEnhance, onClose }) => {
    const bonusText = Object.entries(inheritEnhance)
      .map(([key, value]) => `${key} +${value}`)
      .join(', ');
  
    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-60"
        onClick={onClose}
      >
        <div className="bg-white rounded-2xl p-8 shadow-2xl text-center animate-fade-in-up w-[90%] max-w-xl">
          <div className="text-3xl font-bold text-yellow-600 mb-4">🌟 무기 계승 완료!</div>
          <div className="text-xl font-semibold text-gray-800 mb-2">
            [{newWeaponName}] 무기가 탄생했습니다!
          </div>
  
          <div className="mt-4 text-left text-sm text-gray-700">
            <div className="mb-2"><span className="font-bold">🎁 계승 보상:</span> {inheritReward}</div>
            <div className="mb-2"><span className="font-bold">✨ 추가 강화:</span> {bonusText}</div>
          </div>
  
          <div className="text-gray-500 text-sm mt-6">아무데나 클릭하여 닫기</div>
        </div>
      </div>
    );
  };

// 메인 계승 페이지 컴포넌트
function WeaponInheritance({ weaponData, handleRefresh, isRefreshing}) {
    const [selectedWeapon, setSelectedWeapon] = useState('');
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [inheritResult, setInheritResult] = useState(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    const enhancementLevel = weaponData.enhancements.enhancement_level || 0;
    const enhancementToInherit = Math.max(0, enhancementLevel - 15);
    const isEligible = enhancementLevel >= 15;

    const handleInheritClick = () => {
        setIsModalOpen(true);
    };

    const handleModalConfirm = async (newWeaponName) => {
        setIsSubmitting(true); // 버튼 비활성화
        try {
            const response = await fetch(`${baseUrl}/api/inherit/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                // 필요 시 Authorization 헤더 추가
                // 'Authorization': `Bearer ${yourToken}`
            },
            credentials: 'include', // 쿠키 기반 인증 시 필수
            body: JSON.stringify({
                selectedWeapon,
                newWeaponName
            }),
            });

            if (!response.ok) {
            throw new Error('계승 요청 실패');
            }

            const result = await response.json();
            const { inherit_reward, inherit_additional_enhance } = result;

            setInheritResult({
                newWeaponName,
                inheritReward: inherit_reward,
                inheritEnhance: inherit_additional_enhance
              });
              
            setIsModalOpen(false); // 기존 모달은 닫고 결과 모달은 새로 띄움

        } catch (error) {
            console.error('계승 중 오류 발생:', error);
            alert('계승에 실패했습니다. 다시 시도해주세요.');
        } finally{
            setIsSubmitting(false);
        }
    };

    if (!isEligible) {
        return <EligibilityWarning handleRefresh={handleRefresh} enhancementLevel={enhancementLevel} isRefreshing={isRefreshing}/>;
    }

    return (
        <>
            {isModalOpen && (
                <InheritanceModal 
                    selectedWeapon={selectedWeapon}
                    onConfirm={handleModalConfirm}
                    onCancel={() => setIsModalOpen(false)}
                    isSubmitting={isSubmitting}
                />
            )}
            {inheritResult && (
                <InheritResultModal
                    newWeaponName={inheritResult.newWeaponName}
                    inheritReward={inheritResult.inheritReward}
                    inheritEnhance={inheritResult.inheritEnhance}
                    onClose={() => setInheritResult(null)}
                />
            )}
            <div className="p-6 max-w-4xl mx-auto bg-white shadow-xl rounded-2xl relative">
                {/* 🔄 오른쪽 상단 새로고침 버튼 */}
                <button
                    onClick={handleRefresh}
                    className="absolute top-4 right-4 p-2 bg-gray-100 rounded-full shadow hover:bg-indigo-100 text-indigo-600 transition"
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

                <div className="text-center mb-8">
                    <Sparkles className="w-12 h-12 mx-auto text-indigo-500" />
                    <h1 className="text-4xl font-extrabold text-indigo-700 mt-2">
                    <span className="text-yellow-400">+{enhancementLevel}</span>강 달성! 무기 계승
                    </h1>
                    <p className="text-lg text-gray-600 mt-2">
                    새로운 가능성을 향해 무기를 재탄생시키세요.
                    </p>
                </div>

                {/* 계승 규칙 안내 */}
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 mb-8">
                    <h2 className="text-xl font-bold text-gray-800 mb-4">📜 계승 규칙</h2>
                    <ul className="space-y-3 text-gray-700">
                        <li className="flex items-start gap-3">
                            <ArrowRightLeft className="w-5 h-5 text-indigo-500 mt-1 flex-shrink-0" />
                            <span>새로운 <span className="font-semibold">무기 종류</span>를 선택합니다. 현재 무기는 사라집니다.</span>
                        </li>
                        <li className="flex items-start gap-3">
                            <RefreshCw className="w-5 h-5 text-red-500 mt-1 flex-shrink-0" />
                            <span>강화 단계가 <span className="font-semibold text-red-500">초기화</span>됩니다.</span>
                        </li>
                        <li className="flex items-start gap-3">
                            <Gem className="w-5 h-5 text-yellow-500 mt-1 flex-shrink-0" />
                            <span>+15강 이후의 강화 횟수(<span className="font-semibold text-yellow-500">{enhancementToInherit}회</span>)만큼 <span className="font-semibold">기존 강화 내역</span>을 계승합니다.</span>
                        </li>
                        <li className="flex items-start gap-3">
                            <Gift className="w-5 h-5 text-green-500 mt-1 flex-shrink-0" />
                            <span>'기본 스탯 증가' 또는 '기본 스킬 레벨 증가' 중 하나의 <span className="font-semibold text-green-500">계승 보상</span>을 획득합니다.</span>
                        </li>
                    </ul>
                </div>

                {/* 무기 선택 */}
                <div className="space-y-4">
                    <label htmlFor="weapon-select" className="block text-xl font-bold text-gray-800">
                        1. 새로운 무기 타입 선택
                    </label>
                    <select
                        id="weapon-select"
                        value={selectedWeapon}
                        onChange={(e) => setSelectedWeapon(e.target.value)}
                        className="w-full p-4 border border-gray-300 rounded-lg text-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition"
                    >
                        <option value="" disabled>계승할 무기 타입을 선택하세요...</option>
                        {weaponOptions.map(opt => (
                            <option key={opt.value} value={opt.value}>
                                {opt.label} - {opt.description}
                            </option>
                        ))}
                    </select>
                </div>
                
                {/* 계승 진행 버튼 */}
                <div className="mt-8 text-center">
                    <button
                        onClick={handleInheritClick}
                        disabled={!selectedWeapon}
                        className="w-full max-w-xs px-8 py-4 bg-indigo-600 text-white text-xl font-bold rounded-lg shadow-lg hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed transform hover:scale-105 transition-all duration-300 flex items-center justify-center gap-3 mx-auto"
                    >
                        <span>2. 계승 진행</span>
                        <ChevronsRight className="w-7 h-7" />
                    </button>
                </div>
            </div>
        </>
    );
}


// 이 컴포넌트를 사용하는 예시 페이지
export default function InheritancePage() {
    const { isLoggedIn, user } = useAuth();
    const [weaponData, setWeaponData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [isRefreshing, setIsRefreshing] = useState(false); // 새로고침 중인지

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
        } catch (error) {
          console.error("데이터 새로고침 실패:", error);
          alert("데이터 새로고침 중 오류가 발생했습니다.");
        } finally {
          setIsRefreshing(false);
        }
      };

    useEffect(() => {
        if (!isLoggedIn || !user) return;
        fetchAllData(user.discord_username);
      }, [isLoggedIn, user]);
    
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
    
        } catch (err) {
          console.error("데이터 불러오기 실패:", err);
        } finally {
          setLoading(false); // 무기 불러오기 완료 기준으로 사용 중이라면 여기만 처리
        }
    };

    if (!isLoggedIn) {
        return <p className="text-center text-indigo-600 font-semibold">로그인 후 이용 가능합니다.</p>;
      }
    
    if (loading || !weaponData) {
    return <p className="text-center text-gray-600">무기 정보 로딩 중...</p>;
    }
    

    return (
        <WeaponInheritance weaponData={weaponData} handleRefresh={handleRefresh} isRefreshing={isRefreshing} />
    );
}

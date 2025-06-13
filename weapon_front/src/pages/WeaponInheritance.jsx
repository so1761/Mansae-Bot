import React, { useState, useMemo } from 'react';
import { 
  ShieldAlert, 
  Sparkles, 
  ArrowRightLeft, 
  RefreshCw, 
  Gem, 
  Gift,
  ChevronsRight,
  X
} from 'lucide-react';

// --- Mock Data: 실제로는 props로 이 데이터를 받아야 합니다. ---
// 부모 컴포넌트로부터 weaponData를 전달받는다고 가정합니다.
const mockWeaponData = {
  name: "오래된 대검",
  enhancements: {
    attack_enhance: 10,
    defense_enhance: 5,
    speed_enhance: 2,
    // 필요에 따라 다른 강화 수치 추가
  },
  // ... 기타 무기 데이터
};
// ----------------------------------------------------------------

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
const EligibilityWarning = ({ enhancementLevel }) => (
    <div className="flex flex-col items-center justify-center text-center p-8 border-2 border-red-300 bg-red-50 rounded-lg shadow-md">
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
const InheritanceModal = ({ selectedWeapon, onConfirm, onCancel }) => {
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
                    placeholder="예: 영광의 불꽃 활"
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
                        disabled={!newWeaponName.trim()}
                        className="px-4 py-2 bg-indigo-600 text-white font-semibold rounded-md hover:bg-indigo-700 disabled:bg-indigo-300 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                        <Sparkles className="w-5 h-5" />
                        계승 완료
                    </button>
                </div>
            </div>
        </div>
    );
};


// 메인 계승 페이지 컴포넌트
function WeaponInheritance({ weaponData }) {
    const [selectedWeapon, setSelectedWeapon] = useState('');
    const [isModalOpen, setIsModalOpen] = useState(false);

    // 총 강화 수치를 계산 (useMemo로 불필요한 재연산 방지)
    const totalEnhancement = useMemo(() => {
        if (!weaponData || !weaponData.enhancements) return 0;
        return Object.values(weaponData.enhancements).reduce((sum, level) => sum + level, 0);
    }, [weaponData]);

    const enhancementToInherit = Math.max(0, totalEnhancement - 15);
    const isEligible = totalEnhancement >= 15;

    const handleInheritClick = () => {
        setIsModalOpen(true);
    };

    const handleModalConfirm = (newWeaponName) => {
        console.log(`계승 시작!`);
        console.log(`선택된 무기 타입: ${selectedWeapon}`);
        console.log(`새로운 무기 이름: ${newWeaponName}`);
        
        // 여기에 실제 계승 로직 API 호출
        // 예: 70% 확률로 '기본 스탯 증가', 30% 확률로 '기본 스킬 레벨 증가' 보상 결정
        const reward = Math.random() < 0.7 ? "기본 스탯 증가" : "기본 스킬 레벨 증가";
        console.log(`계승 보상: ${reward}`);
        
        alert(`${newWeaponName}(으)로 계승이 완료되었습니다! 보상: ${reward}`);
        setIsModalOpen(false);
    };

    if (!isEligible) {
        return <EligibilityWarning enhancementLevel={totalEnhancement} />;
    }

    return (
        <>
            {isModalOpen && (
                <InheritanceModal 
                    selectedWeapon={selectedWeapon}
                    onConfirm={handleModalConfirm}
                    onCancel={() => setIsModalOpen(false)}
                />
            )}
            <div className="p-6 max-w-4xl mx-auto bg-white shadow-xl rounded-2xl">
                <div className="text-center mb-8">
                    <Sparkles className="w-12 h-12 mx-auto text-indigo-500" />
                    <h1 className="text-4xl font-extrabold text-indigo-700 mt-2">
                        <span className="text-yellow-400">+{totalEnhancement}</span>강 달성! 무기 계승
                    </h1>
                    <p className="text-lg text-gray-600 mt-2">새로운 가능성을 향해 무기를 재탄생시키세요.</p>
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
    // 실제로는 API를 통해 유저의 무기 데이터를 가져와야 합니다.
    const [myWeapon] = useState(mockWeaponData);

    return (
        <WeaponInheritance weaponData={myWeapon} />
    );
}

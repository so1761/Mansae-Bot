import { useEffect, useState } from "react";

export default function EnhancementInfoPage() {
  const [enhancementOptions, setEnhancementOptions] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchEnhancements = async () => {
      try {
        const response = await fetch("http://localhost:8000/api/enhancement-info/");
        const data = await response.json();
        setEnhancementOptions(data);
      } catch (error) {
        console.error("데이터 가져오기 실패:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchEnhancements();
  }, []);

  if (loading) return <p>로딩 중...</p>;

  return (
    <div className="px-8 py-4 max-w-screen-xl mx-auto">
      <h2 className="text-3xl font-bold text-indigo-600 text-center mb-6">강화 효과 정보</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
        {Object.entries(enhancementOptions).map(([enhanceType, data]) => (
          <div
          key={enhanceType}
          className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm min-h-[205px] flex flex-col justify-between"
        >
          <div>
            <h3 className="text-lg font-semibold text-gray-800 mb-1">{enhanceType}</h3>
            <p className="text-sm text-gray-500 mb-3">주 능력치: {data.main_stat}</p>
            <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm text-gray-700">
            {Object.entries(data.stats)
              .sort(([statA], [statB]) => {
                if (statA === data.main_stat) return -1;
                if (statB === data.main_stat) return 1;
                return 0;
              })
              .map(([statName, value]) => {
                const isPercentStat = ["치명타 대미지", "치명타 확률", "적중률"].includes(statName);
                const displayValue = isPercentStat ? `+${value * 100}%` : `+${value}`;
                return (
                  <div key={statName}>
                    <span className="font-medium">{statName}:</span> {displayValue}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
        ))}
      </div>
    </div>
  );
}
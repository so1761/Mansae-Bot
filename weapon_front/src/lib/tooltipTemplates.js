// tooltipTemplates.js
import React from "react";

export const tooltipTemplates = {
  skill_tooltip_v1: (params) => {
    const 명중 = params.중거리_기본_명중_증가 + params.레벨 * params.중거리_레벨당_명중_증가;
    const 추가피해 = Math.round(params.중거리_기본공격_추가피해_레벨당 * params.레벨 * 100);

    return (
      <div className="space-y-1">
        <div>거리 {params.근접_밀쳐내기_거리} 이하일 경우, 적을 {params.밀쳐내기_조건_거리}칸 밀쳐냅니다.</div>
        <div>
          거리 {params.중거리_조건_거리}에서의 공격은 반드시 치명타로 적용되고,<br/>
          명중이{" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-content={`기본: ${params.중거리_기본_명중_증가}, 레벨당 + ${params.중거리_레벨당_명중_증가}`}
            data-tooltip-place="top"
          >
            {명중}
          </span>{" "}
          증가하며, 기본 공격 시&nbsp;
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-damage"
            data-tooltip-content={`레벨당 +${params.중거리_기본공격_추가피해_레벨당 * 100}%`}
            data-tooltip-place="top"
          >
            {추가피해}%
          </span>{" "}
          추가 피해를 입힙니다.
        </div>
        <div>거리 {params.최대_사용_사거리 + 1} 이상에서는 스킬을 사용할 수 없습니다.</div>
      </div>
    );
  },
  skill_tooltip_v2: (params) => {
    const 피해량 = params.기본_피해량 + params.레벨 * params.레벨당_피해량_증가;
    const 공격력계수 = params.기본_공격력_계수 + params.레벨 * params.레벨당_공격력_계수_증가;
    const 스증계수 = params.기본_스킬증폭_계수 + params.레벨 * params.레벨당_스킬증폭_계수_증가;
    const 최소흡혈 = Math.round(params.기본_흡혈_비율 * 100);
    const 추가흡혈 = Math.round(params.스킬증폭당_추가흡혈_비율 * 10000) / 100; // 예: 0.004 => 0.4%
    const 스킬피해 = Math.round(피해량 + params.공격력 * 공격력계수 + params.스킬_증폭 * 스증계수)
    const 흡혈비율 = Math.round(최소흡혈 + params.스킬_증폭 * 추가흡혈)
    return (
      <div className="space-y-1 text-sm text-gray-600">
        <div>
          대상에게{" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              스킬 피해 = 
              <span style="color: #facc15;">${피해량}</span> + 
              (공격력 <span style="color: #f97316;">${params.공격력}</span> × <span style="color: #f97316;">${공격력계수.toFixed(2)}</span>) + 
              (스킬 증폭 <span style="color: #34d399;">${params.스킬_증폭}</span> × <span style="color: #34d399;">${스증계수.toFixed(2)}</span>)
            `}
            data-tooltip-place="top"
          >
            {스킬피해}
          </span>
          의 스킬 피해를 입힙니다.
          <span
            className="text-gray-400 cursor-help"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
            <div style="font-size: 13px; line-height: 1.5;">
              <span style="color: #60a5fa;">📊 피해 계산 상세</span><br />
              <span style="color: #f97316;">· 기본 피해량:</span> <span style="color: #fff;">${params.기본_피해량} + (${params.레벨당_피해량_증가} × 레벨)</span><br />
              <span style="color: #facc15;">· 공격력 계수:</span> <span style="color: #fff;">${params.기본_공격력_계수.toFixed(2)} + (${params.레벨당_공격력_계수_증가.toFixed(2)} × 레벨)</span><br />
              <span style="color: #34d399;">· 스킬 증폭 계수:</span> <span style="color: #fff;">${params.기본_스킬증폭_계수.toFixed(2)} + (${params.레벨당_스킬증폭_계수_증가.toFixed(2)} × 레벨)</span>
            </div>
          `}
            data-tooltip-place="top"
          >
            ℹ️
          </span>
        </div>
        <div>
          최종 피해량의{" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <span style="color: #f87171;">${최소흡혈}%</span> + 
              (스킬 증폭 <span style="color: #34d399;">${params.스킬_증폭}</span> × 
              <span style="color: #34d399;">${추가흡혈}%</span>)
            `}
            data-tooltip-place="top"
          >
            {흡혈비율}%
          </span>
          만큼 내구도를 회복합니다.
        </div>
      </div>
    );
  },
  
  skill_tooltip_v3: (params) => {
    const {
      타격횟수결정_스피드값 = 20,
      일반타격_기본_피해배율 = 0.2,
      마지막타격_기본_피해배율 = 0.8,
      레벨당_피해배율 = 0.1,
      레벨 = 1,
      스피드 = 0,
    } = params;
    const 일반계수 = 일반타격_기본_피해배율 + 레벨 * 레벨당_피해배율;
    const 마지막계수 = 마지막타격_기본_피해배율 + 레벨 * 레벨당_피해배율;
  
    const 타격횟수 = Math.max(2, Math.floor(스피드 / 타격횟수결정_스피드값));
  
    return (
      <div className="space-y-1 text-sm text-gray-600">
        <div>
          속도를 기반으로{" "}
            <span
              className="text-indigo-500"
              data-tooltip-id="tooltip-hit"
              data-tooltip-html={`
                <div style="font-size: 13px; line-height: 1.5; text-align: left;">
                  <span style="color: #60a5fa;">🧮 타격 횟수 계산</span><br />
                  <span style="color: #fff;">· 기본 최소 2회</span><br />
                  <span style="color: #34d399;">· 스피드 ${타격횟수결정_스피드값}당 1회 증가</span><br />
                  현재 스피드: <span style="color: #facc15;">${스피드}</span><br />
                  → 최종 타격 횟수: <span style="color: #facc15;">${타격횟수}회</span>
                </div>
              `}
              data-tooltip-place="top"
              >
            {타격횟수}회
            </span>{" "}
           연속 타격을 가하고,<br/>마지막 일격은 강화되어 더 큰 피해를 입힙니다.
            <span
            className="text-gray-400 cursor-help ml-1"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <div style="font-size: 13px; line-height: 1.5; text-align: left;">
                <span style="color: #60a5fa;">📊 피해 배율</span><br />
                · 일반 공격: <span style="color: #f97316;">${Math.round(일반계수 * 100)}%</span><br />
                · 마지막 공격: <span style="color: #f97316;">${Math.round(마지막계수 * 100)}%</span><br />
                · 레벨당 증가량: <span style="color: #34d399;">+${Math.round(레벨당_피해배율 * 100)}%</span>
              </div>
            `}
            data-tooltip-place="top"
            >
            ℹ️
          </span>
        </div>
      </div>
    );
  },
  skill_tooltip_v4: (params) => {
    const 증가_공격력 = params.레벨 * params.레벨당_공격력_증가;
    const 증가_치명타피해 = params.레벨 * params.레벨당_치명타피해_증가;
  
    return (
      <div className="space-y-1 text-sm text-gray-600">
        <div>
          다음 공격에 치명타가 적용되는 공격을 가하고,<br/>
          이 공격의 공격력은{" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <div style="font-size: 13px; line-height: 1.5;">
                <span style="color: #60a5fa;">📈 공격력 증가</span><br />
                · 레벨당 +${params.레벨당_공격력_증가}<br />
                → 총 +${증가_공격력}
              </div>
            `}
            data-tooltip-place="top"
          >
            +{증가_공격력}
          </span>
          , 치명타 피해 배율은{" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <div style="font-size: 13px; line-height: 1.5;">
                <span style="color: #f87171;">🔥 치명타 피해 증가</span><br />
                · 레벨당 +${(params.레벨당_치명타피해_증가 * 100).toFixed(0)}%<br />
                → 총 +${(증가_치명타피해 * 100).toFixed(0)}%
              </div>
            `}
            data-tooltip-place="top"
          >
            +{(증가_치명타피해 * 100).toFixed(0)}%
          </span>{" "}
          증가합니다.
        </div>
      </div>
    );
  },
  skill_tooltip_v5: (params) => {
    const 회피율 = Math.min(
      params.기본_회피율 + params.레벨 * params.레벨당_회피율_증가,
      params.최대_회피율
    );
    const 방관증가 = params.레벨 * params.은신공격_레벨당_방관_증가;
    const 추가피해배율 = params.은신공격_기본_피해_배율 + params.레벨 * params.은신공격_레벨당_피해_배율;
    const 출혈확률 = params.레벨 * params.은신공격_레벨당_출혈_확률;
    const 출혈피해 = params.은신공격_출혈_기본_지속피해 + params.레벨 * params.은신공격_출혈_레벨당_지속피해;
  
    return (
      <div className="space-y-2 text-sm text-gray-600">
        {/* 은신 상태 효과 */}
        <div>
          {params.지속시간}턴간{" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <div style="font-size: 13px; line-height: 1.5;">
                <span style="color: #60a5fa;">🎯 회피율 증가</span><br />
                · 기본: ${(params.기본_회피율 * 100).toFixed(0)}%<br />
                · 레벨당: +${(params.레벨당_회피율_증가 * 100).toFixed(0)}%<br />
                → 최종: ${(회피율 * 100).toFixed(0)}% (최대 ${params.최대_회피율 * 100}%)
              </div>
            `}
            data-tooltip-place="top"
          >
            은신 상태
          </span>
          가 되어 회피율이 증가합니다.
        </div>
  
        {/* 은신 중 공격 효과 */}
        <div>
          은신 중 공격 시{" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <div style="font-size: 13px; line-height: 1.5;">
                <span style="color: #fbbf24;">🗡 방어력 관통 증가</span><br />
                · 레벨당: +${params.은신공격_레벨당_방관_증가}<br />
                → 총 +${방관증가}
                <hr />
                <span style="color: #34d399;">📈 추가 피해 배율</span><br />
                · 기본: ${params.은신공격_기본_피해_배율 * 100}%<br />
                · 레벨당: +${params.은신공격_레벨당_피해_배율 * 100}%<br />
                → 총: ${추가피해배율.toFixed(1)* 100}%
              </div>
            `}
            data-tooltip-place="top"
          >
            방어력 관통, 추가 피해
          </span>
          를 입힙니다.
        </div>
  
        {/* 출혈 효과 */}
        <div>
          또한{" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <div style="font-size: 13px; line-height: 1.5;">
                <span style="color: #f87171;">💉 출혈 확률</span><br />
                · 레벨당: +${(params.은신공격_레벨당_출혈_확률 * 100).toFixed(0)}%<br />
                → 총: ${(출혈확률 * 100).toFixed(0)}%
                <hr />
                <span style="color: #ef4444;">🩸 출혈 피해</span><br />
                · 기본: ${params.은신공격_출혈_기본_지속피해}<br />
                · 레벨당: +${params.은신공격_출혈_레벨당_지속피해}<br />
                → 매턴 ${출혈피해} 피해, ${params.은신공격_출혈_지속시간}턴 지속
              </div>
            `}
            data-tooltip-place="top"
          >
            출혈
          </span>{" "}
          상태이상을 확률적으로 부여합니다.
        </div>
      </div>
    );
  },
  skill_tooltip_v6: (params) => {
    const 공격력계수 = params.기본_공격력_계수 + params.레벨 * params.레벨당_공격력_계수_증가;
    const 스킬증폭계수 = params.기본_스킬증폭_계수 + params.레벨 * params.레벨당_스킬증폭_계수_증가;
    const 치확 = Math.round(params.치명타_확률 * 100);
    const 총배율 = (1 + params.치명타_확률);
  
    const 피해량_표시 = Math.round(
      (params.공격력 * 공격력계수 + params.스킬_증폭 * 스킬증폭계수) * 총배율
    );
  
    return (
      <div className="space-y-2 text-sm text-gray-600">
        {/* 헤드샷 효과 */}
        <div>
          대상에게{" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <div style="font-size: 13px; line-height: 1.5;">
                <span style="color: #facc15;">💥 피해 계산</span><br />
                · 공격력 계수: <span style="color: #f97316;">${(공격력계수 * 100).toFixed(1)}%</span><br />
                · 스킬 증폭 계수: <span style="color: #34d399;">${(스킬증폭계수 * 100).toFixed(1)}%</span><br />
                · 치명타 확률: <span style="color: #60a5fa;">${치확}%</span><br />
                → 총 배율: <span style="color: #f87171;">${(총배율 * 100).toFixed(0)}%</span>
              </div>
            `}
            data-tooltip-place="top"
          >
            {피해량_표시}의 스킬 피해
          </span>
          를 입힙니다.
        </div>
  
        {/* 장전 효과 */}
        <div>
          이후{" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <div style="font-size: 13px; line-height: 1.5;">
                <span style="color: #ef4444;">🔫 장전 상태</span><br />
                공격 및 스킬 사용이 불가능합니다.<br />
                장전 지속 시간은 쿨다운에 따라 결정됩니다.
              </div>
            `}
            data-tooltip-place="top"
          >
            '장전' 상태
          </span>
          가 되어 다음 행동이 제한됩니다.
        </div>
      </div>
    );
  },
};
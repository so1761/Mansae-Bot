// tooltipTemplates.js
import React from "react";

export const tooltipTemplates = {
  skill_tooltip_v1: (params) => {
    const 피해량_기본 = params.기본_피해량 + params.레벨당_피해량_증가 * params.레벨;
    const 공격력계수 = params.기본_공격력_계수 + params.레벨당_공격력_계수_증가 * params.레벨;
    const 피해량 = Math.round(피해량_기본 + params.공격력 * 공격력계수);
  
    return (
      <div className="space-y-2 text-sm text-gray-600">
        {/* 피해량 */}
        <div>
          대상에게{" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              스킬 피해 = 
              <span style="color: #facc15;">${피해량_기본}</span> + 
              (공격력 <span style="color: #f97316;">${params.공격력}</span> × 
              <span style="color: #f97316;">${공격력계수.toFixed(2)}</span>)
            `}
            data-tooltip-place="top"
          >
            {피해량}
          </span>
          의 스킬 피해를 입힙니다.
          <span
            className="text-gray-400 cursor-help"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <div style="font-size: 13px; line-height: 1.5;">
                <span style="color: #60a5fa;">📊 피해 계산 상세</span><br />
                <span style="color: #facc15;">· 기본 피해량:</span> <span style="color: #fff;">${params.기본_피해량} + (${params.레벨당_피해량_증가} × 레벨)</span><br />
                <span style="color: #f97316;">· 공격력 계수:</span> <span style="color: #fff;">${params.기본_공격력_계수.toFixed(2)} + (${params.레벨당_공격력_계수_증가.toFixed(2)} × 레벨)</span>
              </div>
            `}
            data-tooltip-place="top"
          >
            ℹ️
          </span>
        </div>
  
        {/* 꿰뚫림 부여 */}
        <div>
          명중 시, 적에게{" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <div style="font-size: 13px; line-height: 1.5;">
                <span style="color: #a5b4fc;">꿰뚫림</span><br />
                4턴 동안 지속되며,<br />
                받는 피해가 <span style="color: #f87171;">30%</span> 증가합니다.<br />
                최대 <b>2스택</b>까지 중첩됩니다.
              </div>
            `}
            data-tooltip-place="top"
          >
            꿰뚫림
          </span>{" "}
          상태이상을 4턴간 부여합니다.
        </div>
  
        {/* 꿰뚫림 2스택 효과 */}
        <div>
          이미 꿰뚫림이 2스택일 경우, <br />
          꿰뚫림 상태를 제거하고 창격 피해가 <span className="text-indigo-500">2배</span>, 대상은 1턴간 <span className="text-indigo-500">기절</span>합니다.
        </div>
      </div>
    );
  },
  skill_tooltip_v2: (params) => {
    const 피해량 = params.기본_피해량 + params.레벨 * params.레벨당_피해량_증가;
    const 공격력계수 = params.기본_공격력_계수 + params.레벨 * params.레벨당_공격력_계수_증가;
    const 스증계수 = params.기본_스킬증폭_계수 + params.레벨 * params.레벨당_스킬증폭_계수_증가;
    const 스킬피해 = Math.round(피해량 + params.공격력 * 공격력계수 + params.스킬_증폭 * 스증계수)
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
              <span style="color: #facc15;">· 기본 피해량:</span> <span style="color: #fff;">${params.기본_피해량} + (${params.레벨당_피해량_증가} × 레벨)</span><br />
              <span style="color: #f97316;">· 공격력 계수:</span> <span style="color: #fff;">${params.기본_공격력_계수.toFixed(2)} + (${params.레벨당_공격력_계수_증가.toFixed(2)} × 레벨)</span><br />
              <span style="color: #34d399;">· 스킬 증폭 계수:</span> <span style="color: #fff;">${params.기본_스킬증폭_계수.toFixed(2)} + (${params.레벨당_스킬증폭_계수_증가.toFixed(2)} × 레벨)</span>
            </div>
          `}
            data-tooltip-place="top"
          >
            ℹ️
          </span>
        </div>
        <div>
          최종 피해량의 {round(params.기본_흡혈_비율 * 100)}% 만큼 내구도를 회복합니다.
        </div>
      </div>
    );
  },
  
  skill_tooltip_v3: (params) => {
    const 타격횟수 = 2 + Math.floor(params.스피드 / params.타격횟수결정_스피드값);
  
    const 공격력계수 =
      params.기본_공격력_계수 + params.레벨당_공격력_계수_증가 * params.레벨;
    const 피해량_기본 = params.기본_대미지 + params.레벨당_대미지 * params.레벨;
    
    const 스피드_계수 = 1 + Number((params.스피드당_계수 * params.스피드).toFixed(2));
    const 명중률 = Math.min(0.99, 1 - 30 / (30 + params.명중));
    const 최소피해 = Math.round(피해량_기본 + params.공격력 * 공격력계수 * 스피드_계수 * 명중률);
    const 최대피해 = Math.round(피해량_기본 + params.공격력 * 공격력계수 * 스피드_계수);
  
    return (
      <div className="space-y-2 text-sm text-gray-600">
        {/* 타격 횟수 설명 */}
        <div>
          스피드 기반으로{" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <div style="font-size: 13px; line-height: 1.5; text-align: left;">
                <span style="color: #60a5fa;">🧮 타격 횟수 계산</span><br />
                · 기본 2회 + 스피드 ${params.타격횟수결정_스피드값}당 1회 추가<br />
                현재 스피드: <span style="color: #facc15;">${params.스피드}</span><br />
                → 최종 타격 횟수: <span style="color: #facc15;">${타격횟수}회</span>
              </div>
            `}
            data-tooltip-place="top"
          >
            {타격횟수}회
          </span>{" "}
          연속 타격을 가합니다.
        </div>
  
        {/* 피해량 설명 */}
        <div className="flex items-center gap-1">
          각 타격은{" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              스킬 피해 = 
              (<span style="color: #facc15;">${피해량_기본}</span> + 
              (공격력 <span style="color: #f97316;">${params.공격력}</span> × 
              <span style="color: #f97316;">${공격력계수.toFixed(2)}</span>)) ×
              스피드 계수 <span style="color: #34d399;">${스피드_계수}</span>
            `}
            data-tooltip-place="top"
          >
            {최소피해} ~ {최대피해}
          </span>
          의 피해를 입힙니다.
  
          {/* 정보 아이콘 */}
          <span
            className="ml-1 text-gray-400 cursor-help"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <div style="font-size: 13px; line-height: 1.5;">
                <span style="color: #60a5fa;">📊 피해 계산 상세</span><br />
                <span style="color: #facc15;">· 기본 피해량:</span> <span style="color: #fff;">
                  ${params.기본_대미지} + (${params.레벨당_대미지} × 레벨)
                </span><br />
                <span style="color: #f97316;">· 공격력 계수:</span> <span style="color: #fff;">
                  ${params.기본_공격력_계수.toFixed(2)} + (${params.레벨당_공격력_계수_증가.toFixed(2)} × 레벨)
                </span><br />
                <span style="color: #34d399;">· 스피드 계수:</span> <span style="color: #fff;">
                  1 + (${params.스피드당_계수.toFixed(3)} × 스피드 ${params.스피드})</span>
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
    const {
      레벨,
      기본_피해량,
      레벨당_피해량_증가,
      기본_공격력_계수,
      레벨당_공격력_계수_증가,
      공격력,
    } = params;
  
    const base_damage = 기본_피해량 + 레벨 * 레벨당_피해량_증가;
    const multiplier = 기본_공격력_계수 + 레벨 * 레벨당_공격력_계수_증가;
    const total_damage = base_damage + 공격력 * multiplier;
    const 명중률 = Math.min(0.99, 1 - 30 / (30 + params.명중));
    const 최소피해 = Math.round(total_damage * 명중률);
    const 최대피해 = Math.round(total_damage);
  
    return (
      <div className="space-y-2 text-sm text-gray-600">
        {/* 피해량 */}
        <div className="flex items-center gap-1">
          적에게{" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              스킬 피해 = 
              <span style="color: #facc15;">${base_damage}</span> + 
              (공격력 <span style="color: #f97316;">${공격력}</span> × 
              <span style="color: #f97316;">${multiplier.toFixed(2)}</span>)
            `}
            data-tooltip-place="top"
          >
            {최소피해} ~ {최대피해}
          </span>
          의 피해를 입힙니다.
          {/* 정보 아이콘 */}
          <span
            className="ml-1 text-gray-400 cursor-help"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <div style="font-size: 13px; line-height: 1.5;">
                <span style="color: #60a5fa;">📊 피해 계산 상세</span><br />
                <span style="color: #facc15;">· 기본 피해량:</span> <span style="color: #fff;">
                  ${기본_피해량} + (${레벨} × ${레벨당_피해량_증가}) = ${base_damage}
                </span><br />
                <span style="color: #f97316;">· 공격력 계수:</span> <span style="color: #fff;">
                  ${기본_공격력_계수.toFixed(2)} + (${레벨} × ${레벨당_공격력_계수_증가.toFixed(2)}) = ${multiplier.toFixed(2)}
                </span>
              </div>
            `}
            data-tooltip-place="top"
          >
            ℹ️
          </span>
        </div>
  
        {/* 명중 효과 */}
        <div>
          <span className="text-indigo-500">보호막</span>을 파괴하며,{" "}
          <span className="text-indigo-500">치명타</span>일 경우{" "}
          1턴간 <span className="text-indigo-500">기절</span> 상태를 부여합니다.
        </div>
  
        {/* 회피 페널티 */}
        <div>
          스킬이 <span className="text-indigo-500">빗나갈 경우</span>, 자신에게{" "}
          1턴간 <span className="text-indigo-500">기절</span> 상태를 부여합니다.
        </div>
      </div>
    );
  },
  skill_tooltip_v5: (params) => {
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
                <span style="color: #60a5fa;">🎯 은신 상태</span><br />
                · 회피율이 100% 증가합니다<br />
              </div>
            `}
            data-tooltip-place="top"
          >
            은신
          </span>{" "}
          상태가 되어 회피율이 증가합니다.
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
    const {
      레벨,
      기본_피해량,
      레벨당_피해량_증가,
      기본_공격력_계수,
      레벨당_공격력_계수_증가,
      공격력,
      치명타_확률_증가,
      명중
    } = params;
  
    const base_damage = 기본_피해량 + 레벨 * 레벨당_피해량_증가;
    const multiplier = 기본_공격력_계수 + 레벨 * 레벨당_공격력_계수_증가;
    const 피해량 = Math.round(base_damage + 공격력 * multiplier);
    const 명중률 = Math.min(0.99, 1 - 30 / (30 + 명중));
    const 최소피해 = Math.round(피해량 * 명중률);
    const 최대피해 = 피해량;
  
    return (
      <div className="space-y-2 text-sm text-gray-700">
        {/* 피해량 */}
        <div>
          적에게{" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              스킬 피해 = 
              <span style="color: #facc15;">${base_damage}</span> + 
              (공격력 <span style="color: #f97316;">${공격력}</span> × 
              <span style="color: #f97316;">${multiplier.toFixed(2)}</span>)
            `}
            data-tooltip-place="top"
          >
            {최소피해} ~ {최대피해}
          </span>{" "}
          의 스킬 피해를 입힙니다.
          <span
            className="ml-1 text-gray-400 cursor-help"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <div style="font-size: 13px; line-height: 1.5;">
                <span style="color: #60a5fa;">📊 피해 계산 상세</span><br />
                <span style="color: #facc15;">· 기본 피해량:</span> <span style="color: #fff;">
                  ${기본_피해량} + (${레벨} × ${레벨당_피해량_증가}) = ${base_damage}
                </span><br />
                <span style="color: #f97316;">· 공격력 계수:</span> <span style="color: #fff;">
                  ${기본_공격력_계수.toFixed(2)} + (${레벨} × ${레벨당_공격력_계수_증가.toFixed(2)}) = ${multiplier.toFixed(2)}
                </span>
              </div>
            `}
            data-tooltip-place="top"
          >
            ℹ️
          </span>
        </div>
  
        {/* 치명타 효과 */}
        <div>
          스킬 사용 시 치명타 확률이 {Math.round(치명타_확률_증가 * 100)}% 증가하며,<br/>
          치명타 발생 시 헤드샷 쿨타임이 1턴 감소합니다.
        </div>
  
        {/* 장전 상태 */}
        <div>
          스킬 사용 후{" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <div style="font-size: 13px; line-height: 1.5; text-align: left;">
                <span style="color: #f87171;">장전 효과</span><br />
                · 1턴간 장전 상태가 되어 공격이 불가능합니다.
              </div>
            `}
            data-tooltip-place="top"
          >
            장전 상태
          </span>
          가 됩니다.
        </div>
      </div>
    );
  },
  skill_tooltip_v7: (params) => {
    const 스킬증폭계수 = params.스킬증폭당_보호막_계수 + params.레벨 * params.레벨당_보호막_계수_증가;
    const 보호막량 = Math.round(
      params.스킬_증폭 * 스킬증폭계수
    );
  
    return (
      <div className="space-y-2 text-sm text-gray-600">
          <div>
          모든 스킬의 쿨타임이 1 감소합니다.
          </div>
          <div>
          1턴간{" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
            보호막 = 
            스킬 증폭 <span style="color: #34d399;">${params.스킬_증폭}</span> × <span style="color: #34d399;">${스킬증폭계수.toFixed(1)}</span>
            `}
            data-tooltip-place="top"
          >
            {보호막량}
          </span>
          의 보호막을 얻습니다.
          <span
            className="text-gray-400 cursor-help"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
            <div style="font-size: 13px; line-height: 1.5;">
              <span style="color: #60a5fa;">📊 보호막 상세</span><br />
              <span style="color: #34d399;">· 스킬 증폭 계수:</span> <span style="color: #fff;">${(params.스킬증폭당_보호막_계수.toFixed(1) * 100)}% + (${(params.레벨당_보호막_계수_증가.toFixed(1) * 100)} × 레벨)%</span><br />          
              </div>
          `}
            data-tooltip-place="top"
          >
            ℹ️
          </span>
          </div>
          <div>
          명상 스택이 1 증가합니다.
          
        </div>
      </div>
    );
  },
  skill_tooltip_v8: (params) => {
  // 플레어 스킬 피해 계산
  const 플레어_기본피해 = Math.round(params.기본_피해량 + params.레벨 * params.레벨당_기본_피해량_증가);
  const 플레어_증폭 = (params.기본_스킬증폭_계수 + params.레벨 * params.레벨당_스킬증폭_계수_증가) * 100; // 100 곱함
  const 플레어_피해 = Math.round(플레어_기본피해 + (플레어_증폭 / 100) * params.스킬_증폭); // 다시 100으로 나누어 계산

  // 메테오 스킬 피해 계산
  const 메테오_기본피해 = Math.round(params.강화_기본_피해량 + params.레벨 * params.레벨당_강화_기본_피해량_증가);
  const 메테오_증폭 = (params.강화_기본_스킬증폭_계수 + params.레벨 * params.레벨당_강화_스킬증폭_계수_증가) * 100; // 100 곱함
  const 메테오_피해 = Math.round(메테오_기본피해 + (메테오_증폭 / 100) * params.스킬_증폭); // 다시 100으로 나누어 계산

  // 화상 피해 계산
  const 화상_피해 = Math.round(params.화상_대미지 * params.레벨)
    return (
      <div className="space-y-2 text-sm text-gray-600">
        <div>
          플레어 : 대상에게 {" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <div style="font-size: 13px; line-height: 1.5;">
                <span style="color: #f87171;">🔥 플레어</span><br />
                · 기본 피해: ${플레어_기본피해}<br />
                · 스킬증폭 계수: ${플레어_증폭.toFixed(0)}%<br />
              </div>
            `}
            data-tooltip-place="top"
          >
            {플레어_피해}
          </span>
          의 스킬 피해를 입히고<br />1턴간{" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <div style="font-size: 13px; line-height: 1.5;">
                <span style="color: #f87171;">🔥 화상</span><br />
                턴마다 상대에게 고정 피해를 입힙니다.<br />
                · 화상 피해량: ${화상_피해}<br />
              </div>
            `}
            data-tooltip-place="top"
          >
            화상
          </span>{" "}
          상태이상을 부여합니다.
        </div>
        <div>
          메테오 : 대상에게 {" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <div style="font-size: 13px; line-height: 1.5;">
                <span style="color: #fb923c;">☄️ 메테오</span><br />
                · 기본 피해: ${메테오_기본피해}<br />
                · 스킬증폭 계수: ${메테오_증폭.toFixed(0)}%<br />
              </div>
            `}
            data-tooltip-place="top"
          >
            {메테오_피해}
          </span>
          의 스킬 피해를 입히고<br />1턴간 기절, 3턴간{" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <div style="font-size: 13px; line-height: 1.5;">
                <span style="color: #f87171;">🔥 화상</span><br />
                턴마다 상대에게 고정 피해를 입힙니다.<br />
                · 화상 피해량: ${화상_피해}<br />
              </div>
            `}
            data-tooltip-place="top"
          >
            화상
          </span> {" "}
          상태이상을 부여합니다.
        </div>
      </div>
    );
  },
  skill_tooltip_v9: (params) => {
    const 프로스트_기본피해 = Math.round(params.기본_피해량 + params.레벨 * params.레벨당_기본_피해량_증가);
    const 프로스트_증폭 = (params.기본_스킬증폭_계수 + params.레벨 * params.레벨당_스킬증폭_계수_증가) * 100;
    const 프로스트_피해 = Math.round(프로스트_기본피해 + (프로스트_증폭 / 100) * params.스킬_증폭); // 다시 100으로 나누어 계산

    const 블리자드_기본피해 = Math.round(params.강화_기본_피해량 + params.레벨 * params.레벨당_강화_기본_피해량_증가);
    const 블리자드_증폭 = (params.강화_기본_스킬증폭_계수 + params.레벨 * params.레벨당_강화_스킬증폭_계수_증가) * 100;
    const 블리자드_피해 = Math.round(블리자드_기본피해 + (블리자드_증폭 / 100) * params.스킬_증폭); // 다시 100으로 나누어 계산

    const 둔화율 = Math.round((params.강화_둔화율 + params.레벨 * params.강화_레벨당_둔화율) * 100);
    return (
      <div className="space-y-2 text-sm text-gray-600">
        <div>
          프로스트 : 대상에게 {" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <div style="font-size: 13px; line-height: 1.5;">
                <span style="color: #60a5fa;">❄️ 프로스트</span><br />
                · 기본 피해: ${프로스트_기본피해}<br />
                · 스킬증폭 계수: ${프로스트_증폭.toFixed(0)}%<br />
              </div>
            `}
            data-tooltip-place="top"
          >
            {프로스트_피해}
          </span>
          의 스킬 피해를 입히고<br />1턴간{" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <div style="font-size: 13px; line-height: 1.5;">
                <span style="color: #60a5fa;">❄️ 빙결</span><br />
                · 공격받기 전까지 아무런 행동도 할 수 없습니다.
              </div>
            `}
            data-tooltip-place="top"
          >
          빙결
          </span>{" "} 
          상태이상을 부여합니다.
        </div>
        <div>
          블리자드 : 대상에게 {" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <div style="font-size: 13px; line-height: 1.5;">
                <span style="color: #3b82f6;">🌨 블리자드</span><br />
                · 기본 피해: ${블리자드_기본피해}<br />
                · 스킬증폭 계수: ${블리자드_증폭.toFixed(0)}%<br />
              </div>
            `}
            data-tooltip-place="top"
          >
            {블리자드_피해}
          </span>
          의 스킬 피해를 입히고<br />3턴간{" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <div style="font-size: 13px; line-height: 1.5;">
                <span style="color: #60a5fa;">❄️ 빙결</span><br />
                · 공격받기 전까지 아무런 행동도 할 수 없습니다.
              </div>
            `}
            data-tooltip-place="top"
          >
          빙결
          </span>,{" "}5턴간{" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <div style="font-size: 13px; line-height: 1.5; text-align: left;">
                <span style="color: #60a5fa;">📊 둔화율</span><br />
                · 기본 둔화율: <span style="color: #f97316;">${Math.round(params.강화_둔화율 * 100)}%</span><br />
                · 레벨당 증가량: <span style="color: #34d399;">+${Math.round(params.강화_레벨당_둔화율 * 100)}%</span>
              </div>
            `}
            data-tooltip-place="top"
          >
            {둔화율}%
          </span>{" "}
          둔화 상태이상을 부여합니다.
        </div>
      </div>
    );
  },
  skill_tooltip_v10: (params) => {
    const 블레스_기본피해 = Math.round(
      params.기본_피해량 + params.레벨 * params.레벨당_기본_피해량_증가
    );
    const 블레스_증폭 = (
      params.기본_스킬증폭_계수 +
      params.레벨 * params.레벨당_스킬증폭_계수_증가
    ) * 100;
    const 블레스_피해 = Math.round(블레스_기본피해 + (블레스_증폭 / 100) * params.스킬_증폭); // 다시 100으로 나누어 계산
    const 회복량 = params.레벨당_치유량 * params.레벨;
  
    const 저지먼트_기본피해 = Math.round(
      params.강화_기본_피해량 + params.레벨 * params.레벨당_강화_기본_피해량_증가
    );
    const 저지먼트_증폭 = (
      params.강화_기본_스킬증폭_계수 +
      params.레벨 * params.레벨당_강화_스킬증폭_계수_증가
    ) * 100;
    const 저지먼트_피해 = Math.round(저지먼트_기본피해 + (저지먼트_증폭 / 100) * params.스킬_증폭); // 다시 100으로 나누어 계산
  
    return (
      <div className="space-y-2 text-sm text-gray-600">
        {/* 기본: 블레스 */}
        <div>
          블레스 : 대상에게 {" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`  
              <div style="font-size: 13px; line-height: 1.5;">
                <span style="color: #f9fafb;">✨ 블레스</span><br />
                · 기본 피해: ${블레스_기본피해}<br />
                · 스킬증폭 계수: ${블레스_증폭.toFixed(0)}%<br />
              </div>
            `}
            data-tooltip-place="top"
          >
            {블레스_피해}
          </span>
          의 스킬 피해를 입히고<br />
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`  
              <div style="font-size: 13px; line-height: 1.5;">
                <span style="color: #f9fafb;">✨ 블레스</span><br />
                · 레벨 당 회복량: ${params.레벨당_치유량}<br />
                · 총 회복량: ${회복량}<br />
              </div>
            `}
            data-tooltip-place="top"
          >
            {회복량}
          </span>
          만큼 내구도를 회복합니다.
        </div>
  
        {/* 강화: 저지먼트 */}
        <div>
          저지먼트 : 대상에게 {" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`  
              <div style="font-size: 13px; line-height: 1.5;">
                <span style="color: #fde68a;">🌟 저지먼트</span><br />
                · 기본 피해: ${저지먼트_기본피해}<br />
                · 스킬증폭 계수: ${저지먼트_증폭.toFixed(0)}%<br />
              </div>
            `}
            data-tooltip-place="top"
          >
            {저지먼트_피해}
          </span>
          의 스킬 피해를 입히고<br />3턴간{" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <div style="font-size: 13px; line-height: 1.5;">
                <span style="color: #60a5fa;">🌟 침묵</span><br />
                · 스킬을 사용할 수 없습니다.
              </div>
            `}
            data-tooltip-place="top"
          >
          침묵
          </span>{" "} 
          상태이상을 부여합니다.
        </div>
      </div>
    );
  },
  skill_tooltip_v11: (params) => {
    const 명중반영비율 = params.기본_명중_반영_비율 + params.레벨 * params.레벨당_명중_반영_비율;
    const 명중전환 = Math.round(
      params.명중 * 명중반영비율
    );
    const 명중반영비율_퍼센트 = (명중반영비율 * 100).toFixed(0);
    const 명중률 = Math.min(0.99, 1 - 30 / (30 + params.명중));
    const 치명타확률_퍼센트 = (params.치명타_확률 * 100).toFixed(0);
    const 최소피해 = Math.round(
      (params.공격력 + params.명중 * 명중반영비율) * 명중률
    );
    const 최대피해 = Math.round(
      (params.공격력 + params.명중 * 명중반영비율)
    );
    const 출혈피해 = params.출혈_대미지 + params.레벨 * params.레벨당_출혈_대미지;
  
    return (
      <div className="space-y-2 text-sm text-gray-600">
        <div>
          <span className="text-red-500">🗡️ 일섬</span> : 대상에게 한 턴 뒤{" "}
          <span
            className="text-indigo-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`  
              <div style="font-size: 13px; line-height: 1.5;">
                <span style="color: #f87171;">🗡️ 일섬</span><br />
                · 공격력으로 전환되는 명중: ${명중전환} (명중 반영: ${명중반영비율_퍼센트}%)<br />
              </div>
            `}
            data-tooltip-place="top"
          >
            {최소피해} ~ {최대피해}
          </span>
          의 피해를 입힙니다.<br />
          적이 <span className="text-rose-500">출혈 상태</span>일 경우, 출혈 상태를 없앤 뒤,<br />
          남은 출혈 피해를 대미지에 합산하고,<br />
          총 피해의 50%를 <span className="text-rose-500">고정피해</span>로 입힙니다.

        </div>
  
        <div>
          <span className="text-gray-700">[패시브 효과]</span><br />
          치명타 공격 시,{" "}
          <span
            className="text-rose-500"
            data-tooltip-id="tooltip-hit"
            data-tooltip-html={`
              <div style="font-size: 13px; line-height: 1.5;">
                · 기본 출혈: 2턴 지속<br />
                · 출혈 상태에게 적중 시: 3턴 추가<br />
                · 출혈 확률 : ${치명타확률_퍼센트}%<br />
                · 출혈 피해: 10 + 레벨 × 5 = ${출혈피해}<br />
              </div>
            `}
            data-tooltip-place="top"
          >
            출혈 상태이상🩸
          </span>
          을 부여합니다.
        </div>
      </div>
    );
  },  
};
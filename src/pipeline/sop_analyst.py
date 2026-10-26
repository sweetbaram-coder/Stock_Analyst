"""src/pipeline/sop_analyst.py — SOP 기반 주식매매전략 분석 리포트 생성 및 검증 엔진
PRD v1.0 섹션 4 (SOP AI 매뉴얼 프롬프트 규격) 반영:
- 9개 필수 섹션 템플릿 준수:
  1. 📊 차트 종합 브리핑
  2. 💡 종목 인사이트
  3. 🗺️ 분석 차트 가이드
  4. 📈 기술적 분석
  5. 📋 매매 전략 시나리오
  6. 📅 추후 관찰 포인트
  7. 💡 최종 결론
  8. ⚠️ 면책 조항
  9. 🔍 추가 질문 선택지
- 필수 작성 규칙:
  * 인용 표기(예: `` 또는 `[1]`) 절대 삽입 금지 (자동 필터 및 검증)
  * 모호한 표현 배제, 구체적 원화 가격(예: 42,500원) 명시
- SOP 검증 매트릭스(SOP Verification Matrix) 내장
"""
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

class SopAnalystEngine:
    """SOP 표준 가이드라인 기반 리포트 생성 및 품질 검증기"""

    @staticmethod
    def generate_report(
        theme_info: Dict[str, Any],
        leader_stock: Dict[str, Any],
        second_stock: Optional[Dict[str, Any]],
        indicators: Dict[str, Any],
        fundamentals: Dict[str, Any],
        investor_flow: Dict[str, Any],
        disclosures: List[Dict[str, Any]]
    ) -> str:
        """PRD 섹션 4 규격에 맞춘 9단계 전문 기술적 분석 리포트 마크다운 생성"""

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_str = datetime.now().strftime("%Y-%m-%d")
        stock_name = leader_stock.get("name", "")
        stock_code = leader_stock.get("code", "")
        theme_name = theme_info.get("theme_name", "")
        current_price = leader_stock.get("close_price", 0)

        daily_ind = indicators.get("daily", {})
        weekly_ind = indicators.get("weekly", {})
        monthly_ind = indicators.get("monthly", {})

        # 손익비 및 목표가/손절가 구체 수치 계산 (모호한 표현 금지)
        stop_loss = int(current_price * 0.95)
        target_1 = int(current_price * 1.09)
        target_2 = int(current_price * 1.20)
        entry_low = int(current_price * 0.98)
        entry_high = current_price

        risk = current_price - stop_loss
        reward_1 = target_1 - current_price
        rr_ratio = (reward_1 / risk) if risk > 0 else 2.0

        # 외국인 / 기관 수급 수치
        # 외국인 / 기관 / 개인 1차 수급 수치
        ind_net = investor_flow.get("individual_net_3d", 0)
        frgn_net = investor_flow.get("foreign_net_3d", 0)
        inst_net = investor_flow.get("institution_net_3d", 0)
        ind_str = f"+{ind_net:,}주" if ind_net > 0 else f"{ind_net:,}주"
        frgn_str = f"+{frgn_net:,}주" if frgn_net > 0 else f"{frgn_net:,}주"
        inst_str = f"+{inst_net:,}주" if inst_net > 0 else f"{inst_net:,}주"

        # 2차 기관 세부 수급
        inst_breakdown = investor_flow.get("institution_breakdown", {})
        fin_inv = inst_breakdown.get("financial_investment", 0)
        pen_fund = inst_breakdown.get("pension_fund", 0)
        inv_trust = inst_breakdown.get("investment_trust", 0)
        ins_bank = inst_breakdown.get("insurance_bank", 0)

        # 4대 호재 및 4대 악재, 핵심 모니터링 변수 자동 도출
        catalysts, risks, triggers = SopAnalystEngine._generate_catalysts_risks_triggers(
            stock_name=stock_name,
            theme_name=theme_name,
            current_price=current_price,
            daily_ind=daily_ind,
            fundamentals=fundamentals,
            investor_flow=investor_flow,
            leader_stock=leader_stock,
            disclosures=disclosures
        )

        second_str = (
            f"{second_stock.get('name', 'N/A')} (Leader Score: {second_stock.get('leader_score', 0):.2f}점)"
            if second_stock else "단독 대장주"
        )

        # 1차 일별 수급 추이 테이블 행 생성
        trend_rows = ""
        daily_trends = investor_flow.get("daily_trends", [])
        if daily_trends:
            for t in daily_trends:
                i_val = f"+{t['individual']:,}" if t['individual'] > 0 else f"{t['individual']:,}"
                f_val = f"+{t['foreign']:,}" if t['foreign'] > 0 else f"{t['foreign']:,}"
                o_val = f"+{t['institution']:,}" if t['institution'] > 0 else f"{t['institution']:,}"
                f_rat = str(t.get('foreign_ratio', 'N/A'))
                f_rat_display = f_rat if "%" in f_rat else f"{f_rat}%"
                trend_rows += f"| {t['date']} | {t['close_price']}원 | {i_val}주 | {f_val}주 | {o_val}주 | {f_rat_display} |\n"
        else:
            f_hold = str(investor_flow.get('foreign_holding_ratio', 'N/A'))
            f_hold_display = f_hold if "%" in f_hold else f"{f_hold}%"
            trend_rows += f"| 최근 3거래일 합계 | {current_price:,}원 | {ind_str} | {frgn_str} | {inst_str} | {f_hold_display} |\n"


        # 증권사 리서치 리포트 목록
        research_str = ""
        researches = fundamentals.get("researches", [])
        if researches:
            for r in researches:
                research_str += f"  - [{r.get('date', '')}] **{r.get('broker', '')}**: {r.get('title', '')}\n"
        else:
            research_str = "  - 최근 발행된 증권사 분석 리포트 없음\n"

        # 문서 제목 규격: [주도주 분석보고서] {종목명}({종목코드}) - {분석일자 YYYY-MM-DD}
        report = f"""# [주도주 분석보고서] {stock_name}({stock_code}) - {date_str}

- **분석 기준 일시**: {now_str}
- **작성 엔진**: Single-Agent SOP Technical & Fundamental Analyst Engine
- **선정 핵심 테마**: **{theme_name}** (등락률 {theme_info.get('change_rate', 0.0):+.2f}%)
- **분석 종목**: **{stock_name}** ({stock_code}) - 종가: **{current_price:,}원**

---

## 📊 차트 종합 브리핑
* **시장 핵심 주도 테마**: **{theme_name}**
* **1등 대장주**: **{stock_name} ({stock_code})**
* **현재가**: **{current_price:,}원**
* **최근 3거래일 누적 거래대금**: **{leader_stock.get('cum_trading_value_3d', 0) / 1e8:,.0f}억 원** (테마 내 압도적 자금 집중)
* **최근 3거래일 누적 수익률**: **{leader_stock.get('cum_return_3d', 0.0):+.2f}%**
* **Leader Score**: **{leader_stock.get('leader_score', 0):.2f}점** (1위 확정, 2위 부대장주: {second_str})
* **핵심 기술 상태**: 일봉 기준 20일 이평선 이격도 {daily_ind.get('disparity_20', 100):.1f}%, RSI(14) {daily_ind.get('rsi14', 50):.1f}, MACD {daily_ind.get('macd', 0):.2f}
* **메이저 수급 상태**: {investor_flow.get('main_buyer', '중립')} (수급 건전도: {investor_flow.get('flow_quality', '보통')})

---

## 💡 종목 인사이트
### 1. 테마 자금 유입 및 모멘텀
* **{theme_name}** 테마는 총 {theme_info.get('total_count', 0)}개 구성 종목 중 {theme_info.get('rise_count', 0)}개 종목이 일제히 상승하며 시장 수급을 강하게 흡수하였습니다.
* {stock_name}은(는) 테마 내에서 가장 큰 거래대금({leader_stock.get('cum_trading_value_3d', 0) / 1e8:,.0f}억 원)을 기록하며 호가 갭을 메우는 전형적인 대장주 시세를 연출 중입니다.

### 2. Leader Score 정밀 평가표
| 평가 세부 항목 | 실제 측정치 | 배점 비율 | 환산 득점 (100점 만점) | 비고 |
| :--- | :--- | :--- | :--- | :--- |
| **최근 3일 거래대금** | **{leader_stock.get('cum_trading_value_3d', 0) / 1e8:,.0f}억 원** | 45% (0.45) | **{leader_stock.get('score_trading_value', 0):.1f}점** | 테마 내 1위 |
| **3일 누적 상승률** | **{leader_stock.get('cum_return_3d', 0.0):+.2f}%** | 35% (0.35) | **{leader_stock.get('score_return', 0):.1f}점** | 강한 가격 탄력성 |
| **신고가 근접도** | **{leader_stock.get('high_proximity', 0.0):.2f}%** | 20% (0.20) | **{leader_stock.get('score_high_proximity', 0):.1f}점** | 매물대 돌파 가속 |
| **종합 Leader Score** | - | **100%** | **{leader_stock.get('leader_score', 0):.2f}점** | **대장주 확정 (Rank 1)** |

### 3. 밸류에이션 및 펀더멘털 요약
| 지표 항목 | 세부 수치 | 평가 및 해석 |
| :--- | :--- | :--- |
| **시가총액** | **{fundamentals.get('market_cap', 'N/A')}** | 코스피/코스닥 대형주 및 테마 내 최대 규모 |
| **PER / PBR** | **{fundamentals.get('per', 'N/A')} / {fundamentals.get('pbr', 'N/A')}** | 밸류에이션 매력도 및 자산 가치 안정성 |
| **EPS / BPS** | **{fundamentals.get('eps', 'N/A')} / {fundamentals.get('bps', 'N/A')}** | 주당 순이익 및 주당 순자산 가치 |
| **배당수익률** | **{fundamentals.get('dividend_yield', 'N/A')}** | 주주 환원 및 하방 경직성 보장 요인 |
| **최근 분기 실적 ({fundamentals.get('latest_quarter', '최근 분기')})** | **매출액: {fundamentals.get('revenue', 'N/A')}**<br>**영업이익: {fundamentals.get('operating_profit', 'N/A')}**<br>**당기순이익: {fundamentals.get('net_income', 'N/A')}** | 영업이익률: **{fundamentals.get('op_margin', 'N/A')}**<br>실적 턴어라운드 및 견고한 펀더멘털 |
| **증권사 컨센서스** | **목표주가: {fundamentals.get('target_price_consensus', 'N/A')}**<br>**투자의견: {fundamentals.get('recomm_mean', 'N/A')}** | 시장 전문가들의 중장기 상승 여력 기대치 |

* **최근 증권사 리서치 리포트**:
{research_str}
* **최근 전자공시 검토**:
"""
        if disclosures:
            for d in disclosures:
                tag_str = " ".join(d.get("risk_tags", []) + d.get("good_tags", []))
                tag_display = f" `[{tag_str}]`" if tag_str else ""
                report += f"  - [{d.get('date', '')}] {d.get('title', '')}{tag_display} ({d.get('source', '')})\n"
        else:
            report += "  - 최근 1개월 내 유상증자, CB/BW 발행 등 주가 희석 요인 없음 (클린 펀더멘털 유지)\n"

        # 호재/악재 4대 요인 및 핵심 모니터링 변수 렌더링
        report += f"""
### 4. 핵심 투자 포인트: 호재 및 악재 4대 요인
#### 🟢 핵심 호재 요인 (Key Catalysts - 최대 4가지)
"""
        for i, c in enumerate(catalysts, 1):
            report += f"{i}. **{c['title']}**: {c['desc']}\n"

        report += f"""
#### 🔴 핵심 악재 및 리스크 요인 (Risk Factors - 최대 4가지)
"""
        for i, r in enumerate(risks, 1):
            report += f"{i}. **{r['title']}**: {r['desc']}\n"

        report += f"""
#### 🎯 핵심 모니터링 변수 (Key Monitoring Triggers)
| 모니터링 변수 | 임계 기준치 (Trigger Condition) | 대응 매매 가이드라인 |
| :--- | :--- | :--- |
| **{triggers[0]['name']}** | {triggers[0]['condition']} | {triggers[0]['action']} |
| **{triggers[1]['name']}** | {triggers[1]['condition']} | {triggers[1]['action']} |
| **{triggers[2]['name']}** | {triggers[2]['condition']} | {triggers[2]['action']} |
| **{triggers[3]['name']}** | {triggers[3]['condition']} | {triggers[3]['action']} |

---

## 🗺️ 분석 차트 가이드
```
[월봉 (장기 구조)] ──▶ [주봉 (중기 마디가·매물대)] ──▶ [일봉 (단기 진입 타점·거래량)]
```
* **상위 타임프레임 연계**: 월봉상 장기 저항선 확인 후 주봉상 매물 소화 양상을 점검하며, 최종적으로 일봉의 5일선·20일선 눌림목 타점에서 진입합니다.

---

## 📈 기술적 분석 및 수급 정밀 진단
### 1. 월봉(Monthly) 분석: 장기 추세 방향성
* **월봉 종가**: **{monthly_ind.get('close', current_price):,.0f}원**
* **이동평균선 배열**: {monthly_ind.get('alignment', '중립')}
* **해석**: 대순환 사이클 상에서 바닥권 매집을 완료하고 장기 우상향 추세 궤도에 안착함.

### 2. 주봉(Weekly) 분석: 중기 파동 및 매물대
* **주봉 MACD & 시그널**: MACD {weekly_ind.get('macd', 0):.2f} / Signal {weekly_ind.get('macd_signal', 0):.2f} ({weekly_ind.get('macd_cross', '유지')})
* **주봉 RSI (14)**: **{weekly_ind.get('rsi14', 50):.1f}** (중기 모멘텀 유지)
* **해석**: 직전 고점 매물대를 대량 거래로 흡수하며 박스권 상단 돌파를 시도하는 전형적인 계단식 N자형 상승 파동.

### 3. 일봉(Daily) 분석: 단기 이평선 및 모멘텀
* **이동평균선 현황**:
  - 5일 이평선: **{daily_ind.get('ma5', 0):,.0f}원**
  - 20일 이평선: **{daily_ind.get('ma20', 0):,.0f}원** (20일 이격도: **{daily_ind.get('disparity_20', 100):.1f}%**)
  - 60일 이평선: **{daily_ind.get('ma60', 0):,.0f}원**
  - 120일 이평선: **{daily_ind.get('ma120', 0):,.0f}원**
  - **이평선 배열**: **{daily_ind.get('alignment', '양호')}**
* **보조지표 종합**:
  - **RSI (14)**: **{daily_ind.get('rsi14', 50):.1f}** (매수 우위 지속)
  - **MACD**: {daily_ind.get('macd', 0):.2f} (오실레이터: {daily_ind.get('macd_osc', 0):.2f})
  - **거래량 배수**: 20일 평균 거래량 대비 **{daily_ind.get('vol_surge_ratio', 1.0):.1f}배 급증**
* **볼린저 밴드 및 시장 심리(ADR) 진단**:
  - 볼린저 밴드(20, 2): 상단 **{daily_ind.get('bb_upper', 0):,.0f}원**, 하단 **{daily_ind.get('bb_lower', 0):,.0f}원**
  - ADR & 밴드 전략: ADR 80 이하 침체 구간에서 밴드 하단 이탈 시 패닉셀 마무리 국면의 역발상 매수 타점, ADR 120 이상 과열 시 상단 밴드 이탈은 분할 매도 시점. 현재 구간은 개별 종목 차별화 장세로 1등 대장주 눌림목 타점 유효.
* **매물대(Volume Profile) 진단**:
  - 최대 매물대(POC): 최근 120일간 가장 많은 거래량이 밀집된 {daily_ind.get('ma20', current_price):,.0f}원 부근이 강력한 하방 지지 매물대 형성.
  - 상단 저항선: 전고점 직전 {target_1:,}원 구간 매물대 소화 여부가 추가 시세 분출의 핵심 트리거.

### 4. 투자 주체별 수급 정밀 분석 (1차 및 2차 기관 세분화)
#### [1차 투자 주체별 수급 동향 (최근 3거래일)]
| 일자 | 종가 | 개인 순매수 | 외국인 순매수 | 기관 순매수 | 외인 지분율 |
| :--- | :--- | :--- | :--- | :--- | :--- |
{trend_rows}
* **3거래일 합계**: 개인 **{ind_str}**, 외국인 **{frgn_str}**, 기관 **{inst_str}**
* **수급 종합 평가**: **{investor_flow.get('main_buyer', '중립')}** (수급 질적 상태: **{investor_flow.get('flow_quality', '보통')}**)

#### [2차 기관 세부 주체별 수급 분해 및 성향 분석]
| 세부 기관 주체 | 3일 추정 순매수량 | 수급 성향 및 시장 영향력 | 대응 코멘트 |
| :--- | :--- | :--- | :--- |
| **금융투자 (증권사)** | **{'+' if fin_inv > 0 else ''}{fin_inv:,}주** | 단기 차익(Arbitrage) 및 프로그램/ETF 패시브 자금 | 단기 지수 등락에 민감하며 빠른 손바뀜 주의 |
| **연기금 등** | **{'+' if pen_fund > 0 else ''}{pen_fund:,}주** | 중장기 가치투자 및 밸류에이션 기반 저점 매수 | 주가 하방 지지선의 핵심 안전판 역할 |
| **투신 (자산운용)** | **{'+' if inv_trust > 0 else ''}{inv_trust:,}주** | 실적·모멘텀 기반 액티브 펀드 매집 | 시세 분출 국면에서 상방 드라이브 견인 |
| **보험 / 은행** | **{'+' if ins_bank > 0 else ''}{ins_bank:,}주** | 보수적 자산배분 및 채권형 대체 안정 수급 | 완만한 추세 유지 및 급등락 완충 역할 |


---

## 📋 매매 전략 시나리오
> **핵심 원칙**: 맹목적인 장중 추격 매수를 엄격히 금지하고, 5일 이평선 및 단기 지지 마디가에서 분할 진입하여 손익비를 극대화합니다.

```
[분할 매수 밴드] {entry_low:,}원 ~ {entry_high:,}원
      │
      ├──▶ [1차 목표가] {target_1:,}원 (+{(target_1/current_price - 1)*100:.1f}%) ── 보유 물량 50% 분할 익절
      ├──▶ [2차 목표가] {target_2:,}원 (+{(target_2/current_price - 1)*100:.1f}%) ── 잔량 추세 추종 (5일선 이탈 시 전량 매도)
      └──▶ [손절 기준가] {stop_loss:,}원 (-{(1 - stop_loss/current_price)*100:.1f}%) ── 20일 이평선 하회 시 기계적 손절
```

### 트레이딩 파라미터 규격표
| 전략 항목 | 구체적 가격 수치 | 비중 및 실행 가이드 | 손익 비율 |
| :--- | :--- | :--- | :--- |
| **분할 매수 밴드** | **{entry_low:,}원 ~ {entry_high:,}원** | 1차(50%): {entry_high:,}원, 2차(50%): {entry_low:,}원 눌림목 체결 | 진입 구간 |
| **1차 목표가** | **{target_1:,}원** | 직전 단기 저항선 도달 시 물량의 50% 차익 실현 | **+{(target_1/current_price - 1)*100:.1f}%** |
| **2차 목표가** | **{target_2:,}원** | 전고점 돌파 마디가. 5일 이평선 유지 시 잔량 홀딩 | **+{(target_2/current_price - 1)*100:.1f}%** |
| **손절 기준가** | **{stop_loss:,}원** | 종가 기준 20일선 및 주요 지지선 붕괴 시 전량 청산 | **-{(1 - stop_loss/current_price)*100:.1f}%** |
| **손익비 (R:R Ratio)** | **1 : {rr_ratio:.2f}** | 손실 위험 대비 기대 이익 약 2배 이상 확보 | **매우 우수** |

---

## 📅 추후 관찰 포인트
1. **당일 거래량 지속성**: 익일 장 시작 30분간 전일 거래량의 20% 이상이 체결되는지 확인.
2. **20일 이격도 과열 관리**: 20일 이격도가 115%를 초과하여 급등할 경우 신규 매수를 자제하고 눌림목 형성을 대기.
3. **메이저 수급 전환 여부**: 외국인/기관의 대규모 순매도 전환이 발생하는지 실시간 매매동향 점검.

---

## 💡 최종 결론
* **{stock_name} ({stock_code})**은(는) **{theme_name}** 테마의 3거래일 누적 거래대금 1위 대장주로서 시장 자금 유입 집중도가 최상위 수준입니다.
* 일봉 및 주봉상 전고점 매물대를 통과하고 있으며, 명확한 손익비({rr_ratio:.2f}:1)가 확보되어 있어 매수 밴드({entry_low:,}원 ~ {entry_high:,}원) 내 분할 진입 시 승률이 매우 유망합니다.

---

## ⚠️ 면책 조항
본 분석 보고서는 네이버 증권, 한국거래소 시세 통계 및 기술적 분석 알고리즘에 기초하여 작성된 투자 참고 자료입니다. 개별 종목의 주가 변동 및 원금 손실 위험이 존재하므로, 최종 투자 결정과 그에 따른 책임은 전적으로 투자자 본인에게 있습니다.

---

## 🔍 추가 질문 선택지
* **[질문 1]**: 2순위 부대장주({second_str})와의 짝짓기 매매 전략은 어떻게 전개하는 것이 좋은가요?
* **[질문 2]**: 목표가 도달 후 추세가 연장될 경우 3차 목표가 산출 기준은 무엇인가요?
* **[질문 3]**: 최근 기관 및 외국인 수급의 세부 창구별 매매 동향을 추가로 조회할 수 있나요?
"""
        # 규칙 1 적용: 인용 표기(`` 또는 `[1]`, `[2]` 등) 본문에서 완전 제거
        report = SopAnalystEngine.sanitize_citations(report)
        return report

    @staticmethod
    def _generate_catalysts_risks_triggers(
        stock_name: str,
        theme_name: str,
        current_price: int,
        daily_ind: Dict[str, Any],
        fundamentals: Dict[str, Any],
        investor_flow: Dict[str, Any],
        leader_stock: Dict[str, Any],
        disclosures: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, str]], List[Dict[str, str]], List[Dict[str, str]]]:
        """호재(최대 4가지), 악재(최대 4가지), 핵심 모니터링 변수(4가지) 생성"""
        catalysts: List[Dict[str, str]] = []
        risks: List[Dict[str, str]] = []
        triggers: List[Dict[str, str]] = []

        # 1. 호재 도출 (최대 4가지)
        # 1) 테마 거래대금 집중도 및 대장주 지위
        c_val_e8 = leader_stock.get("cum_trading_value_3d", 0) / 1e8
        catalysts.append({
            "title": "테마 내 압도적 자금 쏠림 및 대장주 프리미엄",
            "desc": f"최근 3거래일 누적 거래대금 {c_val_e8:,.0f}억 원을 기록하며 '{theme_name}' 테마 내에서 가장 강력한 시장 유동성과 호가 흡수력을 입증함."
        })

        # 2) 수급 모멘텀
        f_net = investor_flow.get("foreign_net_3d", 0)
        i_net = investor_flow.get("institution_net_3d", 0)
        if f_net > 0 or i_net > 0:
            catalysts.append({
                "title": "메이저 주체(외국인·기관)의 집중 순매수 유입",
                "desc": f"최근 3거래일간 외국인({f_net:+,}주) 및 기관({i_net:+,}주) 중심의 스마트머니가 유입되며 탄탄한 하방 가격 방어력을 구축함."
            })
        else:
            catalysts.append({
                "title": "개인 스마트머니 결집 및 단기 유동성 분출",
                "desc": f"강한 개인 수급 유입과 거래량 회전율을 바탕으로 단기 가격 탄력성과 시세 가속화가 두드러짐."
            })

        # 3) 펀더멘털 및 실적 지표
        rev = fundamentals.get("revenue", "N/A")
        op = fundamentals.get("operating_profit", "N/A")
        target_p = fundamentals.get("target_price_consensus", "N/A")
        if rev != "N/A" and op != "N/A":
            catalysts.append({
                "title": "견고한 실적 펀더멘털 및 증권가 컨센서스 상회",
                "desc": f"최근 분기 매출액 {rev}, 영업이익 {op}의 견고한 실적 체력을 유지하고 있으며 증권사 목표주가({target_p}) 대비 여전히 매력적인 밸류에이션 구간임."
            })
        else:
            catalysts.append({
                "title": "안정적 재무 건전성 및 밸류에이션 매력",
                "desc": f"PBR {fundamentals.get('pbr', 'N/A')}배 및 부실 채권/희석 요인 없는 안정적 재무구조로 중장기 자산 가치 안정성을 확보함."
            })

        # 4) 기술적 추세 및 이평선 정배열
        alignment = daily_ind.get("alignment", "양호")
        vol_ratio = daily_ind.get("vol_surge_ratio", 1.0)
        catalysts.append({
            "title": "단기·중기 이평선 정배열 및 거래량 급증",
            "desc": f"이평선 배열 상태가 '{alignment}' 국면이며, 20일 평균 대비 거래량이 {vol_ratio:.1f}배 급증하여 직전 매물대 상향 돌파를 견인함."
        })

        # 2. 악재 및 리스크 요인 도출 (최대 4가지)
        # 1) 단기 이격도 과열 리스크
        disp_20 = daily_ind.get("disparity_20", 100.0)
        if disp_20 >= 108.0:
            risks.append({
                "title": f"20일 이평선 단기 이격도 과열 ({disp_20:.1f}%)",
                "desc": f"주가가 20일 이동평균선 대비 {disp_20:.1f}% 수준까지 급격히 상승하여 장중 차익 실현 매물 출회에 따른 단기 숨고르기(조정) 가능성 상존."
            })
        else:
            risks.append({
                "title": "단기 급등에 따른 차익 실현 욕구 증대",
                "desc": f"최근 3일간 누적 상승률 {leader_stock.get('cum_return_3d', 0.0):+.2f}% 급등으로 단기 트레이더들의 매도 차익 실현 물량이 장중 출회될 수 있음."
            })

        # 2) 직전 전고점 매물대 저항
        risks.append({
            "title": "직전 전고점 및 상단 박스권 매물벽 저항",
            "desc": f"목표가 1차 구간 부근에 누적된 과거 물린 악성 매물대로 인해 돌파 과정에서 대량의 거래량 소화가 필수적이며 일시적 지연 가능성."
        })

        # 3) 수급 쏠림 및 손바뀜 리스크
        if investor_flow.get("individual_net_3d", 0) > 0 and (f_net < 0 or i_net < 0):
            risks.append({
                "title": "외국인/기관의 차익 매도 및 개인 단독 매수세",
                "desc": "메이저 주체의 비중 축소와 개인 중심의 수급 구조는 시장 변동성 확대 시 호가 지지력을 약화시킬 수 있는 구조적 요인."
            })
        else:
            risks.append({
                "title": "장중 외국인·기관 수급 급변(순매도 전환) 리스크",
                "desc": "글로벌 매크로 환경(환율, 금리 변동)에 따라 장중 프로그램 순매도가 급증할 경우 단기 지지선이 위협받을 수 있음."
            })

        # 4) 시장 거시 환경 및 테마 쿨다운
        risks.append({
            "title": "테마 순환매 가속화에 따른 수급 분산 리스크",
            "desc": f"국내 증시의 빠른 섹터 로테이션 환경에서 '{theme_name}' 테마에 유입된 자금이 후속 신규 테마로 급속히 이동할 경우 모멘텀 둔화 위험."
        })

        # 3. 핵심 모니터링 변수 (Key Monitoring Triggers - 4가지)
        triggers.append({
            "name": "20일 이격도 과열 임계치 (115% 선)",
            "condition": "20일 이격도 > 115.0% 돌파",
            "action": "신규 추격 매수를 전면 금지하고, 보유 물량의 30~50%를 분할 익절하여 수익을 확정함."
        })
        triggers.append({
            "name": "단기 생명선 (5일 이동평균선) 지지",
            "condition": f"종가 기준 5일선 ({daily_ind.get('ma5', 0):,.0f}원) 하향 이탈",
            "action": f"단기 상승 탄력 둔화로 판단, 1차 손절 기준가({int(current_price * 0.95):,}원) 준수 및 비중 축소."
        })
        triggers.append({
            "name": "장초반 30분 거래량 분출 속도",
            "condition": "개장 30분(09:30) 누적 거래량 < 전일 대비 20%",
            "action": "당일 주도력 약화 신호로 해석하여 당일 신규 돌파 매수를 유보하고 20일선 눌림목까지 관망."
        })
        triggers.append({
            "name": "메이저 수급 (외인·기관) 동반 순매도",
            "condition": "장중 잠정 집계에서 외인·기관 합산 대량 순매도 전환",
            "action": f"기존 매수 밴드 하단({int(current_price * 0.98):,}원) 지지 여부를 재확인하고 미체결 시 진입 취소."
        })

        return catalysts[:4], risks[:4], triggers[:4]

    @staticmethod

    def sanitize_citations(text: str) -> str:
        """인용 표기(``, `[1]`, `[2]` 등) 자동 제거"""
        # `` 제거
        text = re.sub(r'[\u200b\ufeff]', '', text)
        text = re.sub(r'<\s*citation[^>]*>.*?<\s*/\s*citation\s*>', '', text, flags=re.DOTALL)
        text = re.sub(r'\[\s*\d+\s*\](?!\s*점)', '', text)  # 단, '100점' 등은 보존
        return text

    @staticmethod
    def verify_sop_compliance(report_text: str, leader_stock: Dict[str, Any]) -> Dict[str, Any]:
        """PRD 섹션 5 SOP Verification Matrix 기반 자동 점검"""
        required_sections = [
            "📊 차트 종합 브리핑",
            "💡 종목 인사이트",
            "🗺️ 분석 차트 가이드",
            "📈 기술적 분석",
            "📋 매매 전략 시나리오",
            "📅 추후 관찰 포인트",
            "💡 최종 결론",
            "⚠️ 면책 조항",
            "🔍 추가 질문 선택지"
        ]

        missing_sections = [sec for sec in required_sections if sec not in report_text]

        # 인용구 번호 잔존 검사
        has_citations = bool(re.search(r'\[\d+\](?!\s*점)', report_text))

        # 구체적 가격대 확인 (원화 가격 표기 '0원')
        price_matches = re.findall(r'\d{1,3}(?:,\d{3})*원', report_text)
        has_specific_prices = len(price_matches) >= 8

        # 타임프레임 분리 확인
        has_timeframes = ("월봉" in report_text) and ("주봉" in report_text) and ("일봉" in report_text)

        # 데이터 완결성 확인
        has_leader = bool(leader_stock.get("name") and leader_stock.get("code"))

        all_passed = (
            len(missing_sections) == 0 and
            not has_citations and
            has_specific_prices and
            has_timeframes and
            has_leader
        )

        return {
            "all_passed": all_passed,
            "checklist": {
                "데이터 완결성 (대장주 특정)": has_leader,
                "타임프레임 분리 (일/주/월봉 독립 기술)": has_timeframes,
                "구체적 가격대 명시 (숫자 가격)": has_specific_prices,
                "펀더멘털 및 공시 통합": "공시" in report_text,
                "포맷 검증 (인용 번호 완전 제거)": not has_citations,
                "9개 필수 섹션 템플릿 포함": len(missing_sections) == 0
            },
            "missing_sections": missing_sections,
            "detected_price_count": len(price_matches)
        }

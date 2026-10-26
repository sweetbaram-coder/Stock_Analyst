"""src/screener/screener.py — 테마 주도주 스크리닝 및 Leader Score 랭킹 엔진
PRD F-01 기능 요구사항 완벽 반영:
- 3거래일 누적 거래대금/거래량/상승률 집계
- 필터링 기준: 거래대금 500억(중소형 200억), 3일상승률 >= 15%, 시총 500억 이하 및 정지 종목 제외
- Leader Score = 0.45 * 거래대금 점수 + 0.35 * 3일 상승률 점수 + 0.20 * 신고가 근접도 점수
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class ThemeLeaderScreener:
    """주도 테마 및 대장주 발굴 스크리너"""

    def __init__(self,
                 min_trading_value_large: int = 50_000_000_000,   # 500억 원
                 min_trading_value_small: int = 20_000_000_000,   # 200억 원
                 min_cum_return: float = 15.0,                    # 15% 이상
                 min_market_cap: int = 50_000_000_000,            # 500억 원 이상
                 min_price: int = 1000):                          # 동전주 제외 (1,000원 이상)
        self.min_trading_value_large = min_trading_value_large
        self.min_trading_value_small = min_trading_value_small
        self.min_cum_return = min_cum_return
        self.min_market_cap = min_market_cap
        self.min_price = min_price

    def filter_basic(self, stock: Dict[str, Any]) -> Tuple[bool, str]:
        """기본 종목 필터링 (거래정지, 시가총액, 동전주)"""
        # 거래정지 여부
        if not stock.get("is_trading", True) or not stock.get("is_tradable", True):
            return False, "거래정지 또는 비거래 상태"

        # 동전주 필터링
        price = stock.get("close_price", 0)
        if price < self.min_price:
            return False, f"동전주 제외 (현재가 {price}원 < {self.min_price}원)"

        # 시가총액 500억 이하 제외
        market_cap = stock.get("market_cap", 0)
        if 0 < market_cap < self.min_market_cap:
            return False, f"시가총액 500억 이하 제외 ({market_cap / 1e8:.0f}억)"

        return True, "통과"

    def calculate_3day_stats(self, daily_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        r"""최근 3거래일 누적 통계 계산 ($T-2 \sim T$)"""
        if not daily_history or len(daily_history) < 3:
            return {
                "valid": False,
                "cum_return_3d": 0.0,
                "cum_trading_value_3d": 0,
                "high_120d": 0,
                "high_proximity": 0.0
            }

        # 최근 3거래일 추출 (history는 최신 날짜가 0번째 인덱스)
        recent_3 = daily_history[:3]

        # 3일 누적 거래대금 합산
        cum_value = sum(item.get("est_trade_value", 0) for item in recent_3)

        # 3일 누적 수익률: (T일 종가 - T-3일 종가) / T-3일 종가 또는 일별 등락률 복리/단리
        t0_close = recent_3[0].get("close", 0)
        t2_close = recent_3[-1].get("close", 0)

        # 4번째가 있으면 3거래일 전 종가 기준
        if len(daily_history) >= 4:
            base_close = daily_history[3].get("close", 1)
        else:
            base_close = recent_3[-1].get("open", 1)

        cum_return = ((t0_close - base_close) / base_close) * 100 if base_close > 0 else 0.0

        # 신고가 근접도 계산 (전체 히스토리 중 최고가 대비 현재가)
        all_highs = [h.get("high", 0) for h in daily_history]
        highest_price = max(all_highs) if all_highs else t0_close
        high_proximity = (t0_close / highest_price * 100.0) if highest_price > 0 else 0.0

        return {
            "valid": True,
            "cum_return_3d": round(cum_return, 2),
            "cum_trading_value_3d": cum_value,
            "high_120d": highest_price,
            "high_proximity": round(high_proximity, 2)
        }

    def evaluate_candidates(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """후보군 대상 Leader Score 산출 및 정렬"""
        if not candidates:
            return []

        # 1. 거래대금 정규화 점수 (0~100점)
        values = [c["cum_trading_value_3d"] for c in candidates]
        max_val = max(values) if values else 1
        min_val = min(values) if values else 0
        range_val = max_val - min_val if max_val != min_val else 1

        # 2. 3일 상승률 정규화 점수 (0~100점)
        returns = [c["cum_return_3d"] for c in candidates]
        max_ret = max(returns) if returns else 1
        min_ret = min(returns) if returns else 0
        range_ret = max_ret - min_ret if max_ret != min_ret else 1

        scored = []
        for c in candidates:
            # 거래대금 점수
            v_score = ((c["cum_trading_value_3d"] - min_val) / range_val) * 100.0
            # 수익률 점수
            r_score = ((c["cum_return_3d"] - min_ret) / range_ret) * 100.0
            # 신고가 근접도 점수 (이미 0~100 scale)
            h_score = min(c.get("high_proximity", 0.0), 100.0)

            # Leader Score 공식:
            # 0.45 * 거래대금 순위/점수 + 0.35 * 3일 상승률 + 0.20 * 신고가 근접도
            leader_score = (0.45 * v_score) + (0.35 * r_score) + (0.20 * h_score)

            item = dict(c)
            item["score_trading_value"] = round(v_score, 1)
            item["score_return"] = round(r_score, 1)
            item["score_high_proximity"] = round(h_score, 1)
            item["leader_score"] = round(leader_score, 2)
            scored.append(item)

        # Leader Score 내림차순 정렬
        scored.sort(key=lambda x: x["leader_score"], reverse=True)
        return scored

    def rank_themes(self, theme_list: List[Dict[str, Any]], candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """후보군 종목 집계 및 테마별 주도력 점수 계산"""
        # 테마별 후보 종목 매핑
        theme_candidates_map = {}
        for c in candidates:
            t_name = c["theme_name"]
            theme_candidates_map.setdefault(t_name, []).append(c)

        ranked = []
        for t in theme_list:
            t_name = t["theme_name"]
            t_stocks = theme_candidates_map.get(t_name, [])

            # 테마 주도 점수: 테마 등락률(40%) + 후보종목 합산 거래대금(30%) + 최고 Leader Score(30%)
            top_leader_score = t_stocks[0]["leader_score"] if t_stocks else 0.0
            total_theme_val = sum(s["cum_trading_value_3d"] for s in t_stocks)

            t_score = (t["change_rate"] * 2.0) + (top_leader_score * 0.5)

            ranked.append({
                "theme_no": t["theme_no"],
                "theme_name": t_name,
                "change_rate": t["change_rate"],
                "total_count": t["total_count"],
                "rise_count": t["rise_count"],
                "candidate_count": len(t_stocks),
                "total_trading_value_3d": total_theme_val,
                "top_leader_score": top_leader_score,
                "theme_score": round(t_score, 2),
                "top_stock": t_stocks[0]["name"] if t_stocks else "N/A",
                "top_stock_code": t_stocks[0]["code"] if t_stocks else ""
            })

        ranked.sort(key=lambda x: (x["candidate_count"] > 0, x["theme_score"]), reverse=True)
        return ranked

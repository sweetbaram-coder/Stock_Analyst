"""src/pipeline/indicators.py — 멀티 타임프레임 기술적 분석 지표 계산 엔진
PRD F-02 기능 요구사항 반영:
- 이동평균선: MA5, MA20, MA60, MA120 (정배열/역배열, 이격도)
- 거래량 이동평균선: VMA5, VMA20 및 거래량 급증 배수
- RSI (14)
- MACD (12, 26, 9) 및 시그널, 오실레이터
- 멀티 타임프레임(일봉, 주봉, 월봉) 지표 일괄 산출
"""
import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

class TechnicalIndicatorEngine:
    """캔들 데이터로부터 기술적 지표를 계산하는 엔진"""

    @staticmethod
    def calculate_indicators(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """단일 타임프레임(예: 120개 캔들)에 대한 기술적 지표 계산"""
        if not candles or len(candles) < 20:
            return {"error": "캔들 데이터 부족"}

        df = pd.DataFrame(candles)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.sort_values("date").reset_index(drop=True)

        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        close = df["close"]
        volume = df["volume"]

        # 1. 이동평균선 (5, 20, 60, 120)
        df["ma5"] = close.rolling(window=5).mean()
        df["ma20"] = close.rolling(window=20).mean()
        df["ma60"] = close.rolling(window=60).mean()
        df["ma120"] = close.rolling(window=120).mean()

        # 거래량 이동평균선 (5, 20)
        df["vma5"] = volume.rolling(window=5).mean()
        df["vma20"] = volume.rolling(window=20).mean()

        # 2. RSI (14)
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=13, adjust=False).mean()
        avg_loss = loss.ewm(com=13, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df["rsi14"] = 100 - (100 / (1 + rs))

        # 3. MACD (12, 26, 9)
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        df["macd"] = ema12 - ema26
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_osc"] = df["macd"] - df["macd_signal"]

        # 4. 볼린저 밴드 (20, 2)
        std20 = close.rolling(window=20).std()
        df["bb_upper"] = df["ma20"] + (std20 * 2)
        df["bb_lower"] = df["ma20"] - (std20 * 2)

        # 최신 캔들(가장 최근 데이터) 요약 추출
        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else last

        # 정배열/역배열 판정
        c_price = last["close"]
        m5 = last["ma5"]
        m20 = last["ma20"]
        m60 = last["ma60"]
        m120 = last["ma120"]

        alignment = "혼조세"
        if pd.notna(m5) and pd.notna(m20) and pd.notna(m60):
            if pd.notna(m120):
                if m5 > m20 > m60 > m120:
                    alignment = "완전 정배열 (강한 상승세)"
                elif m5 < m20 < m60 < m120:
                    alignment = "완전 역배열 (강한 하락세)"
                elif m5 > m20 > m60:
                    alignment = "중단기 정배열 (상승 전환)"
            elif m5 > m20 > m60:
                alignment = "단기 정배열 (상승 추세)"

        # 20일 이격도 (Disparity)
        disparity_20 = ((c_price / m20) * 100.0) if pd.notna(m20) and m20 > 0 else 100.0

        # 거래량 증가율 (전일 대비 및 20일 평균 대비)
        vol_surge_ratio = (last["volume"] / last["vma20"]) if pd.notna(last["vma20"]) and last["vma20"] > 0 else 1.0

        # MACD 골든크로스/데드크로스 여부
        macd_cross = "중립"
        if prev["macd"] <= prev["macd_signal"] and last["macd"] > last["macd_signal"]:
            macd_cross = "골든크로스 발생 (매수 시그널)"
        elif prev["macd"] >= prev["macd_signal"] and last["macd"] < last["macd_signal"]:
            macd_cross = "데드크로스 발생 (매도 시그널)"

        return {
            "latest_date": str(last["date"].date()) if pd.notna(last["date"]) else "",
            "close": float(c_price),
            "open": float(last["open"]),
            "high": float(last["high"]),
            "low": float(last["low"]),
            "volume": int(last["volume"]),
            "ma5": round(float(m5), 2) if pd.notna(m5) else None,
            "ma20": round(float(m20), 2) if pd.notna(m20) else None,
            "ma60": round(float(m60), 2) if pd.notna(m60) else None,
            "ma120": round(float(m120), 2) if pd.notna(m120) else None,
            "alignment": alignment,
            "disparity_20": round(float(disparity_20), 2),
            "rsi14": round(float(last["rsi14"]), 2) if pd.notna(last["rsi14"]) else None,
            "macd": round(float(last["macd"]), 2) if pd.notna(last["macd"]) else None,
            "macd_signal": round(float(last["macd_signal"]), 2) if pd.notna(last["macd_signal"]) else None,
            "macd_osc": round(float(last["macd_osc"]), 2) if pd.notna(last["macd_osc"]) else None,
            "macd_cross": macd_cross,
            "bb_upper": round(float(last["bb_upper"]), 2) if pd.notna(last["bb_upper"]) else None,
            "bb_lower": round(float(last["bb_lower"]), 2) if pd.notna(last["bb_lower"]) else None,
            "vol_surge_ratio": round(float(vol_surge_ratio), 2),
            "series_df": df
        }

    @classmethod
    def compute_multi_timeframe(cls, daily_candles: List[Dict[str, Any]],
                                weekly_candles: List[Dict[str, Any]],
                                monthly_candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """멀티 타임프레임(일/주/월) 종합 지표 분석"""
        daily_res = cls.calculate_indicators(daily_candles)
        weekly_res = cls.calculate_indicators(weekly_candles)
        monthly_res = cls.calculate_indicators(monthly_candles)

        return {
            "daily": daily_res,
            "weekly": weekly_res,
            "monthly": monthly_res
        }

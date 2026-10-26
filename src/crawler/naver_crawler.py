"""src/crawler/naver_crawler.py — 네이버 증권 테마 및 종목 시세 크롤러
참고자료의 web-crawler 패턴을 완벽히 적용:
- RateLimiter를 통한 Polite Crawling
- Softblock 감지 및 에러 회복
- 테마 목록, 테마별 종목, 일별 시세, 멀티 타임프레임(일/주/월) OHLCV 차트 데이터 수집
"""
import logging
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
import requests

from .utils import RateLimiter, detect_softblock, validate_values

logger = logging.getLogger(__name__)

class NaverStockCrawler:
    """네이버 증권 테마 및 종목 데이터 수집 엔진"""

    BASE_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(self, delay: float = 0.5):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.BASE_USER_AGENT,
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        })
        self.limiter = RateLimiter(delay=delay)

    def fetch_theme_list(self, max_pages: int = 3, page_size: int = 20) -> List[Dict[str, Any]]:
        """등락률 상위 테마 목록 수집"""
        themes = []
        for page in range(1, max_pages + 1):
            self.limiter.wait()
            url = f"https://m.stock.naver.com/api/stocks/theme?page={page}&pageSize={page_size}"
            try:
                res = self.session.get(url, timeout=10)
                softblock = detect_softblock(res.text, status=res.status_code)
                if softblock["blocked"]:
                    logger.warning(f"테마 목록 수집 중 블록 감지: {softblock}")
                    self.limiter.backoff()
                    continue

                self.limiter.reset_errors()
                data = res.json()
                groups = data.get("groups", [])
                if not groups:
                    break

                for g in groups:
                    themes.append({
                        "theme_no": g.get("no"),
                        "theme_name": g.get("name"),
                        "change_rate": float(g.get("changeRate", 0.0)),
                        "total_count": int(g.get("totalCount", 0)),
                        "rise_count": int(g.get("riseCount", 0)),
                        "fall_count": int(g.get("fallCount", 0)),
                        "steady_count": int(g.get("steadyCount", 0)),
                    })
            except Exception as e:
                logger.error(f"테마 목록 페이지 {page} 수집 에러: {e}")
                self.limiter.backoff()

        logger.info(f"총 {len(themes)}개 테마 정보 수집 완료")
        return themes

    def fetch_theme_stocks(self, theme_no: int, max_stocks: int = 50) -> List[Dict[str, Any]]:
        """특정 테마에 속한 종목 상세 시세 수집"""
        self.limiter.wait()
        url = f"https://m.stock.naver.com/api/stocks/theme/{theme_no}?page=1&pageSize={max_stocks}"
        stocks = []
        try:
            res = self.session.get(url, timeout=10)
            softblock = detect_softblock(res.text, status=res.status_code)
            if softblock["blocked"]:
                logger.warning(f"테마({theme_no}) 종목 수집 중 블록 감지: {softblock}")
                return stocks

            self.limiter.reset_errors()
            data = res.json()
            raw_stocks = data.get("stocks", [])
            group_info = data.get("groupInfo", {})
            theme_name = group_info.get("name", "")

            for s in raw_stocks:
                # 숫자 원시값(Raw) 정제
                close_price = int(s.get("closePriceRaw", 0) or 0)
                trading_value = int(s.get("accumulatedTradingValueRaw", 0) or 0)
                trading_vol = int(s.get("accumulatedTradingVolumeRaw", 0) or 0)
                market_cap = int(s.get("marketValueRaw", 0) or 0)
                change_rate = float(s.get("fluctuationsRatio", 0.0) or 0.0)

                # 거래정지 / 매매가능 여부
                trade_stop = s.get("tradeStopType", {}).get("name", "")
                tradable = s.get("tradableStatus", "")

                stocks.append({
                    "theme_no": theme_no,
                    "theme_name": theme_name,
                    "code": s.get("itemCode", ""),
                    "name": s.get("stockName", ""),
                    "market": s.get("stockExchangeType", {}).get("nameKor", ""),
                    "close_price": close_price,
                    "change_rate": change_rate,
                    "trading_volume": trading_vol,
                    "trading_value": trading_value,  # 원 단위
                    "market_cap": market_cap,        # 원 단위
                    "is_trading": trade_stop == "TRADING",
                    "is_tradable": tradable == "tradable",
                })
        except Exception as e:
            logger.error(f"테마({theme_no}) 종목 수집 에러: {e}")
            self.limiter.backoff()

        return stocks

    def fetch_daily_price_history(self, code: str, count: int = 10) -> List[Dict[str, Any]]:
        """종목의 최근 N거래일 일별 시세 수집 (최근 3거래일 등락/거래대금 계산용)"""
        self.limiter.wait()
        url = f"https://m.stock.naver.com/api/stock/{code}/price?count={count}"
        history = []
        try:
            res = self.session.get(url, timeout=10)
            if res.status_code == 200:
                self.limiter.reset_errors()
                data = res.json()
                for item in data:
                    close_val = int(str(item.get("closePrice", "0")).replace(",", ""))
                    open_val = int(str(item.get("openPrice", "0")).replace(",", ""))
                    high_val = int(str(item.get("highPrice", "0")).replace(",", ""))
                    low_val = int(str(item.get("lowPrice", "0")).replace(",", ""))
                    vol = int(item.get("accumulatedTradingVolume", 0) or 0)
                    rate = float(item.get("fluctuationsRatio", 0.0) or 0.0)
                    date_str = item.get("localTradedAt", "")

                    # 대략적인 당일 거래대금 추정 (종가 * 거래량 또는 평균가 * 거래량)
                    est_trade_value = close_val * vol

                    history.append({
                        "date": date_str,
                        "open": open_val,
                        "high": high_val,
                        "low": low_val,
                        "close": close_val,
                        "volume": vol,
                        "change_rate": rate,
                        "est_trade_value": est_trade_value,
                    })
        except Exception as e:
            logger.error(f"종목({code}) 일별시세 수집 에러: {e}")
            self.limiter.backoff()

        return history

    def fetch_candle_chart(self, code: str, timeframe: str = "day", count: int = 120) -> List[Dict[str, Any]]:
        """fchart API를 통한 멀티 타임프레임(day/week/month) 120개 캔들 OHLCV 수집

        Args:
            code: 6자리 종목코드
            timeframe: 'day' | 'week' | 'month'
            count: 캔들 수 (기본 120개)
        """
        self.limiter.wait()
        url = f"https://fchart.stock.naver.com/sise.nhn?symbol={code}&timeframe={timeframe}&count={count}&requestType=0"
        candles = []
        try:
            res = self.session.get(url, timeout=10)
            res.encoding = "euc-kr"
            if res.status_code == 200:
                self.limiter.reset_errors()
                root = ET.fromstring(res.text)
                for item in root.findall(".//item"):
                    raw = item.get("data", "")
                    # data 형식: "날짜|시가|고가|저가|종가|거래량"
                    parts = raw.split("|")
                    if len(parts) >= 6:
                        candles.append({
                            "date": parts[0],
                            "open": float(parts[1]),
                            "high": float(parts[2]),
                            "low": float(parts[3]),
                            "close": float(parts[4]),
                            "volume": float(parts[5]),
                        })
        except Exception as e:
            logger.error(f"종목({code}) {timeframe} 캔들 수집 에러: {e}")
            self.limiter.backoff()

        return candles

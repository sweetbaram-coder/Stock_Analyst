"""src/crawler/stock_resolver.py — 종목명 / 종목코드 자동 해석 및 정보 확인 모듈
- 사용자가 종목명(예: "삼성전자", "SK하이닉스") 또는 종목코드(예: "005930")를 입력했을 때
  표준 6자리 코드 및 공식 종목명, 현재가, 기본 시세를 정확히 반환
- 소속 주요 테마 역추적 지원
"""
import logging
import re
from typing import Any, Dict, Optional, Tuple
import requests

from .utils import RateLimiter, detect_softblock

logger = logging.getLogger(__name__)

class StockResolver:
    """종목명 ↔ 종목코드 해석기"""

    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def __init__(self, delay: float = 0.3):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.USER_AGENT})
        self.limiter = RateLimiter(delay=delay)

    def resolve(self, query: str) -> Optional[Dict[str, Any]]:
        """종목명 또는 종목코드를 받아 유효한 종목 기본 정보 딕셔너리 반환

        Returns:
            {
                "code": "005930",
                "name": "삼성전자",
                "close_price": 75000,
                "change_rate": 1.25,
                "market": "코스피",
                "is_trading": True,
                "is_tradable": True
            } or None
        """
        query = query.strip()
        if not query:
            return None

        # 1. 6자리 숫자인 경우 직접 코드 검증
        if re.fullmatch(r'\d{6}', query):
            return self.fetch_basic_by_code(query)

        # 2. 종목명인 경우 네이버 검색을 통한 코드 역추적
        code = self.search_code_by_name(query)
        if code:
            info = self.fetch_basic_by_code(code)
            if info:
                return info

        logger.error(f"종목을 찾을 수 없습니다: '{query}'")
        return None

    def search_code_by_name(self, name: str) -> Optional[str]:
        """종목명으로 네이버 검색을 통해 6자리 종목코드 추출"""
        self.limiter.wait()
        url = f"https://m.search.naver.com/search.naver?query={name}+주가"
        try:
            res = self.session.get(url, timeout=8)
            if res.status_code == 200:
                # m.stock.naver.com/domestic/stock/XXXXXX 또는 item/XXXXXX 패턴
                matches = re.findall(r'm\.stock\.naver\.com/(?:domestic/stock|item)/(\d{6})', res.text)
                if matches:
                    return matches[0]

                # 또는 6자리 코드 후보군 중 첫 번째
                raw_codes = re.findall(r'data-stock-code="(\d{6})"', res.text)
                if raw_codes:
                    return raw_codes[0]
        except Exception as e:
            logger.warning(f"종목명 검색 예외 ({name}): {e}")

        return None

    def fetch_basic_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """6자리 종목코드로 기본 시세 및 종목 정보 수집"""
        self.limiter.wait()
        url = f"https://m.stock.naver.com/api/stock/{code}/basic"
        try:
            res = self.session.get(url, timeout=8)
            if res.status_code == 200:
                data = res.json()
                stock_name = data.get("stockName", "")
                if not stock_name:
                    return None

                close_str = str(data.get("closePrice", "0")).replace(",", "")
                close_price = int(close_str) if close_str.isdigit() else 0
                change_rate = float(data.get("fluctuationsRatio", 0.0) or 0.0)

                market = data.get("stockExchangeName", "")
                trade_stop = data.get("tradeStopType", {}).get("name", "TRADING")
                tradable = data.get("tradableStatus", "tradable")

                return {
                    "code": code,
                    "name": stock_name,
                    "close_price": close_price,
                    "change_rate": change_rate,
                    "market": market,
                    "is_trading": trade_stop == "TRADING",
                    "is_tradable": tradable == "tradable",
                }
        except Exception as e:
            logger.error(f"종목 기본정보 수집 실패 ({code}): {e}")

        return None

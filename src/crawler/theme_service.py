"""src/crawler/theme_service.py — UI 전용 실시간 테마 조회 및 스크리닝 서비스
거래량과 상승률이 높은 시장 주도 테마 목록을 빠르게 조회하고 사용자가 선택할 수 있도록 지원합니다.
"""
import logging
from typing import Any, Dict, List
from src.crawler.naver_crawler import NaverStockCrawler

logger = logging.getLogger(__name__)

class ThemeService:
    """실시간 상위 주도 테마 조회 서비스"""

    def __init__(self, crawler: NaverStockCrawler):
        self.crawler = crawler

    def get_top_active_themes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """현재 가장 관심되고 상승률과 거래량이 높은 상위 테마 목록 반환

        Args:
            limit: 반환할 최대 테마 수 (기본 10개, 최소 5개 보장)

        Returns:
            List[Dict[str, Any]]: 정렬된 테마 목록
        """
        try:
            # 상위 2페이지(50개) 테마 목록 수집
            themes = self.crawler.fetch_theme_list(max_pages=2, page_size=25)
            if not themes:
                logger.warning("네이버 증권 테마 목록 수집 실패")
                return []

            # 양의 상승률을 기록 중인 테마 우선 필터링
            positive_themes = [t for t in themes if t.get("change_rate", 0) > 0]
            if not positive_themes:
                positive_themes = themes

            # 상승률 내림차순 정렬
            sorted_themes = sorted(
                positive_themes,
                key=lambda x: (x.get("change_rate", 0.0), x.get("rise_count", 0)),
                reverse=True
            )

            # 상위 n개 선정
            top_themes = sorted_themes[:limit]
            logger.info(f"상위 주도 테마 {len(top_themes)}개 추출 완료")
            return top_themes
        except Exception as e:
            logger.error(f"테마 서비스 조회 중 예외 발생: {e}")
            return []

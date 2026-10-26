"""src/crawler/utils.py — 웹 크롤링 및 데이터 수집 공통 유틸리티
참고자료(web-crawler)의 설계 패턴을 차용하여 구축:
- RateLimiter: 과도한 호출 방지 및 지수 백오프
- Softblock 감지: WAF, 캡차, 빈 응답 탐지
- PII 검사: 개인정보 보호
- Validate Values: 스키마 및 결측률 검증
"""
import json
import logging
import os
import re
import time
from urllib.parse import urlparse
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class BudgetExceeded(Exception):
    """요청 상한 초과 또는 서버 연속 거부 예외"""
    pass

class RateLimiter:
    """요청 간 대기 시간 제어 및 연속 에러 시 백오프"""
    MIN_DELAY = 0.3

    def __init__(self, delay: float = 0.5, min_delay: float = MIN_DELAY,
                 max_requests: Optional[int] = None, max_consecutive_errors: int = 5):
        self.min_delay = max(min_delay, 0.0)
        self.delay = max(delay, self.min_delay)
        self.max_requests = max_requests
        self.max_consecutive_errors = max_consecutive_errors
        self.request_count = 0
        self.consecutive_errors = 0
        self._last_request = 0.0

    def wait(self):
        """요청 전 필요한 만큼 대기"""
        if self.max_requests is not None and self.request_count >= self.max_requests:
            raise BudgetExceeded(f"총 요청 상한({self.max_requests}건)에 도달했습니다.")
        elapsed = time.time() - self._last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_request = time.time()
        self.request_count += 1

    def backoff(self):
        """연속 에러 시 대기시간 2배 증가"""
        self.consecutive_errors += 1
        if self.consecutive_errors >= self.max_consecutive_errors:
            raise BudgetExceeded(f"연속 {self.consecutive_errors}회 에러 응답으로 중단합니다.")
        self.delay = min(self.delay * 2, 10.0)

    def reset_errors(self):
        """요청 성공 시 에러 카운터 초기화"""
        self.consecutive_errors = 0

_SOFTBLOCK_MARKERS = (
    "sec-if-cpt-container",
    "access denied",
    "errors.edgesuite.net",
    "reference #",
    "pardon our interruption",
    "captcha-delivery.com",
    "just a moment...",
    "cf-browser-verification",
    "attention required",
    "verifying you are human",
    "enable javascript and cookies to continue",
)

def detect_softblock(text: str, status: int = 200, selector_hit: Optional[bool] = None) -> Dict[str, Any]:
    """HTTP 상태코드 및 본문 마커 분석을 통한 가짜 200(소프트블록) 판별"""
    text = text or ""
    low = text.lower()

    if status in (401, 403, 429):
        return {"blocked": True, "verdict": "blocked", "signals": [f"HTTP {status}"]}

    signals = []
    for marker in _SOFTBLOCK_MARKERS:
        if marker in low:
            signals.append(f"marker:{marker}")

    if signals:
        return {"blocked": True, "verdict": "challenge", "signals": signals}

    if selector_hit is False and len(text) < 1000:
        return {"blocked": True, "verdict": "empty_shell", "signals": ["low_content_no_selector"]}

    return {"blocked": False, "verdict": "ok", "signals": []}

_EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
_PHONE_PATTERN = re.compile(r'(?<!\d)(\d{2,4}[-.\s]\d{3,4}[-.\s]\d{4}|01\d{9})(?!\d)')

def detect_pii(data: List[Dict[str, Any]]) -> List[str]:
    """수집 데이터에서 개인식별정보(PII) 누출 감지"""
    warnings = []
    if not data:
        return warnings

    for i, item in enumerate(data[:50]):
        if not isinstance(item, dict):
            continue
        for field, value in item.items():
            if not isinstance(value, str):
                continue
            if _EMAIL_PATTERN.search(value):
                warnings.append(f"이메일 패턴 감지: 필드 '{field}' (행 {i+1})")
            if _PHONE_PATTERN.search(value):
                warnings.append(f"전화번호 패턴 감지: 필드 '{field}' (행 {i+1})")
    return warnings

def validate_values(data: List[Dict[str, Any]], rules: Dict[str, Dict[str, Any]]) -> List[str]:
    """수집된 데이터셋의 스키마 및 결측률 유효성 검증

    Args:
        data: 딕셔너리 리스트
        rules: 필드별 규칙 딕셔너리. 예:
            {
                "종목코드": {"type": "str", "required": True, "max_empty_ratio": 0.05},
                "현재가": {"type": "num", "required": True}
            }
    """
    issues = []
    if not data:
        return ["데이터셋이 비어 있습니다."]

    total = len(data)
    for field, rule in rules.items():
        req = rule.get("required", False)
        max_empty = rule.get("max_empty_ratio", 0.0)
        expected_type = rule.get("type", None)

        empty_count = 0
        type_mismatch = 0

        for row in data:
            val = row.get(field)
            if val is None or val == "" or val == "N/A":
                empty_count += 1
            else:
                if expected_type == "str" and not isinstance(val, str):
                    type_mismatch += 1
                elif expected_type == "num" and not isinstance(val, (int, float)):
                    # 숫자 변환 가능 여부 확인
                    try:
                        float(str(val).replace(",", ""))
                    except ValueError:
                        type_mismatch += 1

        empty_ratio = empty_count / total
        if req and empty_ratio > max_empty:
            issues.append(f"필드 '{field}' 결측률 초과: {empty_ratio:.1%} (허용치: {max_empty:.1%})")
        if type_mismatch > 0:
            issues.append(f"필드 '{field}' 타입 불일치 {type_mismatch}건")

    return issues

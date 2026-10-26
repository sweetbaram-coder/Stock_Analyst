"""src/pipeline/drive_storage.py — 구글 드라이브 연도별 자동 저장 모듈
사용자의 구글 드라이브 내 '120.주식종목분석' 폴더 아래 현재 연도별 서브폴더를 자동 생성하고
생성된 분석 보고서(Markdown, HTML, Excel)를 동기화 저장합니다.
"""
import os
import shutil
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class GoogleDriveStorage:
    """구글 드라이브 '120.주식종목분석' 연도별 자동 저장 관리자"""

    DEFAULT_DRIVE_CANDIDATES = [
        r"G:\내 드라이브\120.주식종목분석",
        r"G:\120.주식종목분석",
        r"F:\50.GoogleCloud\120.주식종목분석",
    ]

    def __init__(self, custom_base_path: Optional[str] = None):
        self.base_path = self._resolve_base_path(custom_base_path)
        logger.info(f"구글 드라이브 기준 저장 경로 설정: {self.base_path}")

    def _resolve_base_path(self, custom_path: Optional[str]) -> str:
        """구글 드라이브 기본 저장 경로 탐색 및 결정"""
        # 1. 인자로 전달된 커스텀 경로 확인
        if custom_path and os.path.exists(custom_path):
            return custom_path

        # 2. 환경 변수 확인
        env_path = os.environ.get("GOOGLE_DRIVE_STOCK_PATH")
        if env_path and os.path.exists(env_path):
            return env_path

        # 3. 사전 정의된 후보군 경로 확인
        for cand in self.DEFAULT_DRIVE_CANDIDATES:
            if os.path.exists(cand):
                return cand

        # 4. 후보군 중 첫 번째 경로 생성 시도
        first_candidate = self.DEFAULT_DRIVE_CANDIDATES[0]
        try:
            drive_root = os.path.splitdrive(first_candidate)[0]
            if os.path.exists(drive_root):
                os.makedirs(first_candidate, exist_ok=True)
                return first_candidate
        except Exception:
            pass

        # 5. 로컬 폴백 경로
        fallback = os.path.abspath(os.path.join("output", "GoogleDrive", "120.주식종목분석"))
        os.makedirs(fallback, exist_ok=True)
        return fallback

    def get_yearly_folder(self, year: Optional[str] = None) -> str:
        """현재 연도(예: 2026) 서브 폴더 경로 반환 및 생성"""
        if not year:
            year = datetime.now().strftime("%Y")
        yearly_path = os.path.join(self.base_path, str(year))
        os.makedirs(yearly_path, exist_ok=True)
        return yearly_path

    def get_target_folder(
        self,
        stock_name: str,
        year: Optional[str] = None,
        timestamp_str: Optional[str] = None
    ) -> str:
        """연도(예: 2026) 폴더 아래 '년월일시_종목명' 구조의 서브 폴더 경로 반환 및 생성

        예시:
            G:\\내 드라이브\\120.주식종목분석\\2026\\20261019_0006_삼성전자
        """
        yearly_dir = self.get_yearly_folder(year)

        if not timestamp_str:
            # 년월일시_분 포맷 (실행 시점 완벽 보존 및 동일 시간대 덮어쓰기 방지)
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M")

        # 폴더명 규격: 년월일시_종목명 (예: 20261019_0006_삼성전자)
        folder_name = f"{timestamp_str}_{stock_name}"
        target_dir = os.path.join(yearly_dir, folder_name)
        os.makedirs(target_dir, exist_ok=True)
        return target_dir

    def save_analysis_results(
        self,
        stock_name: str,
        stock_code: str,
        report_md: str,
        report_html: Optional[str] = None,
        excel_source_path: Optional[str] = None,
        date_str: Optional[str] = None,
        timestamp_str: Optional[str] = None
    ) -> Dict[str, str]:
        """분석 결과 파일 3종(MD, HTML, XLSX)을 구글드라이브 '{연도}/{년월일시_종목명}/' 폴더에 저장

        Returns:
            Dict[str, str]: 저장된 파일들의 절대 경로 맵
        """
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        year_str = date_str[:4]

        # 연도 폴더 아래 '년월일시_종목명' 서브폴더 생성
        dest_dir = self.get_target_folder(
            stock_name=stock_name,
            year=year_str,
            timestamp_str=timestamp_str
        )

        saved_files = {
            "dest_dir": dest_dir,
            "md_path": "",
            "html_path": "",
            "excel_path": ""
        }

        # 1. Markdown 보고서 저장
        md_filename = f"[주도주 분석보고서] {stock_name}({stock_code}) - {date_str}.md"
        md_dest = os.path.join(dest_dir, md_filename)
        with open(md_dest, "w", encoding="utf-8") as f:
            f.write(report_md)
        saved_files["md_path"] = md_dest
        logger.info(f"구글 드라이브 마크다운 저장: {md_dest}")

        # 2. Styled HTML 보고서 저장
        if report_html:
            html_filename = f"[주도주 분석보고서] {stock_name}({stock_code}) - {date_str}.html"
            html_dest = os.path.join(dest_dir, html_filename)
            with open(html_dest, "w", encoding="utf-8") as f:
                f.write(report_html)
            saved_files["html_path"] = html_dest
            logger.info(f"구글 드라이브 HTML 저장: {html_dest}")

        # 3. Excel 데이터 복사/저장
        if excel_source_path and os.path.exists(excel_source_path):
            excel_filename = f"[주식분석] {stock_name}({stock_code}) - {date_str}.xlsx"
            excel_dest = os.path.join(dest_dir, excel_filename)
            shutil.copy2(excel_source_path, excel_dest)
            saved_files["excel_path"] = excel_dest
            logger.info(f"구글 드라이브 엑셀 저장: {excel_dest}")

        return saved_files

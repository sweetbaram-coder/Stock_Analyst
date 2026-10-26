"""src/pipeline/gdocs_exporter.py — Google Docs 및 완성형 문서 내보내기 엔진
PRD F-04 및 Step 4 요구사항 반영:
- 문서 제목 규격: [주도주 분석보고서] {종목명}({종목코드}) - {분석일자 YYYY-MM-DD}
- Google Docs API 연동 지원 (OAuth 및 서비스 계정 지원)
- Styled HTML: Google Docs 복사/붙여넣기 및 브라우저 열람에 최적화된 레이아웃
"""
import os
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

class DocumentExporter:
    """분석 보고서 파일 저장 및 Google Docs 연동 내보내기"""

    @staticmethod
    def generate_doc_title(stock_name: str, stock_code: str, date_str: Optional[str] = None) -> str:
        """PRD F-04 규격 문서 제목 생성: [주도주 분석보고서] {종목명}({종목코드}) - {분석일자 YYYY-MM-DD}"""
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        return f"[주도주 분석보고서] {stock_name}({stock_code}) - {date_str}"

    @staticmethod
    def export_markdown(content: str, filepath: str) -> str:
        """마크다운 파일로 저장"""
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Markdown 보고서 저장 완료: {filepath}")
        return filepath

    @staticmethod
    def export_styled_html(content: str, filepath: str, title: str = "주도주 분석보고서") -> str:
        """Google Docs 붙여넣기 및 브라우저 열람에 최적화된 Styled HTML 생성"""
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

        lines = content.split("\n")
        html_lines = []
        in_table = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("# "):
                html_lines.append(f"<h1 style='color:#1a365d; font-size:24px; border-bottom:2px solid #2b6cb0; padding-bottom:8px; margin-top:20px;'>{stripped[2:]}</h1>")
            elif stripped.startswith("## "):
                html_lines.append(f"<h2 style='color:#2b6cb0; font-size:18px; margin-top:24px; border-bottom:1px solid #cbd5e0; padding-bottom:6px;'>{stripped[3:]}</h2>")
            elif stripped.startswith("### "):
                html_lines.append(f"<h3 style='color:#2d3748; font-size:15px; margin-top:16px; margin-bottom:6px;'>{stripped[4:]}</h3>")
            elif stripped.startswith("|") and stripped.endswith("|"):
                if not in_table:
                    html_lines.append("<table style='border-collapse:collapse; width:100%; margin:16px 0; font-size:13px; font-family:맑은 고딕, Malgun Gothic, sans-serif;'>")
                    in_table = True
                cells = [c.strip() for c in stripped.split("|")[1:-1]]
                if all(c.startswith("-") or c.startswith(":") for c in cells):
                    continue  # 구분선
                row_html = "".join([f"<td style='border:1px solid #cbd5e0; padding:8px 12px;'>{c}</td>" for c in cells])
                html_lines.append(f"<tr>{row_html}</tr>")
            else:
                if in_table:
                    html_lines.append("</table>")
                    in_table = False
                if stripped.startswith("> "):
                    html_lines.append(f"<blockquote style='background:#f0f4f8; border-left:4px solid #3182ce; padding:10px 16px; margin:12px 0; color:#2c5282;'>{stripped[2:]}</blockquote>")
                elif stripped.startswith("```"):
                    continue
                elif stripped.startswith("* "):
                    html_lines.append(f"<li style='margin-bottom:6px; line-height:1.5;'>{stripped[2:]}</li>")
                elif stripped:
                    html_lines.append(f"<p style='line-height:1.6; margin:8px 0; color:#2d3748;'>{stripped}</p>")

        if in_table:
            html_lines.append("</table>")

        body_content = "\n".join(html_lines)
        full_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="utf-8">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Malgun Gothic", "맑은 고딕", Roboto, sans-serif;
            max-width: 920px;
            margin: 40px auto;
            padding: 0 24px;
            color: #2d3748;
            background-color: #ffffff;
        }}
        table tr:nth-child(even) {{ background-color: #f7fafc; }}
        table tr:first-child {{ background-color: #ebf8ff; font-weight: bold; color: #1a365d; }}
        strong {{ color: #1a202c; }}
        hr {{ border: 0; border-top: 1px solid #e2e8f0; margin: 24px 0; }}
        li {{ margin-left: 20px; }}
    </style>
</head>
<body>
{body_content}
</body>
</html>"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_html)
        logger.info(f"Styled HTML 보고서 저장 완료: {filepath}")
        return filepath

    @staticmethod
    def upload_to_google_docs(title: str, content: str, credentials_path: str = "credentials.json") -> Optional[str]:
        """Google Docs API를 통한 문서 자동 생성 (docs.googleapis.com/v1)"""
        if not os.path.exists(credentials_path):
            logger.info("Google Docs 인증키(credentials.json)가 감지되지 않아 로컬 Markdown/HTML 리포트를 생성했습니다.")
            return None

        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            creds = service_account.Credentials.from_service_account_file(
                credentials_path, scopes=["https://www.googleapis.com/auth/documents", "https://www.googleapis.com/auth/drive"]
            )
            service = build("docs", "v1", credentials=creds)

            doc = service.documents().create(body={"title": title}).execute()
            doc_id = doc.get("documentId")

            requests_body = [{
                "insertText": {
                    "location": {"index": 1},
                    "text": content
                }
            }]
            service.documents().batchUpdate(documentId=doc_id, body={"requests": requests_body}).execute()
            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
            logger.info(f"Google Docs 생성 성공: {doc_url}")
            return doc_url
        except Exception as e:
            logger.error(f"Google Docs API 연동 에러: {e}")
            return None

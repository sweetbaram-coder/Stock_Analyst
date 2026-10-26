"""main.py — 한국 주식 테마 주도주 발굴 및 사용자 지정 종목 정밀 분석 파이프라인
PRD v1.0 명세 및 참고자료(web-crawler) 크롤링 아키텍처 반영:
- [모드 1] 시장 전체 주도 테마 스크리닝 및 1등 대장주 자동 발굴 모드 (`python main.py`)
- [모드 2] 사용자 지정 종목 정밀 타겟 분석 모드 (`python main.py --stock "삼성전자"` 또는 `--stock 005930`)
- 공통 파이프라인: 멀티 타임프레임(일/주/월), 볼린저밴드+ADR, 매물대(Volume Profile), 펀더멘털, 3일 수급, DART 공시
- SOP AI 매뉴얼 프롬프트 규격 9개 섹션 리포트 생성 및 검증 매트릭스(SOP Verification Matrix)
- [주도주 분석보고서] {종목명}({종목코드}) - {분석일자} 규격 Google Docs / HTML / Excel 퍼블리싱
- Phase 5: 평일 장 마감(15:40) 자동화 스케줄링 모드 지원
"""
import argparse
import json
import logging
import os
import shutil
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

# 프로젝트 루트 경로 등록
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CURRENT_DIR)

from src.crawler import (
    NaverStockCrawler,
    ProgressTracker,
    StockResolver,
    detect_pii,
    validate_values,
    export_multi_sheet_excel
)
from src.screener import ThemeLeaderScreener
from src.pipeline import (
    TechnicalIndicatorEngine,
    MultiDataBridge,
    SopAnalystEngine,
    DocumentExporter,
    GoogleDriveStorage
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("StockPipeline")

# ─────────────────────────────────────────────────────────────────
# [모드 1] 시장 전체 테마 스크리닝 및 1위 대장주 자동 발굴
# ─────────────────────────────────────────────────────────────────
def run_pipeline(max_themes: int = 5, top_stocks_per_theme: int = 10, output_dir: str = "output"):
    """시장 전체 테마 스크리닝 모드"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    date_str = datetime.now().strftime("%Y-%m-%d")
    run_dir = os.path.join(output_dir, f"run_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)

    progress_file = os.path.join(run_dir, "progress.json")
    tracker = ProgressTracker(filepath=progress_file, total_steps=4)
    crawler = NaverStockCrawler(delay=0.4)
    screener = ThemeLeaderScreener()
    bridge = MultiDataBridge(delay=0.4)

    # [Step 1] 스크리닝 & 랭킹 엔진
    tracker.update_step(1, "네이버 증권 테마 및 종목 스크리닝 시작", {
        "수집 대상 테마 수": max_themes,
        "테마당 검토 종목 수": top_stocks_per_theme
    })

    all_themes = crawler.fetch_theme_list(max_pages=1, page_size=max_themes)
    if not all_themes:
        logger.error("테마 목록을 가져오지 못했습니다. 파이프라인을 중단합니다.")
        return False

    logger.info(f"상위 {len(all_themes)}개 테마 수집 완료")

    candidate_stocks = []
    scanned_stocks_count = 0

    for t in all_themes:
        t_no = t["theme_no"]
        t_name = t["theme_name"]
        logger.info(f"테마 탐색 중: [{t_name}] (등락률 {t['change_rate']:+.2f}%)")

        stocks = crawler.fetch_theme_stocks(t_no, max_stocks=top_stocks_per_theme)
        for s in stocks:
            scanned_stocks_count += 1
            passed, reason = screener.filter_basic(s)
            if not passed:
                continue

            code = s["code"]
            history = crawler.fetch_daily_price_history(code, count=15)
            stats = screener.calculate_3day_stats(history)
            if not stats["valid"]:
                continue

            is_large = s["market_cap"] >= 500_000_000_000
            min_val = screener.min_trading_value_large if is_large else screener.min_trading_value_small

            c_item = dict(s)
            c_item.update(stats)
            c_item["is_large"] = is_large
            c_item["filter_passed"] = (stats["cum_trading_value_3d"] >= min_val) and (stats["cum_return_3d"] >= screener.min_cum_return)
            candidate_stocks.append(c_item)

    logger.info(f"총 {scanned_stocks_count}개 종목 스캔, {len(candidate_stocks)}개 후보군 추출")

    evaluated_candidates = screener.evaluate_candidates(candidate_stocks)
    ranked_themes = screener.rank_themes(all_themes, evaluated_candidates)

    if not evaluated_candidates:
        logger.warning("조건에 부합하는 종목이 없어 스크리닝을 종료합니다.")
        return False

    # [Step 2] 1등 대장주 확정 및 멀티 데이터 파이프라인
    top_theme = ranked_themes[0]
    theme_candidates = [c for c in evaluated_candidates if c["theme_name"] == top_theme["theme_name"]]
    if theme_candidates:
        leader_stock = theme_candidates[0]
        second_stock = theme_candidates[1] if len(theme_candidates) > 1 else None
    else:
        leader_stock = evaluated_candidates[0]
        second_stock = evaluated_candidates[1] if len(evaluated_candidates) > 1 else None

    tracker.update_step(2, "1등 대장주 확정 및 멀티 데이터 파이프라인 가동", {
        "선정 테마": top_theme["theme_name"],
        "1등 대장주": f"{leader_stock['name']} ({leader_stock['code']})",
        "Leader Score": leader_stock["leader_score"]
    })

    l_code = leader_stock["code"]

    daily_candles = crawler.fetch_candle_chart(l_code, timeframe="day", count=120)
    weekly_candles = crawler.fetch_candle_chart(l_code, timeframe="week", count=120)
    monthly_candles = crawler.fetch_candle_chart(l_code, timeframe="month", count=120)

    indicators = TechnicalIndicatorEngine.compute_multi_timeframe(
        daily_candles, weekly_candles, monthly_candles
    )

    fundamentals = bridge.fetch_fundamental_info(l_code)
    investor_flow = bridge.fetch_investor_flow_3d(l_code)
    disclosures = bridge.fetch_recent_disclosures(l_code)

    logger.info(f"대장주({leader_stock['name']}) 멀티 소스 데이터 정제 완료")

    # [Step 3] 단일 AI 분석 에이전트 (SOP 9개 섹션 리포트 생성)
    tracker.update_step(3, "SOP 9개 섹션 규격 기술적 분석 보고서 생성 중")

    report_content = SopAnalystEngine.generate_report(
        theme_info=top_theme,
        leader_stock=leader_stock,
        second_stock=second_stock,
        indicators=indicators,
        fundamentals=fundamentals,
        investor_flow=investor_flow,
        disclosures=disclosures
    )

    sop_verification = SopAnalystEngine.verify_sop_compliance(report_content, leader_stock)
    logger.info("SOP 검증 체크리스트 결과:")
    for check_item, passed in sop_verification["checklist"].items():
        logger.info(f"  [{'PASS' if passed else 'FAIL'}] {check_item}")
    tracker.update_detail("sop_verification", sop_verification)

    # [Step 4] 다중 포맷 퍼블리싱 및 엑셀 내보내기
    tracker.update_step(4, "엑셀 및 리포트 파일 출력/퍼블리싱")

    val_rules = {
        "code": {"type": "str", "required": True},
        "name": {"type": "str", "required": True},
        "close_price": {"type": "num", "required": True}
    }
    issues = validate_values(evaluated_candidates, val_rules)
    if issues:
        logger.warning(f"데이터 검증 이슈: {issues}")
    pii_warns = detect_pii(evaluated_candidates)
    if pii_warns:
        logger.warning(f"PII 감지 경고: {pii_warns}")

    excel_path = os.path.join(run_dir, "screening_result.xlsx")

    sheet1_data = []
    for t in ranked_themes:
        sheet1_data.append({
            "테마코드": t["theme_no"],
            "테마명": t["theme_name"],
            "등락률(%)": f"{t['change_rate']:+.2f}%",
            "전체종목수": t["total_count"],
            "상승종목수": t["rise_count"],
            "후보발굴수": t["candidate_count"],
            "3일합산거래대금(억)": round(t["total_trading_value_3d"] / 1e8, 1),
            "대장주점수": t["top_leader_score"],
            "테마주도점수": t["theme_score"],
            "1등대장주": t["top_stock"]
        })

    sheet2_data = []
    for c in evaluated_candidates:
        sheet2_data.append({
            "종목코드": c["code"],
            "종목명": c["name"],
            "테마명": c["theme_name"],
            "현재가(원)": c["close_price"],
            "등락률(%)": f"{c['change_rate']:+.2f}%",
            "3일누적수익률(%)": f"{c['cum_return_3d']:+.2f}%",
            "3일거래대금(억)": round(c["cum_trading_value_3d"] / 1e8, 1),
            "신고가근접도(%)": c["high_proximity"],
            "거래대금점수": c["score_trading_value"],
            "수익률점수": c["score_return"],
            "신고가점수": c["score_high_proximity"],
            "LeaderScore": c["leader_score"],
            "시가총액(억)": round(c["market_cap"] / 1e8, 1),
            "필터통과여부": "통과" if c.get("filter_passed") else "후보(완화)"
        })

    sheet3_data = []
    daily_df = indicators.get("daily", {}).get("series_df")
    if daily_df is not None:
        for _, row in daily_df.tail(60).iterrows():
            sheet3_data.append({
                "날짜": str(row["date"].date()) if hasattr(row["date"], "date") else str(row["date"]),
                "시가": row["open"], "고가": row["high"], "저가": row["low"], "종가": row["close"], "거래량": row["volume"],
                "MA5": round(row["ma5"], 1) if "ma5" in row and row["ma5"] else "",
                "MA20": round(row["ma20"], 1) if "ma20" in row and row["ma20"] else "",
                "MA60": round(row["ma60"], 1) if "ma60" in row and row["ma60"] else "",
                "MA120": round(row["ma120"], 1) if "ma120" in row and row["ma120"] else "",
                "RSI14": round(row["rsi14"], 2) if "rsi14" in row and row["rsi14"] else "",
                "MACD": round(row["macd"], 2) if "macd" in row and row["macd"] else "",
                "MACD_Signal": round(row["macd_signal"], 2) if "macd_signal" in row and row["macd_signal"] else ""
            })

    export_multi_sheet_excel({
        "주도테마 랭킹": sheet1_data,
        "후보종목 스코어보드": sheet2_data,
        "대장주 일봉지표": sheet3_data
    }, excel_path)

    doc_title = DocumentExporter.generate_doc_title(leader_stock["name"], leader_stock["code"], date_str)
    md_path = os.path.join(run_dir, "analysis_report.md")
    html_path = os.path.join(run_dir, "analysis_report.html")

    DocumentExporter.export_markdown(report_content, md_path)
    DocumentExporter.export_styled_html(report_content, html_path, title=doc_title)

    doc_url = DocumentExporter.upload_to_google_docs(title=doc_title, content=report_content)

    try:
        shutil.copyfile(md_path, os.path.join(output_dir, "latest_analysis_report.md"))
        shutil.copyfile(html_path, os.path.join(output_dir, "latest_analysis_report.html"))
        shutil.copyfile(excel_path, os.path.join(output_dir, "latest_screening_result.xlsx"))
    except Exception:
        pass

    # 구글 드라이브 '120.주식종목분석' 연도별 자동 저장
    drive_storage = GoogleDriveStorage()
    with open(html_path, "r", encoding="utf-8") as hf:
        html_raw = hf.read()
    drive_files = drive_storage.save_analysis_results(
        stock_name=leader_stock["name"],
        stock_code=leader_stock["code"],
        report_md=report_content,
        report_html=html_raw,
        excel_source_path=excel_path,
        date_str=date_str,
        timestamp_str=timestamp[:13]
    )

    summary = (
        f"1위 테마: {top_theme['theme_name']} | "
        f"대장주: {leader_stock['name']} ({leader_stock['code']}) | "
        f"Leader Score: {leader_stock['leader_score']}점 | "
        f"문서 제목: {doc_title}"
    )
    tracker.complete(summary=summary)

    print("\n" + "=" * 65)
    print(f"★ [PRD v1.0] 주도 테마 스크리닝 및 SOP 분석 완료 ★")
    print(f"1. 문서 제목 규격: {doc_title}")
    print(f"2. 주도 테마: {top_theme['theme_name']} ({top_theme['change_rate']:+.2f}%)")
    print(f"3. 1등 대장주: {leader_stock['name']} ({leader_stock['code']}) - 점수: {leader_stock['leader_score']}점")
    if second_stock:
        print(f"   (2위 부대장주: {second_stock['name']} - {second_stock['leader_score']}점)")
    print(f"4. SOP 검증 매트릭스: {'모두 통과 (ALL PASS)' if sop_verification['all_passed'] else '일부 확인 필요'}")
    print(f"5. 엑셀 파일: {excel_path}")
    print(f"6. 마크다운 보고서: {md_path}")
    print(f"7. Styled HTML 보고서: {html_path}")
    print(f"8. 구글드라이브 저장 ({drive_files['dest_dir']}):")
    print(f"   - MD: {os.path.basename(drive_files['md_path'])}")
    print(f"   - XLSX: {os.path.basename(drive_files['excel_path'])}")
    if doc_url:
        print(f"9. Google Docs 발행 URL: {doc_url}")
    print("=" * 65 + "\n")

    return {
        "doc_title": doc_title,
        "theme_info": top_theme,
        "leader_stock": leader_stock,
        "second_stock": second_stock,
        "indicators": indicators,
        "fundamentals": fundamentals,
        "investor_flow": investor_flow,
        "report_content": report_content,
        "md_path": md_path,
        "html_path": html_path,
        "excel_path": excel_path,
        "drive_files": drive_files
    }

# ─────────────────────────────────────────────────────────────────
# [모드 2] 사용자 지정 특정 종목 타겟 정밀 분석
# ─────────────────────────────────────────────────────────────────
def run_single_stock_pipeline(stock_query: str, output_dir: str = "output") -> bool:
    """사용자가 지정한 특정 종목(명/코드)에 대한 정밀 분석 모드"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    date_str = datetime.now().strftime("%Y-%m-%d")
    run_dir = os.path.join(output_dir, f"run_target_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)

    progress_file = os.path.join(run_dir, "progress.json")
    tracker = ProgressTracker(filepath=progress_file, total_steps=4)
    crawler = NaverStockCrawler(delay=0.4)
    screener = ThemeLeaderScreener()
    bridge = MultiDataBridge(delay=0.4)
    resolver = StockResolver(delay=0.3)

    # [Step 1] 종목 식별 및 기본 정보 확인
    tracker.update_step(1, f"지정 종목 식별 및 테마 탐색: '{stock_query}'")
    stock_basic = resolver.resolve(stock_query)
    if not stock_basic:
        logger.error(f"종목을 식별할 수 없습니다: '{stock_query}'. 정확한 종목명이나 6자리 코드를 입력해주세요.")
        return False

    code = stock_basic["code"]
    name = stock_basic["name"]
    logger.info(f"종목 식별 성공: {name} ({code}) - 현재가: {stock_basic['close_price']:,}원")

    # 소속 주요 테마 탐색
    all_themes = crawler.fetch_theme_list(max_pages=2, page_size=25)
    matched_theme = None
    for t in all_themes:
        stocks = crawler.fetch_theme_stocks(t["theme_no"], max_stocks=30)
        if any(s["code"] == code for s in stocks):
            matched_theme = t
            logger.info(f"소속 테마 매핑 완료: [{t['theme_name']}] (등락률 {t['change_rate']:+.2f}%)")
            break

    if not matched_theme:
        matched_theme = {
            "theme_no": 0,
            "theme_name": f"{name} 주도 섹터",
            "change_rate": stock_basic["change_rate"],
            "total_count": 1,
            "rise_count": 1 if stock_basic["change_rate"] > 0 else 0
        }

    # 3거래일 누적 시세 및 Leader Score 계산
    history = crawler.fetch_daily_price_history(code, count=15)
    stats = screener.calculate_3day_stats(history)
    stock_basic.update(stats)
    stock_basic["theme_name"] = matched_theme["theme_name"]

    # Leader Score 산출
    c_val = stats["cum_trading_value_3d"]
    v_score = min(round((c_val / 100_000_000_000) * 100.0, 1), 100.0)
    r_score = min(max(round((stats["cum_return_3d"] / 20.0) * 100.0, 1), 0.0), 100.0)
    h_score = stats["high_proximity"]
    leader_score = round((0.45 * v_score) + (0.35 * r_score) + (0.20 * h_score), 2)

    stock_basic["score_trading_value"] = v_score
    stock_basic["score_return"] = r_score
    stock_basic["score_high_proximity"] = h_score
    stock_basic["leader_score"] = leader_score

    # [Step 2] 멀티 타임프레임 차트 및 펀더멘털 파이프라인
    tracker.update_step(2, f"멀티 타임프레임 및 데이터 파이프라인 가동: {name} ({code})")
    daily_candles = crawler.fetch_candle_chart(code, timeframe="day", count=120)
    weekly_candles = crawler.fetch_candle_chart(code, timeframe="week", count=120)
    monthly_candles = crawler.fetch_candle_chart(code, timeframe="month", count=120)

    indicators = TechnicalIndicatorEngine.compute_multi_timeframe(
        daily_candles, weekly_candles, monthly_candles
    )

    fundamentals = bridge.fetch_fundamental_info(code)
    investor_flow = bridge.fetch_investor_flow_3d(code)
    disclosures = bridge.fetch_recent_disclosures(code)

    logger.info(f"지정 종목({name}) 기술적 지표, 펀더멘털, 3일 수급, 공시 수집 완료")

    # [Step 3] SOP AI 매뉴얼 프롬프트 9개 섹션 리포트 생성 및 검증
    tracker.update_step(3, f"SOP 9개 섹션 규격 기술적 분석 보고서 생성 중: {name}")
    report_content = SopAnalystEngine.generate_report(
        theme_info=matched_theme,
        leader_stock=stock_basic,
        second_stock=None,
        indicators=indicators,
        fundamentals=fundamentals,
        investor_flow=investor_flow,
        disclosures=disclosures
    )

    sop_verification = SopAnalystEngine.verify_sop_compliance(report_content, stock_basic)
    logger.info("SOP 검증 체크리스트 결과:")
    for check_item, passed in sop_verification["checklist"].items():
        logger.info(f"  [{'PASS' if passed else 'FAIL'}] {check_item}")
    tracker.update_detail("sop_verification", sop_verification)

    # [Step 4] 다중 포맷 퍼블리싱 및 엑셀 내보내기
    tracker.update_step(4, "엑셀 및 리포트 파일 출력/퍼블리싱")
    doc_title = DocumentExporter.generate_doc_title(name, code, date_str)

    md_path = os.path.join(run_dir, "analysis_report.md")
    html_path = os.path.join(run_dir, "analysis_report.html")
    excel_path = os.path.join(run_dir, "stock_analysis.xlsx")

    DocumentExporter.export_markdown(report_content, md_path)
    DocumentExporter.export_styled_html(report_content, html_path, title=doc_title)

    inst_breakdown = investor_flow.get("institution_breakdown", {})
    sheet1_data = [{
        "종목코드": code,
        "종목명": name,
        "소속테마": matched_theme["theme_name"],
        "현재가(원)": stock_basic["close_price"],
        "등락률(%)": f"{stock_basic['change_rate']:+.2f}%",
        "3일누적수익률(%)": f"{stock_basic['cum_return_3d']:+.2f}%",
        "3일거래대금(억)": round(stock_basic["cum_trading_value_3d"] / 1e8, 1),
        "신고가근접도(%)": stock_basic["high_proximity"],
        "LeaderScore": stock_basic["leader_score"],
        "시가총액": fundamentals.get("market_cap", "N/A"),
        "PER": fundamentals.get("per", "N/A"),
        "PBR": fundamentals.get("pbr", "N/A"),
        "EPS": fundamentals.get("eps", "N/A"),
        "BPS": fundamentals.get("bps", "N/A"),
        "최근분기매출": fundamentals.get("revenue", "N/A"),
        "최근분기영업이익": fundamentals.get("operating_profit", "N/A"),
        "영업이익률": fundamentals.get("op_margin", "N/A"),
        "목표주가컨센서스": fundamentals.get("target_price_consensus", "N/A"),
        "개인3일순매수(주)": investor_flow.get("individual_net_3d", 0),
        "외인3일순매수(주)": investor_flow.get("foreign_net_3d", 0),
        "기관3일순매수(주)": investor_flow.get("institution_net_3d", 0),
        "금융투자(주)": inst_breakdown.get("financial_investment", 0),
        "연기금등(주)": inst_breakdown.get("pension_fund", 0),
        "투신(주)": inst_breakdown.get("investment_trust", 0),
        "보험은행(주)": inst_breakdown.get("insurance_bank", 0),
        "수급종합평가": investor_flow.get("main_buyer", "중립")
    }]

    sheet2_data = []
    daily_df = indicators.get("daily", {}).get("series_df")
    if daily_df is not None:
        for _, row in daily_df.tail(60).iterrows():
            sheet2_data.append({
                "날짜": str(row["date"].date()) if hasattr(row["date"], "date") else str(row["date"]),
                "시가": row["open"], "고가": row["high"], "저가": row["low"], "종가": row["close"], "거래량": row["volume"],
                "MA5": round(row["ma5"], 1) if "ma5" in row and row["ma5"] else "",
                "MA20": round(row["ma20"], 1) if "ma20" in row and row["ma20"] else "",
                "MA60": round(row["ma60"], 1) if "ma60" in row and row["ma60"] else "",
                "MA120": round(row["ma120"], 1) if "ma120" in row and row["ma120"] else "",
                "RSI14": round(row["rsi14"], 2) if "rsi14" in row and row["rsi14"] else "",
                "MACD": round(row["macd"], 2) if "macd" in row and row["macd"] else ""
            })

    export_multi_sheet_excel({
        "종목분석 요약": sheet1_data,
        "일봉기술지표": sheet2_data
    }, excel_path)

    doc_url = DocumentExporter.upload_to_google_docs(title=doc_title, content=report_content)

    try:
        shutil.copyfile(md_path, os.path.join(output_dir, "latest_analysis_report.md"))
        shutil.copyfile(html_path, os.path.join(output_dir, "latest_analysis_report.html"))
        shutil.copyfile(excel_path, os.path.join(output_dir, "latest_screening_result.xlsx"))
    except Exception:
        pass

    # 구글 드라이브 '120.주식종목분석' 연도별 자동 저장
    drive_storage = GoogleDriveStorage()
    with open(html_path, "r", encoding="utf-8") as hf:
        html_raw = hf.read()
    drive_files = drive_storage.save_analysis_results(
        stock_name=name,
        stock_code=code,
        report_md=report_content,
        report_html=html_raw,
        excel_source_path=excel_path,
        date_str=date_str,
        timestamp_str=timestamp[:13]
    )

    tracker.complete(summary=f"지정 종목: {name}({code}) | 문서 제목: {doc_title}")

    print("\n" + "=" * 65)
    print(f"★ [지정 종목 타겟 분석 완료] ★")
    print(f"1. 대상 종목: {name} ({code}) - 현재가: {stock_basic['close_price']:,}원")
    print(f"2. 소속 테마: {matched_theme['theme_name']}")
    print(f"3. Leader Score: {stock_basic['leader_score']}점")
    print(f"4. SOP 검증 매트릭스: {'모두 통과 (ALL PASS)' if sop_verification['all_passed'] else '일부 확인 필요'}")
    print(f"5. 문서 제목 규격: {doc_title}")
    print(f"6. 마크다운 보고서: {md_path}")
    print(f"7. Styled HTML 보고서: {html_path}")
    print(f"8. 엑셀 파일: {excel_path}")
    print(f"9. 구글드라이브 저장 ({drive_files['dest_dir']}):")
    print(f"   - MD: {os.path.basename(drive_files['md_path'])}")
    print(f"   - XLSX: {os.path.basename(drive_files['excel_path'])}")
    if doc_url:
        print(f"10. Google Docs 발행 URL: {doc_url}")
    print("=" * 65 + "\n")

    return {
        "doc_title": doc_title,
        "theme_info": matched_theme,
        "leader_stock": stock_basic,
        "second_stock": None,
        "indicators": indicators,
        "fundamentals": fundamentals,
        "investor_flow": investor_flow,
        "report_content": report_content,
        "md_path": md_path,
        "html_path": html_path,
        "excel_path": excel_path,
        "drive_files": drive_files
    }

# ─────────────────────────────────────────────────────────────────
# [모드 1-B] UI 전용: 사용자가 선택한 특정 테마의 1등 대장주 정밀 분석
# ─────────────────────────────────────────────────────────────────
def run_target_theme_pipeline(theme_no: int, theme_name: str = "", max_stocks: int = 25, output_dir: str = "output") -> Optional[Dict[str, Any]]:
    """사용자가 UI에서 선택한 특정 테마의 구성 종목을 스캔하고 1등 대장주를 자동 선정하여 심층 분석"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    date_str = datetime.now().strftime("%Y-%m-%d")
    run_dir = os.path.join(output_dir, f"run_theme_{theme_no}_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)

    tracker = ProgressTracker(total_steps=4)
    crawler = NaverStockCrawler(delay=0.1)
    screener = ThemeLeaderScreener()
    bridge = MultiDataBridge(delay=0.1)

    # [Step 1] 해당 테마 구성 종목 수집 및 대장주 스크리닝
    display_theme = theme_name or f"테마(No.{theme_no})"
    tracker.update_step(1, f"테마 [{display_theme}] 구성 종목 스캔 및 Leader Score 산출")

    stocks = crawler.fetch_theme_stocks(theme_no, max_stocks=max_stocks)
    if not stocks:
        logger.error(f"테마(No.{theme_no})의 종목 정보를 가져오지 못했습니다.")
        return None

    theme_info = {
        "theme_no": theme_no,
        "theme_name": theme_name or (stocks[0].get("theme_name") if stocks else f"테마_{theme_no}"),
        "change_rate": round(sum(s.get("change_rate", 0) for s in stocks) / len(stocks), 2) if stocks else 0.0,
        "total_count": len(stocks),
        "rise_count": sum(1 for s in stocks if s.get("change_rate", 0) > 0)
    }

    candidate_stocks = []
    for s in stocks:
        code = s["code"]
        history = crawler.fetch_daily_price_history(code, count=15)
        stats = screener.calculate_3day_stats(history)
        if not stats["valid"]:
            continue
        c_item = dict(s)
        c_item.update(stats)
        c_item["theme_name"] = theme_info["theme_name"]
        candidate_stocks.append(c_item)

    if not candidate_stocks:
        logger.warning(f"테마 [{display_theme}] 내 유효한 거래 데이터 종목이 없습니다.")
        return None

    evaluated_candidates = screener.evaluate_candidates(candidate_stocks)
    leader_stock = evaluated_candidates[0]
    second_stock = evaluated_candidates[1] if len(evaluated_candidates) > 1 else None

    # [Step 2] 멀티 데이터 파이프라인 가동
    tracker.update_step(2, f"1등 대장주({leader_stock['name']}) 멀티 소스 데이터 수집")
    l_code = leader_stock["code"]

    daily_candles = crawler.fetch_candle_chart(l_code, timeframe="day", count=120)
    weekly_candles = crawler.fetch_candle_chart(l_code, timeframe="week", count=120)
    monthly_candles = crawler.fetch_candle_chart(l_code, timeframe="month", count=120)

    indicators = TechnicalIndicatorEngine.compute_multi_timeframe(
        daily_candles, weekly_candles, monthly_candles
    )

    fundamentals = bridge.fetch_fundamental_info(l_code)
    investor_flow = bridge.fetch_investor_flow_detailed(l_code)
    disclosures = bridge.fetch_recent_disclosures(l_code)

    # [Step 3] SOP 9개 섹션 리포트 생성 및 검증
    tracker.update_step(3, f"SOP 규격 기술적 분석 리포트 생성 중: {leader_stock['name']}")
    report_content = SopAnalystEngine.generate_report(
        theme_info=theme_info,
        leader_stock=leader_stock,
        second_stock=second_stock,
        indicators=indicators,
        fundamentals=fundamentals,
        investor_flow=investor_flow,
        disclosures=disclosures
    )

    sop_verification = SopAnalystEngine.verify_sop_compliance(report_content, leader_stock)

    # [Step 4] 다중 포맷 퍼블리싱 및 엑셀 내보내기
    tracker.update_step(4, "엑셀 및 구글드라이브 저장")
    doc_title = DocumentExporter.generate_doc_title(leader_stock["name"], l_code, date_str)

    md_path = os.path.join(run_dir, "analysis_report.md")
    html_path = os.path.join(run_dir, "analysis_report.html")
    excel_path = os.path.join(run_dir, "theme_leader_analysis.xlsx")

    DocumentExporter.export_markdown(report_content, md_path)
    DocumentExporter.export_styled_html(report_content, html_path, title=doc_title)

    inst_breakdown = investor_flow.get("institution_breakdown", {})
    sheet1_data = [{
        "종목코드": l_code,
        "종목명": leader_stock["name"],
        "소속테마": theme_info["theme_name"],
        "현재가(원)": leader_stock["close_price"],
        "등락률(%)": f"{leader_stock['change_rate']:+.2f}%",
        "3일누적수익률(%)": f"{leader_stock['cum_return_3d']:+.2f}%",
        "3일거래대금(억)": round(leader_stock["cum_trading_value_3d"] / 1e8, 1),
        "신고가근접도(%)": leader_stock["high_proximity"],
        "LeaderScore": leader_stock["leader_score"],
        "시가총액": fundamentals.get("market_cap", "N/A"),
        "PER": fundamentals.get("per", "N/A"),
        "PBR": fundamentals.get("pbr", "N/A"),
        "EPS": fundamentals.get("eps", "N/A"),
        "BPS": fundamentals.get("bps", "N/A"),
        "최근분기매출": fundamentals.get("revenue", "N/A"),
        "최근분기영업이익": fundamentals.get("operating_profit", "N/A"),
        "영업이익률": fundamentals.get("op_margin", "N/A"),
        "목표주가컨센서스": fundamentals.get("target_price_consensus", "N/A"),
        "개인3일순매수(주)": investor_flow.get("individual_net_3d", 0),
        "외인3일순매수(주)": investor_flow.get("foreign_net_3d", 0),
        "기관3일순매수(주)": investor_flow.get("institution_net_3d", 0),
        "금융투자(주)": inst_breakdown.get("financial_investment", 0),
        "연기금등(주)": inst_breakdown.get("pension_fund", 0),
        "투신(주)": inst_breakdown.get("investment_trust", 0),
        "보험은행(주)": inst_breakdown.get("insurance_bank", 0),
        "수급종합평가": investor_flow.get("main_buyer", "중립")
    }]

    sheet2_data = []
    for c in evaluated_candidates:
        sheet2_data.append({
            "순위": evaluated_candidates.index(c) + 1,
            "종목코드": c["code"],
            "종목명": c["name"],
            "현재가(원)": c["close_price"],
            "등락률(%)": f"{c['change_rate']:+.2f}%",
            "3일수익률(%)": f"{c['cum_return_3d']:+.2f}%",
            "3일거래대금(억)": round(c["cum_trading_value_3d"] / 1e8, 1),
            "LeaderScore": c["leader_score"]
        })

    sheet3_data = []
    daily_df = indicators.get("daily", {}).get("series_df")
    if daily_df is not None:
        for _, row in daily_df.tail(60).iterrows():
            sheet3_data.append({
                "날짜": str(row["date"].date()) if hasattr(row["date"], "date") else str(row["date"]),
                "시가": row["open"], "고가": row["high"], "저가": row["low"], "종가": row["close"], "거래량": row["volume"],
                "MA5": round(row["ma5"], 1) if "ma5" in row and row["ma5"] else "",
                "MA20": round(row["ma20"], 1) if "ma20" in row and row["ma20"] else "",
                "MA60": round(row["ma60"], 1) if "ma60" in row and row["ma60"] else "",
                "MA120": round(row["ma120"], 1) if "ma120" in row and row["ma120"] else "",
                "RSI14": round(row["rsi14"], 2) if "rsi14" in row and row["rsi14"] else "",
                "MACD": round(row["macd"], 2) if "macd" in row and row["macd"] else ""
            })

    export_multi_sheet_excel({
        "대장주분석요약": sheet1_data,
        "테마구성종목순위": sheet2_data,
        "일봉기술지표": sheet3_data
    }, excel_path)

    # 구글 드라이브 '120.주식종목분석' 연도별 자동 저장
    drive_storage = GoogleDriveStorage()
    with open(html_path, "r", encoding="utf-8") as hf:
        html_raw = hf.read()
    drive_files = drive_storage.save_analysis_results(
        stock_name=leader_stock["name"],
        stock_code=l_code,
        report_md=report_content,
        report_html=html_raw,
        excel_source_path=excel_path,
        date_str=date_str,
        timestamp_str=timestamp[:13]
    )

    tracker.complete(summary=f"선택 테마 대장주: {leader_stock['name']}({l_code}) | 문서 제목: {doc_title}")

    return {
        "doc_title": doc_title,
        "theme_info": theme_info,
        "leader_stock": leader_stock,
        "second_stock": second_stock,
        "indicators": indicators,
        "fundamentals": fundamentals,
        "investor_flow": investor_flow,
        "report_content": report_content,
        "md_path": md_path,
        "html_path": html_path,
        "excel_path": excel_path,
        "drive_files": drive_files
    }

def run_scheduled_mode(target_time_str: str = "15:40", themes: int = 5, stocks_per_theme: int = 10, output: str = "output"):
    """Phase 5: 평일 장 마감 후 자동 실행 스케줄러 루프"""
    print(f"\n[*] 평일 장 마감 자동 실행 모드가 활성화되었습니다. (목표 시각: 매일 {target_time_str})")
    print("[*] 종료하려면 Ctrl+C를 누르세요.\n")

    while True:
        now = datetime.now()
        is_weekday = now.weekday() < 5
        current_time_str = now.strftime("%H:%M")

        if is_weekday and current_time_str == target_time_str:
            print(f"\n[!] 목표 시각({target_time_str}) 도달! 주도주 분석 파이프라인을 자동 가동합니다.")
            try:
                run_pipeline(max_themes=themes, top_stocks_per_theme=stocks_per_theme, output_dir=output)
            except Exception as e:
                logger.error(f"스케줄 실행 중 에러 발생: {e}")
            time.sleep(65)
        else:
            time.sleep(20)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="한국 주식 테마 주도주 발굴 및 자동 분석 파이프라인 (PRD v1.0)")
    parser.add_argument("--stock", type=str, default=None, help="분석할 특정 종목명 또는 6자리 종목코드 (예: '삼성전자' 또는 '005930')")
    parser.add_argument("--themes", type=int, default=5, help="검색할 상위 테마 수 (기본: 5)")
    parser.add_argument("--stocks-per-theme", type=int, default=10, help="테마당 검토할 상위 종목 수 (기본: 10)")
    parser.add_argument("--output", type=str, default="output", help="결과 저장 디렉토리")
    parser.add_argument("--schedule", type=str, default=None, help="장 마감 자동 실행 시각 설정 (예: 15:40)")

    args = parser.parse_args()

    if args.stock:
        # 모드 2: 사용자 지정 종목 타겟 분석
        success = run_single_stock_pipeline(
            stock_query=args.stock,
            output_dir=args.output
        )
        sys.exit(0 if success else 1)
    elif args.schedule:
        # Phase 5: 스케줄러 모드
        run_scheduled_mode(
            target_time_str=args.schedule,
            themes=args.themes,
            stocks_per_theme=args.stocks_per_theme,
            output=args.output
        )
    else:
        # 모드 1: 시장 전체 테마 스크리닝 후 대장주 자동 발굴
        success = run_pipeline(
            max_themes=args.themes,
            top_stocks_per_theme=args.stocks_per_theme,
            output_dir=args.output
        )
        sys.exit(0 if success else 1)

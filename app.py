"""app.py — AI 주도주 & 특정 종목 퀀트 분석 대시보드 (Streamlit UI)
사용자 요구사항 완벽 반영:
1. 첫 번째 조회 조건: '테마주 대장주 분석' vs '특정 종목 분석'
2. '테마주 대장주 분석' 선택 시:
   - 상승률 및 거래량 기준 상위 테마 (5~10개) 실시간 조회 및 선택 인터페이스
   - 선택 테마의 1등 대장주 자동 스크리닝 및 심층 분석
3. '특정 종목 분석' 선택 시:
   - 종목명(예: 삼성전자) 또는 종목코드(예: 005930) 입력 및 분석
4. 구글 드라이브 연도별 자동 저장:
   - 'G:\\내 드라이브\\120.주식종목분석\\{연도}\\' 폴더에 결과 3종 자동 저장
5. UI 화면 내 종합 분석 보고서 및 펀더멘털/세분화 수급 실시간 열람 & 다운로드
"""
import os
import sys
import subprocess
import streamlit as st
import pandas as pd
from datetime import datetime

# 프로젝트 루트 경로 추가
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from src.crawler import NaverStockCrawler
from src.crawler.theme_service import ThemeService
from src.pipeline import GoogleDriveStorage, HtsChartEngine
from main import run_target_theme_pipeline, run_single_stock_pipeline

# ─────────────────────────────────────────────────────────────────
# 1. 페이지 환경 설정 및 커스텀 테마 스타일링
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI 주도주 & 종목 분석 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 세련된 커스텀 CSS 적용
st.markdown("""
<style>
    .main-title {
        font-size: 26px;
        font-weight: 700;
        color: #1a365d;
        margin-bottom: 4px;
    }
    .sub-title {
        font-size: 14px;
        color: #4a5568;
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: #f7fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .drive-banner {
        background-color: #ebf8ff;
        border-left: 4px solid #3182ce;
        padding: 12px 16px;
        border-radius: 4px;
        margin-bottom: 16px;
        font-size: 14px;
        color: #2b6cb0;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 44px;
        border-radius: 6px 6px 0 0;
        padding-left: 16px;
        padding-right: 16px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# 2. 사이드바: 조회 조건 및 사용자 제어판
# ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ 분석 제어판")
    st.markdown("---")

    # [조건 1] 분석 모드 선택
    analysis_mode = st.radio(
        "**1단계: 분석 모드 선택**",
        options=["테마주 대장주 분석", "특정 종목 분석"],
        index=0,
        help="시장 인기 테마의 대장주를 분석하거나, 특정 개별 종목을 직접 지정하여 분석합니다."
    )
    st.markdown("---")

    selected_theme_no = None
    selected_theme_name = ""
    stock_query_input = ""

    # [조건 2-A] 테마주 대장주 분석 선택 시
    if analysis_mode == "테마주 대장주 분석":
        st.markdown("**2단계: 실시간 주도 테마 선택**")

        # 상위 테마 목록 로드 (캐시 또는 실시간)
        @st.cache_data(ttl=60)
        def load_top_themes():
            crawler = NaverStockCrawler(delay=0.1)
            service = ThemeService(crawler)
            return service.get_top_active_themes(limit=8)

        with st.spinner("실시간 주도 테마 수집 중..."):
            top_themes = load_top_themes()

        if top_themes:
            theme_options = []
            theme_map = {}
            for t in top_themes:
                label = f"{t['theme_name']} ({t['change_rate']:+.2f}% / 상승 {t['rise_count']}/{t['total_count']}개)"
                theme_options.append(label)
                theme_map[label] = t

            selected_label = st.radio(
                "현재 거래량 및 상승률 상위 테마 (Top 8):",
                options=theme_options,
                index=0
            )
            selected_theme_info = theme_map[selected_label]
            selected_theme_no = selected_theme_info["theme_no"]
            selected_theme_name = selected_theme_info["theme_name"]

            st.caption(f"선택 테마 코드: `{selected_theme_no}` | 등락률: `{selected_theme_info['change_rate']:+.2f}%`")
        else:
            st.error("테마 정보를 불러오지 못했습니다. 네트워크 상태를 확인하세요.")

        if st.button("🔄 테마 목록 새로고침"):
            st.cache_data.clear()
            st.rerun()

    # [조건 2-B] 특정 종목 분석 선택 시
    else:
        st.markdown("**2단계: 분석 대상 종목 입력**")
        stock_query_input = st.text_input(
            "종목명 또는 6자리 종목코드",
            value="삼성전자",
            help="예: 삼성전자, SK하이닉스, 005930, 000660 등"
        ).strip()

        st.info("💡 종목명 또는 6자리 코드를 입력하면 해당 종목의 소속 테마 및 대장주 지표, 기술적·펀더멘털 분석을 일괄 수행합니다.")

    st.markdown("---")
    execute_btn = st.button("🚀 주식 정밀 분석 실행", type="primary", use_container_width=True)

    st.markdown("---")
    st.markdown("### 📁 구글 드라이브 동기화 정보")
    drive_storage = GoogleDriveStorage()
    curr_year = datetime.now().strftime("%Y")
    dest_folder = drive_storage.get_yearly_folder(curr_year)
    st.caption(f"**자동 저장 폴더**: `{dest_folder}`")

# ─────────────────────────────────────────────────────────────────
# 3. 메인 화면 헤더 및 상태 관리
# ─────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">📈 AI 주도주 & 종목 퀀트 분석 대시보드</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">SOP 기반 멀티 타임프레임 기술적 분석([Technical Analysis.md]) 및 펀더멘털·수급 정밀 분석([Qualitative Analysis.md]) 리포트 시스템</div>',
    unsafe_allow_html=True
)

if "analysis_result" not in st.session_state:
    st.session_state["analysis_result"] = None

# 분석 실행 트리거 처리
if execute_btn:
    with st.spinner("AI 퀀트 분석 파이프라인 가동 중... (차트 계산, 실적/공시 수집, 1차·2차 세분화 수급 분석)"):
        try:
            if analysis_mode == "테마주 대장주 분석":
                if not selected_theme_no:
                    st.error("분석할 테마를 선택해주세요.")
                else:
                    res = run_target_theme_pipeline(
                        theme_no=selected_theme_no,
                        theme_name=selected_theme_name,
                        output_dir="output"
                    )
                    st.session_state["analysis_result"] = res
            else:
                if not stock_query_input:
                    st.error("분석할 종목명 또는 코드를 입력해주세요.")
                else:
                    res = run_single_stock_pipeline(
                        stock_query=stock_query_input,
                        output_dir="output"
                    )
                    st.session_state["analysis_result"] = res

            st.toast("✅ 주식 정밀 분석이 성공적으로 완료되었습니다!", icon="🎉")
        except Exception as e:
            st.error(f"분석 실행 중 오류 발생: {e}")

# ─────────────────────────────────────────────────────────────────
# 4. 분석 결과 화면 렌더링
# ─────────────────────────────────────────────────────────────────
result = st.session_state["analysis_result"]

if result and isinstance(result, dict):
    leader = result.get("leader_stock", {})
    fundamentals = result.get("fundamentals", {})
    investor_flow = result.get("investor_flow", {})
    indicators = result.get("indicators", {}).get("daily", {})
    theme = result.get("theme_info", {})
    drive_files = result.get("drive_files", {})
    report_content = result.get("report_content", "")

    # 구글 드라이브 저장 안내 배너
    st.markdown(f"""
    <div class="drive-banner">
        💾 <b>구글 드라이브 자동 저장 완료</b><br>
        • 대상 폴더: <code>{drive_files.get('dest_dir', '')}</code><br>
        • 저장 파일: <code>{os.path.basename(drive_files.get('md_path', ''))}</code> | <code>{os.path.basename(drive_files.get('excel_path', ''))}</code>
    </div>
    """, unsafe_allow_html=True)

    # 상단 핵심 KPI 요약 카드 메트릭
    col1, col2, col3, col4, col5 = st.columns(5)
    current_price = leader.get("close_price", 0)
    change_rate = leader.get("change_rate", 0.0)

    target_1 = int(current_price * 1.09)
    stop_loss = int(current_price * 0.95)

    with col1:
        st.metric(
            label="분석 종목 (현재가)",
            value=f"{leader.get('name', '')} {current_price:,}원",
            delta=f"{change_rate:+.2f}%"
        )
    with col2:
        st.metric(
            label="1차 목표가 (+9.0%)",
            value=f"{target_1:,}원",
            delta=f"+{target_1 - current_price:,}원"
        )
    with col3:
        st.metric(
            label="손절 기준가 (-5.0%)",
            value=f"{stop_loss:,}원",
            delta=f"-{current_price - stop_loss:,}원",
            delta_color="inverse"
        )
    with col4:
        st.metric(
            label="Leader Score",
            value=f"{leader.get('leader_score', 0):.2f}점",
            delta=f"소속: {theme.get('theme_name', '')}"
        )
    with col5:
        st.metric(
            label="메이저 수급 상태",
            value=investor_flow.get("flow_quality", "보통"),
            delta=investor_flow.get("main_buyer", "중립")
        )

    st.markdown("---")

    # 탭 구성: 보고서 전문 / 펀더멘털 & 수급표 / 기술지표 데이터 / 파일 관리
    tab1, tab2, tab3, tab4 = st.tabs([
        "📑 종합 분석 보고서 (SOP 9개 섹션)",
        "📊 펀더멘털 & 세분화 수급 요약표",
        "📈 일봉 시세 & 보조지표 데이터",
        "💾 파일 다운로드 & 저장 관리"
    ])

    # [탭 1] 마크다운 보고서 전문
    with tab1:
        st.markdown(report_content)

    # [탭 2] 펀더멘털 & 수급 상세표
    with tab2:
        st.markdown("### 🏢 밸류에이션 및 최근 분기 실적 요약")
        f_data = [
            {"지표": "시가총액", "수치": fundamentals.get("market_cap", "N/A")},
            {"지표": "PER / PBR", "수치": f"{fundamentals.get('per', 'N/A')} / {fundamentals.get('pbr', 'N/A')}"},
            {"지표": "EPS / BPS", "수치": f"{fundamentals.get('eps', 'N/A')} / {fundamentals.get('bps', 'N/A')}"},
            {"지표": "배당수익률", "수치": fundamentals.get("dividend_yield", "N/A")},
            {"지표": f"최근 분기 매출액 ({fundamentals.get('latest_quarter', '최근분기')})", "수치": fundamentals.get("revenue", "N/A")},
            {"지표": "최근 분기 영업이익", "수치": fundamentals.get("operating_profit", "N/A")},
            {"지표": "영업이익률", "수치": fundamentals.get("op_margin", "N/A")},
            {"지표": "증권사 컨센서스 목표주가", "수치": fundamentals.get("target_price_consensus", "N/A")},
            {"지표": "증권사 투자의견", "수치": fundamentals.get("recomm_mean", "N/A")},
        ]
        st.table(pd.DataFrame(f_data))

        st.markdown("### 👥 투자 주체별 세분화 수급 분석 (1차 및 2차 기관)")
        col_sub1, col_sub2 = st.columns(2)

        with col_sub1:
            st.markdown("#### [1차] 최근 3거래일 주체별 누적 순매수")
            ind_val = investor_flow.get("individual_net_3d", 0)
            frg_val = investor_flow.get("foreign_net_3d", 0)
            ins_val = investor_flow.get("institution_net_3d", 0)
            flow_df1 = pd.DataFrame([
                {"투자 주체": "개인 (Individual)", "3일 누적 순매수": f"{ind_val:+,}주"},
                {"투자 주체": "외국인 (Foreigner)", "3일 누적 순매수": f"{frg_val:+,}주"},
                {"투자 주체": "기관 (Institution)", "3일 누적 순매수": f"{ins_val:+,}주"},
                {"투자 주체": "외국인 지분율", "3일 누적 순매수": str(investor_flow.get("foreign_holding_ratio", "N/A"))}
            ])
            st.table(flow_df1)

        with col_sub2:
            st.markdown("#### [2차] 기관 세부 주체별 분해 (추정)")
            inst_bk = investor_flow.get("institution_breakdown", {})
            flow_df2 = pd.DataFrame([
                {"세부 주체": "금융투자 (증권사)", "추정 순매수": f"{inst_bk.get('financial_investment', 0):+,}주", "성향": "단기 차익/패시브"},
                {"세부 주체": "연기금 등", "추정 순매수": f"{inst_bk.get('pension_fund', 0):+,}주", "성향": "중장기 가치/하방 지지"},
                {"세부 주체": "투신 (자산운용)", "추정 순매수": f"{inst_bk.get('investment_trust', 0):+,}주", "성향": "실적·모멘텀 액티브"},
                {"세부 주체": "보험 / 은행", "추정 순매수": f"{inst_bk.get('insurance_bank', 0):+,}주", "성향": "보수적 자산배분"}
            ])
            st.table(flow_df2)

    # [탭 3] 일봉 기술지표 데이터 및 HTS 인터랙티브 차트
    with tab3:
        st.markdown("### 📈 일봉 시세 및 증권사 HTS 멀티 패널 차트")
        daily_df = result.get("indicators", {}).get("daily", {}).get("series_df")
        if daily_df is not None and not daily_df.empty:
            view_mode = st.radio(
                "화면 표시 방식 선택:",
                options=["📊 HTS 인터랙티브 차트 보기", "📋 데이터 표로 보기"],
                horizontal=True,
                index=0
            )

            if view_mode == "📊 HTS 인터랙티브 차트 보기":
                st.caption("💡 캔들스틱, 이동평균선(5/20/60/120), 볼린저밴드(20,2), 매물대(POC), 거래량, RSI(14), MACD 4단 동기화 차트입니다. 마우스 휠로 확대/축소 및 드래그로 이동할 수 있습니다.")
                s_name = leader.get("name", "")
                s_code = leader.get("code", "")

                col_c1, col_c2 = st.columns([3, 7])
                with col_c1:
                    candle_count = st.selectbox(
                        "표시 캔들 기간 선택:",
                        options=[60, 90, 120],
                        index=1,
                        format_func=lambda x: f"최근 {x}거래일 캔들"
                    )

                fig = HtsChartEngine.build_hts_chart(
                    series_df=daily_df,
                    stock_name=s_name,
                    stock_code=s_code,
                    display_candles=candle_count
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.markdown("#### 최근 60거래일 일봉 시세 및 기술적 보조지표 데이터")
                display_df = daily_df.tail(60).copy()
                st.dataframe(display_df, use_container_width=True)
        else:
            st.info("표시할 일봉 데이터가 없습니다.")

    # [탭 4] 파일 관리 및 다운로드
    with tab4:
        st.markdown("### 💾 파일 다운로드 및 로컬/클라우드 저장소")
        d_col1, d_col2 = st.columns(2)

        excel_p = result.get("excel_path", "")
        if excel_p and os.path.exists(excel_p):
            with open(excel_p, "rb") as ef:
                d_col1.download_button(
                    label="📥 엑셀 분석 데이터 다운로드 (.xlsx)",
                    data=ef,
                    file_name=os.path.basename(excel_p),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

        html_p = result.get("html_path", "")
        if html_p and os.path.exists(html_p):
            with open(html_p, "r", encoding="utf-8") as hf:
                d_col2.download_button(
                    label="🌐 웹 보고서 다운로드 (.html)",
                    data=hf.read(),
                    file_name=os.path.basename(html_p),
                    mime="text/html",
                    use_container_width=True
                )

        st.markdown("---")
        st.markdown("#### 📂 구글 드라이브 연도별 폴더 열기")
        dest_dir = drive_files.get("dest_dir", "")
        st.write(f"현재 저장 경로: `{dest_dir}`")
        if st.button("📁 윈도우 탐색기에서 저장 폴더 열기", use_container_width=True):
            if os.path.exists(dest_dir):
                subprocess.Popen(f'explorer "{dest_dir}"')
                st.success(f"탐색기에서 폴더를 열었습니다: {dest_dir}")
            else:
                st.warning("폴더를 찾을 수 없습니다.")

else:
    # 아직 분석을 실행하지 않았을 때의 안내 화면
    st.info("👈 좌측 사이드바에서 **[테마주 대장주 분석]** 또는 **[특정 종목 분석]** 조건을 설정한 후 **'주식 정밀 분석 실행'** 버튼을 클릭하세요.")
    
    st.markdown("""
    ### 🎯 본 대시보드의 주요 기능
    1. **주도 테마 대장주 스크리닝**:
       - 실시간으로 가장 핫한 테마 중 사용자가 선택한 테마의 1등 대장주(Leader Score 1위)를 즉시 발굴합니다.
    2. **특정 종목 지정 심층 분석**:
       - 삼성전자, SK하이닉스 등 종목명 또는 코드를 입력하면 동일한 SOP 스킬에 따라 기술적/정성적 분석을 수행합니다.
    3. **정밀 펀더멘털 및 1차·2차 세분화 수급 분석**:
       - 시총, PER/PBR, 분기 실적 및 4대 호재/악재, 핵심 모니터링 변수를 도출합니다.
       - 개인/외인/기관(1차) 및 금융투자/연기금/투신/보험은행(2차)으로 수급 주체를 정밀 분해합니다.
    4. **구글 드라이브 연도별 자동 아카이빙**:
       - `G:\\내 드라이브\\120.주식종목분석\\{연도}\\` 폴더에 마크다운, HTML, 엑셀 파일을 전자동으로 영구 보관합니다.
    """)

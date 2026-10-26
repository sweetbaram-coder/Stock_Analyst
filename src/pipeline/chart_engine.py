"""src/pipeline/chart_engine.py — 증권사 HTS급 4단 인터랙티브 주식 차트 엔진
Plotly 기반 4개 수직 동기화 패널 (Shared X-axis):
1. 메인 패널: 일봉 캔들스틱 + 이동평균선(5/20/60/120) + 볼린저밴드(20, 2) + 매물대(Volume Profile/POC)
2. 거래량 패널: 일별 거래량(상승 빨강/하락 파랑) + 20일 거래량 이동평균선(VMA20)
3. RSI 패널: RSI(14) + 과열선(70) / 침체선(30)
4. MACD 패널: MACD(12, 26) + Signal(9) + MACD 오실레이터 바
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)

class HtsChartEngine:
    """증권사 HTS 스타일의 전문 인터랙티브 차트 생성기"""

    @staticmethod
    def calculate_volume_profile(df: pd.DataFrame, num_bins: int = 12) -> List[Dict[str, Any]]:
        """최근 데이터 기반 가격대별 누적 거래량 매물대(Volume Profile) 계산

        Returns:
            List[Dict]: 각 가격 구간(low, high, volume, pct, is_poc) 목록
        """
        if df.empty or len(df) < 5:
            return []

        min_price = float(df["low"].min())
        max_price = float(df["high"].max())
        if min_price >= max_price:
            return []

        bin_step = (max_price - min_price) / num_bins
        bins = [min_price + i * bin_step for i in range(num_bins + 1)]

        bin_volumes = [0.0] * num_bins

        # Typical Price = (High + Low + Close) / 3 기준으로 거래량 가중 누적
        for _, row in df.iterrows():
            typical = (row["high"] + row["low"] + row["close"]) / 3.0
            vol = float(row["volume"])
            for i in range(num_bins):
                if bins[i] <= typical <= bins[i + 1] or (i == num_bins - 1 and typical >= bins[i]):
                    bin_volumes[i] += vol
                    break

        total_vol = sum(bin_volumes) or 1.0
        max_vol = max(bin_volumes) if bin_volumes else 0.0

        profile = []
        for i in range(num_bins):
            v = bin_volumes[i]
            profile.append({
                "price_low": bins[i],
                "price_high": bins[i + 1],
                "price_mid": (bins[i] + bins[i + 1]) / 2.0,
                "volume": v,
                "pct": (v / total_vol) * 100.0,
                "is_poc": (v == max_vol and max_vol > 0)  # Point of Control (최대 매물대)
            })

        return profile

    @classmethod
    def build_hts_chart(
        cls,
        series_df: pd.DataFrame,
        stock_name: str = "",
        stock_code: str = "",
        display_candles: int = 90
    ) -> go.Figure:
        """증권사 HTS급 4단 연동 인터랙티브 차트 생성"""
        if series_df.empty:
            fig = go.Figure()
            fig.update_layout(title="차트 데이터가 없습니다.")
            return fig

        df = series_df.copy()
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        # 표시할 최근 캔들 개수 제한 (기본 최근 90거래일)
        if len(df) > display_candles:
            df = df.tail(display_candles).reset_index(drop=True)

        dates = df["date"]

        # 4단 서브플롯 생성: 메인(54%), 거래량(16%), RSI(15%), MACD(15%)
        fig = make_subplots(
            rows=4, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.025,
            row_heights=[0.54, 0.16, 0.15, 0.15],
            subplot_titles=(
                f"<b>{stock_name} ({stock_code})</b> 일봉 캔들스틱 / 이동평균선 / 볼린저밴드 / 매물대",
                "거래량 (Volume)",
                "RSI (14)",
                "MACD (12, 26, 9)"
            )
        )

        # ─────────────────────────────────────────────────────────────
        # [패널 1] 메인 차트: 볼린저밴드, 이동평균선, 캔들스틱
        # ─────────────────────────────────────────────────────────────

        # 1-1. 볼린저 밴드 (20, 2) 음영 오버레이
        if "bb_upper" in df.columns and "bb_lower" in df.columns:
            # 하단선
            fig.add_trace(
                go.Scatter(
                    x=dates, y=df["bb_lower"],
                    mode="lines",
                    line=dict(color="rgba(56, 189, 248, 0.6)", width=1, dash="dot"),
                    name="BB 하단",
                    hoverinfo="skip"
                ),
                row=1, col=1
            )
            # 상단선 및 채우기
            fig.add_trace(
                go.Scatter(
                    x=dates, y=df["bb_upper"],
                    mode="lines",
                    line=dict(color="rgba(56, 189, 248, 0.6)", width=1, dash="dot"),
                    fill="tonexty",
                    fillcolor="rgba(56, 189, 248, 0.08)",
                    name="볼린저밴드(20,2)",
                    hoverinfo="skip"
                ),
                row=1, col=1
            )

        # 1-2. 이동평균선 4종 (MA5, MA20, MA60, MA120)
        ma_configs = [
            ("ma5", "MA 5", "#ff6b6b", 1.5),     # 주홍/빨강
            ("ma20", "MA 20 (중심선)", "#f59e0b", 2.0), # 골드/노랑
            ("ma60", "MA 60", "#10b981", 1.5),   # 에메랄드 초록
            ("ma120", "MA 120", "#8b5cf6", 1.5), # 보라
        ]
        for col_name, label, color, width in ma_configs:
            if col_name in df.columns and df[col_name].notna().any():
                fig.add_trace(
                    go.Scatter(
                        x=dates, y=df[col_name],
                        mode="lines",
                        line=dict(color=color, width=width),
                        name=label,
                        hovertemplate=f"{label}: %{{y:,.0f}}원<extra></extra>"
                    ),
                    row=1, col=1
                )

        # 1-3. 일봉 캔들스틱 (한국 HTS 표준: 양봉 빨강, 음봉 파랑)
        fig.add_trace(
            go.Candlestick(
                x=dates,
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name="일봉 캔들",
                increasing=dict(
                    line=dict(color="#ef4444", width=1.2),
                    fillcolor="#ef4444"
                ),
                decreasing=dict(
                    line=dict(color="#3b82f6", width=1.2),
                    fillcolor="#3b82f6"
                ),
                hovertemplate=(
                    "<b>%{x|%Y-%m-%d}</b><br>"
                    "시가: %{open:,.0f}원<br>"
                    "고가: %{high:,.0f}원<br>"
                    "저가: %{low:,.0f}원<br>"
                    "종가: %{close:,.0f}원<extra></extra>"
                )
            ),
            row=1, col=1
        )

        # 1-4. 매물대(Volume Profile) 수평 바 오버레이
        profile = cls.calculate_volume_profile(df, num_bins=12)
        if profile and len(dates) > 10:
            # 오른쪽 끝 날짜를 기준으로 좌측으로 뻗어나가는 가로 바 렌더링
            last_date = dates.iloc[-1]
            total_days = len(dates)

            for item in profile:
                # 거래량 비율에 비례하여 바의 가로 길이(캔들 수) 결정 (최대 폭: 전체 캔들의 25%)
                bar_candles = int((item["pct"] / 100.0) * (total_days * 0.35))
                bar_candles = max(bar_candles, 1)

                start_idx = max(0, total_days - bar_candles)
                start_date = dates.iloc[start_idx]

                # POC(최대 매물대)는 골드 강조, 일반 매물대는 반투명 슬레이트
                if item["is_poc"]:
                    b_color = "rgba(245, 158, 11, 0.45)"
                    l_color = "rgba(245, 158, 11, 0.9)"
                    label_text = f"★최대매물(POC) {item['pct']:.1f}%"
                else:
                    b_color = "rgba(148, 163, 184, 0.22)"
                    l_color = "rgba(148, 163, 184, 0.5)"
                    label_text = f"{item['pct']:.1f}%"

                # 수평 사각형 박스 추가
                fig.add_shape(
                    type="rect",
                    xref="x1", yref="y1",
                    x0=start_date, y0=item["price_low"],
                    x1=last_date, y1=item["price_high"],
                    fillcolor=b_color,
                    line=dict(color=l_color, width=1),
                    layer="below"
                )

                # 매물대 비율 라벨 표기 (비율 6% 이상인 주요 매물대만 표시)
                if item["pct"] >= 6.0:
                    fig.add_annotation(
                        xref="x1", yref="y1",
                        x=last_date, y=item["price_mid"],
                        text=label_text,
                        showarrow=False,
                        xanchor="left",
                        font=dict(size=9, color="#b45309" if item["is_poc"] else "#64748b"),
                        bgcolor="rgba(255, 255, 255, 0.7)"
                    )

        # ─────────────────────────────────────────────────────────────
        # [패널 2] 거래량 차트 (Volume)
        # ─────────────────────────────────────────────────────────────
        # 전일비 상승/하락에 따른 거래량 바 색상 매핑
        price_diff = df["close"].diff().fillna(0)
        vol_colors = [
            "rgba(239, 68, 68, 0.85)" if d >= 0 else "rgba(59, 130, 246, 0.85)"
            for d in price_diff
        ]

        fig.add_trace(
            go.Bar(
                x=dates, y=df["volume"],
                marker_color=vol_colors,
                name="거래량",
                hovertemplate="거래량: %{y:,.0f}주<extra></extra>"
            ),
            row=2, col=1
        )

        if "vma20" in df.columns and df["vma20"].notna().any():
            fig.add_trace(
                go.Scatter(
                    x=dates, y=df["vma20"],
                    mode="lines",
                    line=dict(color="#64748b", width=1.5),
                    name="VMA 20",
                    hovertemplate="20일 평균거래량: %{y:,.0f}주<extra></extra>"
                ),
                row=2, col=1
            )

        # ─────────────────────────────────────────────────────────────
        # [패널 3] RSI (14)
        # ─────────────────────────────────────────────────────────────
        if "rsi14" in df.columns and df["rsi14"].notna().any():
            fig.add_trace(
                go.Scatter(
                    x=dates, y=df["rsi14"],
                    mode="lines",
                    line=dict(color="#8b5cf6", width=2),
                    name="RSI(14)",
                    hovertemplate="RSI(14): %{y:.1f}<extra></extra>"
                ),
                row=3, col=1
            )
            # 과열선 70 / 침체선 30 기준선 추가
            fig.add_hline(
                y=70, line_dash="dash", line_color="#ef4444", line_width=1,
                annotation_text="과열 (70)", annotation_position="right",
                annotation_font=dict(size=9, color="#ef4444"),
                row=3, col=1
            )
            fig.add_hline(
                y=30, line_dash="dash", line_color="#3b82f6", line_width=1,
                annotation_text="침체 (30)", annotation_position="right",
                annotation_font=dict(size=9, color="#3b82f6"),
                row=3, col=1
            )
            fig.update_yaxes(range=[10, 90], row=3, col=1)

        # ─────────────────────────────────────────────────────────────
        # [패널 4] MACD (12, 26, 9)
        # ─────────────────────────────────────────────────────────────
        if "macd" in df.columns and "macd_signal" in df.columns:
            # MACD선 및 Signal선
            fig.add_trace(
                go.Scatter(
                    x=dates, y=df["macd"],
                    mode="lines",
                    line=dict(color="#2563eb", width=1.5),
                    name="MACD",
                    hovertemplate="MACD: %{y:.2f}<extra></extra>"
                ),
                row=4, col=1
            )
            fig.add_trace(
                go.Scatter(
                    x=dates, y=df["macd_signal"],
                    mode="lines",
                    line=dict(color="#ea580c", width=1.5),
                    name="Signal",
                    hovertemplate="Signal: %{y:.2f}<extra></extra>"
                ),
                row=4, col=1
            )
            # MACD 오실레이터 바 (0선 기준)
            if "macd_osc" in df.columns:
                osc = df["macd_osc"]
                osc_colors = [
                    "rgba(239, 68, 68, 0.75)" if val >= 0 else "rgba(59, 130, 246, 0.75)"
                    for val in osc
                ]
                fig.add_trace(
                    go.Bar(
                        x=dates, y=osc,
                        marker_color=osc_colors,
                        name="Oscillator",
                        hovertemplate="Oscillator: %{y:.2f}<extra></extra>"
                    ),
                    row=4, col=1
                )
            fig.add_hline(y=0, line_color="#94a3b8", line_width=1, row=4, col=1)

        # ─────────────────────────────────────────────────────────────
        # HTS 공통 레이아웃 및 주말 갭 제거 (Rangebreaks)
        # ─────────────────────────────────────────────────────────────
        fig.update_layout(
            height=950,
            margin=dict(l=40, r=60, t=50, b=40),
            hovermode="x unified",
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.01,
                xanchor="right",
                x=1.0,
                font=dict(size=11)
            ),
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
            xaxis=dict(
                rangeslider=dict(visible=False),
                showgrid=True,
                gridcolor="#f1f5f9"
            )
        )

        # 주말 휴장일 빈 공간 제거 (연속 캔들 처리)
        fig.update_xaxes(
            rangebreaks=[dict(bounds=["sat", "mon"])],
            showgrid=True,
            gridcolor="#f1f5f9"
        )
        fig.update_yaxes(showgrid=True, gridcolor="#f1f5f9")

        # 패널별 Y축 타이틀 간소화
        fig.update_yaxes(title_text="가격(원)", row=1, col=1)
        fig.update_yaxes(title_text="거래량", row=2, col=1)
        fig.update_yaxes(title_text="RSI", row=3, col=1)
        fig.update_yaxes(title_text="MACD", row=4, col=1)

        return fig

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from auth import require_login
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

require_login()  # 로그인 되어 있지 않으면 여기서 차단됨

# 현재 연도 및 월 정보
this_year = datetime.today().year
current_month = datetime.today().month
months = list(range(1, 13))

# CSV 파일 불러오기
gs_target_path = st.secrets["google_sheets"]["gs_target_url"]
gs_result_path = st.secrets["google_sheets"]["gs_result_url"]
memo_path = st.secrets["google_sheets"]["memo_url"]

@st.cache_data(ttl=1800)
def load_data():
    df_target = pd.read_csv(gs_target_path)
    df_result = pd.read_csv(gs_result_path)
    df_memo = pd.read_csv(memo_path)
    df_target.columns = df_target.columns.str.strip()
    df_result.columns = df_result.columns.str.strip()
    df_memo.columns = df_memo.columns.str.strip()
    return df_target, df_result, df_memo

df_target, df_result, df_memo = load_data()

# 정량/정성 UID 구분
numeric_uids = df_target[df_target["지표 유형"] == "정량"]
textual_uids = df_target[df_target["지표 유형"] == "정성"]

numeric_kpi_tables = {}

for uid in numeric_uids["UID"].unique():
    kpi_name = df_target[df_target["UID"] == uid]["추진 목표"].iloc[0]
    df_uid = df_result[df_result["UID"] == uid].copy()
    df_uid["목표"] = pd.to_numeric(df_uid["목표"], errors="coerce").fillna(0)
    df_uid["실적"] = pd.to_numeric(df_uid["실적"], errors="coerce").fillna(0)

    row_목표 = {"주요 추진 목표": kpi_name, "구분": "목표"}
    row_실적 = {"구분": "실적"}
    row_차이 = {"구분": "목표比"}
    total_목표 = total_실적 = 0

    for m in months:
        m_df = df_uid[df_uid["월"] == m]
        m_target = m_df["목표"].sum()
        m_result = m_df["실적"].sum()
        row_목표[f"{m}월"] = m_target
        row_실적[f"{m}월"] = m_result

        # 누적값은 현재 월 - 1 까지만 집계, 차이값은 현재 월 - 1 까지만 표시
        if m <= current_month - 1:
            total_목표 += m_target
            total_실적 += m_result
            row_차이[f"{m}월"] = m_result - m_target
        else:
            row_차이[f"{m}월"] = None

    row_목표["누적"] = total_목표
    row_실적["누적"] = total_실적
    row_차이["누적"] = total_실적 - total_목표
    row_실적["주요 추진 목표"] = ""
    row_차이["주요 추진 목표"] = ""

    df_single = pd.DataFrame([row_목표, row_실적, row_차이])
    numeric_kpi_tables[kpi_name] = df_single

# 숫자 포맷 정리
for df in numeric_kpi_tables.values():
    numeric_cols = df.select_dtypes(include=["float", "int"]).columns
    df[numeric_cols] = df[numeric_cols].round(0).astype("Int64")

# 정성 KPI 처리
df_textual = df_result[df_result["UID"].isin(textual_uids["UID"])]
textual_kpi_rows = []

for uid in textual_uids["UID"].unique():
    kpi_name = df_target[df_target["UID"] == uid]["추진 목표"].iloc[0]
    df_kpi = df_textual[df_textual["UID"] == uid]
    row_target = {"UID": uid, "주요 추진 목표": kpi_name, "구분": "목표"}
    row_result = {"UID": uid, "주요 추진 목표": kpi_name, "구분": "실적"}
    for m in months:
        m_df = df_kpi[df_kpi["월"] == m]
        row_target[f"{m}월"] = m_df["목표"].iloc[0] if not m_df.empty else None
        row_result[f"{m}월"] = m_df["실적"].iloc[0] if not m_df.empty else None
    textual_kpi_rows.extend([row_target, row_result])

df_textual_fixed = pd.DataFrame(textual_kpi_rows)

# ─────────────────────────────────────────────────────────────
# 표 스타일(CSS)
# ─────────────────────────────────────────────────────────────
def highlight_row_if_diff(row):
    if row["구분"] != "목표比":
        return [''] * len(row)
    return ['color: blue' if isinstance(v, (int, float)) and v > 0 else
            'color: red' if isinstance(v, (int, float)) and v < 0 else ''
            for v in row]

format_dict = {
    col: "{:,.0f}"
    for df in numeric_kpi_tables.values()
    for col in df.columns
    if pd.api.types.is_numeric_dtype(df[col])
}

# 정량용 공통 표 CSS
custom_css = """
<style>
table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Noto Sans KR', sans-serif;
    font-size: 13px;
    line-height: 1.2;
}
th, td {
    padding: 3px 6px;
    text-align: right;
    border: 1px solid #ddd;
    vertical-align: middle;
    word-break: keep-all;
    white-space: pre-wrap;
}
thead {
    background-color: #f2f2f2;
    font-weight: bold;
}
.row_heading { display: none !important; }
.blank { display: none !important; }
</style>
"""

# ⬇️ 정성 표 전용 CSS (가독성 강화 + sticky 헤더/열 + 현재월 강조 + 카드형)
textual_css = """
<style>
.textual-wrap {
    overflow-y: auto;
    overflow-x: hidden;
    max-height: 78vh;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    background: #ffffff;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
table.textual {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
    line-height: 1.45;
    color: #111827;
}
table.textual thead th {
    position: sticky;
    top: 0;
    z-index: 3;
    background: #f8fafc;
    color: #374151;
    font-weight: 700;
    text-align: left;
    padding: 10px 12px;
    border-bottom: 1px solid #e5e7eb;
}
table.textual th, table.textual td {
    border-bottom: 1px solid #f1f5f9;
    vertical-align: top;
    padding: 8px 12px;
    word-wrap: break-word;
    white-space: pre-wrap;
}
table.textual th:nth-child(1), table.textual td:nth-child(1) { width: 56px; }
table.textual th:nth-child(2), table.textual td:nth-child(2) { width: 38%; }
table.textual th:nth-child(3), table.textual td:nth-child(3) { width: auto; }
table.textual tbody tr:nth-child(odd)  { background: #fcfcfd; }
table.textual tbody tr:nth-child(even) { background: #ffffff; }
table.textual tbody tr:hover { background: #f6faff; }
table.textual td:nth-child(1), table.textual th:nth-child(1) {
    position: sticky; left: 0;
    background: inherit; z-index: 2;
}
table.textual td:nth-child(2), table.textual th:nth-child(2) {
    position: sticky; left: 56px;
    background: inherit; z-index: 2;
    border-right: 1px solid #eef2f7;
}
.goal-badge {
    display: inline-block;
    background: #eef2ff;
    color: #3447d4;
    border: 1px solid #d9e1ff;
    border-radius: 8px;
    padding: 6px 10px;
    font-weight: 600;
    line-height: 1.35;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.6);
}
tr.current-row { 
    background: #fffdf5 !important;
    box-shadow: inset 3px 0 0 #f59e0b;
}
tr.current-row td:nth-child(1) { font-weight: 700; color: #92400e; }
.textual .result { line-height: 1.6; }
.muted { color: #9ca3af; }
.card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 12px;
}
.card {
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 12px;
    background: #ffffff;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
.card .chip {
    display: inline-block;
    border-radius: 999px;
    padding: 2px 8px;
    font-size: 12px;
    font-weight: 700;
    border: 1px solid #e5e7eb;
    background: #f8fafc;
    color: #374151;
    margin-right: 6px;
}
.card .goal {
    display: inline-block;
    margin-top: 6px;
    background: #eef2ff;
    color: #3447d4;
    border: 1px solid #d9e1ff;
    border-radius: 8px;
    padding: 4px 8px;
    font-weight: 600;
}
.card .result { margin-top: 8px; white-space: pre-wrap; }
</style>
"""

# 화면 구성
st.markdown(f"### {this_year}년 글로벌전략본부 주요 추진 목표")

kpi_counter = 1  # 공통 번호 시작

# 정량 KPI 그래프용 데이터 준비
df_result["목표"] = pd.to_numeric(df_result["목표"], errors="coerce").fillna(0)
df_result["실적"] = pd.to_numeric(df_result["실적"], errors="coerce").fillna(0)

# 그래프용 병합 데이터셋 (UID 기준)
df_plot_base = df_result.merge(df_target[["UID", "추진 목표"]], on="UID")

# ─────────────────────────────────────────────────────────────
# 정량 KPI 출력
# ─────────────────────────────────────────────────────────────
keys = list(numeric_kpi_tables.keys())
for i in range(0, len(keys), 2):
    col1, col2 = st.columns(2)
    for idx, col in enumerate([col1, col2]):
        if i + idx >= len(keys):
            break

        kpi_name = keys[i + idx]
        df_single = numeric_kpi_tables[kpi_name]

        with col:
            st.markdown(f"<h6>{kpi_counter}. {kpi_name}</h6>", unsafe_allow_html=True)
            kpi_counter += 1

            # 해당 KPI의 UID 가져오기
            uid = df_target[df_target["추진 목표"] == kpi_name]["UID"].iloc[0]
            df_plot = df_plot_base[df_plot_base["UID"] == uid]

            # 월별 집계 및 누적 계산
            df_plot = df_plot.groupby("월")[["목표", "실적"]].sum().reset_index()
            df_plot = df_plot[df_plot["월"].between(1, 12)]

            df_plot["누적 목표"] = df_plot["목표"].cumsum()
            df_plot["누적 실적"] = df_plot["실적"].cumsum()

            unit = df_target[df_target["UID"] == uid]["단위"].iloc[0]

            # 혼합형 그래프 생성
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_plot["월"], y=df_plot["목표"], name="월별 목표",
                marker_color="#333f50",
                hovertemplate=f'%{{y:,.0f}}{unit}, 월별 목표<extra></extra>'
            ))
            fig.add_trace(go.Bar(
                x=df_plot["월"], y=df_plot["실적"], name="월별 실적",
                marker_color="#8497b0",
                hovertemplate=f'%{{y:,.0f}}{unit}, 월별 실적<extra></extra>'
            ))
            fig.add_trace(go.Scatter(
                x=df_plot["월"], y=df_plot["누적 목표"], name="누적 목표",
                mode="lines+markers",
                line=dict(color="#ff7f0e", width=2.5),
                marker=dict(color="#ffffff", line=dict(color="#ff7f0e", width=1.5), size=6),
                yaxis="y2",
                hovertemplate=f'%{{y:,.0f}}{unit}, 누적 목표<extra></extra>'
            ))
            fig.add_trace(go.Scatter(
                x=df_plot["월"], y=df_plot["누적 실적"], name="누적 실적",
                mode="lines+markers",
                line=dict(color="#e31a1c", width=2.5),
                marker=dict(color="#ffffff", line=dict(color="#e31a1c", width=1.5), size=6),
                yaxis="y2",
                hovertemplate=f'%{{y:,.0f}}{unit}, 누적 실적<extra></extra>'
            ))

            fig.update_layout(
                barmode='group',
                yaxis2=dict(overlaying='y', side='right', showgrid=False),
                height=250,
                margin=dict(t=30, b=20),
                xaxis=dict(tickmode='linear', tick0=1, dtick=1),
                legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5),
                plot_bgcolor="#fafafa"
            )

            st.plotly_chart(fig, use_container_width=True, key=f"plot_{uid}")

            # 연간 목표 (1~12월 전체 합산 기준)
            df_uid = df_result[df_result["UID"] == uid].copy()
            df_uid["목표"] = pd.to_numeric(df_uid["목표"], errors="coerce").fillna(0)
            yearly_goal = df_uid[df_uid["월"].between(1, 12)]["목표"].sum()

            # 단위 텍스트
            unit_text = df_target[df_target["UID"] == uid]["단위"].iloc[0]

            # KPI 표 출력 (정량)
            df_display = df_single.drop(columns=["주요 추진 목표"])
            styled = df_display.style.apply(highlight_row_if_diff, axis=1).format(format_dict, na_rep="-")
            html_code = styled.to_html(index=False)

            st.markdown(
                f"""
                <div style='display:flex; justify-content:space-between; font-size:13px; font-weight:500; margin-bottom:2px;'>
                    <div style='color:#666;'>[연간목표: {int(yearly_goal):,}{unit_text}]</div>
                    <div style='color:#666;'>[단위: {unit_text}]</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            st.markdown(f"<div style='overflow-x:auto'>{custom_css + html_code}</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 정성 테이블/카드 HTML 생성 함수 (개선 UI)
# ─────────────────────────────────────────────────────────────
def generate_vertical_html_table(df, current_month:int):
    """
    df: 열에 '구분', '1월'..'12월'만 남긴 상태(두 행: 목표/실적)
    반환: sticky 헤더/열 + 현재월 하이라이트 적용한 HTML
    """
    months_cols = [f"{m}월" for m in range(1, 13)]

    def val(kind, mcol):
        s = df[df["구분"] == kind][mcol] if mcol in df.columns else pd.Series(dtype=object)
        if s.empty: return "-"
        v = s.values[0]
        if pd.isna(v) or v == "": return "-"
        return str(v).strip()

    # 월별 목표/실적 정리
    rows = [{"month": m, "target": val("목표", m), "result": val("실적", m)} for m in months_cols]

    # 연속 동일 목표 구간(rowspan) 계산
    groups = []
    i = 0
    while i < len(rows):
        j = i + 1
        while j < len(rows) and rows[j]["target"] == rows[i]["target"] and rows[i]["target"] not in ("-", ""):
            j += 1
        groups.append((i, j - 1))
        i = j

    # HTML 생성
    html = []
    html.append("<table class='textual'>")
    html.append("<thead><tr><th>월</th><th>목표</th><th>실적</th></tr></thead>")
    html.append("<tbody>")

    for start, end in groups:
        rowspan = end - start + 1
        for idx in range(start, end + 1):
            m  = rows[idx]["month"]
            t  = rows[idx]["target"]
            r  = rows[idx]["result"]
            tr_class = "current-row" if m == f"{current_month}월" else ""
            if idx == start:
                # 첫 행
                if t == "-" or rowspan == 1:
                    html.append(
                        f"<tr class='{tr_class}'>"
                        f"<td>{m}</td>"
                        f"<td class='muted'>-</td>"
                        f"<td class='result'>{r if r!='-' else '<span class=\"muted\">-</span>'}</td>"
                        f"</tr>"
                    )
                else:
                    html.append(
                        f"<tr class='{tr_class}'>"
                        f"<td>{m}</td>"
                        f"<td rowspan='{rowspan}'><span class='goal-badge'>{t}</span></td>"
                        f"<td class='result'>{r if r!='-' else '<span class=\"muted\">-</span>'}</td>"
                        f"</tr>"
                    )
            else:
                # 이어지는 행(목표 셀 생략)
                html.append(
                    f"<tr class='{tr_class}'>"
                    f"<td>{m}</td>"
                    f"<td class='result'>{r if r!='-' else '<span class=\"muted\">-</span>'}</td>"
                    f"</tr>"
                )

    html.append("</tbody></table>")
    return "".join(html)

def generate_card_view(df, current_month:int):
    months_cols = [f"{m}월" for m in range(1, 13)]

    def val(kind, mcol):
        s = df[df["구분"] == kind][mcol] if mcol in df.columns else pd.Series(dtype=object)
        if s.empty: return "-"
        v = s.values[0]
        return "-" if (pd.isna(v) or v == "") else str(v).strip()

    cards = []
    for m in months_cols:
        t = val("목표", m)
        r = val("실적", m)
        if t == "-" and r == "-":
            continue  # 완전 공란 월은 카드 생략
        chip_html = f"<span class='chip'>{m}{' · 현재' if m == f'{current_month}월' else ''}</span>"
        goal_html = f"<div class='goal'>{t}</div>" if t != "-" else "<div class='muted'>목표 없음</div>"
        result_html = f"<div class='result'>{r}</div>" if r != "-" else "<div class='result muted'>실적 없음</div>"
        cards.append(f"<div class='card'>{chip_html}{goal_html}{result_html}</div>")

    if not cards:
        return "<div class='muted'>표시할 데이터가 없습니다.</div>"
    return "<div class='card-grid'>" + "".join(cards) + "</div>"

# ─────────────────────────────────────────────────────────────
# 정성 KPI 출력 (향상된 UI: sticky, 현재월 강조, 카드형 대안)
# ─────────────────────────────────────────────────────────────
if not df_textual_fixed.empty:
    st.markdown(textual_css, unsafe_allow_html=True)

    # 보기 모드 선택 (표 / 카드)
    view_mode = st.radio(
        "정성 KPI 보기 모드",
        options=["표 보기", "카드 보기"],
        horizontal=True,
        index=0,
        key="textual_view_mode"
    )

    for uid in textual_uids["UID"].unique():
        kpi_name = df_target[df_target["UID"] == uid]["추진 목표"].iloc[0]
        st.markdown(f"<h6>{kpi_counter}. {kpi_name}</h6>", unsafe_allow_html=True)
        kpi_counter += 1

        df_kpi = df_textual_fixed[df_textual_fixed["UID"] == uid].copy()
        df_display = df_kpi.drop(columns=["UID", "주요 추진 목표"])

        if view_mode == "표 보기":
            vertical_html = generate_vertical_html_table(df_display, current_month=current_month)
            st.markdown(f"<div class='textual-wrap'>{vertical_html}</div>", unsafe_allow_html=True)
        else:
            card_html = generate_card_view(df_display, current_month=current_month)
            st.markdown(card_html, unsafe_allow_html=True)

# 메모 표시
st.markdown("---")
st.markdown(f"<h4>📝 {current_month}월 메모</h4>", unsafe_allow_html=True)

selected_memo = df_memo[
    (df_memo["년도"] == this_year) &
    (df_memo["월"] == current_month) &
    (df_memo["본부"].str.contains("글로벌전략본부", na=False))
]

# 메모 출력
if not selected_memo.empty:
    for _, row in selected_memo.iterrows():
        st.markdown(
            f"<div style='margin-bottom: 12px; padding: 10px; background-color: #eef5ff; border-left: 5px solid #3a7bd5;'>"
            f"입력자 : {row['입력자']}<br>"
            f"<strong>{row['메모']}</strong>"
            f"</div>",
            unsafe_allow_html=True
        )
else:
    st.info("해당 월의 메모가 없습니다.")

# Footer 출력
st.markdown("""
<style>
.footer {
    bottom: 0;
    left: 0;
    right: 0;
    padding: 8px;
    text-align: center;
    font-size: 13px;
    color: #666666;
    z-index: 100;
}
</style>
<div class="footer">
  ⓒ 2025 SeAH Special Steel Corp. All rights reserved.
</div>
""", unsafe_allow_html=True)

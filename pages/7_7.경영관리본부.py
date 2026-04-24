import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from auth import require_login
import warnings
from html import escape  # 메모 안전 이스케이프 및 공백/줄바꿈 보존용
warnings.filterwarnings('ignore')

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

require_login()  # 로그인 되어 있지 않으면 여기서 차단됨

# 현재 연도 및 월 정보
this_year = datetime.today().year
current_month = datetime.today().month
months = list(range(1, 13))

# CSV 파일 불러오기
fa_target_path = st.secrets["google_sheets"]["fa_target_url"]
fa_result_path = st.secrets["google_sheets"]["fa_result_url"]
memo_path = st.secrets["google_sheets"]["memo_url"]

@st.cache_data(ttl=1800)
def load_data():
    df_target = pd.read_csv(fa_target_path)
    df_result = pd.read_csv(fa_result_path)
    df_memo = pd.read_csv(memo_path)
    df_target.columns = df_target.columns.str.strip()
    df_result.columns = df_result.columns.str.strip()
    df_memo.columns = df_memo.columns.str.strip()
    return df_target, df_result, df_memo

df_target, df_result, df_memo = load_data()
df_result = df_result[df_result["년도"] == this_year]
df_target = df_target[df_target["년도"] == this_year]

# 정량/정성 UID 구분
numeric_uids = df_target[df_target["지표 유형"] == "정량"]
textual_uids = df_target[df_target["지표 유형"] == "정성"]

numeric_kpi_tables = {}

# =========================
# 정량 KPI 집계 (1~12월 전체 누적)
# =========================
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
        # 11~12월 전망까지 포함해서 1~12월 전부 반영
        m_df = df_uid[df_uid["월"] == m]
        m_target = m_df["목표"].sum()
        m_result = m_df["실적"].sum()

        row_목표[f"{m}월"] = m_target
        row_실적[f"{m}월"] = m_result
        row_차이[f"{m}월"] = m_result - m_target

        # 1~12월 전체 누적
        total_목표 += m_target
        total_실적 += m_result

    row_목표["누적"] = total_목표
    row_실적["누적"] = total_실적
    row_차이["누적"] = total_실적 - total_목표
    row_실적["주요 추진 목표"] = ""
    row_차이["주요 추진 목표"] = ""

    df_single = pd.DataFrame([row_목표, row_실적, row_차이])
    numeric_kpi_tables[kpi_name] = df_single

for df in numeric_kpi_tables.values():
    numeric_cols = df.select_dtypes(include=["float", "int"]).columns
    df[numeric_cols] = df[numeric_cols].round(0).astype("Int64")

# =========================
# 정성 KPI 처리
# =========================
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

# =========================
# 스타일링 함수 (정량)
# =========================
def highlight_row_if_diff(row):
    if row["구분"] != "목표比":
        return [''] * len(row)
    return ['color: blue' if isinstance(v, (int, float)) and v > 0 else
            'color: red' if isinstance(v, (int, float)) and v < 0 else ''
            for v in row]

format_dict = {col: "{:,.0f}" for df in numeric_kpi_tables.values()
               for col in df.columns if pd.api.types.is_numeric_dtype(df[col])}

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

# =========================
# 정성 KPI 전용 CSS (수직 레이아웃: 월 = 행)
# =========================
textual_css = """
<style>
table.textual-v {
    border-collapse: collapse;
    font-family: 'Noto Sans KR', sans-serif;
    font-size: 13px;
    line-height: 1.4;
    width: 50%;
    max-width: 100%;
}
table.textual-v thead {
    background-color: #f2f2f2;
    font-weight: bold;
}
table.textual-v th,
table.textual-v td {
    padding: 6px 10px;
    text-align: left;
    border: 1px solid #ddd;
    vertical-align: top;
    white-space: pre-wrap;
    word-break: break-word;
}
table.textual-v .month-col {
    width: 52px;
    min-width: 52px;
    text-align: center;
}
table.textual-v .content-col {
    min-width: 120px;
}
</style>
"""

# =========================
# 화면 구성 시작
# =========================
st.markdown(f"### {this_year}년 경영관리본부 주요 추진 목표")

kpi_counter = 1  # 공통 번호 시작

# 정량 KPI 그래프용 데이터 준비
df_result["목표"] = pd.to_numeric(df_result["목표"], errors="coerce").fillna(0)
df_result["실적"] = pd.to_numeric(df_result["실적"], errors="coerce").fillna(0)

# 그래프용 병합 데이터셋 (UID 기준)
df_plot_base = df_result.merge(df_target[["UID", "추진 목표"]], on="UID")

# =========================
# 정량 KPI 출력
# =========================
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

            # 월별 막대: 목표
            fig.add_trace(go.Bar(
                x=df_plot["월"],
                y=df_plot["목표"],
                name="월별 목표",
                marker_color="#333f50",
                hovertemplate=f'%{{y:,.0f}}{unit}, 월별 목표<extra></extra>'
            ))

            # 월별 막대: 실적
            fig.add_trace(go.Bar(
                x=df_plot["월"],
                y=df_plot["실적"],
                name="월별 실적",
                marker_color="#8497b0",
                hovertemplate=f'%{{y:,.0f}}{unit}, 월별 실적<extra></extra>'
            ))

            # 선: 누적 목표
            fig.add_trace(go.Scatter(
                x=df_plot["월"],
                y=df_plot["누적 목표"],
                name="누적 목표",
                mode="lines+markers",
                line=dict(color="#ff7f0e", width=2.5),
                marker=dict(color="#ffffff", line=dict(color="#ff7f0e", width=1.5), size=6),
                yaxis="y2",
                hovertemplate=f'%{{y:,.0f}}{unit}, 누적 목표<extra></extra>'
            ))

            # 선: 누적 실적
            fig.add_trace(go.Scatter(
                x=df_plot["월"],
                y=df_plot["누적 실적"],
                name="누적 실적",
                mode="lines+markers",
                line=dict(color="#e31a1c", width=2.5),
                marker=dict(color="#ffffff", line=dict(color="#e31a1c", width=1.5), size=6),
                yaxis="y2",
                hovertemplate=f'%{{y:,.0f}}{unit}, 누적 실적<extra></extra>'
            ))

            # 레이아웃 설정
            fig.update_layout(
                barmode='group',
                yaxis2=dict(overlaying='y', side='right', showgrid=False),
                height=250,
                margin=dict(t=30, b=20),
                xaxis=dict(tickmode='linear', tick0=1, dtick=1),
                legend=dict(orientation="h", yanchor="bottom", y=1.1,
                            xanchor="center", x=0.5),
                plot_bgcolor="#fafafa"
            )

            st.plotly_chart(fig, use_container_width=True, key=f"plot_{uid}")

            # 연간 목표 (1~12월 전체 합산 기준)
            df_uid = df_result[df_result["UID"] == uid].copy()
            df_uid["목표"] = pd.to_numeric(df_uid["목표"], errors="coerce").fillna(0)
            yearly_goal = df_uid[df_uid["월"].between(1, 12)]["목표"].sum()

            # KPI 표 출력
            df_display = df_single.drop(columns=["주요 추진 목표"])
            styled = df_display.style.apply(highlight_row_if_diff, axis=1).format(format_dict, na_rep="-")
            html_code = styled.to_html(index=False)

            # 위에 연간목표/단위 표시
            st.markdown(
                f"""
                <div style='display:flex; justify-content:space-between; font-size:13px; font-weight:500; margin-bottom:2px;'>
                    <div style='color:#666;'>[연간목표: {int(yearly_goal):,}{unit}]</div>
                    <div style='color:#666;'>[단위: {unit}]</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            st.markdown(f"<div style='overflow-x:auto'>{custom_css + html_code}</div>", unsafe_allow_html=True)

# =========================
# 정성 KPI용 셀 포맷 함수
# =========================
def format_text_cell(val):
    """정성 KPI 셀 텍스트용 포맷: 빈값 -> '-', 줄바꿈 -> <br>, HTML 이스케이프"""
    if pd.isna(val) or val == "":
        return "-"
    s = str(val)
    s = escape(s)  # <, &, " 등 이스케이프
    s = (
        s.replace("\\r\\n", "<br>")
         .replace("\\n", "<br>")
         .replace("\r\n", "<br>")
         .replace("\r", "<br>")
         .replace("\n", "<br>")
    )
    return s

# =========================
# 정성 KPI: 수직 레이아웃 (월 = 행, 목표/실적 = 열)
# =========================
def generate_merged_html_table(df):
    all_months = [f"{m}월" for m in range(1, 13)]

    target_row = df[df['구분'] == '목표'].iloc[0] if not df[df['구분'] == '목표'].empty else None
    result_row = df[df['구분'] == '실적'].iloc[0] if not df[df['구분'] == '실적'].empty else None

    # 데이터가 있는 월만 표시
    visible_months = []
    for m in all_months:
        t_val = target_row.get(m, "") if target_row is not None else ""
        r_val = result_row.get(m, "") if result_row is not None else ""
        if not ((pd.isna(t_val) or t_val == "") and (pd.isna(r_val) or r_val == "")):
            visible_months.append(m)

    if not visible_months:
        visible_months = all_months

    # 목표 열 rowspan 계산 (연속 동일 값 병합)
    target_vals = [target_row.get(m, "") if target_row is not None else "" for m in visible_months]
    rowspan_info = []  # (span, should_render)
    i = 0
    while i < len(visible_months):
        key = None if (pd.isna(target_vals[i]) or target_vals[i] == "") else str(target_vals[i])
        if key is None:
            rowspan_info.append((1, True))
            i += 1
        else:
            j = i + 1
            while j < len(visible_months):
                next_key = None if (pd.isna(target_vals[j]) or target_vals[j] == "") else str(target_vals[j])
                if next_key == key:
                    j += 1
                else:
                    break
            span = j - i
            rowspan_info.append((span, True))
            for _ in range(i + 1, j):
                rowspan_info.append((span, False))
            i = j

    html = "<table class='textual-v'><thead><tr><th class='month-col'>월</th><th class='content-col'>목표</th><th class='content-col'>실적</th></tr></thead><tbody>"

    for idx, m in enumerate(visible_months):
        html += "<tr>"
        html += f"<td class='month-col'>{m}</td>"

        span, should_render = rowspan_info[idx]
        if should_render:
            raw_val = target_row.get(m, "") if target_row is not None else ""
            cell_html = format_text_cell(raw_val)
            rs = f" rowspan='{span}'" if span > 1 else ""
            html += f"<td class='content-col'{rs}>{cell_html}</td>"

        raw_val = result_row.get(m, "") if result_row is not None else ""
        cell_html = format_text_cell(raw_val)
        html += f"<td class='content-col'>{cell_html}</td>"

        html += "</tr>"

    html += "</tbody></table>"
    return textual_css + html

# =========================
# 정성 KPI 출력
# =========================
if not df_textual_fixed.empty:
    for uid in textual_uids["UID"].unique():
        kpi_name = df_target[df_target["UID"] == uid]["추진 목표"].iloc[0]
        st.markdown(f"<h6>{kpi_counter}. {kpi_name}</h6>", unsafe_allow_html=True)
        kpi_counter += 1

        df_kpi = df_textual_fixed[df_textual_fixed["UID"] == uid].copy()
        df_display = df_kpi.drop(columns=["UID", "주요 추진 목표"])

        merged_html = generate_merged_html_table(df_display)
        st.markdown(f"<div style='overflow-x:auto'>{merged_html}</div>", unsafe_allow_html=True)

# =========================
# 메모 표시
# =========================
st.markdown("---")
st.markdown(f"<h4>📝 {current_month}월 메모</h4>", unsafe_allow_html=True)

selected_memo = df_memo[
    (df_memo["년도"] == this_year) &
    (df_memo["월"] == current_month) &
    (df_memo["본부"].str.contains("경영관리본부", na=False))
]

if not selected_memo.empty:
    for _, row in selected_memo.iterrows():
        writer = "" if pd.isna(row.get("입력자", "")) else escape(str(row["입력자"]))
        memo_text = "" if pd.isna(row.get("메모", "")) else escape(str(row["메모"]))

        st.markdown(
            f"""
            <div style='margin-bottom: 12px; padding: 10px; background-color: #eef5ff; border-left: 5px solid #3a7bd5;'>
                <div style='margin-bottom:6px; color:#333;'>입력자 : <strong>{writer}</strong></div>
                <div style='white-space: pre-wrap; font-weight:600;'>{memo_text}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
else:
    st.info("해당 월의 메모가 없습니다.")

# =========================
# Footer 출력
# =========================
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

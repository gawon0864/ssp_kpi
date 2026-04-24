import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from auth import require_login
import warnings
from html import escape  # ✅ 메모 안전 이스케이프 및 공백/줄바꿈 보존용
warnings.filterwarnings('ignore')

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

require_login()  # 로그인 되어 있지 않으면 여기서 차단됨

# 현재 연도 및 월 정보
this_year = datetime.today().year
current_month = datetime.today().month
months = list(range(1, 13))

# CSV 파일 불러오기
op_target_path = st.secrets["google_sheets"]["op_target_url"]
op_result_path = st.secrets["google_sheets"]["op_result_url"]
memo_path = st.secrets["google_sheets"]["memo_url"]

@st.cache_data(ttl=1800)
def load_data():
    df_target = pd.read_csv(op_target_path)
    df_result = pd.read_csv(op_result_path)    
    df_memo = pd.read_csv(memo_path)
    df_target.columns = df_target.columns.str.strip()
    df_result.columns = df_result.columns.str.strip()
    df_memo.columns = df_memo.columns.str.strip()
    return df_target, df_result, df_memo

df_target, df_result, df_memo = load_data()
df_result = df_result[df_result["년도"] == this_year]
df_target = df_target[df_target["년도"] == this_year]

# 실적=bar, 목표=line으로 표시할 UID
BAR_LINE_UIDS = {'OP2601', 'OP2602', 'OP2603'}

OP2601_YEARLY_GOAL_TEXT = "12월말 총재고 75,000톤 이하"
OP2602_YEARLY_GOAL_TEXT = "12월말 장기재고 2,500톤 이하"
OP2603_YEARLY_GOAL_TEXT = "장기채권 5.6억 전액 회수(신영스틸)"

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
        #여기서부터 변경함. 왜냐면 11월, 12월 전망도 입력했거든. 
        m_df = df_uid[df_uid["월"] == m]
        m_target = m_df["목표"].sum()
        m_result = m_df["실적"].sum()
        
        row_목표[f"{m}월"] = m_target
        row_실적[f"{m}월"] = m_result
        row_차이[f"{m}월"] = m_result - m_target

        # ✔ 현재월 제한 없이 12월까지 누적 계산
        total_목표 += m_target
        total_실적 += m_result


    #for m in months:
    #    m_df = df_uid[df_uid["월"] == m]
    #    m_target = m_df["목표"].sum()
    #    m_result = m_df["실적"].sum()
    #    row_목표[f"{m}월"] = m_target
    #    row_실적[f"{m}월"] = m_result
    #    row_차이[f"{m}월"] = m_result - m_target

        # 누적값은 현재 월 - 1 까지만 집계, 차이값은 현재 월 - 1 까지만 표시
        #if m <= current_month - 1:
        #    total_목표 += m_target
        #    total_실적 += m_result
        #    row_차이[f"{m}월"] = m_result - m_target
        #else:
        #    row_차이[f"{m}월"] = None

    #row_목표["누적"] = total_목표
    #row_실적["누적"] = total_실적
    #row_차이["누적"] = total_실적 - total_목표
    row_실적["주요 추진 목표"] = ""
    row_차이["주요 추진 목표"] = ""

    df_single = pd.DataFrame([row_목표, row_실적, row_차이])
    numeric_kpi_tables[kpi_name] = df_single

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

# 스타일링 함수
def highlight_row_if_diff(row):
    if row["구분"] != "목표比":
        return [''] * len(row)
    return ['color: blue' if isinstance(v, (int, float)) and v > 0 else
            'color: red' if isinstance(v, (int, float)) and v < 0 else ''
            for v in row]

format_dict = {col: "{:,.0f}" for df in numeric_kpi_tables.values() for col in df.columns if pd.api.types.is_numeric_dtype(df[col])}

custom_css = """
<style>
table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Noto Sans KR', sans-serif;
    font-size: 13px;
    line-height: 1.2;  /* 행 높이 줄임 */
}
th, td {
    padding: 3px 6px;  /* 세로 여백 줄임 */
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
    width: auto;
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

def format_text_cell(val):
    if pd.isna(val) or val == "":
        return "-"
    s = str(val)
    s = escape(s)
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

    visible_months = []
    for m in all_months:
        t_val = target_row.get(m, "") if target_row is not None else ""
        r_val = result_row.get(m, "") if result_row is not None else ""
        if not ((pd.isna(t_val) or t_val == "") and (pd.isna(r_val) or r_val == "")):
            visible_months.append(m)

    if not visible_months:
        visible_months = all_months

    target_vals = [target_row.get(m, "") if target_row is not None else "" for m in visible_months]
    rowspan_info = []
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


# 화면 구성
st.markdown(f"### {this_year}년 운영기획본부 주요 추진 목표")

kpi_counter = 1  # 공통 번호 시작

# 정량 KPI 그래프용 데이터 준비
df_result["목표"] = pd.to_numeric(df_result["목표"], errors="coerce").fillna(0)
df_result["실적"] = pd.to_numeric(df_result["실적"], errors="coerce").fillna(0)

# 그래프용 병합 데이터셋 (UID 기준)
df_plot_base = df_result.merge(df_target[["UID", "추진 목표"]], on="UID")

# 정량 KPI 출력 _ 커스터마이징 실행
keys = list(numeric_kpi_tables.keys())
textual_uid_list = list(textual_uids["UID"].unique()) if not df_textual_fixed.empty else []
for i in range(0, len(keys), 2):
    col1, col2 = st.columns(2)
    for idx, col in enumerate([col1, col2]):
        if i + idx >= len(keys):
            if idx == 1 and textual_uid_list:
                uid_t = textual_uid_list.pop(0)
                kpi_name_t = df_target[df_target["UID"] == uid_t]["추진 목표"].iloc[0]
                with col:
                    st.markdown(f"<h6>{kpi_counter}. {kpi_name_t}</h6>", unsafe_allow_html=True)
                    kpi_counter += 1
                    df_kpi_t = df_textual_fixed[df_textual_fixed["UID"] == uid_t].copy()
                    df_display_t = df_kpi_t.drop(columns=["UID", "주요 추진 목표"])
                    merged_html_t = generate_merged_html_table(df_display_t)
                    st.markdown(f"<div style='overflow-x:auto'>{merged_html_t}</div>", unsafe_allow_html=True)
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

            fig = go.Figure()

            if uid in BAR_LINE_UIDS:
                # 실적: 막대, 목표: 선
                fig.add_trace(go.Bar(
                    x=df_plot["월"],
                    y=df_plot["실적"],
                    name="월별 실적",
                    marker_color="#e74c3c",
                    hovertemplate=f'%{{y:,.0f}}{unit}, 월별 실적<extra></extra>'
                ))
                fig.add_trace(go.Scatter(
                    x=df_plot["월"],
                    y=df_plot["목표"],
                    name="월별 목표",
                    mode="lines+markers",
                    line=dict(color="#1a6b9a", width=2),
                    marker=dict(color="#ffffff", line=dict(color="#1a6b9a", width=2), size=6),
                    hovertemplate=f'%{{y:,.0f}}{unit}, 월별 목표<extra></extra>'
                ))
            else:
                # 월별 목표: 선 그래프
                fig.add_trace(go.Scatter(
                    x=df_plot["월"],
                    y=df_plot["목표"],
                    name="월별 목표",
                    mode="lines+markers",
                    line=dict(color="#333f50", width=2),
                    marker=dict(color="#ffffff", line=dict(color="#333f50", width=2), size=6),
                    hovertemplate=f'%{{y:,.0f}}{unit}, 월별 목표<extra></extra>'
                ))
                # 월별 실적: 선 그래프
                fig.add_trace(go.Scatter(
                    x=df_plot["월"],
                    y=df_plot["실적"],
                    name="월별 실적",
                    mode="lines+markers",
                    line=dict(color="#8497b0", width=2),
                    marker=dict(color="#ffffff", line=dict(color="#8497b0", width=2), size=6),
                    hovertemplate=f'%{{y:,.0f}}{unit}, 월별 실적<extra></extra>'
                ))

            # 레이아웃 설정
            fig.update_layout(
                barmode='group',
                height=250,
                margin=dict(t=30, b=20),
                xaxis=dict(tickmode='linear', tick0=1, dtick=1),
                legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5),
                plot_bgcolor="#fafafa"
            )

            st.plotly_chart(fig, use_container_width=True, key=f"plot_{uid}")

            # 단위 가져오기
            unit_text = df_target[df_target["UID"] == uid]["단위"].iloc[0]
            unit_html = f"<div style='text-align:right; font-size:13px; color:#666; margin-bottom:2px;'>[단위: {unit_text}]</div>"

            # KPI 표 출력
            df_display = df_single.drop(columns=["주요 추진 목표", "누적"], errors="ignore")
            styled = df_display.style.apply(highlight_row_if_diff, axis=1).format(format_dict, na_rep="-")
            html_code = styled.to_html(index=False)


            # 연간 목표 (1~12월 전체 합산 기준)
            df_uid_goal = df_result[df_result["UID"] == uid].copy()
            df_uid_goal["목표"] = pd.to_numeric(df_uid_goal["목표"], errors="coerce").fillna(0)
            yearly_goal = df_uid_goal[df_uid_goal["월"].between(1, 12)]["목표"].sum()

            # 왼쪽은 연간목표, 오른쪽은 단위 표시 (한 줄에)
            if uid == 'OP2601':
                yearly_goal_text = OP2601_YEARLY_GOAL_TEXT
            elif uid == 'OP2602':
                yearly_goal_text = OP2602_YEARLY_GOAL_TEXT
            elif uid == 'OP2603':
                yearly_goal_text = OP2603_YEARLY_GOAL_TEXT
            else:
                yearly_goal_text = f"{int(yearly_goal):,}{unit}"
            st.markdown(
                f"""
                <div style='display:flex; justify-content:space-between; font-size:13px; font-weight:500; margin-bottom:2px;'>
                    <div style='color:#666;'>[연간목표 : {yearly_goal_text}]</div>
                    <div style='color:#666;'>[단위: {unit}]</div>
                </div>
                """,
                unsafe_allow_html=True
            )

            # 표 출력
            st.markdown(f"<div style='overflow-x:auto'>{custom_css + html_code}</div>", unsafe_allow_html=True)



def format_text_cell(val):
    if pd.isna(val) or val == "":
        return "-"
    s = str(val)
    s = escape(s)
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

    visible_months = []
    for m in all_months:
        t_val = target_row.get(m, "") if target_row is not None else ""
        r_val = result_row.get(m, "") if result_row is not None else ""
        if not ((pd.isna(t_val) or t_val == "") and (pd.isna(r_val) or r_val == "")):
            visible_months.append(m)

    if not visible_months:
        visible_months = all_months

    target_vals = [target_row.get(m, "") if target_row is not None else "" for m in visible_months]
    rowspan_info = []
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



# 정성 KPI 출력
if textual_uid_list:
    for uid in textual_uid_list:
        kpi_name = df_target[df_target["UID"] == uid]["추진 목표"].iloc[0]
        st.markdown(f"<h6>{kpi_counter}. {kpi_name}</h6>", unsafe_allow_html=True)
        kpi_counter += 1

        df_kpi = df_textual_fixed[df_textual_fixed["UID"] == uid].copy()
        df_display = df_kpi.drop(columns=["UID", "주요 추진 목표"])

        merged_html = generate_merged_html_table(df_display)
        st.markdown(f"<div style='overflow-x:auto'>{merged_html}</div>", unsafe_allow_html=True)


# 메모 표시
st.markdown("---")

st.markdown(f"<h4>📝 {current_month}월 메모</h4>", unsafe_allow_html=True)

selected_memo = df_memo[
    (df_memo["년도"] == this_year) &
    (df_memo["월"] == current_month) &
    (df_memo["본부"].str.contains("운영기획본부", na=False))
]


# 메모 출력: 줄바꿈/여러 칸 띄어쓰기 그대로 보존 (white-space: pre-wrap)
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
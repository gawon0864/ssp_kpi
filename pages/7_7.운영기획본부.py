import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from auth import require_login
import warnings
from html import escape  # ✅ 메모 안전 이스케이프 및 공백/줄바꿈 보존용
warnings.filterwarnings('ignore')

st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

# require_login()  # 로그인 되어 있지 않으면 여기서 차단됨

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

            # 전월 실적 복사 로직: 실적이 0인 월 이후에도 마지막 실적 유지
            df_plot = df_plot.sort_values("월").reset_index(drop=True)

            # 마지막 0이 아닌 실적값 찾기
            last_nonzero_idx = df_plot[df_plot["실적"] != 0].last_valid_index()

            if last_nonzero_idx is not None:
                last_value = df_plot.loc[last_nonzero_idx, "실적"]
                for idx in range(last_nonzero_idx + 1, len(df_plot)):
                    if df_plot.loc[idx, "실적"] == 0:
                        df_plot.loc[idx, "실적"] = last_value

            unit = df_target[df_target["UID"] == uid]["단위"].iloc[0]

            # 혼합형 그래프 생성
            fig = go.Figure()

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

            # 단위 + 표 함께 출력
            st.markdown(f"<div style='overflow-x:auto'>{unit_html + custom_css + html_code}</div>", unsafe_allow_html=True)




# 정성 KPI 중 목표가 중복되면 열 병합
def generate_merged_html_table(df):
    months = [f"{m}월" for m in range(1, 13)]
    header_html = "<tr><th>구분</th>" + "".join(f"<th>{m}</th>" for m in months) + "</tr>"
    html = "<table class='textual'><thead>" + header_html + "</thead><tbody>"

    for idx, row in df.iterrows():
        html += "<tr>"
        html += f"<td style='text-align:left'>{row['구분']}</td>"

        if row['구분'] == "목표":
            last_val_key = None
            span = 0

            for m in months:
                raw_val = row.get(m, "")
                is_empty = pd.isna(raw_val) or raw_val == ""
                key = None if is_empty else str(raw_val)
                display_val = "-" if is_empty else str(raw_val)

                if key is not None and key == last_val_key:
                    span += 1
                else:
                    if last_val_key is not None:
                        if span > 1:
                            html += f"<td colspan='{span}' style='text-align:left'>{last_display_val}</td>"
                        else:
                            html += f"<td style='text-align:left'>{last_display_val}</td>"
                    if key is None:
                        html += f"<td style='text-align:left'>-</td>"
                        last_val_key = None
                        span = 0
                    else:
                        last_val_key = key
                        last_display_val = display_val
                        span = 1

            if last_val_key is not None and span > 0:
                if span > 1:
                    html += f"<td colspan='{span}' style='text-align:left'>{last_display_val}</td>"
                else:
                    html += f"<td style='text-align:left'>{last_display_val}</td>"

        else:  # 실적 행은 병합 없이 출력
            for m in months:
                val = row.get(m, "")
                val = "-" if pd.isna(val) or val == "" else str(val)
                html += f"<td style='text-align:left'>{val}</td>"

        html += "</tr>"

    html += "</tbody></table>"
    return custom_css + html



# 정성 KPI 출력
if not df_textual_fixed.empty:
    for uid in textual_uids["UID"].unique():
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
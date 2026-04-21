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
cj_target_path = st.secrets["google_sheets"]["cj_target_url"]
cj_result_path = st.secrets["google_sheets"]["cj_result_url"]
memo_path = st.secrets["google_sheets"]["memo_url"]

@st.cache_data(ttl=1800)
def load_data():
    df_target = pd.read_csv(cj_target_path)
    df_result = pd.read_csv(cj_result_path)
    df_memo = pd.read_csv(memo_path)
    df_target.columns = df_target.columns.str.strip()
    df_result.columns = df_result.columns.str.strip()
    df_memo.columns = df_memo.columns.str.strip()
    return df_target, df_result, df_memo

df_target, df_result, df_memo = load_data()
df_result = df_result[df_result["년도"] == this_year]
df_target = df_target[df_target["년도"] == this_year]

# 상/중/하 스택 그룹: 전체 UID → 서브 UID 매핑
STACKED_GROUPS = {
    'CJ2604': {
        'sub_uids': ['CJ2601', 'CJ2602', 'CJ2603'],
        'labels': ['상', '중', '하'],
    }
}
stacked_sub_uids = {uid for g in STACKED_GROUPS.values() for uid in g['sub_uids']}

CJ2605_YEARLY_GOAL_TEXT = "연간 Q-COST, 2.5억 이하"

# 정량/정성 UID 구분
numeric_uids = df_target[df_target["지표 유형"] == "정량"]
textual_uids = df_target[df_target["지표 유형"] == "정성"]

numeric_kpi_tables = {}

for uid in numeric_uids["UID"].unique():
    if uid in stacked_sub_uids:
        continue  # 상/중/하 개별 UID는 전체(CJ2605)로 통합 표시
    kpi_name = df_target[df_target["UID"] == uid]["추진 목표"].iloc[0]

    if uid in STACKED_GROUPS:
        # 12행 표: 목표/실적/목표比 × (전체/상/중/하)
        group = STACKED_GROUPS[uid]
        sub_uids_list = group['sub_uids']
        labels_list = group['labels']
        uid_label_pairs = [(uid, '전체')] + list(zip(sub_uids_list, labels_list))
        rows_목표, rows_실적, rows_차이 = [], [], []
        for row_uid, row_label in uid_label_pairs:
            df_uid = df_result[df_result["UID"] == row_uid].copy()
            df_uid["목표"] = pd.to_numeric(df_uid["목표"], errors="coerce").fillna(0)
            df_uid["실적"] = pd.to_numeric(df_uid["실적"], errors="coerce").fillna(0)
            row_t = {"주요 추진 목표": kpi_name if row_label == '전체' else "", "구분": f"목표({row_label})"}
            row_r = {"주요 추진 목표": "", "구분": f"실적({row_label})"}
            row_d = {"주요 추진 목표": "", "구분": f"목표比({row_label})"}
            total_t = total_r = 0
            for m in months:
                m_df = df_uid[df_uid["월"] == m]
                m_target = m_df["목표"].sum()
                m_result = m_df["실적"].sum()
                row_t[f"{m}월"] = m_target
                row_r[f"{m}월"] = m_result
                row_d[f"{m}월"] = m_result - m_target
                total_t += m_target
                total_r += m_result
            row_t["누적"] = total_t
            row_r["누적"] = total_r
            row_d["누적"] = total_r - total_t
            rows_목표.append(row_t)
            rows_실적.append(row_r)
            rows_차이.append(row_d)
        df_single = pd.DataFrame(rows_목표 + rows_실적 + rows_차이)

    else:
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
            row_차이[f"{m}월"] = m_result - m_target
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
    if not str(row["구분"]).startswith("목표比"):
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
    vertical-align: right;
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
st.markdown(f"### {this_year}년 충주공장 주요 추진 목표")

kpi_counter = 1  # 공통 번호 시작

# 정량 KPI 그래프용 데이터 준비
df_result["목표"] = pd.to_numeric(df_result["목표"], errors="coerce").fillna(0)
df_result["실적"] = pd.to_numeric(df_result["실적"], errors="coerce").fillna(0)

# 그래프용 병합 데이터셋 (UID 기준)
df_plot_base = df_result.merge(df_target[["UID", "추진 목표"]], on="UID")

# 정량 KPI 출력
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
            unit = df_target[df_target["UID"] == uid]["단위"].iloc[0]

            if uid in STACKED_GROUPS:
                # 상/중/하 스택 막대 + 전체 누적 선
                group = STACKED_GROUPS[uid]
                sub_uids = group['sub_uids']
                labels = group['labels']
                # 하→중→상 순으로 추가해야 상이 맨 위에 쌓임
                target_colors = ['#5dade2', '#1a6b9a', '#0d1b2a']
                result_colors = ['#f1948a', '#e74c3c', '#7b241c']

                fig = go.Figure()

                for k, (sub_uid, label) in enumerate(zip(reversed(sub_uids), reversed(labels))):
                    df_sub = df_plot_base[df_plot_base["UID"] == sub_uid]
                    df_sub = df_sub.groupby("월")[["목표", "실적"]].sum().reset_index()
                    df_sub = df_sub[df_sub["월"].between(1, 12)]
                    fig.add_trace(go.Bar(
                        x=df_sub["월"],
                        y=df_sub["목표"],
                        name=f"목표({label})",
                        marker_color=target_colors[k],
                        offsetgroup=0,
                        hovertemplate=f'%{{y:,.0f}}{unit}, 목표({label})<extra></extra>'
                    ))

                for k, (sub_uid, label) in enumerate(zip(reversed(sub_uids), reversed(labels))):
                    df_sub = df_plot_base[df_plot_base["UID"] == sub_uid]
                    df_sub = df_sub.groupby("월")[["목표", "실적"]].sum().reset_index()
                    df_sub = df_sub[df_sub["월"].between(1, 12)]
                    fig.add_trace(go.Bar(
                        x=df_sub["월"],
                        y=df_sub["실적"],
                        name=f"실적({label})",
                        marker_color=result_colors[k],
                        offsetgroup=1,
                        hovertemplate=f'%{{y:,.0f}}{unit}, 실적({label})<extra></extra>'
                    ))

                df_total = df_plot_base[df_plot_base["UID"] == uid]
                df_total = df_total.groupby("월")[["목표", "실적"]].sum().reset_index()
                df_total = df_total[df_total["월"].between(1, 12)]
                df_total["누적 목표"] = df_total["목표"].cumsum()
                df_total["누적 실적"] = df_total["실적"].cumsum()

                fig.add_trace(go.Scatter(
                    x=df_total["월"],
                    y=df_total["누적 목표"],
                    name="누적 목표",
                    mode="lines+markers",
                    line=dict(color="#ff7f0e", width=2.5),
                    marker=dict(color="#ffffff", line=dict(color="#ff7f0e", width=1.5), size=6),
                    yaxis="y2",
                    hovertemplate=f'%{{y:,.0f}}{unit}, 누적 목표<extra></extra>'
                ))
                fig.add_trace(go.Scatter(
                    x=df_total["월"],
                    y=df_total["누적 실적"],
                    name="누적 실적",
                    mode="lines+markers",
                    line=dict(color="#e31a1c", width=2.5),
                    marker=dict(color="#ffffff", line=dict(color="#e31a1c", width=1.5), size=6),
                    yaxis="y2",
                    hovertemplate=f'%{{y:,.0f}}{unit}, 누적 실적<extra></extra>'
                ))
                fig.update_layout(
                    barmode='relative',
                    yaxis2=dict(overlaying='y', side='right', showgrid=False),
                    height=250,
                    margin=dict(t=30, b=20),
                    xaxis=dict(tickmode='linear', tick0=1, dtick=1),
                    legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5),
                    plot_bgcolor="#fafafa"
                )

            else:
                df_plot = df_plot_base[df_plot_base["UID"] == uid]
                df_plot = df_plot.groupby("월")[["목표", "실적"]].sum().reset_index()
                df_plot = df_plot[df_plot["월"].between(1, 12)]
                df_plot["누적 목표"] = df_plot["목표"].cumsum()
                df_plot["누적 실적"] = df_plot["실적"].cumsum()

                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=df_plot["월"],
                    y=df_plot["목표"],
                    name="월별 목표",
                    marker_color="#333f50",
                    hovertemplate=f'%{{y:,.0f}}{unit}, 월별 목표<extra></extra>'
                ))
                fig.add_trace(go.Bar(
                    x=df_plot["월"],
                    y=df_plot["실적"],
                    name="월별 실적",
                    marker_color="#8497b0",
                    hovertemplate=f'%{{y:,.0f}}{unit}, 월별 실적<extra></extra>'
                ))
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

            # 단위 가져오기
            unit_text = df_target[df_target["UID"] == uid]["단위"].iloc[0]
            unit_html = f"<div style='text-align:right; font-size:13px; color:#666; margin-bottom:2px;'>[단위: {unit_text}]</div>"

            # KPI 표 출력
            df_display = df_single.drop(columns=["주요 추진 목표"])
            styled = df_display.style.apply(highlight_row_if_diff, axis=1).format(format_dict, na_rep="-")
            html_code = styled.to_html(index=False)

            # 왼쪽은 연간목표, 오른쪽은 단위 표시 (한 줄에)
            if uid == 'CJ2605':
                yearly_goal_text = CJ2605_YEARLY_GOAL_TEXT
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
    (df_memo["본부"].str.contains("충주공장", na=False))
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
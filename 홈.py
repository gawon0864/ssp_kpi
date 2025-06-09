import streamlit as st
from datetime import datetime
import calendar
import streamlit.components.v1 as components

st.set_page_config(
    page_title="세아특수강 본부별 성과관리 대시보드",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 현재 연월 기준으로 자동 선택
selected_year = datetime.today().year
selected_month = datetime.today().month

# 오늘 날짜
today = datetime.today()
today_day = today.day if (selected_month == today.month and selected_year == today.year) else -1

# 달력 HTML 생성 함수
def generate_calendar_html(year, month, today_day):
    cal = calendar.monthcalendar(year, month)
    html = "<table style='width:100%; border-collapse:collapse; font-size:15px;'>"
    html += "<thead><tr>" + "".join([
        f"<th style='padding:6px; border-bottom:1px solid #ccc; color:#1e88e5;'>{d}</th>"
        for d in ['월', '화', '수', '목', '금', '토', '일']
    ]) + "</tr></thead><tbody>"

    for week in cal:
        html += "<tr style='height:45px;'>"
        for day in week:
            if day == 0:
                html += "<td style='padding:10px; text-align:center; color:#ccc;'>-</td>"
            elif day == today_day:
                html += f"<td style='padding:10px; text-align:center; background:#1e88e5; color:#fff; border-radius:6px; font-weight:bold;'>{day}</td>"
            else:
                html += f"<td style='padding:10px; text-align:center;'>{day}</td>"
        html += "</tr>"
    html += "</tbody></table>"
    return html

calendar_html = generate_calendar_html(selected_year, selected_month, today_day)

# =========================
# CSS
# =========================
custom_home_css = """
<style>
body {
    background-color: #ffffff;
}
.centered {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    margin-top: 60px;
}
.centered img {
    margin-bottom: 20px;
}
h1 {
    font-size: 38px;
    font-weight: 700;
    color: #2c3e50;
}
h3 {
    font-size: 20px;
    font-weight: 500;
    color: #555;
    margin-top: 10px;
}
.flex-container {
    display: flex;
    justify-content: space-between;
    gap: 60px;
    margin: 40px auto;
    width: 90%;
}
.left-box {
    flex: 1;
}
.right-box {
    flex: 1;
    background: #f9fbfd;
    padding: 20px 30px;
    border-radius: 12px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.05);
}
.card {
    background-color: #f9fbfd;
    padding: 14px 18px;
    border-radius: 10px;
    margin-bottom: 16px;
    font-size: 15px;
    line-height: 1.5;
}
.card.selected {
    background-color: #e3f2fd;
    border-left: 5px solid #1e88e5;
    font-weight: 500;
}
.section-label {
    font-size: 16px;
    color: #1e88e5;
    font-weight: bold;
    margin-bottom: 10px;
}
.update-box {
    background-color: #e3f2fd;
    padding: 12px 16px;
    margin: 30px auto 10px;
    width: 90%;
    border-radius: 6px;
    font-size: 14px;
    color: #1e3a8a;
    text-align: center;
}
</style>
"""

st.markdown(custom_home_css, unsafe_allow_html=True)

# =========================
# 로고 + 타이틀
# =========================
st.markdown('<div class="centered">', unsafe_allow_html=True)
st.image("logo.gif", width=200)
st.markdown("<h1>세아특수강 본부별 성과관리 대시보드</h1>", unsafe_allow_html=True)
st.markdown("<h3>본부별 주요 추진 목표 및 실적 관리</h3>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# =========================
# 콘텐츠 박스
# =========================
html_main_content = f"""
<div class="flex-container">
    <div class="left-box">
        <div class="section-label">📌 대시보드 개요</div>
        <div class="card">
            세아특수강의 본부별 주요 추진 목표 및 실적을 체계적으로 관리하기 위한 DX 기반 성과관리 시스템입니다.<br>
            당월 기준 실적 비교, 누적 달성률, 메모 기반 질적 피드백 등을 한눈에 확인할 수 있습니다.
        </div>

        <div class="section-label">📂 대시보드 구성</div>
        <div class="card">🔹 <strong>정량 지표</strong>: 수치 기반의 주요 목표를 월별로 집계 및 시각화</div>
        <div class="card">🔹 <strong>정성 지표</strong>: 정성적 활동 기록을 월별로 정리</div>
        <div class="card">🔹 <strong>월별 메모</strong>: 각 본부별 월간 이슈 및 활동 메모 관리</div>

        <div class="section-label">🎯 활용 목적</div>
        <div class="card">
            주요 추진 목표 달성 현황을 직관적으로 파악하고, 월별 실행 성과와 차이를 분석하며<br>
            전략 방향성을 개선하기 위한 실시간 참고 자료로 사용 가능합니다.
        </div>
    </div>

    <div class="right-box">
        <div class="section-label">🗓 캘린더</div>
        <div style="text-align:center; font-size:18px; color:#555; margin-bottom:10px;">
            {selected_year}년 {selected_month}월
        </div>
        {calendar_html}
    </div>
</div>
"""

components.html(custom_home_css + html_main_content, height=550, scrolling=False)

# =========================
# 업데이트 표시
# =========================
st.markdown(f"""
<div class="update-box">
✅ 최근 업데이트: <strong>2025-05-27</strong> 기준 데이터가 반영되었습니다.
</div>
""", unsafe_allow_html=True)

# =========================
# Footer
# =========================
st.markdown("""
<style>
.footer {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 8px;
    background-color: rgba(255, 255, 255, 0.9);
    text-align: center;
    font-size: 13px;
    color: #666666;
    z-index: 100;
    box-shadow: 0 -1px 4px rgba(0, 0, 0, 0.05);
}
</style>

<div class="footer">
  ⓒ 2025 SeAH Special Steel Corp. All rights reserved.
</div>
""", unsafe_allow_html=True)
import streamlit as st
from datetime import datetime
import requests as py_requests
from urllib.parse import urlencode
import pandas as pd
import plotly.graph_objects as go

# ======== Google OAuth2 설정 ========
GOOGLE_CLIENT_ID = st.secrets["google_oauth"]["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = st.secrets["google_oauth"]["GOOGLE_CLIENT_SECRET"]
REDIRECT_URI = st.secrets["google_oauth"]["REDIRECT_URI"]

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

def get_authorization_url():
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"{AUTH_URL}?{urlencode(params)}"

def exchange_code_for_token(code):
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    response = py_requests.post(TOKEN_URL, data=data)
    return response.json()

def get_user_info(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = py_requests.get(USERINFO_URL, headers=headers)
    return response.json()

# ======== 인증 처리 ========
st.set_page_config(
    page_title="세아특수강 본부별 주요 추진 목표 및 실적 대시보드",
    layout="wide",
    initial_sidebar_state="expanded"
)

code = st.query_params.get("code", None)
user_info = None

if code:
    tokens = exchange_code_for_token(code)
    if tokens.get("access_token"):
        user_info = get_user_info(tokens["access_token"])
        st.session_state["user"] = user_info
else:
    user_info = st.session_state.get("user", None)

if not user_info:
    st.markdown("<h2>Google 로그인 필요</h2>", unsafe_allow_html=True)
    st.markdown("이 서비스를 이용하려면 Google 로그인이 필요합니다.")
    auth_url = get_authorization_url()
    st.markdown(f"[👉 Google 계정으로 로그인하기]({auth_url})", unsafe_allow_html=True)
    st.stop()

# ======== 프로필 표시 + 로그아웃 ========
def render_sidebar_profile(user):
    name = user.get("name", "사용자")
    email = user.get("email", "")
    picture_url = user.get("picture", "")

    with st.sidebar:
        st.markdown("""
        <style>
        .profile-name {
            font-size: 16px;
            margin-top: 10px;
            color: #1f2937;
        }
        .profile-email {
            font-size: 13px;
            color: #6b7280;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown('<div class="profile-box">', unsafe_allow_html=True)

        if picture_url:
            st.image(picture_url, width=80)

        st.markdown(f"<div class='profile-name'>{name}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='profile-email'>{email}</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        if st.button("🔓 로그아웃", key="logout_button"):
            for key in ["user"]:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()

render_sidebar_profile(user_info)

# ======== 스타일 ========
custom_home_css = """
<style>
body {
    background-color: #ffffff;
    margin: 0 !important;
    padding: 0 !important;
}
.block-container {
    padding-top: 1rem !important;
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
.flex-container {
    display: flex;
    justify-content: space-between;
    gap: 60px;
    margin: 40px auto;
    width: 90%;
}
.section-label {
    font-size: 16px;
    color: #000000;
    font-weight: bold;
    margin-bottom: 10px;
}
.card {
    background-color: #f9fbfd;
    padding: 14px 18px;
    border-radius: 10px;
    margin-bottom: 16px;
    font-size: 15px;
    line-height: 1.5;
}
</style>
"""
st.markdown(custom_home_css, unsafe_allow_html=True)

# ======== 상단 타이틀 ========
st.markdown('<div class="centered">', unsafe_allow_html=True)
st.image("logo.gif", width=200)
st.markdown("<h1>세아특수강 본부별 주요 추진 목표 및 실적</h1>", unsafe_allow_html=True)

# ======== 공공데이터 API 연동 함수 ========
@st.cache_data
def fetch_raw_material_data():
    url = "https://api.odcloud.kr/api/3039951/v1/uddi:b6699de8-3b19-4ab7-8ed7-894636ad6c6d_202004071625"
    service_key = st.secrets["api"]["raw_material_service_key"]

    params = {
        "page": 1,
        "perPage": 1000,
        "serviceKey": service_key
    }

    response = py_requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    df = pd.DataFrame(data["data"])
    df = df[["기간", "철광석(달러_톤)", "철스크랩(달러_톤)"]]
    df = df.sort_values("기간")
    return df

# ======== 그래프 생성 함수 ========
def create_price_chart(df):
    df_recent = df[df["기간"] >= "2022-01"]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_recent["기간"],
        y=df_recent["철광석(달러_톤)"],
        name="철광석 ($/톤)",
        mode="lines+markers",
        line=dict(color="#1f77b4", width=2),
        marker=dict(size=4),
        yaxis="y1"
    ))

    fig.add_trace(go.Scatter(
        x=df_recent["기간"],
        y=df_recent["철스크랩(달러_톤)"],
        name="철스크랩 ($/톤)",
        mode="lines+markers",
        line=dict(color="#aec7e8", width=2),
        marker=dict(size=4),
        yaxis="y2"
    ))

    fig.update_layout(
        title="📈 철강 원자재 가격 동향",
        xaxis_title="기간",
        yaxis=dict(
            title=dict(text="철광석 가격 ($/톤)", font=dict(color="#1f77b4")),
            tickfont=dict(color="#1f77b4"),
            side="left"
        ),
        yaxis2=dict(
            title=dict(text="철스크랩 가격 ($/톤)", font=dict(color="#aec7e8")),
            tickfont=dict(color="#aec7e8"),
            overlaying="y",
            side="right"
        ),
        height=420,
        margin=dict(t=100, l=20, r=20, b=20),
        xaxis_tickangle=-45,
        legend=dict(orientation="h", x=0.5, xanchor="center", y=1.15)
    )
    return fig


# ======== 본문 콘텐츠 구성 (좌: 설명 / 우: 그래프) ========
col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("<div class='section-label'>📌 대시보드 개요</div>", unsafe_allow_html=True)
    st.markdown("""
    <div class='card'>
        세아특수강의 본부별 주요 추진 목표 및 실적을 체계적으로 관리하기 위한 DX 기반 성과관리 시스템입니다.<br>
        당월 기준 실적 비교, 누적 달성률, 메모 기반 질적 피드백 등을 한눈에 확인할 수 있습니다.
    </div>
    <div class='section-label'>📂 대시보드 구성</div>
    <div class='card'>🔹 <strong>정량 지표</strong>: 수치 기반의 주요 목표를 월별로 집계 및 시각화</div>
    <div class='card'>🔹 <strong>정성 지표</strong>: 정성적 활동 기록을 월별로 정리</div>
    <div class='card'>🔹 <strong>월별 메모</strong>: 각 본부별 월간 이슈 및 활동 메모 관리</div>
    <div class='section-label'>🎯 활용 목적</div>
    <div class='card'>
        주요 추진 목표 달성 현황을 직관적으로 파악하고, 월별 실행 성과와 차이를 분석하며<br>
        전략 방향성을 개선하기 위한 실시간 참고 자료로 사용 가능합니다.
    </div>
    """, unsafe_allow_html=True)

with col2:
    df_price = fetch_raw_material_data()
    fig_price = create_price_chart(df_price)
    st.plotly_chart(fig_price, use_container_width=True)

# ======== 푸터 ========
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

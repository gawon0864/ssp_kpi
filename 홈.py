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

# ======== 자동차 생산량 그래프 생성 함수 ========
kama_path = st.secrets["google_sheets"]["kama_url"]

@st.cache_data
def load_data():
    df_kama = pd.read_csv(kama_path)
    df_kama.columns = df_kama.columns.str.strip()
    # 부품수출액 컬럼명 정규화 (괄호 문자 인코딩 차이 대응)
    export_col = next((c for c in df_kama.columns if "부품수출액" in c), None)
    if export_col and export_col != "부품수출액(백만불)":
        df_kama = df_kama.rename(columns={export_col: "부품수출액(백만불)"})
    df_kama["기간"] = df_kama["년"].astype(str) + "-" + df_kama["월"].astype(str).str.zfill(2)
    return df_kama

def create_vehicle_production_chart():
    df = load_data()

    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["기간"], y=df["국내생산"], name="국내생산", marker_color="#5dade2", yaxis="y1"))
    fig.add_trace(go.Bar(x=df["기간"], y=df["해외생산"], name="해외생산", marker_color="#1a6b9a", yaxis="y1"))
    fig.add_trace(go.Bar(x=df["기간"], y=df["KD"], name="KD", marker_color="#0d1b2a", yaxis="y1"))
    fig.add_trace(go.Scatter(
        x=df["기간"], y=df["부품수출액(백만불)"],
        name="부품수출액(백만불)",
        mode="lines+markers",
        line=dict(color="#e31a1c", width=2.5),
        marker=dict(color="#ffffff", line=dict(color="#e31a1c", width=1.5), size=4),
        yaxis="y2"
    ))

    fig.update_layout(
        barmode='stack',
        title="🚗 자동차 생산량 및 부품수출액 추이",
        xaxis_title="기간",
        yaxis=dict(title="생산량", side="left"),
        yaxis2=dict(title="부품수출액(백만불)", side="right", overlaying="y", showgrid=False),
        height=500,
        margin=dict(t=120, b=40, l=40, r=60),
        xaxis_tickangle=-45,
        legend=dict(orientation="h", x=0.5, xanchor="center", y=1.15)
    )
    return fig

# ======== 본문 콘텐츠 구성 ========
df_price = fetch_raw_material_data()
fig_price = create_price_chart(df_price)
st.plotly_chart(fig_price, use_container_width=True)

fig_production = create_vehicle_production_chart()
st.plotly_chart(fig_production, use_container_width=True)

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

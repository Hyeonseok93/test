import streamlit as st
import os
import pandas as pd
from groq import Groq

st.set_page_config(page_title="편의점 행사 대시보드", page_icon="🏪", layout="wide")

# 세션 메모리 초기화
if 'recent_keywords' not in st.session_state:
    st.session_state['recent_keywords'] = []

# 채팅 기록 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []


# CSS 로드 (모든 페이지 공통)
if os.path.exists("style.css"):
    with open("style.css", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# 챗봇용 커스텀 CSS (플로팅 버튼)
st.markdown("""
    <style>
    .floating-chatbot {
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 9999;
    }
    /* 팝오버 버튼 스타일 수정 (동그랗게) */
    div[data-testid="stPopover"] > button {
        border-radius: 50% !important;
        width: 60px !important;
        height: 60px !important;
        background-color: #58a6ff !important;
        color: white !important;
        border: none !important;
        font-size: 24px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 0 !important;
    }
    div[data-testid="stPopover"] > button:hover {
        transform: scale(1.1);
        transition: transform 0.2s;
    }
    </style>
""", unsafe_allow_html=True)

# 데이터 로드 (사이드바 통계용)
@st.cache_data(ttl=3600)
def get_summary_stats():
    file_path = os.path.join('data', 'categorized_data.csv')
    if not os.path.exists(file_path):
        return None
    df = pd.read_csv(file_path)
    return {
        "total_count": len(df),
        "brands_count": len(df['brand'].unique())
    }

# 사이드바 공통 영역
def show_sidebar():
    stats = get_summary_stats()
    if stats:
        st.sidebar.markdown("### 📊 실시간 현황")
        st.sidebar.write(f"✅ 총 행사 상품: **{stats['total_count']:,}개**")
        st.sidebar.write(f"🏢 참여 브랜드: **{stats['brands_count']}개**")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🤖 AI 도우미 설정")
    groq_api_key = st.sidebar.text_input("Groq API Key를 입력하세요", type="password")
    if groq_api_key:
        st.session_state.groq_api_key = groq_api_key
        st.sidebar.success("API Key 설정 완료!")
    else:
        st.sidebar.info("Groq API Key가 있어야 챗봇 사용이 가능합니다.")
        
    st.sidebar.markdown("---")
    st.sidebar.caption("© 2026 Convenience Store Dashboard")

# 챗봇 로직
def run_chatbot():
    # 데이터 로드 (챗봇용 컨텍스트)
    df = pd.read_csv('data/categorized_data.csv')
    
    with st.container():
        # 화면 오른쪽 하단에 고정된 팝오버
        with st.popover("🤖", help="AI 챗봇에게 물어보세요!"):
            st.markdown("### 🤖 편의점 득템 도우미")
            st.write("궁금한 행사 정보를 물어보세요! (예: 막걸리 안주 추천)")
            
            # 채팅 기록 출력
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # 채팅 입력
            if prompt := st.chat_input("메시지를 입력하세요..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                # API 키 확인
                if "groq_api_key" not in st.session_state or not st.session_state.groq_api_key:
                    with st.chat_message("assistant"):
                        st.error("사이드바에서 Groq API Key를 먼저 설정해주세요!")
                else:
                    client = Groq(api_key=st.session_state.groq_api_key)
                    
                    # 검색 키워드에 따른 관련 상품 선별 (간단한 검색 기반 컨텍스트 구성)
                    # 7천 개의 데이터를 다 넣으면 토큰 한도가 넘칠 수 있으므로 질문과 관련된 상위 30개만 추출
                    relevant_df = df[df['name'].str.contains(prompt[:4], case=False, na=False)].head(30)
                    if relevant_df.empty:
                        # 질문 키워드가 데이터에 없으면 랜덤하게 샘플링해서 제공
                        relevant_df = df.sample(n=min(len(df), 20))
                    
                    context = relevant_df[['brand', 'name', 'price', 'event', 'category']].to_string(index=False)
                    
                    with st.chat_message("assistant"):
                        response_placeholder = st.empty()
                        full_response = ""
                        
                        try:
                            # Groq API 호출
                            completion = client.chat.completions.create(
                                model="llama3-70b-8192",
                                messages=[
                                    {"role": "system", "content": f"당신은 편의점 행사 상품 전문가입니다. 아래 제공된 최신 행사 데이터(CSV 형태)를 바탕으로 사용자의 질문에 친절하고 똑똑하게 답변해주세요. 상품을 추천할 때는 브랜드, 가격, 행사 내용(1+1 등)을 구체적으로 언급해주세요. 한국어로 답변하세요.\n\n[행사 데이터 샘플]\n{context}"},
                                    {"role": "user", "content": prompt}
                                ],
                                temperature=0.7,
                                max_tokens=1024,
                                stream=True
                            )

                            for chunk in completion:
                                if chunk.choices[0].delta.content:
                                    full_response += chunk.choices[0].delta.content
                                    response_placeholder.markdown(full_response + "▌")
                            
                            response_placeholder.markdown(full_response)
                            st.session_state.messages.append({"role": "assistant", "content": full_response})
                        except Exception as e:
                            st.error(f"오류가 발생했습니다: {e}")

# 페이지 정의
home_page = st.Page("pages/00_home.py", title="🏠 메인보드", default=True)
summary_page = st.Page("pages/01_overall_summary.py", title="🔍 전체 요약")
comparison_page = st.Page("pages/02_brand_comparison.py", title="📊 브랜드 비교")
best_value_page = st.Page("pages/03_best_value.py", title="💎 가성비 TOP 50")
budget_page = st.Page("pages/04_budget_combination.py", title="🍱 내 예산 맞춤 꿀조합 생성기")
diet_guide_page = st.Page("pages/05_diet_guide.py", title="🏋️ 다이어트 & 식단 가이드")
night_snack_page = st.Page("pages/06_night_snack_guide.py", title="🌙 야식 & 안주 가이드")
random_picker_page = st.Page("pages/08_random_picker.py", title="🎁 럭키박스")
map_page = st.Page("pages/07_convenience_store_map.py", title="📍 편의점 지도")

# 내비게이션 구성
pg = st.navigation({
    "대시보드": [home_page],
    "상세 서비스": [summary_page, comparison_page, best_value_page, budget_page, diet_guide_page, night_snack_page, random_picker_page, map_page]
})

# 사이드바 실행
show_sidebar()

# 페이지 실행
pg.run()

# 챗봇 실행 (모든 페이지 하단에 플로팅 버튼으로 표시)
run_chatbot()

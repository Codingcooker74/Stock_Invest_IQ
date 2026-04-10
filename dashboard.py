import streamlit as st
import requests
import pandas as pd
import os
from openai import OpenAI
from dotenv import load_dotenv

# 1. 환경 변수 및 AI 세팅
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    st.error("🚨 .env 파일에 OPENAI_API_KEY가 설정되지 않았습니다.")
    st.stop()

client = OpenAI(api_key=API_KEY)

# 2. 서버 통신 및 AI 분석 함수 (이전과 동일)
def get_data_from_my_server(code):
    url = f"http://127.0.0.1:8000/분봉/{code}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        return None
    return None

def analyze_with_ai(code, stock_data):
    prompt = f"""
    너는 30년 경력의 여의도 스캘핑(초단타) 매매 최고수야.
    아래는 종목코드 {code}의 최근 5분간 1분봉 체결 데이터야.
    
    [데이터]
    {stock_data}
    
    이 데이터를 바탕으로 거래량 추이와 가격 변동을 날카롭게 분석해줘.
    결과는 반드시 아래 3가지 양식에 맞춰서 딱 3줄로만 명확하게 답변해.
    1. 흐름 요약: (1줄로)
    2. 매매 판단: (매수 / 매도 / 관망 중 택 1)
    3. 핵심 이유: (1줄로)
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a professional stock day-trader."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3 
    )
    return response.choices[0].message.content

# ==========================================
# 🎨 3. 스트림릿(Streamlit) 웹 화면 그리기
# ==========================================
st.set_page_config(page_title="AI 단타 관제탑", page_icon="📈", layout="centered")

st.title("🚀 AI 초단타 매매 관제탑")
st.markdown("---")

# 종목 코드 입력란
stock_code = st.text_input("🔍 분석할 종목코드를 입력하세요 (예: 삼성전자 005930, 카카오 035720)", "005930")

# 분석 버튼
if st.button("🔥 실시간 AI 분석 시작", use_container_width=True):
    
    # 로딩 애니메이션 띄우기
    with st.spinner('주방장(키움증권)이 데이터를 볶고, AI가 차트를 노려보는 중입니다...'):
        
        # 데이터 가져오기
        my_data = get_data_from_my_server(stock_code)
        
        if my_data and my_data.get('data'):
            # 성공 시 화면을 두 개의 단(Column)으로 나누기
            col1, col2 = st.columns([1, 1])
            
            # 데이터를 표(DataFrame)로 변환
            df = pd.DataFrame(my_data['data'])
            
            with col1:
                st.subheader("📊 최근 5분 가격 추세")
                # 가격 데이터를 꺾은선 차트로 예쁘게 그리기
                chart_data = df.set_index('time')
                st.line_chart(chart_data['price'])
                
            with col2:
                st.subheader("📝 원본 데이터")
                st.dataframe(df, use_container_width=True)
            
            st.markdown("---")
            st.subheader("🧠 AI 매매 브리핑 리포트")
            
            # AI 분석 요청 및 출력
            ai_report = analyze_with_ai(stock_code, my_data['data'])
            
            # AI의 답변에 따라 색상 다르게 표시
            if "매수" in ai_report:
                st.success(ai_report)
            elif "매도" in ai_report:
                st.error(ai_report)
            else:
                st.warning(ai_report)
                
        else:
            st.error("❌ 서버에서 데이터를 가져오지 못했습니다. FastAPI 서버(server_main.py)가 켜져 있는지 확인하세요.")
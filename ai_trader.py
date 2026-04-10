import os
import requests
from openai import OpenAI
from dotenv import load_dotenv

# 1. .env 파일에 있는 환경 변수들을 싹 다 불러오기
load_dotenv()

# 2. 불러온 환경 변수 중에서 OpenAI 키값만 쏙 빼오기
API_KEY = os.getenv("OPENAI_API_KEY")

# 방어 코드: 만약 키를 못 찾았다면 프로그램 멈추기
if not API_KEY:
    raise ValueError("🚨 API 키를 찾을 수 없습니다! 루트 디렉토리에 .env 파일이 있는지 확인하세요.")

# 안전하게 불러온 키로 OpenAI 통신 준비
client = OpenAI(api_key=API_KEY)

def get_data_from_my_server(code):
    """내가 만든 FastAPI 서버(홀 매니저)에게 데이터 가져오라고 시키기"""
    url = f"http://127.0.0.1:8000/분봉/{code}"
    print(f"📡 [1] 내 서버에 {code} 종목 데이터 요청 중...")
    
    response = requests.get(url)
    if response.status_code == 200:
        print("✅ [2] 데이터 수신 완료!\n")
        return response.json()
    else:
        print("❌ 서버에서 데이터를 가져오지 못했습니다.")
        return None

def analyze_with_ai(code, stock_data):
    """OpenAI에게 데이터 던져주고 분석 브리핑 받아오기"""
    print("🧠 [3] AI(GPT)에게 단타 분석 지시 중... (잠시 대기)\n")
    
    prompt = f"""
    너는 30년 경력의 여의도 스캘핑(초단타) 매매 최고수야.
    아래는 종목코드 {code}의 최근 5분간 1분봉 체결 데이터야.
    
    [데이터]
    {stock_data}
    
    이 데이터를 바탕으로 거래량 추이와 가격 변동을 날카롭게 분석해줘.
    결과는 반드시 아래 3가지 양식에 맞춰서 딱 3줄로만 명확하게 답변해.
    
    1. 흐름 요약: (1줄로 작성)
    2. 매매 판단: (매수 / 매도 / 관망 중 택 1)
    3. 핵심 이유: (1줄로 작성)
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

if __name__ == "__main__":
    target_code = "005930" 
    
    my_data = get_data_from_my_server(target_code)
    
    if my_data:
        ai_report = analyze_with_ai(target_code, my_data['data'])
        
        print("========================================")
        print("📊 [AI 단타 매매 브리핑 리포트]")
        print("========================================")
        print(ai_report)
        print("========================================")
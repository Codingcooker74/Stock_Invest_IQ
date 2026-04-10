import requests
import time
from indicators import calculate_squeeze, get_squeeze_signal

SERVER_URL = "http://127.0.0.1:8000"

def get_target_stocks():
    """서버에서 거래대금 상위 및 등락률 상위 종목을 가져와 합칩니다."""
    print("🔍 [상위 종목 리스트 갱신 중...]")
    
    try:
        # 1. 거래대금 상위 100위
        res_amount = requests.get(f"{SERVER_URL}/상위종목/amount")
        amount_list = res_amount.json().get('data', [])
        
        # 2. 등락률 상위 100위
        res_rate = requests.get(f"{SERVER_URL}/상위종목/rate")
        rate_list = res_rate.json().get('data', [])
        
        # 3. 리스트 합치고 중복 제거
        combined = {}
        for item in amount_list + rate_list:
            combined[item['code']] = item['name']
            
        print(f"✅ 총 {len(combined)}개 종목을 감시 대상으로 설정했습니다.")
        return combined
    except Exception as e:
        print(f"❌ 종목 리스트를 가져오는 중 오류 발생: {e}")
        return {}

def scan_stocks():
    print("=" * 60)
    print("🚀 Squeeze Breakout 실시간 종목 추천 시스템 (동적 스캔 모드)")
    print("=" * 60)
    
    watch_list = get_target_stocks()
    last_update_time = time.time()
    
    while True:
        if time.time() - last_update_time > 3600:
            watch_list = get_target_stocks()
            last_update_time = time.time()
            
        print(f"\n[스캔 시간: {time.strftime('%H:%M:%S')}] {len(watch_list)}개 종목 분석 중...")
        
        for code, name in watch_list.items():
            try:
                response = requests.get(f"{SERVER_URL}/분봉/{code}")
                if response.status_code != 200:
                    continue
                
                res_json = response.json()
                data = res_json.get('data', [])
                if len(data) < 30:
                    continue
                
                # 데이터 역순 (과거 -> 현재)
                data = data[::-1]
                
                # 지표 계산 (순수 파이썬 리스트 사용)
                analyzed_data = calculate_squeeze(data)
                if not analyzed_data:
                    continue
                
                # 신호 확인
                signal = get_squeeze_signal(analyzed_data)
                
                # 결과 출력
                price = analyzed_data[-1]['price']
                if "추천" in signal:
                    print(f"🔥 [추천] {name}({code}) | {price:,}원 | {signal}")
                
                time.sleep(0.2) 
                
            except Exception as e:
                continue
        
        print(f"\n[대기] 한 바퀴 완료! 10초 후 다음 스캔 시작...")
        time.sleep(10)

if __name__ == "__main__":
    scan_stocks()

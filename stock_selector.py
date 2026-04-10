import requests
import time
import json
from indicators import calculate_squeeze

SERVER_URL = "http://127.0.0.1:8000"

def calculate_confluence_score(data_list):
    """트리플 컨플루언스 점수 계산 (Squeeze + 이평선 + 거래량) - 순수 파이썬 버전"""
    if not data_list or len(data_list) < 20:
        return 0
    
    score = 0
    latest = data_list[-1]
    
    # 1. Squeeze 점수 (수축 중이면 가점)
    if latest.get('squeeze_on', False):
        score += 40
        
    # 2. 이평선 밀집도 (5, 20, 60일선이 현재가 근처에 모여 있는지)
    prices = [item['price'] for item in data_list]
    
    def get_sma(p_list, window):
        if len(p_list) < window: return 0
        return sum(p_list[-window:]) / window

    ma5 = get_sma(prices, 5)
    ma20 = get_sma(prices, 20)
    ma60 = get_sma(prices, 60)
    
    if ma5 and ma20 and ma60:
        ma_list = [ma5, ma20, ma60]
        ma_avg = sum(ma_list) / 3
        # 표준편차 간이 계산
        ma_variance = sum((x - ma_avg)**2 for x in ma_list) / 3
        ma_std = ma_variance ** 0.5
        density = ma_std / ma_avg
        
        if density < 0.02: # 2% 이내로 밀집
            score += 30
        elif density < 0.05:
            score += 15
        
    # 3. 거래량 점수 (최근 5일 평균 대비 오늘 거래량이 늘었는지)
    volumes = [item['volume'] for item in data_list]
    avg_vol = sum(volumes[-6:-1]) / 5 if len(volumes) >= 6 else 0
    
    if avg_vol > 0:
        if latest['volume'] > avg_vol * 1.5:
            score += 30
        elif latest['volume'] > avg_vol:
            score += 15
        
    return score

def select_top_100():
    print("🔍 [1/3] 시장 주도주 및 전체 종목 리스트 확보 중...")
    
    try:
        res_amount = requests.get(f"{SERVER_URL}/상위종목/amount")
        res_rate = requests.get(f"{SERVER_URL}/상위종목/rate")
        
        amount_data = res_amount.json().get('data', [])
        rate_data = res_rate.json().get('data', [])
        
        target_pool = {}
        for item in amount_data + rate_data:
            target_pool[item['code']] = item['name']
            
        # 🆕 [실패 방지] 만약 서버에서 종목을 못 가져오면 주요 우량주 10개를 강제로 분석합니다.
        if not target_pool:
            print("⚠️ 서버에서 상위 종목을 가져오지 못했습니다. 주요 우량주 10개를 대신 분석합니다.")
            target_pool = {
                "005930": "삼성전자",
                "000660": "SK하이닉스",
                "035420": "NAVER",
                "035720": "카카오",
                "005380": "현대차",
                "005490": "POSCO홀딩스",
                "000270": "기아",
                "068270": "셀트리온",
                "051910": "LG화학",
                "105560": "KB금융"
            }
            
        print(f"📊 [2/3] 총 {len(target_pool)}개 종목에 대해 트리플 컨플루언스 분석 시작...")
        
        scored_list = []
        for i, (code, name) in enumerate(target_pool.items()):
            try:
                res = requests.get(f"{SERVER_URL}/일봉/{code}")
                data = res.json().get('data', [])
                if not data: continue
                
                # 데이터 역순 정렬 (과거 -> 현재)
                data = data[::-1]
                
                # Squeeze 계산
                analyzed_data = calculate_squeeze(data)
                if not analyzed_data: continue
                
                score = calculate_confluence_score(analyzed_data)
                scored_list.append({
                    "code": code,
                    "name": name,
                    "score": score,
                    "price": analyzed_data[-1]['price']
                })
                
                if i % 10 == 0:
                    print(f"Progress: {i}/{len(target_pool)}...")
                
                time.sleep(0.2) # TR 제한 방지
            except Exception as e:
                continue
                
        # 점수 높은 순 정렬 후 상위 100개 추출
        top_100 = sorted(scored_list, key=lambda x: x['score'], reverse=True)[:100]
        
        print(f"✅ [3/3] 분석 완료! 상위 {len(top_100)}개 종목을 저장합니다.")
        
        with open("triple_targets.json", "w", encoding="utf-8") as f:
            json.dump(top_100, f, ensure_ascii=False, indent=4)
        
        print("🚀 triple_targets.json 저장 완료.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    select_top_100()

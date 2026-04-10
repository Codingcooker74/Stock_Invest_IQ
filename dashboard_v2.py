import streamlit as st
import requests
import time
import json
import os
from datetime import datetime
from indicators import calculate_squeeze, get_squeeze_signal

# 페이지 설정
st.set_page_config(page_title="Stock Invest IQ - Triple Confluence", layout="wide", page_icon="📈")

SERVER_URL = "http://127.0.0.1:8000"

def get_target_stocks(mode="top"):
    if mode == "triple_100":
        if os.path.exists("triple_targets.json"):
            try:
                with open("triple_targets.json", "r", encoding="utf-8") as f:
                    targets = json.load(f)
                    return {item['code']: item['name'] for item in targets}
            except:
                return {}
        else:
            st.error("⚠️ triple_targets.json 파일이 없습니다. stock_selector.py를 먼저 실행하세요.")
            return {}
            
    try:
        res_amount = requests.get(f"{SERVER_URL}/상위종목/amount")
        amount_list = res_amount.json().get('data', [])
        res_rate = requests.get(f"{SERVER_URL}/상위종목/rate")
        rate_list = res_rate.json().get('data', [])
        
        combined = {}
        for item in amount_list + rate_list:
            combined[item['code']] = item['name']
        return combined
    except:
        return {}

def main():
    st.title("🚀 Stock Invest IQ - 실시간 추천 시스템")
    
    # 사이드바 설정
    st.sidebar.header("⚙️ 설정")
    mode = st.sidebar.selectbox("🎯 감시 모드", ["실시간 주도주 스캔", "트리플 컨플루언스 100선"], index=0)
    refresh_rate = st.sidebar.slider("새로고침 주기 (초)", 10, 300, 30)
    max_scan = st.sidebar.number_input("최대 분석 종목 수", 10, 200, 100 if mode == "트리플 컨플루언스 100선" else 50)
    
    mode_key = "top" if mode == "실시간 주도주 스캔" else "triple_100"
    
    # 상태 요약 레이아웃
    col1, col2, col3 = st.columns(3)
    stat_total = col1.empty()
    stat_squeeze = col2.empty()
    stat_breakout = col3.empty()
    
    st.divider()
    
    # 결과 테이블 레이아웃
    st.subheader(f"🎯 {mode} - 실시간 분석 결과")
    table_placeholder = st.empty()
    
    # 로그 출력
    st.sidebar.divider()
    st.sidebar.subheader("📝 시스템 로그")
    log_placeholder = st.sidebar.empty()

    # 무한 루프 시작
    while True:
        watch_list = get_target_stocks(mode_key)
        target_codes = list(watch_list.keys())[:int(max_scan)]
        
        results = []
        squeeze_count = 0
        breakout_count = 0
        
        log_placeholder.text(f"마지막 업데이트: {datetime.now().strftime('%H:%M:%S')}\n{len(target_codes)}개 종목 분석 중...")
        
        for code in target_codes:
            name = watch_list[code]
            try:
                time.sleep(0.2) # TR 제한 준수
                
                response = requests.get(f"{SERVER_URL}/분봉/{code}")
                if response.status_code != 200: continue
                
                res_json = response.json()
                data = res_json.get('data', [])
                if len(data) < 30: continue
                
                # 데이터 역순 (과거 -> 현재)
                data = data[::-1]
                
                analyzed_data = calculate_squeeze(data)
                if not analyzed_data: continue
                
                signal = get_squeeze_signal(analyzed_data)
                latest = analyzed_data[-1]
                price = latest['price']
                
                status = "대기"
                if "Squeeze" in signal:
                    status = "🔹 응축중"
                    squeeze_count += 1
                if "추천" in signal:
                    status = "🚀 돌파발생"
                    breakout_count += 1
                
                results.append({
                    "종목명": name,
                    "코드": code,
                    "현재가": f"{price:,}원",
                    "상태": status,
                    "상세신호": signal,
                    "sort_val": 0 if "추천" in signal else (1 if "Squeeze" in signal else 2)
                })
            except:
                continue
        
        # 데이터프레임 표시 (리스트 오브 딕셔너리로 직접 표시)
        if results:
            # 정렬
            sorted_results = sorted(results, key=lambda x: x['sort_val'])
            # 표시용에서 sort_val 제거
            display_results = []
            for r in sorted_results:
                display_results.append({k: v for k, v in r.items() if k != 'sort_val'})
            
            table_placeholder.table(display_results)
        
        # 지표 업데이트
        stat_total.metric("총 감시 종목", f"{len(watch_list)}개")
        stat_squeeze.metric("에너지 응축(Squeeze)", f"{squeeze_count}개")
        stat_breakout.metric("매수 추천(Breakout)", f"{breakout_count}개", delta=breakout_count if breakout_count > 0 else None)
        
        time.sleep(refresh_rate)

if __name__ == "__main__":
    main()

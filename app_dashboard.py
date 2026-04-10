import streamlit as st
import pandas as pd
import requests
import time
import json
import os
from datetime import datetime
from indicators import calculate_squeeze, get_squeeze_signal

# 페이지 설정
st.set_page_config(page_title="Stock Invest IQ - 통합 대시보드", layout="wide", page_icon="🕹️")

SERVER_URL = "http://127.0.0.1:8000"

def check_server_status():
    try:
        res = requests.get(f"{SERVER_URL}/접속상태", timeout=1)
        return res.json().get('connected', False)
    except:
        return None # 서버 꺼짐

def calculate_confluence_score(df):
    if df is None or len(df) < 20: return 0
    score = 0
    latest = df.iloc[-1]
    if latest.get('squeeze_on', False): score += 40
    ma5 = df['price'].rolling(window=5).mean().iloc[-1]
    ma20 = df['price'].rolling(window=20).mean().iloc[-1]
    ma60 = df['price'].rolling(window=60).mean().iloc[-1]
    ma_std = pd.Series([ma5, ma20, ma60]).std()
    ma_avg = (ma5 + ma20 + ma60) / 3
    density = ma_std / ma_avg
    if density < 0.02: score += 30
    elif density < 0.05: score += 15
    avg_vol = df['volume'].rolling(window=5).mean().iloc[-2]
    if latest['volume'] > avg_vol * 1.5: score += 30
    elif latest['volume'] > avg_vol: score += 15
    return score

def main():
    st.sidebar.title("🕹️ 시스템 제어")
    
    # 1. 서버 상태 체크
    conn_status = check_server_status()
    if conn_status is None:
        st.sidebar.error("❌ API 서버(32bit)가 꺼져 있습니다.")
        st.info("먼저 'python server_main.py'를 실행해 주세요.")
        return
    elif conn_status is False:
        st.sidebar.warning("⚠️ 키움증권 미접속 상태")
        if st.sidebar.button("🔑 키움증권 로그인 실행"):
            requests.get(f"{SERVER_URL}/로그인")
            st.rerun()
    else:
        st.sidebar.success("✅ 키움증권 서버 연결됨")

    # 메뉴 선택
    menu = st.sidebar.radio("메뉴 선택", ["실시간 감시 대시보드", "종목 선정기 (트리플 100선)"])

    if menu == "종목 선정기 (트리플 100선)":
        st.header("🔍 트리플 컨플루언스 종목 선정")
        st.write("시장 주도주들을 분석하여 에너지가 응축된 상위 100개 종목을 골라냅니다.")
        
        if st.button("🚀 분석 및 선정 시작 (약 5~10분 소요)"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # 1. 타겟 풀 확보 (거래대금/등락률 상위)
                status_text.text("분석 대상 종목 리스트 확보 중...")
                res_amount = requests.get(f"{SERVER_URL}/상위종목/amount").json().get('data', [])
                res_rate = requests.get(f"{SERVER_URL}/상위종목/rate").json().get('data', [])
                
                target_pool = {item['code']: item['name'] for item in res_amount + res_rate}
                total = len(target_pool)
                scored_list = []

                for i, (code, name) in enumerate(target_pool.items()):
                    status_text.text(f"분석 중: {name}({code}) [{i+1}/{total}]")
                    try:
                        res = requests.get(f"{SERVER_URL}/일봉/{code}", timeout=5)
                        data = res.json().get('data', [])
                        
                        if data and len(data) >= 20:
                            # 1. 과거 -> 현재 순으로 정렬
                            data_sorted = data[::-1]
                            # 2. 지표 계산 (리스트 형태 유지)
                            analyzed_data = calculate_squeeze(data_sorted)
                            if analyzed_data:
                                # 3. 신호 추출 (마지막 데이터 기준)
                                signal = get_squeeze_signal(analyzed_data)
                                # 4. 분석 결과로 스코어 계산을 위한 DataFrame 생성
                                df_analyzed = pd.DataFrame(analyzed_data)
                                score = calculate_confluence_score(df_analyzed)
                                scored_list.append({"code": code, "name": name, "score": score})
                        else:
                            # 데이터가 부족한 종목은 스킵
                            pass
                    except Exception as e:
                        print(f"Error analyzing {name}: {e}")
                    
                    progress_bar.progress((i + 1) / total)
                    time.sleep(0.2) # TR 제한 방지를 위해 간격 유지

                if not scored_list:
                    st.error("❌ 분석된 종목이 없습니다. 서버 로그를 확인하세요.")
                else:
                    top_100 = sorted(scored_list, key=lambda x: x['score'], reverse=True)[:100]
                    with open("triple_targets.json", "w", encoding="utf-8") as f:
                        json.dump(top_100, f, ensure_ascii=False, indent=4)
                    st.success(f"✅ 선정 완료! {len(top_100)}개 종목이 저장되었습니다.")
            except Exception as e:
                st.error(f"오류 발생: {e}")

    elif menu == "실시간 감시 대시보드":
        st.header("🚀 실시간 종목 추적")
        
        # 설정
        col_set1, col_set2 = st.columns(2)
        mode = col_set1.selectbox("감시 대상", ["트리플 100선 (저장된 리스트)", "실시간 거래대금 상위"])
        refresh_rate = col_set2.slider("새로고침 주기 (초)", 10, 300, 30)

        # 종목 리스트 불러오기
        watch_list = {}
        if mode == "트리플 100선 (저장된 리스트)":
            if os.path.exists("triple_targets.json"):
                with open("triple_targets.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    watch_list = {item['code']: item['name'] for item in data}
            else:
                st.warning("먼저 '종목 선정기' 메뉴에서 종목을 추출해 주세요.")
        else:
            res = requests.get(f"{SERVER_URL}/상위종목/amount").json().get('data', [])
            watch_list = {item['code']: item['name'] for item in res}

        if watch_list:
            # 상태 요약 레이아웃
            m1, m2, m3 = st.columns(3)
            stat_total = m1.empty()
            stat_squeeze = m2.empty()
            stat_breakout = m3.empty()
            
            table_placeholder = st.empty()
            
            # 실시간 루프 (Streamlit의 특성상 세션 스테이트나 재귀 호출이 필요하지만 여기서는 단순 루프로 시연)
            # 실제 운영 시에는 st.empty()와 time.sleep()을 적절히 사용
            while True:
                results = []
                sq_cnt, brk_cnt = 0, 0
                codes = list(watch_list.keys())[:50] # 속도를 위해 상위 50개 우선 분석
                
                for code in codes:
                    try:
                        res = requests.get(f"{SERVER_URL}/분봉/{code}").json().get('data', [])
                        if len(res) < 30: continue
                        
                        # 1. 과거 -> 현재 순으로 정렬
                        data_sorted = res[::-1]
                        # 2. 지표 계산
                        analyzed_data = calculate_squeeze(data_sorted)
                        if not analyzed_data: continue
                        
                        signal = get_squeeze_signal(analyzed_data)
                        price = analyzed_data[-1]['price']
                        
                        status = "대기"
                        if "Squeeze" in signal: 
                            status = "🔹 응축중"
                            sq_cnt += 1
                        if "추천" in signal: 
                            status = "🚀 돌파발생"
                            brk_cnt += 1
                        
                        results.append({"종목명": watch_list[code], "코드": code, "현재가": f"{price:,}", "상태": status, "신호": signal})
                        time.sleep(0.1)
                    except: continue
                
                if results:
                    df_res = pd.DataFrame(results)
                    df_res['sort'] = df_res['상태'].map({"🚀 돌파발생": 0, "🔹 응축중": 1, "대기": 2})
                    df_res = df_res.sort_values('sort').drop(columns=['sort'])
                    table_placeholder.dataframe(df_res, use_container_width=True)
                
                stat_total.metric("감시 종목", f"{len(watch_list)}개")
                stat_squeeze.metric("Squeeze 응축", f"{sq_cnt}개")
                stat_breakout.metric("매수 추천", f"{brk_cnt}개")
                
                time.sleep(refresh_rate)
                st.rerun() # 화면 갱신

if __name__ == "__main__":
    main()

import sys
import threading
import time
import queue
import uvicorn
import random
from fastapi import FastAPI
from PyQt5.QtWidgets import QApplication
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QEventLoop, QTimer

app = FastAPI()
kiwoom_api = None

# 테스트 모드 설정 (True일 경우 로그인 없이도 가짜 데이터를 생성하여 반환합니다)
# 실제 키움증권 서버와 통신하려면 False로 설정하세요.
TEST_MODE = False 

if TEST_MODE:
    print("⚠️ 현재 [테스트 모드]입니다. 가짜 데이터를 사용합니다.")
else:
    print("🚀 현재 [실전 모드]입니다. 키움증권 서버와 통신을 시도합니다.")

# 🆕 주방장과 홀 매니저가 소통할 '주문 전표 꽂이(Queue)'와 '완성품 창구'
order_queue = queue.Queue()
ready_food = {}

class KiwoomAPI:
    def __init__(self):
        self.kiwoom = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        if self.kiwoom.isNull():
            print("❌ 오류: Kiwoom OpenAPI+ OCX를 불러오지 못했습니다. 설치 및 32bit 환경을 확인하세요.")
            sys.exit()
            
        self.kiwoom.OnEventConnect.connect(self.event_connect)
        self.kiwoom.OnReceiveTrData.connect(self.receive_tr_data)
        self.kiwoom.OnReceiveMsg.connect(self.receive_msg)
        
        self.login_loop = QEventLoop()
        self.tr_loop = None # 개별 요청마다 생성
        self.recent_data = [] 
        self.top_stock_list = []
        self.is_processing = False

    def login(self):
        print("키움증권 서버 로그인 중...")
        self.kiwoom.dynamicCall("CommConnect()")
        self.login_loop.exec_()

    def event_connect(self, err_code):
        if err_code == 0:
            print("🚀 로그인 완료! (서버 항시 대기 모드 가동)\n")
        else:
            print(f"❌ 로그인 실패! 에러 코드: {err_code}")
        if self.login_loop.isRunning():
            self.login_loop.exit()

    def get_minute_data(self, code):
        self.recent_data = [] 
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "틱범위", "1")
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")
        res = self.kiwoom.dynamicCall("CommRqData(QString, QString, int, QString)", "주식분봉조회", "opt10080", 0, "1001")
        if res == 0:
            self.tr_loop = QEventLoop()
            self.tr_loop.exec_() 
        else:
            print(f"❌ TR 요청 실패 (주식분봉조회): {res}")
        return self.recent_data

    def get_daily_data(self, code):
        self.recent_data = [] 
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "기준일자", time.strftime('%Y%m%d'))
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1")
        res = self.kiwoom.dynamicCall("CommRqData(QString, QString, int, QString)", "주식일봉조회", "opt10081", 0, "1004")
        if res == 0:
            self.tr_loop = QEventLoop()
            self.tr_loop.exec_() 
        else:
            print(f"❌ TR 요청 실패 (주식일봉조회): {res}")
        return self.recent_data

    def get_top_stocks(self, tr_type):
        self.top_stock_list = []
        if tr_type == "amount": # 거래대금상위
            self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "시장구분", "000") # 전체
            self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "관리종목포함", "0")
            res = self.kiwoom.dynamicCall("CommRqData(QString, QString, int, QString)", "거래대금상위", "opt10032", 0, "1002")
        elif tr_type == "rate": # 등락률상위
            self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "시장구분", "000")
            self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "등락구분", "1") # 급등
            self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "시간구분", "1")
            self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "종목조건", "1")
            self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "거래량조건", "0050") # 5만주 이상
            res = self.kiwoom.dynamicCall("CommRqData(QString, QString, int, QString)", "등락률상위", "opt10027", 0, "1003")
        
        if res == 0:
            self.tr_loop = QEventLoop()
            self.tr_loop.exec_()
        else:
            print(f"❌ TR 요청 실패 ({tr_type}): {res}")
        return self.top_stock_list

    def get_all_codes(self, market_type):
        """market_type: '0' (코스피), '10' (코스닥)"""
        ret = self.kiwoom.dynamicCall("GetCodeListByMarket(QString)", market_type)
        code_list = ret.split(';')
        return [{"code": code, "name": self.kiwoom.dynamicCall("GetMasterCodeName(QString)", code)} for code in code_list if code]

    def check_order(self):
        if self.is_processing or order_queue.empty():
            return
            
        self.is_processing = True
        try:
            order_id, cmd, payload = order_queue.get()
            if cmd == "minute_data":
                data = self.get_minute_data(payload)
                ready_food[order_id] = data
            elif cmd == "daily_data":
                data = self.get_daily_data(payload)
                ready_food[order_id] = data
            elif cmd == "top_stocks":
                data = self.get_top_stocks(payload)
                ready_food[order_id] = data
            elif cmd == "all_codes":
                data = self.get_all_codes(payload)
                ready_food[order_id] = data
        finally:
            self.is_processing = False

    def receive_tr_data(self, screen_no, rqname, trcode, recordname, prev_next, data_len, err_code, msg1, msg2):
        print(f"📥 TR 수신: {rqname} ({trcode})")
        
        if rqname == "주식분봉조회":
            count = self.kiwoom.dynamicCall("GetRepeatCnt(QString, QString)", trcode, recordname)
            fetch_count = min(count, 100) 
            for i in range(fetch_count):
                time_str = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, recordname, i, "체결시간").strip()
                if not time_str or len(time_str) < 12: continue 
                hour, minute = time_str[8:10], time_str[10:12]
                price = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, recordname, i, "현재가").strip()
                volume = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, recordname, i, "거래량").strip()
                self.recent_data.append({"time": f"{hour}:{minute}", "price": abs(int(price or 0)), "volume": int(volume or 0)})
        
        elif rqname == "주식일봉조회":
            count = self.kiwoom.dynamicCall("GetRepeatCnt(QString, QString)", trcode, recordname)
            fetch_count = min(count, 60)
            for i in range(fetch_count):
                date = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, recordname, i, "일자").strip()
                price = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, recordname, i, "현재가").strip()
                volume = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, recordname, i, "거래량").strip()
                if not date: continue
                self.recent_data.append({"date": date, "price": abs(int(price or 0)), "volume": int(volume or 0)})
        
        elif rqname == "거래대금상위":
            count = self.kiwoom.dynamicCall("GetRepeatCnt(QString, QString)", trcode, recordname)
            for i in range(count):
                code = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, recordname, i, "종목코드").strip()
                name = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, recordname, i, "종목명").strip()
                clean_code = code.replace('A', '')
                if clean_code: self.top_stock_list.append({"code": clean_code, "name": name})
        
        elif rqname == "등락률상위":
            count = self.kiwoom.dynamicCall("GetRepeatCnt(QString, QString)", trcode, recordname)
            for i in range(count):
                code = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, recordname, i, "종목코드").strip()
                name = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, recordname, i, "종목명").strip()
                clean_code = code.replace('A', '')
                if clean_code: self.top_stock_list.append({"code": clean_code, "name": name})
                
        if self.tr_loop and self.tr_loop.isRunning():
            self.tr_loop.exit()

    def receive_msg(self, screen_no, rqname, trcode, msg):
        print(f"💬 서버 메시지: {msg}")

# ========================================================
# 🛎️ 홀 매니저의 주문 접수 창구
# ========================================================
@app.get("/접속상태")
def get_status():
    if TEST_MODE: return {"status": "success", "connected": True}
    state = kiwoom_api.kiwoom.dynamicCall("GetConnectState()")
    return {"status": "success", "connected": True if state == 1 else False}

@app.get("/로그인")
def do_login():
    if TEST_MODE: return {"status": "success", "message": "테스트 모드입니다."}
    kiwoom_api.kiwoom.dynamicCall("CommConnect()")
    return {"status": "success", "message": "로그인 창이 실행되었습니다."}

@app.get("/분봉/{code}")
def get_chart(code: str):
    if TEST_MODE:
        mock_data = []
        base_price = random.randint(10000, 100000)
        for i in range(100):
            mock_data.append({"time": f"{15-i//60:02d}:{i%60:02d}", "price": base_price + random.randint(-500, 500), "volume": random.randint(100, 10000)})
        return {"status": "success", "stock_code": code, "data": mock_data}
        
    order_id = f"min_{code}_{time.time()}"
    order_queue.put((order_id, "minute_data", code))
    start_time = time.time()
    while order_id not in ready_food:
        if time.time() - start_time > 10: return {"status": "error", "message": "데이터 요청 타임아웃"}
        time.sleep(0.1)
    return {"status": "success", "stock_code": code, "data": ready_food.pop(order_id)}

@app.get("/일봉/{code}")
def get_daily(code: str):
    if TEST_MODE:
        mock_data = []
        base_price = random.randint(10000, 100000)
        for i in range(60):
            mock_data.append({"date": f"202404{30-i:02d}", "price": base_price + random.randint(-2000, 2000), "volume": random.randint(10000, 1000000)})
        return {"status": "success", "stock_code": code, "data": mock_data}

    order_id = f"day_{code}_{time.time()}"
    order_queue.put((order_id, "daily_data", code))
    start_time = time.time()
    while order_id not in ready_food:
        if time.time() - start_time > 10: return {"status": "error", "message": "데이터 요청 타임아웃"}
        time.sleep(0.1)
    return {"status": "success", "stock_code": code, "data": ready_food.pop(order_id)}

@app.get("/상위종목/{tr_type}")
def get_top_list(tr_type: str):
    if TEST_MODE:
        return {"status": "success", "data": [{"code": "005930", "name": "삼성전자"}, {"code": "000660", "name": "SK하이닉스"}, {"code": "035420", "name": "NAVER"}, {"code": "035720", "name": "카카오"}, {"code": "005380", "name": "현대차"}]}
    
    order_id = f"top_{tr_type}_{time.time()}"
    order_queue.put((order_id, "top_stocks", tr_type))
    start_time = time.time()
    while order_id not in ready_food:
        if time.time() - start_time > 10: return {"status": "error", "message": "데이터 요청 타임아웃"}
        time.sleep(0.1)
    return {"status": "success", "data": ready_food.pop(order_id)}

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    qt_app = QApplication(sys.argv)
    kiwoom_api = KiwoomAPI()
    
    timer = QTimer()
    timer.timeout.connect(kiwoom_api.check_order)
    timer.start(100)
    
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    qt_app.exec_()

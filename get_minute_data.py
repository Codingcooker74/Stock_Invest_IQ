import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QEventLoop

class KiwoomAPI:
    def __init__(self):
        self.kiwoom = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        self.kiwoom.OnEventConnect.connect(self.event_connect)
        self.kiwoom.OnReceiveTrData.connect(self.receive_tr_data)
        
        self.login_loop = QEventLoop()
        self.tr_loop = QEventLoop()
        
    def login(self):
        print("로그인 진행 중... (자동 로그인 설정됨)")
        self.kiwoom.dynamicCall("CommConnect()")
        self.login_loop.exec_()

    def event_connect(self, err_code):
        if err_code == 0:
            print("🚀 백그라운드 자동 로그인 성공!\n")
        self.login_loop.exit()

    def get_minute_data(self, code):
        print(f"[{code}] 1분봉 차트 데이터 요청 중...")
        
        # 주문서 작성 (opt10080: 주식분봉차트조회)
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "틱범위", "1")   # 1분봉
        self.kiwoom.dynamicCall("SetInputValue(QString, QString)", "수정주가구분", "1") # 수정주가 적용
        
        # 주문 제출
        self.kiwoom.dynamicCall("CommRqData(QString, QString, int, QString)", "주식분봉조회", "opt10080", 0, "1001")
        self.tr_loop.exec_()

    def receive_tr_data(self, screen_no, rqname, trcode, recordname, prev_next, data_len, err_code, msg1, msg2):
        if rqname == "주식분봉조회":
            # 데이터 개수 확인
            count = self.kiwoom.dynamicCall("GetRepeatCnt(QString, QString)", trcode, recordname)
            print(f"총 {count}개의 분봉 데이터를 받았습니다. (최근 5분만 출력합니다)\n")
            
            print("시간\t\t현재가\t거래량")
            print("-" * 40)
            
            # 최근 5개의 분봉(5분 치) 데이터만 반복해서 출력
            for i in range(5):
                time = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, recordname, i, "체결시간").strip()
                price = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, recordname, i, "현재가").strip()
                volume = self.kiwoom.dynamicCall("GetCommData(QString, QString, int, QString)", trcode, recordname, i, "거래량").strip()
                
                # 부호(-) 제거
                price = abs(int(price))
                
                # 시간 포맷 예쁘게 (HH:MM:SS)
                formatted_time = f"{time[:2]}:{time[2:4]}:{time[4:]}"
                
                print(f"{formatted_time}\t{price:,}원\t{volume}주")
            
        self.tr_loop.exit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    api = KiwoomAPI()
    
    api.login() 
    api.get_minute_data("005930") # 삼성전자 1분봉 요청
    
    sys.exit()
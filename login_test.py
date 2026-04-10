import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QAxContainer import QAxWidget

class KiwoomLogin:
    def __init__(self):
        # 1. 키움증권 통신 모듈(OCX)을 파이썬으로 불러오기
        self.kiwoom = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        
        # 2. 로그인 결과(성공/실패)를 들을 '귀(이벤트 슬롯)' 열어두기
        self.kiwoom.OnEventConnect.connect(self.event_connect)
        
        # 3. 키움증권 서버에 "로그인 창 띄워줘!" 라고 명령하기
        self.kiwoom.dynamicCall("CommConnect()")

    # 4. 서버에서 로그인 결과를 알려주면 실행되는 함수
    def event_connect(self, err_code):
        if err_code == 0:
            print("\n===============================")
            print("🚀 로그인 성공! 키움증권 서버 접속 완료!")
            print("===============================\n")
        else:
            print(f"로그인 실패 (에러코드: {err_code})")
        
        # 결과를 확인했으니 프로그램 안전하게 종료
        sys.exit()

if __name__ == "__main__":
    # 파이썬에서 화면(GUI) 관련 이벤트를 처리하기 위한 기본 세팅
    app = QApplication(sys.argv) 
    
    # 우리가 만든 로그인 클래스 실행
    my_system = KiwoomLogin()    
    
    # 프로그램이 바로 꺼지지 않고 로그인 결과를 기다리도록 대기 상태 만들기
    app.exec_()
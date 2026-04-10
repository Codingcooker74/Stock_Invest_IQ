import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QAxContainer import QAxWidget

app = QApplication(sys.argv)
kiwoom = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")

# 로그인 창 띄우기
kiwoom.dynamicCall("CommConnect()")

print("프로그램이 켜져 있는 동안 아이콘을 찾아 자동 로그인을 설정하세요!")

# 프로그램이 종료되지 않게 무한 대기 시킴
app.exec_()
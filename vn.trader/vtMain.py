# encoding: UTF-8

'''
History
<id>            <author>        <description>
2017050300      hetajen         Bat[Auto-CTP连接][Auto-Symbol订阅][Auto-DB写入][Auto-CTA加载]
'''

import sys
import os
import ctypes
import platform

import vtPath
from vtEngine import MainEngine
from uiMainWindow import *

# 文件路径名
path = os.path.abspath(os.path.dirname(__file__))    
ICON_FILENAME = 'vnpy.ico'
ICON_FILENAME = os.path.join(path, ICON_FILENAME)  

SETTING_FILENAME = 'VT_setting.json'
SETTING_FILENAME = os.path.join(path, SETTING_FILENAME)  

#----------------------------------------------------------------------
def main(isInitCTP=False, isInitCTA=False, isInitDB=False): # 2017050300 Modify by hetajen
    """主程序入口"""
    # 重载sys模块，设置默认字符串编码方式为utf8
    reload(sys)
    sys.setdefaultencoding('utf8')
    
    # 设置Windows底部任务栏图标
    if 'Windows' in platform.uname() :
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('vn.trader')  
    
    # 初始化Qt应用对象
    app = QtGui.QApplication(sys.argv)
    app.setWindowIcon(QtGui.QIcon(ICON_FILENAME))
    app.setFont(BASIC_FONT)
    
    # 设置Qt的皮肤
    try:
        f = file(SETTING_FILENAME)
        setting = json.load(f)    
        if setting['darkStyle']:
            import qdarkstyle
            app.setStyleSheet(qdarkstyle.load_stylesheet(pyside=False))
        f.close()
    except:
        pass
    
    # 初始化主引擎和主窗口对象
    '''2017050300 Modify by hetajen begin'''
    mainEngine = MainEngine(isInitCTP, isInitDB)
    mainWindow = MainWindow(mainEngine, mainEngine.eventEngine, isInitCTA, isInitDB)
    '''2017050300 Modify by hetajen end'''
    mainWindow.showMaximized()
    
    # 在主线程中启动Qt事件循环
    sys.exit(app.exec_())
    
if __name__ == '__main__':
    '''2017050300 Modify by hetajen begin'''
    argv = sys.argv
    isInitCTP = True
    isInitCTA = False
    isInitDB = True
    if len(argv) > 1:
        isInitCTP = (unicode(argv[1]) == str(True))
        isInitCTA = (unicode(argv[2]) == str(True))
        isInitDB = (unicode(argv[3]) == str(True))

    main(isInitCTP, isInitCTA, isInitDB)
    '''2017050300 Modify by hetajen end'''

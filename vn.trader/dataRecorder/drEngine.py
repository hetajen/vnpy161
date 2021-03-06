# encoding: UTF-8

'''
本文件中实现了行情数据记录引擎，用于汇总TICK数据，并生成K线插入数据库。

使用DR_setting.json来配置需要收集的合约，以及主力合约代码。

History
<id>            <author>        <description>
2017050300      hetajen         Bat[Auto-CTP连接][Auto-Symbol订阅][Auto-DB写入][Auto-CTA加载]
2017050301      hetajen         DB[CtaTemplate增加日线bar数据获取接口][Mongo不保存Tick数据][新增数据来源Sina]
2017051500      hetajen         夜盘tick|bar数据增加tradingDay字段，用于指明夜盘tick|bar数据的真实交易日
2017052500      hetajen         DB[增加：5分钟Bar数据的记录、存储和获取]
'''

import json
import os
import copy
from collections import OrderedDict
from datetime import datetime, timedelta
from Queue import Queue
from threading import Thread

from eventEngine import *
from vtGateway import VtSubscribeReq, VtLogData
from drBase import *
from vtFunction import todayDate
from language import text
'''2017050300 Add by hetajen begin'''
'''2017052500 Add by hetajen begin'''
from ctaHistoryData import XH_HistoryDataEngine, HistoryDataEngine
'''2017052500 Add by hetajen end'''
'''2017050300 Add by hetajen end'''


########################################################################
class DrEngine(object):
    """数据记录引擎"""
    
    settingFileName = 'DR_setting.json'
    path = os.path.abspath(os.path.dirname(__file__))
    settingFileName = os.path.join(path, settingFileName)    

    #----------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine):
        """Constructor"""
        self.mainEngine = mainEngine
        self.eventEngine = eventEngine
        
        # 当前日期
        self.today = todayDate()
        
        # 主力合约代码映射字典，key为具体的合约代码（如IF1604），value为主力合约代码（如IF0000）
        self.activeSymbolDict = {}
        
        # Tick对象字典
        self.tickDict = {}
        
        # K线对象字典
        self.barDict = {}
        
        # 负责执行数据库插入的单独线程相关
        self.active = False                     # 工作状态
        self.queue = Queue()                    # 队列
        self.thread = Thread(target=self.run)   # 线程
        
        # 载入设置，订阅行情
        self.loadSetting()
        
    #----------------------------------------------------------------------
    def loadSetting(self):
        """载入设置"""
        with open(self.settingFileName) as f:
            drSetting = json.load(f)
            
            # 如果working设为False则不启动行情记录功能
            working = drSetting['working']
            if not working:
                return
            
            if 'tick' in drSetting:
                l = drSetting['tick']
                
                for setting in l:
                    symbol = setting[0]
                    vtSymbol = symbol

                    req = VtSubscribeReq()
                    req.symbol = setting[0]
                    
                    # 针对LTS和IB接口，订阅行情需要交易所代码
                    if len(setting)>=3:
                        req.exchange = setting[2]
                        vtSymbol = '.'.join([symbol, req.exchange])
                    
                    # 针对IB接口，订阅行情需要货币和产品类型
                    if len(setting)>=5:
                        req.currency = setting[3]
                        req.productClass = setting[4]
                    
                    self.mainEngine.subscribe(req, setting[1])
                    
                    drTick = DrTickData()           # 该tick实例可以用于缓存部分数据（目前未使用）
                    self.tickDict[vtSymbol] = drTick
                    
            if 'bar' in drSetting:
                l = drSetting['bar']
                
                for setting in l:
                    symbol = setting[0]
                    vtSymbol = symbol
                    
                    req = VtSubscribeReq()
                    req.symbol = symbol                    

                    if len(setting)>=3:
                        req.exchange = setting[2]
                        vtSymbol = '.'.join([symbol, req.exchange])

                    if len(setting)>=5:
                        req.currency = setting[3]
                        req.productClass = setting[4]                    
                    
                    self.mainEngine.subscribe(req, setting[1])  
                    
                    bar = DrBarData() 
                    self.barDict[vtSymbol] = bar
                    
            if 'active' in drSetting:
                d = drSetting['active']
                
                # 注意这里的vtSymbol对于IB和LTS接口，应该后缀.交易所
                for activeSymbol, vtSymbol in d.items():
                    self.activeSymbolDict[vtSymbol] = activeSymbol
            
            # 启动数据插入线程
            self.start()
            
            # 注册事件监听
            self.registerEvent()    

    #----------------------------------------------------------------------
    def procecssTickEvent(self, event):
        """处理行情推送"""
        tick = event.dict_['data']
        vtSymbol = tick.vtSymbol

        # 转化Tick格式
        drTick = DrTickData()
        d = drTick.__dict__
        for key in d.keys():
            if key != 'datetime':
                d[key] = tick.__getattribute__(key)
        drTick.datetime = datetime.strptime(' '.join([tick.date, tick.time]), '%Y%m%d %H:%M:%S.%f')            
        
        # 更新Tick数据
        if vtSymbol in self.tickDict:
            '''2017050301 Delete by hetajen begin'''
            # self.insertData(TICK_DB_NAME, vtSymbol, drTick)
            #
            # if vtSymbol in self.activeSymbolDict:
            #     activeSymbol = self.activeSymbolDict[vtSymbol]
            #     self.insertData(TICK_DB_NAME, activeSymbol, drTick)
            '''2017050301 Delete by hetajen end'''
            
            # 发出日志
            self.writeDrLog(text.TICK_LOGGING_MESSAGE.format(symbol=drTick.vtSymbol,
                                                             time=drTick.time, 
                                                             last=drTick.lastPrice, 
                                                             bid=drTick.bidPrice1, 
                                                             ask=drTick.askPrice1))
            
        # 更新分钟线数据
        if vtSymbol in self.barDict:
            bar = self.barDict[vtSymbol]
            
            # 如果第一个TICK或者新的一分钟
            if not bar.datetime or bar.datetime.minute != drTick.datetime.minute:    
                if bar.vtSymbol:
                    '''2017050301 Delete by hetajen begin'''
                    # newBar = copy.copy(bar)
                    # self.insertData(MINUTE_DB_NAME, vtSymbol, newBar)
                    
                    # if vtSymbol in self.activeSymbolDict:
                    #     activeSymbol = self.activeSymbolDict[vtSymbol]
                    #     self.insertData(MINUTE_DB_NAME, activeSymbol, newBar)
                    '''2017050301 Delete by hetajen end'''
                    
                    self.writeDrLog(text.BAR_LOGGING_MESSAGE.format(symbol=bar.vtSymbol, 
                                                                    time=bar.time, 
                                                                    open=bar.open, 
                                                                    high=bar.high, 
                                                                    low=bar.low, 
                                                                    close=bar.close))
                         
                bar.vtSymbol = drTick.vtSymbol
                bar.symbol = drTick.symbol
                bar.exchange = drTick.exchange
                
                bar.open = drTick.lastPrice
                bar.high = drTick.lastPrice
                bar.low = drTick.lastPrice
                bar.close = drTick.lastPrice

                '''2017051500 Add by hetajen begin'''
                bar.tradingDay = drTick.tradingDay
                bar.actionDay = drTick.actionDay
                '''2017051500 Add by hetajen end'''

                bar.date = drTick.date
                bar.time = drTick.time
                bar.datetime = drTick.datetime
                bar.volume = drTick.volume
                bar.openInterest = drTick.openInterest        
            # 否则继续累加新的K线
            else:                               
                bar.high = max(bar.high, drTick.lastPrice)
                bar.low = min(bar.low, drTick.lastPrice)
                bar.close = drTick.lastPrice            

    #----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.eventEngine.register(EVENT_TICK, self.procecssTickEvent)
 
    # ----------------------------------------------------------------------
    '''2017050300 Add by hetajen begin'''
    def insertDailyBar(self):
        e = XH_HistoryDataEngine()
        for vtSymbol in self.barDict:
            e.downloadFuturesDailyBarSina(vtSymbol)
            if vtSymbol in self.activeSymbolDict:
                activeSymbol = self.activeSymbolDict[vtSymbol]
                e.downloadFuturesDailyBarSina(activeSymbol)
    '''2017050300 Add by hetajen end'''

    # ----------------------------------------------------------------------
    '''2017052500 Add by hetajen begin'''
    def insert5MinBar(self):
        e = XH_HistoryDataEngine()
        for vtSymbol in self.barDict:
            e.downloadFutures5MinBarSina(vtSymbol)
            if vtSymbol in self.activeSymbolDict:
                activeSymbol = self.activeSymbolDict[vtSymbol]
                e.downloadFutures5MinBarSina(activeSymbol)

    def insertTradeCal(self):
        e = HistoryDataEngine()
        e.loadTradeCal()
        # e.downloadTradeCal()
    '''2017052500 Add by hetajen end'''

    #----------------------------------------------------------------------
    def insertData(self, dbName, collectionName, data):
        """插入数据到数据库（这里的data可以是CtaTickData或者CtaBarData）"""
        self.queue.put((dbName, collectionName, data.__dict__))
        
    #----------------------------------------------------------------------
    def run(self):
        """运行插入线程"""
        while self.active:
            try:
                dbName, collectionName, d = self.queue.get(block=True, timeout=1)
                self.mainEngine.dbInsert(dbName, collectionName, d)
            except Empty:
                pass
            
    #----------------------------------------------------------------------
    def start(self):
        """启动"""
        self.active = True
        self.thread.start()
        
    #----------------------------------------------------------------------
    def stop(self):
        """退出"""
        if self.active:
            self.active = False
            self.thread.join()
        
    #----------------------------------------------------------------------
    def writeDrLog(self, content):
        """快速发出日志事件"""
        log = VtLogData()
        log.logContent = content
        event = Event(type_=EVENT_DATARECORDER_LOG)
        event.dict_['data'] = log
        self.eventEngine.put(event)   
    
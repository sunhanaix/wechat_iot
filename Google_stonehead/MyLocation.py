#!/usr/bin/python3
import re,io,sys,os,time,json
import cgi,cgitb,logging
import requests
import hashlib
import MyDB

#由于配置文件，可能是xxx_config.py，为了便于移植，这里动态载入下
import glob,importlib
app_path = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.append(app_path)
cfg_file=glob.glob(f'{app_path}/*config.py')[0]
cfg_file=os.path.basename(cfg_file)
cfg_model=os.path.splitext(cfg_file)[0]
cfg=importlib.import_module(cfg_model)

def nearBy(addr): #给定当前用户的详细地址，返回这个地址对应的就近库房信息
	db=MyDB.UserDB(cfg.wechat_db)
	stocks=db.getAllStocks()
	db.close()
	for stock in stocks:
		stock=stock.replace('分库','')
		stock=stock.replace('库','')
		if addr.find(stock)>-1 :
			return stock
		if addr.find('江苏')>-1 :
			return '南京'
		if addr.find('江西')>-1 :
			return '南昌' 
		if addr.find('安徽')>-1 :
			return '合肥' 
		if addr.find('黑龙江')>-1 :
			return '哈尔滨' 
		if addr.find('山西')>-1 :
			return '太原' 
		if addr.find('广东')>-1 :
			return '广州' 
		if addr.find('广西')>-1 :
			return '南宁' 
		if addr.find('四川')>-1 :
			return '成都' 
		if addr.find('西藏')>-1 :
			return '拉萨' 
		if addr.find('云南')>-1 :
			return '昆明' 
		if addr.find('浙江')>-1 :
			return '杭州' 
		if addr.find('湖北')>-1 :
			return '武汉' 
		if addr.find('辽宁')>-1 :
			return '沈阳' 
		if addr.find('河北')>-1 :
			return '石家庄' 
		if addr.find('福建')>-1 :
			return '福州' 
		if addr.find('陕西')>-1 :
			return '西安' 
		if addr.find('贵州')>-1 :
			return '贵阳' 
		if addr.find('河南')>-1 :
			return '郑州' 
		if addr.find('吉林')>-1 :
			return '长春' 
		if addr.find('湖南')>-1 :
			return '长沙' 
	return None

class Location(object):
	def __init__(self,wechat_db=cfg.wechat_db,cache_file='coords.db'):
		self.cache_file=cache_file
		self.wechat_db=wechat_db
		self.cache=MyDB.KeyValueStore(self.cache_file)
		
	def getAddrByGPS(self,gps): #给定gps，先查缓存，再去百度查，返回地址信息
		if gps in self.cache:
			return self.cache[gps]
		addr=MyDB.getLocByBaiduGPS(gps)
		if addr:
			self.cache[gps]=addr
			self.cache.commit()
			return addr
		else:
			return ""
		

if __name__=='__main__':
	a=nearBy('北京市顺义区火沙辅线辅路,天洋国际大厦')
	#print(a)
	stime=time.time()
	l=Location(wechat_db='wechat.db',cache_file='coords.db')
	addr=l.getAddrByGPS('22.023771,110.411859')
	etime=time.time()
	print(addr)
	print("cosumed %.2f seconds" % (etime-stime))
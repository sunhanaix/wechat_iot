#!/usr/bin/python3
import sqlite3,requests
import sys,os,re,json,random,time
from hashlib import md5
import traceback  
import pypinyin
import MyLocation
import stonehead_config as cfg
mylogger=cfg.logger
#sqlite3的用户表和登录日志表数据库维护管理

def getLocByBaiduIP(ip): #给定一个ip地址，通过百度api，查地址
	if not ip:
		return False
	url=f"http://api.map.baidu.com/location/ip?ip={ip}&coor=bd09ll&ak={cfg.baidu_ak}"
	check_page = requests.get(url).content.decode('utf8')
	loc=json.loads(check_page)
	if not 'status' in loc:
		return False
	if not loc['status']==0:
		return False
	if not 'address' in loc:
		return False
	return loc['address']

def getLocByBaiduGPS(gps): #给定一个gps位置信息，通过百度api，查地址
	if not gps:
		return False
	url=f"http://api.map.baidu.com/geocoder/v2/?callback=renderReverse&coordtype=wgs84ll&location={gps}&output=json&pois=1&ak={cfg.baidu_ak}"
	r = requests.get(url).content.decode('utf8')
	r=r.replace('renderReverse&&renderReverse(','') #把前缀去掉
	r=r[:-1] #把最后的一个右括号扔了
	loc=json.loads(r)
	if not 'status' in loc:
		return False
	if not loc['status']==0:
		return False
	if not 'result' in loc:
		return False
	return loc['result']['formatted_address']
	
class UserDB(object):
	conn=None
	cur=None
	def __init__(self,dbname=cfg.wechat_db,params=None):
		self.connected = 0 
		self.dbname=dbname
		try:
			self.conn=sqlite3.connect(dbname)
			self.cur=self.conn.cursor()
			self.connected = 1  
		except Exception as e:
			print(e)
			traceback.print_exc()
			self.connected = 0
		self.conn.execute('pragma foreign_keys=on') #启用外键一致性检查
		if not os.path.isfile(dbname):
			print("not file:"+dbname)
			self.createLogTable()
			self.crateSynctimeTable()
			self.createUsersTable()
			self.createSubUserTable()
		else:
			if not self.checkTable('oplog'):
				self.createLogTable()
			if not self.checkTable('synctime'):
				self.crateSynctimeTable()
			if not self.checkTable('users'):
				self.createUsersTable()
			if not self.checkTable('subscribe_user'):
				self.createSubUserTable()
	@property
	def is_connected(self):  
		return self.connected != 0
	def close(self):
		if self.connected == 0:
			return
		try:
			self.cur.close() 
			self.conn.close() 
			self.connected = 0 
		except:
			pass

	def createLogTable(self):
		sql='''CREATE TABLE oplog(id integer PRIMARY KEY autoincrement,
       openid varchar(255) not null,
       user varchar(255) ,       
       msg_type varchar(255) ,
       msg_content varchar(255),       
       in_out char(255),       
       time int not null,
       gps varchar(255) ,       
       addr varchar(255)
      )
					'''
		self.cur.execute(sql)
		self.conn.commit()
		
	def crateSynctimeTable(self):
		sql='''CREATE TABLE synctime(id integer PRIMARY KEY autoincrement,
                       tname varchar(255) unique not null,       
                       time int not null
                      )
					'''
		self.cur.execute(sql)
		self.conn.commit()	

	def createUsersTable(self): #创建用户表
		sql='''CREATE TABLE users (
                                        id integer PRIMARY KEY autoincrement,
                                        name varchar(255) not null,
                                        gender varchar(2) ,
                                        enable varchar(2),
                                        mobile varchar(255),
                                        tel varchar(255),
                                        department varchar(255),
                                        alias varchar(255),
                                        mail varchar(255) unique not null
                                        )
					'''
		self.cur.execute(sql)
		self.conn.commit()		
	def createSubUserTable(self): #创建订阅此公众号用户表
		sql='''CREATE TABLE subscribe_user (
                                        id integer PRIMARY KEY autoincrement,
                                        openid varchar(255) unique not null,
                                        nickname varchar(255) not null,
                                        subscribe int,
                                        sex int,
                                        city varchar(255),
                                        province varchar(255),
                                        headimgurl varchar(255),
                                        subscribe_time int,
                                        erp_user varchar(255) 
                                        )
					'''
		self.cur.execute(sql)
		self.conn.commit()
		
	def getLastAddress(self,openid): #给定openid，取得上次该用户所在地址信息
		sql=r"select addr from oplog where openid=? and gps is not null and not gps='' order by time desc limit 0,1"
		self.cur.execute(sql,(openid,))
		t=self.cur.fetchone()
		if t:
			return t[0]
		sql=r'select province,city from subscribe_user where openid=? order by subscribe_time desc limit 0,1'
		self.cur.execute(sql,(openid,))
		t=self.cur.fetchone()
		if t:
			return "".join(t)

	def addUser2Users(self,uinfo): #从别处（比如腾讯企业邮箱抓来的用户信息），插入到数据库中
		#uinfo是一个字典，含有'enable','gender','mobile','tel','mail','alias','department'键值
		sql=r"insert into users(name,enable,gender,mobile,tel,mail,alias,department) values(?,?,?,?,?,?,?,?)"
		for key in ['enable','gender','mobile','tel','mail','alias','department']:
			if not key in uinfo:
				uinfo[key]=''
		if cfg.debug:
			mylogger.info('addUser2Users(),userinfo=%s' % json.dumps(uinfo,indent=2,ensure_ascii=False))
		self.cur.execute(sql,(uinfo['name'],uinfo['enable'],uinfo['gender'],uinfo['mobile'],uinfo['tel'],uinfo['mail'],uinfo['alias'],uinfo['department']))
		self.conn.commit()

	def queryUser(self,name,exact=True): #给定用户名（汉字），返回用户属性信息
		sql=r'select * from users where name=?'
		if cfg.debug:
			mylogger.info('queryUser(),name=%s' % name)
		old_factory=self.conn.row_factory
		#print("old self.conn=%s" % self.conn.row_factory)
		self.conn.row_factory=self.dictFactory #设置处理row结果的方法，此处让它自动转义到dict数组
		#print("new self.conn=%s" % self.conn.row_factory)
		self.cur=self.conn.cursor() #因为前面设置了self.con.row_factory，这里要重新获得一个corsor
		self.cur.execute(sql,(name,))
		res=self.cur.fetchall()
		#res=self.cur.fetchone()
		if res or exact: ##要是姓名用汉字精确匹配到了，或者强制精确匹配，就直接返回了
			self.conn.row_factory=old_factory  #恢复原有句柄设置
			self.cur=self.conn.cursor() #恢复cursor指向
			return res 
		pinyin_name=pypinyin.lazy_pinyin(name)
		sql=r'select * from users'
		self.cur=self.conn.cursor()
		self.cur.execute(sql)
		allUsers=self.cur.fetchall()
		res=[]
		for user in allUsers:
			if pypinyin.lazy_pinyin(user['name'])==pinyin_name:
				user['拼音模糊匹配']=1
				res.append(user)
		self.conn.row_factory=old_factory  #恢复原有句柄设置
		self.cur=self.conn.cursor() #恢复cursor指向
		return res
	
	def logUserOp(self,userinfo): #记录用户的操作记录入库
		sql=r"insert into oplog(openid,user,msg_type,msg_content,in_out,time,gps,addr) values(?,?,?,?,?,?,?,?)"
		if 'gps' in userinfo and  ('addr' not in userinfo or not userinfo['addr']) :
			ml=MyLocation.Location()
			userinfo['addr']=ml.getAddrByGPS(userinfo['gps'])
		userinfo['gps']=userinfo['gps'] if 'gps' in userinfo else ''
		userinfo['addr']=userinfo['addr'] if 'addr' in userinfo else ''
		userinfo['in_out']=userinfo['in_out'] if 'in_out' in userinfo else 'client_send'
		userinfo['msg_type']=userinfo['msg_type'] if 'msg_type' in userinfo else 'text'
		userinfo['time']=int(time.time()) if userinfo['in_out']=='server_reply' else userinfo['time'];  #判断是服务器返回结果的话，时间戳取服务器时间，不取默认的消息时间
		if cfg.debug:
			mylogger.info('logUserOp(),userinfo=%s' % json.dumps(userinfo,indent=2,ensure_ascii=False))
		self.cur.execute(sql,(userinfo['openid'],userinfo['user'],userinfo['msg_type'],userinfo['msg_content'],userinfo['in_out'],userinfo['time'],userinfo['gps'],userinfo['addr']))
		self.conn.commit()

	def getNameByOpenid(self,openid): #给定openid，查库表返回用户名
		sql=r'select erp_user from subscribe_user where openid=?'
		self.cur.execute(sql,(openid,))
		t=self.cur.fetchone()
		if t:
			return t[0]
		return ''

	def addSubscriber(self,uinfo): #给定用微信接口获得的订阅用户属性信息，将它插入订阅用户表
		sql=r"insert or replace into subscribe_user(openid,nickname,subscribe,sex,city,province,headimgurl,subscribe_time,erp_user) values(?,?,?,?,?,?,?,?,?)"
		uinfo['erp_user']=uinfo['erp_user'] if 'erp_user' in uinfo else ''
		if cfg.debug:
			mylogger.info('addSubscriber(),uinfo=%s' % json.dumps(uinfo,indent=2,ensure_ascii=False))
		try:
			self.cur.execute(sql,(uinfo['openid'],uinfo['nickname'],uinfo['subscribe'],uinfo['sex'],uinfo['city'],uinfo['province'],uinfo['headimgurl'],uinfo['subscribe_time'],uinfo['erp_user']))
			self.conn.commit()
		except Exception as e:
			mylogger.error('addSubscriber(),Error:%s' % str(e))

			
	def checkTable(self,tname): #给定一个表名字，判断表是否存在
			sql="select count(*) from sqlite_master where type='table' and name='%s'" % tname;
			self.cur.execute(sql)
			count=self.cur.fetchone()[0]
			if count==0:
				return False
			else:
				return True

	def dictFactory(self,cursor,row):
		#将sql查询结果整理成字典形式
		d={}
		for index,col in enumerate(cursor.description):
			d[col[0]]=row[index]
		return d				

class KeyValueStore(dict): #新造一个轮子，继承dict类，用于key/value持久化存储在sqlite3中
	def __init__(self, filename='coords.db'):
		self.conn = sqlite3.connect(filename)
		self.conn.execute("CREATE TABLE IF NOT EXISTS kv (key text unique, value text)")
	
	def commit(self):
		self.conn.commit()

	def close(self):
		self.conn.commit()
		self.conn.close()

	def __len__(self):
		rows = self.conn.execute('SELECT COUNT(*) FROM kv').fetchone()[0]
		return rows if rows is not None else 0

	def iterkeys(self):
		c = self.conn.cursor()
		for row in self.conn.execute('SELECT key FROM kv'):
			yield row[0]

	def itervalues(self):
		c = self.conn.cursor()
		for row in c.execute('SELECT value FROM kv'):
			yield row[0]

	def iteritems(self):
		c = self.conn.cursor()
		for row in c.execute('SELECT key, value FROM kv'):
			yield row[0], row[1]

	def keys(self):
		return list(self.iterkeys())

	def values(self):
		return list(self.itervalues())

	def items(self):
		return list(self.iteritems())

	def __contains__(self, key):
		return self.conn.execute('SELECT 1 FROM kv WHERE key = ?', (key,)).fetchone() is not None

	def __getitem__(self, key):
		item = self.conn.execute('SELECT value FROM kv WHERE key = ?', (key,)).fetchone()
		if item is None:
			raise KeyError(key)
		return item[0]

	def __setitem__(self, key, value):
		self.conn.execute('REPLACE INTO kv (key, value) VALUES (?,?)', (key, value))

	def __delitem__(self, key):
		if key not in self:
			raise KeyError(key)
		self.conn.execute('DELETE FROM kv WHERE key = ?', (key,))

	def __iter__(self):
		return self.iterkeys()
		
if __name__=='__main__':
	db=UserDB('wechat2.db')
	#print(db.getAllStock())
	#res=getLocByBaiduGPS('39.934868,116.331177')
	#print(res)
	uinfo=  {
    "tel": "13512345678",
    "mail": "12345678@qq.com",
    "department": "摸鱼部",
    "alias": "",
    "mobile": "",
    "gender": "男",
    "enable": 1,
    "name": "张三"
  }
	#db.addUser2Users(uinfo)
	t=db.queryUser('张三')
	print(t)
#!/usr/bin/python3
import werobot
from html import unescape
from lxml import html, etree
from werobot.replies import ArticlesReply, Article,TextReply
from werobot.utils import cached_property
import json,sys,os,time,re
import warnings,logging
import threading
import random
import MyDB
import MyLocation
import MyMail
import MyMQTT
import stonehead_config as cfg
'''
微信公众号守护daemon，确保微信公众号指向本daemon服务的web url
'''
VERSION='0.2.2022.02.09'
mylogger=cfg.logger

AppID=cfg.WechatAppID
AppSecret=cfg.WechatAppSecret
Token=cfg.WechatToken
EncodingAESKey=cfg.WechatEncodingAESKey
wechat_db=cfg.wechat_db
noPrivMsg='请发送“我是xxx，邮箱地址是xxx.xx@xxx.com，申请开通访问此服务号权限”。\n收到验证码进行验证后，方可正常使用。\n请使用help命令查看帮助'

class WxRobot(werobot.WeRoBot): #继承werobot.WeRoBot类
	@cached_property
	def client(self): #重构client，用编写的类
		return WxClient(self.config)
		
class WxClient(werobot.client.Client):
	def get_access_token(self):
		"""
		判断现有的token是否过期。
		不重构这个方法的话，每次请求时，都会要去获得一次access_token，性能差，容易超微信规定调用阈值，因此需要重构这个方法
		把token缓存在sqlite的库里面，如果要token时，先查本地库里的，如果没有过期，直接返回缓存的token，如果过期了，现去请求一个
		此方法返回值是access_token
		"""
		kv=MyDB.KeyValueStore(wechat_db)
		if 'token' in kv:
			self._token=kv['token']
		if 'token_expires_at' in kv:
			self.token_expires_at=float(kv['token_expires_at'])
			self.exp_date_time=time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(self.token_expires_at))
		if self._token:
			now = time.time()
			if self.token_expires_at - now > 60:
				mylogger.info("token=%s,exp_at=%s" % (self._token,self.exp_date_time))
				return self._token
		j = self.grant_token()
		self._token = j["access_token"]
		self.token_expires_at = int(time.time()) + j["expires_in"]
		kv['token']=self._token
		kv['token_expires_at']=self.token_expires_at
		kv.close()
		mylogger.info("token=%s,exp_at=%s" % (self._token,self.exp_date_time))
		return self._token

		
def wf(fname,ss,*option): 
	if not option:
		option=['w']
	with open(fname,option[0]) as f:
		f.write(ss)
		f.close			
	
def msg2uinfo(msg): #给定微信消息的msg object对象，返回userinfo信息
	openid=msg.FromUserName
	#uinfo=client.get_user_info(openid)
	db=MyDB.UserDB(wechat_db)
	erp_user=db.getNameByOpenid(openid)
	if not erp_user:
		erp_user=''
	userinfo={
			'openid':openid,
			'user':erp_user,
			'in_out':'client_sent',
			'time':msg.time,
			'msg_type':msg.type,
				}
	try: #如果是text之类，有内容的，就取得，没有就为空
		userinfo['msg_content']=msg.content
	except Exception as e:
		print(e)
		userinfo['msg_content']=''
	if msg.type=='click_event':
		userinfo['msg_content']=msg.EventKey
	try: #如果有gps坐标，就获得它
		userinfo['gps']="%s,%s" % (msg.Latitude,msg.Longitude)
	except Exception as e:
		print(e)
		userinfo['gps']=''
	if cfg.debug:
		print("in msg2uinfo:%s" % json.dumps(userinfo,indent=2,ensure_ascii=False))
	return userinfo

def help(openid):
    #当遇到关键字help时，通过MQTT去publish一个/wechat/askKeywords的消息，然后树莓派那面发一个可以支持的keywords到/wechat/help消息上
    #在MyMQTT.SubMsg分支订阅里面，处理keywords信息，并返回给这个openid用户
	content="目前你可以对它说或者敲入文字：\n\n"
	MyMQTT.PubMsg(topic=f'/{cfg.username}/wechat/askKeywords',payload=MyMQTT.pack_data(msgType="text",openid=openid,data='keywords'))
	return content

def msgNoPriv(msgObj,client,msg=noPrivMsg):
	#传入msgObj为微信Message消息对象，
	#传入client为werobot.WeRoBot.client对象
	#用另启一个线程方式返回信息，提示用户没权限
	openid=msgObj.FromUserName
	ctp=threading.Thread(target=client.send_text_message,args=(openid,msg))
	ctp.start()

def deal_subscribe(msgObj,client)	: #处理关注公众号后的操作
	openid=msgObj.FromUserName
	msg="欢迎关注此公众号，\n"+noPrivMsg
	stime=time.time()
	msgNoPriv(msgObj,client,msg)
	uinfo=client.get_user_info(openid)
	db=MyDB.UserDB(wechat_db)
	db.addSubscriber(uinfo)
	etime=time.time()
	mylogger.info("consumed=%s" % (etime-stime))

def validCodeOK(uinfo,name,mail):
	db=MyDB.UserDB(wechat_db)
	client.remark_user(uinfo['openid'],name)
	#client.tag_users(uinfo['openid'],[100]); #把用户加入到100号tag的分组里面（“已经注册过用户”）
	userinfo=client.get_user_info(uinfo['openid'])
	userinfo['erp_user']=name
	mylogger.info('userinfo=%s' % json.dumps(userinfo,indent=2,ensure_ascii=False))
	db.addSubscriber(userinfo)
	m=MyMail.mail()
	mail_info={'subject':"%s申请微信服务号权限已经开通" % (name),
		'body':"%s申请微信服务号权限已经开通，微信昵称：%s，位置：%s" % (name,userinfo['nickname'],userinfo['province']),
			'to_accounts': [mail]
			}
	m.sendmail(mail_info)
	db.conn.close()

def deal_vioce(openid,media_id,uinfo):
    r=client.download_media(media_id)
    if not os.path.isdir(cfg.voice_dir):
        os.mkdir(cfg.voice_dir)
    date_time=time.strftime("%Y-%m-%d_%H_%M_%S")
    fname=f"{uinfo['user']}-{date_time}.amr"
    fname=os.path.join(cfg.voice_dir,fname)
    open(fname,'wb').write(r.content)
    mylogger.info(f"trying to publish to MQTT: /{cfg.username}/wechat/voice")
    MyMQTT.PubMsg(topic=f'/{cfg.username}/wechat/voice',payload=MyMQTT.pack_data(msgType="voice",openid=openid,fname=fname))

#robot = WxRobot(app_id=AppID,app_secret=AppSecret,encoding_aes_key=EncodingAESKey,token=Token)
robot = WxRobot(app_id=AppID,app_secret=AppSecret,token=Token)
client=robot.client
db=MyDB.UserDB(wechat_db)
kv=MyDB.KeyValueStore(wechat_db)


@robot.subscribe
def subscribe(msg):
	uinfo=msg2uinfo(msg)
	db=MyDB.UserDB(wechat_db)
	db.logUserOp(uinfo)
	if cfg.debug:
		mylogger.info("Subscribe:%s" % str(vars(msg)))
	ct = threading.Thread(target=deal_subscribe,args=(msg,client))
	ct.start()
	return ''

@robot.unsubscribe
def unsubscribe(msg):
	mylogger.info("Unsubscribe:%s" % str(vars(msg)))
	return ''

@robot.location
def location(msg): #处理用户端发过来的位置消息
	mylogger.info("location message:%s" % str(vars(msg)))
	uinfo=msg2uinfo(msg)
	db=MyDB.UserDB(wechat_db)
	db.logUserOp(uinfo)

@robot.location_event
def loc_event(msg): #处理用户端主动上报的位置消息，这个不可修改，可以用来打卡
	mylogger.info("location event:%s" % str(vars(msg)))
	db=MyDB.UserDB(wechat_db)
	uinfo=msg2uinfo(msg)
	db.logUserOp(uinfo)

@robot.click
def click_menu(msg):  #处理点击了对应菜单的话，做如何响应
	mylogger.info("click_menu:%s" % str(vars(msg)))
	db=MyDB.UserDB(wechat_db)
	uinfo=msg2uinfo(msg)
	db.logUserOp(uinfo)
	openid=str(msg.source)
	if not uinfo['user']:
		uinfo['in_out']='server_reply'
		uinfo['msg_content']=noPrivMsg
		db.logUserOp(uinfo)
		return noPrivMsg
	if uinfo['msg_content']=='help':
		uinfo['in_out']='server_reply'
		uinfo['msg_content']=help(openid)
		db.logUserOp(uinfo)
		return uinfo['msg_content']
	if uinfo['msg_content']=='release':
		uinfo['in_out']='server_reply'
		uinfo['msg_content']=release()
		db.logUserOp(uinfo)
		return uinfo['msg_content']
	if uinfo['msg_content']=='addr':
		uinfo['in_out']='server_reply'
		uinfo['msg_content']=addr()
		db.logUserOp(uinfo)
		return uinfo['msg_content']	

@robot.filter('version') #返回当前版本信息
def actVersion(msg):
	mylogger.info("text version:%s" % str(vars(msg)))
	db=MyDB.UserDB(wechat_db)
	uinfo=msg2uinfo(msg)
	db.logUserOp(uinfo)
	if not uinfo['user']:
		uinfo['in_out']='server_reply'
		uinfo['msg_content']=noPrivMsg
		db.logUserOp(uinfo)
		return noPrivMsg
	if uinfo['msg_content']=='version':
		uinfo['in_out']='server_reply'
		uinfo['msg_content']=VERSION
		db.logUserOp(uinfo)
		return uinfo['msg_content']
		
@robot.filter('help')
def actHelp(msg):
	mylogger.info("text help:%s" % str(vars(msg)))
	uinfo=msg2uinfo(msg)
	db=MyDB.UserDB(wechat_db)
	db.logUserOp(uinfo)
	openid=str(msg.source)
	if not uinfo['user']:
		uinfo['in_out']='server_reply'
		uinfo['msg_content']=noPrivMsg
		db.logUserOp(uinfo)
		return noPrivMsg
	if uinfo['msg_content']=='help':
		uinfo['in_out']='server_reply'
		uinfo['msg_content']=help(openid)
		db.logUserOp(uinfo)
		return uinfo['msg_content']

@robot.filter('record')
def actRecord(msg):
	mylogger.info("text record:%s" % str(vars(msg)))
	uinfo=msg2uinfo(msg)
	db=MyDB.UserDB(wechat_db)
	db.logUserOp(uinfo)
	if not uinfo['user']:
		uinfo['in_out']='server_reply'
		uinfo['msg_content']=noPrivMsg
		db.logUserOp(uinfo)
		return noPrivMsg
	if uinfo['msg_content']=='record':
		uinfo['in_out']='server_reply'
		uinfo['msg_content']=record()
		db.logUserOp(uinfo)
		return uinfo['msg_content']

								
patern_whoami=re.compile(r'我是(\S+)[,，]\s*邮箱地址是[:：]*([a-zA-Z0-9]+\.*[a-zA-Z0-9]+@[a-zA-Z0-9\.]+)')
@robot.filter(patern_whoami)  #特殊的指令关键字识别测试
def needReg(msg,session):
	mylogger.info("needReg:%s" % str(vars(msg)))
	uinfo=msg2uinfo(msg)
	print("patern_whoami=%s,uinfo=%s" % (patern_whoami,uinfo))
	rr=re.search(patern_whoami,uinfo['msg_content'])
	print(rr)
	print(rr.group())
	name=rr.group(1)
	mail=rr.group(2)
	db=MyDB.UserDB(wechat_db)
	db.logUserOp(uinfo)
	code="%06d"  % random.randint(99999,999999)
	session['code']=code
	session['name']=name
	session['mail']=mail
	m=MyMail.mail()
	mail_info={'subject':"%s正在申请验证,验证码：%s" % (name,code),
		'body':"%s正在申请微信公众号的访问，验证码为：%s\n如是本人操作，请在微信中，将其回复给微信公众号用于验证" % (name,code),
			'to_accounts': [mail]
			}
	ct=threading.Thread(target=m.sendmail,args=(mail_info,))
	ct.start()
	return "发了一个验证码，到%s，请收到后，回复给我" % (mail)

patern_code=re.compile(r'^(\d{6})$')
@robot.filter(patern_code)  #如果是纯6位数字
def verifyCode(msg,session):
	uinfo=msg2uinfo(msg)
	db=MyDB.UserDB(wechat_db)
	db.logUserOp(uinfo)
	rr=re.search(patern_code,uinfo['msg_content'])
	code=rr.group(1)
	mylogger.info("verifyCode:%s" % str(vars(msg)))
	if not code==session.get('code'):
		return "校验码不正确\n"+noPrivMsg
	name=session.get('name')
	mail=session.get('mail')
	ct=threading.Thread(target=validCodeOK,args=(uinfo,name,mail))
	ct.start()
	del session['code'] #这时权限都赋予后，临时的code键值，可以删除掉了
	return "帐号验证正确，权限正在开通。请使用help命令查看帮助信息"	

	
#定义处理文本消息的函数
@robot.text  #普通的文本消息内容响应处理
def echo(msg):
	mylogger.info("just text :%s" % str(vars(msg)))
	uinfo=msg2uinfo(msg)
	db=MyDB.UserDB(wechat_db)
	db.logUserOp(uinfo)
	if not uinfo['user']:
		uinfo['in_out']='server_reply'
		uinfo['msg_content']=noPrivMsg
		db.logUserOp(uinfo)
		return noPrivMsg
	print("msg=%s" % uinfo['msg_content'])
	mylogger.info(f"trying to publish to MQTT: /{cfg.username}/wechat/text")
	openid=str(msg.source)
	MyMQTT.PubMsg(topic=f'/{cfg.username}/wechat/text',payload=MyMQTT.pack_data(msgType="text",openid=openid,data=uinfo['msg_content']))
	return ''
	#return "message=%s,session=%s" % (str(message.source),str(session))

#定义处理voice消息的函数
@robot.voice
def voice(msg):
	mylogger.info("just voice :%s" % str(vars(msg)))
	uinfo=msg2uinfo(msg)
	db=MyDB.UserDB(wechat_db)
	db.logUserOp(uinfo)
	if not uinfo['user']:
		uinfo['in_out']='server_reply'
		uinfo['msg_content']=noPrivMsg
		db.logUserOp(uinfo)
		return noPrivMsg	
	msgid=msg.message_id
	MediaId=msg.MediaId
	openid=str(msg.source)
	target=str(msg.target)
	rec=msg.recognition
	format=msg.format
	sys.stderr.write("msgid=%s,MediaId=%s,source=%s,rec=%s,format=%s,uinfo=%s\n" % (msgid,MediaId,openid,rec,format,uinfo))
	ct = threading.Thread(target=deal_vioce,args=(openid,MediaId,uinfo))
	ct.setDaemon(True)
	ct.start()
	return ''


if __name__=='__main__'	:
    # 让服务器监听在 0.0.0.0:8001
    #这个可以和apache/ngix的反向代理配合做域名一致性，否则微信不支持非80/443端口的url绑定
    mylogger.info("Starting server")
    robot.config['HOST'] = '0.0.0.0'
    robot.config['PORT'] = 8001

    ct = threading.Thread(target=MyMQTT.SubRespone)
    ct.setDaemon(True)
    ct.start()
    
    #开发模式下，设置reloader参数，并且环境变量配置BOTTLE_LOCKFILE=/tmp/bottle.lock
    # 每次修改脚本，让它自己重启bottle server
    #robot.wsgi.run(server=robot.config['SERVER'],host=robot.config['HOST'],port=robot.config['PORT'],reloader=True)
    robot.run() #直接默认run方式
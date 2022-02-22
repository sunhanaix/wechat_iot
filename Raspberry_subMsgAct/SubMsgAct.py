#!/usr/local/bin/python3
import os,sys,re,json,random
import time,base64,difflib
import paho.mqtt.client as mqtt
import base64,threading
import broadlink
from broadlink.exceptions import ReadError, StorageError
import configparser
import MsgAct_config as cfg
from ChineseNum2Num import cn2dig
import requests
import mymp3
from MyTTS import voice_to_word,word_to_voice,myplay
import Alarm

'''
本程序订阅/wechat/text和/wechat/voice消息,
   收到微信消息后，识别成对应的指令，
   然后也用MQTT发布消息到比如/iot/broadlink上。
   并发送响应消息给/wechat/response，告知执行情况
   （/wechat/response的消息，由stonehead_wechat的公网服务器上监听消息，做响应处理）
/iot/broadlink，也由其进行监听
   发现有消息后，解析消息指令，发送对应的iot指令
   并发送响应消息给/wechat/response，告知执行情况
   （/wechat/response的消息，由stonehead_wechat的公网服务器上监听消息，做响应处理）
'''
VERSION = 'v0.9.0.20220211'

mylogger=cfg.logger


#下面读取broadlink操控的配置文件信息
bl_config=configparser.ConfigParser()
bl_config.read(cfg.broadlink_cfg,encoding='utf8')
print(cfg.broadlink_cfg)
print([k for k in bl_config],"\n")
#下面读取mitv.ini小米电视配置文件可以操控的配置信息
mitv_config=configparser.ConfigParser()
mitv_config.read(cfg.mitv_cfg,encoding='utf8')
print(cfg.mitv_cfg)
print([k for k in mitv_config],"\n")
#下面读取miio.ini小米miservice/micli.py可以操控的配置信息
miio_config=configparser.ConfigParser()
miio_config.read(cfg.miio_cfg,encoding='utf8')
print(cfg.miio_cfg)
print([k for k in miio_config],"\n")

dev=None

def get_broadlink_rm(timeout=3): #找到当前同网段中的broadlink设备
    devices = broadlink.discover(timeout=timeout)
    if not devices:
        return None
    for device in devices:
        if isinstance(device, broadlink.rm):
            break
    else:
        raise Exception("Not broadlink rm Pro device found !!")
    device.auth()
    return device

def now():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

def pack_data(msgType,data=None,fname=None):
    '''
    :param msgType: 该报文的类型，可以是text, audio , image , file等等
    :param data:  报文的具体内容，如果给了fname，则data应该为空
    :param fname: 要发送的文件名字，如果给data，则此fname应该为空
    :return:  #返回编码后的报文信息
    '''
    #给定一个文件名，获得文件大小信息，把文件内容用bytearray转码，好发送给MQTT
    #数据的头部信息，包含了文件名字，文件大小，报文类型，内容
    msgId=random.randint(0,4294967296)
    if data:
        size = len(data)
        if msgType=='text':
            b64_data=data
        else:
            b64_data=bytearray(data)
            b64_data = base64.b64encode(data).decode()
        return json.dumps({'type':msgType,'size':size,'msgId':msgId,'fname':fname,'data':b64_data})
    if fname:
        size = os.stat(fname).st_size
        data = open(fname, 'rb').read()
        b64_data = base64.b64encode(data).decode()
        return json.dumps({'type': msgType, 'size': size,'msgId':msgId, 'fname': fname, 'data': b64_data})

def unpack_data(raw_data): #把前面pack_data编码后的数据，还原回来
    try:
        data=raw_data.decode()
    except Exception as e:
        mylogger.error(f"raw_data can not be decode,ERROR={e}")
        return ''
    try:
        data=json.loads(data)
    except Exception as e:
        mylogger.error(f"data can not be json.loads,ERROR={e}")
        return ''
    if not data['type']=='text':
        try:
            data['data']=base64.b64decode(data['data'])
        except Exception as e:
            mylogger.error(f"data can not be b64decode,ERROR={e}")
    return data
    
    
def simRatio(s1,s2): #比较两个字符串的相似度，结果为0-1之间的数
	s=difflib.SequenceMatcher(None,s1,s2)
	return s.ratio()

def bestSim(ss): #给定个字符串，在config.py里面的keywords里面，匹配一个最接近的keyword
    max_sim=0
    ret=None
    for k in cfg.keywords:
        #print(f"ss={ss},type of ss={type(ss)},k={k},type of k={type(k)})")
        if simRatio(ss,k) >max_sim:
            max_sim=simRatio(ss,k)
            ret=k
    if max_sim <cfg.accurate: #相似度小于设定值，认为不可信
        return {'k':None,'r':max_sim}
    return {'k':ret,'r':max_sim}
            
try:
    dev=get_broadlink_rm()
except Exception as e:
    mylogger.error(e)
    mylogger.error("未找到broadlink RM设备，请确认是否加电！!")

print(dev)

    
def actWechatVoice(data): 
    #处理收到的微信语音信息，调用百度语音识别成文字，然后到关键keywords指令列表里面去匹配到一个最接近的一个指令
    #找到最接近的指令，用MQTT发布消息给keyword对应指定的消息topic，后续由对应的actXXXXXX函数处理
    if not os.path.isdir(cfg.voice_dir):
        os.mkdir(cfg.voice_dir)
    fname=data['fname']
    if data['type']=='voice' and fname:
        fname=os.path.join(cfg.voice_dir,os.path.basename(fname))
        open(fname,'wb').write(data['data'])
        openid = data['openid']
        words=voice_to_word(fname)
        mylogger.info(f"{sys.argv[0]}: Speach-To-Text:{words}")
        if re.search('广播',words):
            mylogger.info("found:'广播' keyword")
            PubMsg(topic=f'/{cfg.username}/broadcast/audio', payload=pack_data(msgType="text", data=fname))
            PubMsg(topic=f'/{cfg.username}/wechat/response', payload=pack_data(msgType="text", data={'openid':openid,'code':0,'text':f'您的语音广播指令已执行'}))
            return        
        match_keywords = bestSim(words)
        mylogger.info(f"{sys.argv[0]}: match_keywords={match_keywords}")
        if match_keywords['r'] <cfg.accurate:
            PubMsg(topic=f'/{cfg.username}/wechat/response', payload=pack_data(msgType="text", data={'openid':openid,'code':0,'text':f'您的指令未能识别，请输入help查看支持的指令'}))
            return
        if match_keywords['k']:
            k=match_keywords['k']
            msg=cfg.keywords[k]['msg']
            topic=cfg.keywords[k]['topic']
            msg['openid']=openid
            if k.find('图图时间')>-1 and re.search(r'加(.+)分钟',words):
                minute=re.search(r'加(.+)分钟',words).group(1)
                if not re.search(r'^\d+$',minute):
                    try:
                        minute=cn2dig(minute)
                    except Exception as e:
                         mylogger.error("转换时间失败")
                         return
                mylogger.info(f"尝试给图图加时间")
                PubMsg(topic=f'/{cfg.username}/stanley/time', payload=pack_data(msgType="text", data={'openid':openid,'minute':minute}))
                return            
            if k.find('音量')>-1 and re.search(r'到(.+)',words):
                vol=re.search(r'到(.+)',words).group(1)
                print(f"matched: vol={vol}")
                if re.search(r'(\d+)',vol):
                    vol=re.search(r'(\d+)',vol).group(1)
                    print(f"matched 1st if switch: vol={vol}")
                else:
                    try:
                        vol=cn2dig(vol)
                    except Exception as e:
                         mylogger.error("转换时间失败")
                         return
                mylogger.info(f"尝试调整音乐音量到{vol}")
                PubMsg(topic=f'/{cfg.username}/iot/mp3', payload=pack_data(msgType="text", data={'openid':openid,'op':'set_vol','vol':vol}))
                PubMsg(topic=f'/{cfg.username}/wechat/response', payload=pack_data(msgType="text", data={'openid':openid,'code':0,'text':f'"音乐音量调整到{vol}"已经发送'}))
                return    
            if k.find('播放')>-1 and re.search(r'播放(.+)的歌',words):
                xxx=re.search(r'播放(.+)的歌',words).group(1)
                print(f"matched: xxx={xxx}")
                mylogger.info(f"尝试播放{xxx}的歌曲")
                PubMsg(topic=f'/{cfg.username}/iot/mp3', payload=pack_data(msgType="text", data={'openid':openid,'op':'play_xxx','xxx':xxx}))
                PubMsg(topic=f'/{cfg.username}/wechat/response', payload=pack_data(msgType="text", data={'openid':openid,'code':0,'text':f'尝试播放{xxx}的歌曲'}))
                return    
            if k.find('叫我xx')>-1 and re.search(r'(.+)(分钟|小时)',words):
                mylogger.info(f"匹配到规则:{k},for words={words}")
                qty=re.search(r'(.+)(分钟|小时)',words).group(1)
                unit=re.search(r'(.+)(分钟|小时)',words).group(2)
                mylogger.info(f"qty={qty},unit={unit}")
                if not re.search(r'^[0-9\.]+$',qty):
                    try:
                        qty=cn2dig(qty)
                    except Exception as e:
                         mylogger.error("转换时间失败")
                         return
                qty=float(qty)
                if unit=='分钟':
                    qty*=60
                else:
                    qty*=3600
                mylogger.info(f"qty={qty} after int")
                desc=re.search(r'叫我(\S*)',words).group(1)
                if desc.lstrip().rstrip()=='':
                    desc='闹钟'
                mylogger.info(f"desc={desc}")
                target_time=time.localtime(time.time()+qty)
                cron_format_time=time.strftime("%M %H %d %m %w",target_time)
                target_time_text=time.strftime("%Y-%m-%d %H:%M",target_time)
                mylogger.info(f"为您设置{target_time_text}的闹钟")
                Alarm.add_alarm_fr_plain(f"{cron_format_time} {desc}")
                PubMsg(topic=f'/{cfg.username}/wechat/response', payload=pack_data(msgType="text", data={'openid':openid,'code':0,'text':f'为您设置{target_time_text}的闹钟'}))
                return 
            PubMsg(topic=f'/{cfg.username}{topic}', payload=pack_data(msgType="text", data=msg))
            PubMsg(topic=f'/{cfg.username}/wechat/response', payload=pack_data(msgType="text", data={'openid':openid,'code':0,'text':f'您的指令:"{k}"已经发送'}))

def actWechatText(data):
    #处理收到的微信文本信息，然后到关键keywords指令列表里面去匹配到一个最接近的一个指令
    #找到最接近的指令，用MQTT发布消息给keyword对应指定的消息topic，后续由对应的actXXXXXX函数处理    
    ss=data['data'].lstrip().rstrip()
    openid = data['openid']
    mylogger.info(f"{sys.argv[0]}: wechat get text:{ss}")
    if re.search(r'^广播',ss):
        ss=ss.replace('广播通知','').replace('广播','')
        mylogger.info(f"after raplce:ss={ss}")
        PubMsg(topic=f'/{cfg.username}/broadcast/text', payload=pack_data(msgType="text", data=ss))
        PubMsg(topic=f'/{cfg.username}/wechat/response', payload=pack_data(msgType="text", data={'openid':openid,'code':0,'text':f'您的广播:"{ss}"已经发送'}))
        return
    if re.search(r'图图时间.+加(\d+)分钟',ss):
        minute=re.search(r'图图时间.+加(\d+)分钟',ss).group(1)
        mylogger.info(f"尝试给图图加时间")
        PubMsg(topic=f'/{cfg.username}/stanley/time', payload=pack_data(msgType="text", data={'openid':openid,'minute':minute}))
        return
    if re.search(r'音量调整*到(\d+)',ss):
        vol=re.search(r'音量调整*到(\d+)',ss).group(1)
        mylogger.info(f"尝试调整音量到{vol}")
        PubMsg(topic=f'/{cfg.username}/iot/mp3', payload=pack_data(msgType="text", data={'openid':openid,'op':'set_vol','vol':vol}))
        PubMsg(topic=f'/{cfg.username}/wechat/response', payload=pack_data(msgType="text", data={'openid':openid,'code':0,'text':f'"音乐音量调整到{vol}"已经发送'}))
        return
    if re.search(r'播放(.+)的歌',ss):
        xxx=re.search(r'播放(.+)的歌',ss).group(1)
        mylogger.info(f"搜索{xxx}的歌曲")
        PubMsg(topic=f'/{cfg.username}/iot/mp3', payload=pack_data(msgType="text", data={'openid':openid,'op':'play_xxx','xxx':xxx}))
        PubMsg(topic=f'/{cfg.username}/wechat/response', payload=pack_data(msgType="text", data={'openid':openid,'code':0,'text':f'尝试播放{xxx}的歌曲'}))
        return
    if re.search(r'(.+)(分钟|小时)后叫我(\S*)',ss):
        mylogger.info(f"匹配到闹钟规则")
        qty=re.search(r'(.+)(分钟|小时)后叫我(\S*)',ss).group(1)
        qty=float(qty)
        unit=re.search(r'(.+)(分钟|小时)后叫我(\S*)',ss).group(2)
        if unit=='分钟':
            qty*=60
        else:
            qty*=3600
        desc=re.search(r'(.+)(分钟|小时)后叫我(\S*)',ss).group(2)
        if desc.lstrip().rstrip()=='':
            desc='闹钟'
        target_time=time.localtime(time.time()+qty)
        cron_format_time=time.strftime("%M %H %d %m %w",target_time)
        target_time_text=time.strftime("%Y-%m-%d %H:%M",target_time)
        mylogger.info(f"为您设置{target_time_text}的闹钟")
        Alarm.add_alarm_fr_plain(f"{cron_format_time} {desc}")
        PubMsg(topic=f'/{cfg.username}/wechat/response', payload=pack_data(msgType="text", data={'openid':openid,'code':0,'text':f'为您设置{target_time_text}的闹钟'}))
        return        
    match_keywords=bestSim(ss)
    mylogger.info(f"{sys.argv[0]}: match_keywords={match_keywords}")
    if match_keywords['r'] <cfg.accurate:
        PubMsg(topic=f'/{cfg.username}/wechat/response', payload=pack_data(msgType="text", data={'openid':openid,'code':0,'text':f'您的指令未能识别，请输入help查看支持的指令'}))
        return
    if match_keywords['k']:
        k=match_keywords['k']
        msg=cfg.keywords[k]['msg']
        topic=cfg.keywords[k]['topic']
        msg['openid']=openid
        PubMsg(topic=f'/{cfg.username}{topic}', payload=pack_data(msgType="text", data=msg))
        PubMsg(topic=f'/{cfg.username}/wechat/response', payload=pack_data(msgType="text", data={'openid':openid,'code':0,'text':f'您的指令:"{k}"已经发送'}))                

def actBroadlink(data):
    #处理收到的MQTT的topic是broadlink的消息，到其配置文件中，找到对应的设备(item)，执行对应的操作(op)
    #也就是对应的base64编码的红外线/射频信号编码，然后发射它
    global dev
    global bl_config
    mylogger.info(f"尝试发送broadlink指令，data={data}")
    openid=data['openid']    
    if not dev:
        dev = get_broadlink_rm()
        if not dev:
            mylogger.info("未找到broadlink RM设备，请确认是否加电！")
            PubMsg(topic=f'/{cfg.username}/wechat/response', payload=pack_data(msgType="text", data={'openid':openid,'code':1,'text':f'未找到broadlink RM设备，请确认是否加电！'}))                
            return
    try:
        item=data['item']
        op=data['op']
        v=bl_config[item][op]
        mylogger.info(f"item={item},op={op},v={v}")
        dev.send_data(base64.b64decode(v))
    except Exception as e:
        mylogger.error(e)
        mylogger.error(f"ERROR: item={item},op={op},v={v}")
        PubMsg(topic=f'/{cfg.username}/wechat/response', payload=pack_data(msgType="text", data={'openid':openid,'code':2,'text':f'指令执行出现异常，ERROR:{e}'}))                

def actTV(data):
    #处理收到的MQTT的topic是/iot/mitv的消息，到其配置文件中，找到对应的设备(item)，执行对应的操作(op)
    #用requests.get去访问这个url来执行操作电视    
    global mitv_config
    mylogger.info(f"尝试发送电视控制指令，data={data}")
    openid=data['openid']    
    try:
        item=data['item']
        op=data['op']
        v=mitv_config[item][op]
        mylogger.info(f"item={item},op={op},v={v}")
        r=requests.get(v)
        ret=r.json()
        mylogger.info(f"control tv ret={ret}")
    except Exception as e:
        mylogger.error(e)
        mylogger.error(f"ERROR: item={item},op={op},v={v}")
        PubMsg(topic=f'/{cfg.username}/wechat/response', payload=pack_data(msgType="text", data={'openid':openid,'code':2,'text':f'指令执行出现异常，ERROR:{e}'}))                

def actMIIO(data):
    #处理收到的MQTT的topic是/iot/miio的消息，到其配置文件中，找到对应的设备(item)，执行对应的操作(op)
    #然后设置MI_USER/MI_PASS/MI_DID环境变量,执行类似/home/pi/MiService/micli.py '2-1=#false'之类的指令
    global miio_config
    mylogger.info(f"尝试发送micli指令，data={data}")
    openid=data['openid']    
    try:
        item=data['item']
        op=data['op']
        mi_did=miio_config[item]['mi_did']
        v=miio_config[item][op]
        mylogger.info(f"item={item},mi_did={mi_did},op={op},v={v}")
        cmd=f"{cfg.miio_cmd} '{v}'"
        mylogger.info(cmd)
        os.environ['MI_USER']=cfg.mi_user
        os.environ['MI_PASS']=cfg.mi_pass
        os.environ['MI_DID']=mi_did
        os.system(cmd)
    except Exception as e:
        mylogger.error(e)
        mylogger.error(f"ERROR: item={item},op={op},v={v}")
        PubMsg(topic=f'/{cfg.username}/wechat/response', payload=pack_data(msgType="text", data={'openid':openid,'code':2,'text':f'指令执行出现异常，ERROR:{e}'}))                

def actAskKeywords(data):
    #处理收到的MQTT的topic是/wechat/askKeywords的消息，到config.py的配置文件中，去找keywords
    #把所有keywords的指令信息，publish到/wechat/help消息上，后续由stonehead_wechat程序端响应以及发给对应微信用户
    if cfg.debug:
        mylogger.debug(f"in actAskKeywords(),data={data}")
    openid=data['openid']
    keywords=list(cfg.keywords.keys())
    msg={'openid':openid,'code':0,'keywords':keywords}
    mylogger.info(f"trying to publish: topic=/{cfg.username}/wechat/help,data={msg}")
    PubMsg(topic=f'/{cfg.username}/wechat/help', payload=pack_data(msgType="text", data=msg))                

def actBroadcastText(data):
    #处理收到的MQTT的topic是/broadcast/text，
    #把它通过树莓派接的客厅音箱广播出来
    if cfg.debug:
        mylogger.debug(f"in actBroadcastText(),data={data}")
    audio_file=word_to_voice(data)
    mylogger.info(f"{data}-->{audio_file}")
    if audio_file:
        myplay(audio_file,2)
    else:
        mylogger.error("文字合成语音没有成功，没找到结果音频文件")

def actBroadcastAudio(data):
    #处理收到的MQTT的topic是/broadcast/text，
    #把它通过树莓派接的客厅音箱广播出来    
    if cfg.debug:
        mylogger.debug(f"in actBroadcastAudio(),data={data}")
    if data and os.path.isfile(data):
        mylogger.info("try to play it")
        myplay(data,2)
    else:
        mylogger.error("没有找到微信发来的语音文件，广播不成功")

def actStanleyTime(data):
    #处理收到的MQTT的topic是/stanley/time，
    #给图图加上网时间        
    if cfg.debug:
        mylogger.debug(f"in actStanleyTime(),data={data}")
    minute=data['minute']
    cmd=f"{cfg.deny_stanley} off {minute}"
    try:
        openid=data['openid']
    except Exception as e:
        mylogger.error(e)
        openid=None
    if openid and not openid in cfg.allow_openid:
        PubMsg(topic=f'/{cfg.username}/wechat/response', payload=pack_data(msgType="text", data={'openid':openid,'code':2,'text':'您没有执行加时间的权限'}))                
        return
    mylogger.info(f"try to exec {cmd}")
    target_ts=int(minute)*60+time.time()
    target_time=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(target_ts))
    os.system(cmd)
    PubMsg(topic=f'/{cfg.username}/wechat/response', payload=pack_data(msgType="text", data={'openid':openid,'code':2,'text':f'+{minute}分钟已执行，预计到{target_time}结束'}))          

def actMp3(data):
    #处理收到的MQTT的topic是/iot/mp3，
    #对mp3播放进行控制          
    if cfg.debug:
        mylogger.debug(f"in actMp3(),data={data}")
    if data['op']=='stop':
        mymp3.stop_mp3()
        return
    if data['op']=='pause':
        mymp3.pause_mp3()
        return
    if data['op']=='resume':
        mymp3.resume_mp3()
        return
    if data['op']=='play_rand':
        mymp3.play_rand()
        return
    if data['op']=='prev':
        mymp3.prev_mp3()
        return
    if data['op']=='next':
        mymp3.next_mp3()
        return
    if data['op']=='set_vol':
        mymp3.set_vol_mp3(data['vol'])
        return
    if data['op']=='play_xxx':
        mymp3.play_xxx_mp3(data['xxx'])
        return

class SubMsg(): #订阅者模式，初始化订阅哪些topic，然后一直loop等待收到消息
    def __init__(self,broker=cfg.broker,port=cfg.port,user=cfg.username,passwd=cfg.password):
        #client_id = f'mqtt-subscriber-{random.randint(0, 1000)}'
        client_id = f'mqtt-SubMsgAct-sub'
        self.client = mqtt.Client(client_id=client_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.username_pw_set(username=user, password=passwd)
        self.client.connect(broker, port, 600)  # 600为keepalive的时间间隔
        self.sub_all()
        self.client.loop_forever()
        mylogger.info("end loop")

    def sub_all(self): #从配置文件config.py中，读取topic主题，并订阅它
        sub_act=['/iot/broadlink', #通过博联设备可以控制的操作
                    '/iot/tv',  #关于几个电视，可以控制的操作
                    '/iot/miio', #调用miservice的micli.py可以控制的操作
                    '/iot/mp3',  #播放歌曲的操作
                    '/broadcast/text',  #用树莓派音箱广播文字TTS输出语音
                    '/broadcast/audio', #用树莓派音箱广播微信语音amr文件
                    '/wechat/text',  #接收公网微信服务器发来的文本信息，做指令解析
                    '/wechat/voice', #接收公网微信服务器发来的语音信息，做指令解析
                    '/wechat/askKeywords', #接收公网微信服务器发来的查询有哪些关键字请求，结果回给MQTT的/wechat/help的topic
                    '/stanley/time',  #接收放开stanley手机上网管控的时间（分钟为单位）
                    ]
        for topic in sub_act:
            mylogger.info(f"topic=/{cfg.username}{topic} was subscribed")
            self.client.subscribe(topic=f'/{cfg.username}{topic}', qos=0)

    def on_connect(self,client, userdata, flags, rc):
        mylogger.info(f"Connected with result code: {rc},userdata={userdata},flags={flags}")

    def on_message(self,client, userdata, msg):
        try:
            ret=unpack_data(msg.payload)
        except Exception as e:
            mylogger.error(f"error:{e}")
            return
        mylogger.info(f"topic={msg.topic},ret={ret}")
        topic=msg.topic
        #注意下面，有的是传ret去响应，有的是ret['data']去响应，遗留问题
        try:
            openid=ret['openid']
        except Exception as e:
            mylogger.error(e)
            openid=None
        if topic==f'/{cfg.username}/wechat/text':
            actWechatText(ret)
            return
        if topic==f'/{cfg.username}/wechat/voice':
            actWechatVoice(ret)
            return
        if topic==f'/{cfg.username}/iot/broadlink':
            mylogger.info(f"found msg on /{cfg.username}/iot/broadlink")
            actBroadlink(ret['data'])
            return
        if topic==f'/{cfg.username}/iot/tv':
            mylogger.info(f"found msg on /{cfg.username}/iot/tv")
            actTV(ret['data'])
            return
        if topic==f'/{cfg.username}/iot/miio':
            mylogger.info(f"found msg on /{cfg.username}/iot/miio")
            actMIIO(ret['data'])
            return
        if topic==f'/{cfg.username}/wechat/askKeywords':
            mylogger.info(f"found msg on /{cfg.username}/wechat/askKeywords")
            actAskKeywords(ret)
            return
        if topic==f'/{cfg.username}/broadcast/text':
            mylogger.info(f"found msg on /{cfg.username}/broadcast/text")
            actBroadcastText(ret['data'])
            return            
        if topic==f'/{cfg.username}/broadcast/audio':
            mylogger.info(f"found msg on /{cfg.username}/broadcast/audio")
            actBroadcastAudio(ret['data'])
            return
        if topic==f'/{cfg.username}/stanley/time':
            mylogger.info(f"found msg on /{cfg.username}/stanley/time")
            actStanleyTime(ret['data'])
            return                                    
        if topic==f'/{cfg.username}/iot/mp3':
            mylogger.info(f"found msg on /{cfg.username}/iot/mp3")
            actMp3(ret['data'])
            return                                    
class PubMsg(): #publish一个消息到MQTT的一个topic上
    def __init__(self, topic, payload, broker=cfg.broker, port=cfg.port, user=cfg.username, passwd=cfg.password):
        #client_id = f'mqtt-publisher-{random.randint(0, 1000)}'
        client_id = f'mqtt-mqtt-SubMsgAct-pub'
        self.client = mqtt.Client(client_id=client_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.username_pw_set(username=user, password=passwd)
        self.client.connect(broker, port, 600)  # 600为keepalive的时间间隔
        self.client.publish(topic=topic, payload=payload, qos=0)

    def on_connect(self,client, userdata, flags, rc):
        mylogger.info("Connected with result code: " + str(rc))

    def on_message(self,client, userdata, msg):
        mylogger.info(msg.topic + " " + str(msg.payload))


if __name__=='__main__':
    #先启动一个闹钟守护进程，监控管理闹钟事件
    mylogger.info("尝试执行Alarm.loop")
    ct = threading.Thread(target=Alarm.loop)
    ct.setDaemon(True)
    ct.start()

    SubMsg()
    #SubMsg()

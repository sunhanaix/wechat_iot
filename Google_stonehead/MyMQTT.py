#!/usr/bin/python3
import os,sys,re,json,random
import time,base64
import paho.mqtt.client as mqtt
import MyDB
import stonehead_wechat

#由于配置文件，可能是xxx_config.py，为了便于移植，这里动态载入下
import glob,importlib
app_path = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.append(app_path)
cfg_file=glob.glob(f'{app_path}/*config.py')[0]
cfg_file=os.path.basename(cfg_file)
cfg_model=os.path.splitext(cfg_file)[0]
cfg=importlib.import_module(cfg_model)

#封装的MQTT类，用于MQTT消息的发布，而订阅部分，专为微信的几个订阅消息进行了定制

VERSION = 'v0.9.0.20220211'
mylogger=cfg.logger


def pack_data(msgType,data=None,openid=None,fname=None):
    '''
    :param msgType: 该报文的类型，可以是text, audio , image , file等等
    :param data:  报文的具体内容，如果给了fname，则data应该为空
    :param fname: 要发送的文件名字，如果给data，则此fname应该为空
    :return:  #返回编码后的报文信息
    '''
    #给定一个文件名，获得文件大小信息，把文件内容用bytearray转码，好发送给MQTT
    #数据的头部信息，包含了文件名字，文件大小，报文类型，内容
    if data:
        size = len(data)
        if msgType=='text':
            b64_data=data
        else:
            b64_data=bytearray(data)
            b64_data = base64.b64encode(data).decode()
        return json.dumps({'type':msgType,'openid':openid,'size':size,'fname':fname,'data':b64_data})
    if fname:
        size = os.stat(fname).st_size
        data = open(fname, 'rb').read()
        b64_data = base64.b64encode(data).decode()
        return json.dumps({'type': msgType, 'openid':openid,'size': size, 'fname': fname, 'data': b64_data})

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

class SubRespone(): #给StoneHead使用的class，订阅/wechat/response这个topic，然后一直loop等待收到消息
    def __init__(self,broker=cfg.broker,port=cfg.mqtt_port,user=cfg.username,passwd=cfg.password):
        #client_id = f'mqtt-subscriber-{random.randint(0, 1000)}'
        client_id = f'mqtt-serv-subReponse-{cfg.username}'
        self.client = mqtt.Client(client_id=client_id)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.username_pw_set(username=user, password=passwd)
        self.client.connect(broker, port, 600)  # 600为keepalive的时间间隔
        self.sub_all()
        self.client.loop_forever()
        mylogger.info("end loop")

    def sub_all(self): #从配置文件config.py中，读取topic主题，并订阅它
        topics=[f'/{cfg.username}/wechat/response',
                f'/{cfg.username}/wechat/help',
                f'/{cfg.username}/heartbeat/client',
                ]
        for topic in topics:
            mylogger.info(f"topic={topic} was subscribed")
            self.client.subscribe(topic=topic, qos=0)

    def on_connect(self,client, userdata, flags, rc):
        mylogger.info(f"Connected with result code: {rc},userdata={userdata}")

    def on_message(self,client, userdata, msg):
        try:
            ret=unpack_data(msg.payload)
        except Exception as e:
            mylogger.error(f"error:{e}")
            return
        mylogger.info(f"topic={msg.topic},mid={msg.mid},qos={msg.qos},ret={ret}")
        openid=ret['data']['openid']
        if msg.topic==f'/{cfg.username}/wechat/response': #要是收到树莓派那面publish的执行反馈信息，就把它们扔回给微信用户
            msg = ret['data']['text']
            stonehead_wechat.client.send_text_message(openid,msg)
            return
        if msg.topic==f'/{cfg.username}/wechat/help': #要是收到了树莓派那面publish的支持的keywords有哪些，那就把它们扔回给微信用户
            keywords=ret['data']['keywords']
            content="\n\n".join(keywords)+"\n\n"
            stonehead_wechat.client.send_text_message(openid,content)
            return
        if msg.topic==f'/{cfg.username}/heartbeat/client': #要是收到了树莓派那面publish的心跳信息
            ts=ret['data']['ts']
            #收到心跳信息，就把它记录到日志中，并更新DB中的记录
            mylogger.info(f"got heartbeat,ts={ts}")
            kv=MyDB.KeyValueStore(cfg.wechat_db)
            kv['last_heartbeat']={'server_ts':int(time.time()),'client_ts':int(ts)}
            kv.close()
            return


class PubMsg(): #用于publish消息到指定topic的类封装
    def __init__(self, topic, payload, broker=cfg.broker, port=cfg.mqtt_port, user=cfg.username, passwd=cfg.password):
        client_id = f'mqtt-serv-pub'
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
    #PubMsg(topic='/broadcast/text',payload=pack_data(msgType="vioce",fname="XzK2761goVe6eoM8qpAlnc1V4wlsScXhC49dP_jzNVF5BGM4_KEyA7BOT_FUjwhG.amr"))
    #msg={'item':'楼下客厅灯','op':'灯'}
    #PubMsg(topic='/iot/broadlink', payload=pack_data(msgType="text",data=msg))
    SubRespone()

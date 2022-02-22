import os,sys,re,json,random,logging

debug=False
voice_dir='voice' #存放语音消息的本地缓存目录
video_dir='video' #存放视频消息的本地缓存目录
image_dir='image' #存放图片消息的本地缓存目录

broker = 'x.x.x.x' #MQTT服务器地址
port = 1883
username='sunbeat' #MQTT用户名
password='mqtt_password' #MQTT密码

mp3_user='sunbeat'  #自己搭的音乐播放web登录的用户名
mp3_pass='password' #自己搭的音乐播放web登录的密码
mp3_url='http://localhost/mp3'  #自己搭的音乐播放web地址

accurate=0.4 #获得指令与指令列表匹配度，0-1的置信区间，1为完全匹配；小于此值，认为没有匹配到技能
deny_stanley='/var/www/html/deny_stanley.py'  #一键禁止小孩手机、pad上网控制脚本路径
allow_openid=['or_fJ6cvJqrK80PN7MsI8W123456'] #允许执行deny_stanley脚本的openid列表，目前执行其它操作，没有做权限控制
broadlink_cfg=r'/var/www/html/broadlink/MyBroadlink.ini'  #博联遥控器学习好了的射频信号和红外信号配置文件
mitv_cfg='mitv.ini'  #几个小米电视的操作控制配置文件
miio_cfg='miio.ini'  #几个小米智能设备控制的配置文件
miio_cmd=r'/home/pi/MiService/micli.py'  #miservice带的操作小米智能设备的命令行程序，github上自行下载
mi_user='13512345678'  #小米官网的账号
mi_pass='mipassword'   #小米官网的密码
baidu_aip_APP_ID='12345678'  #百度语音识别以及文字转语音的id（需要自己申请）
baidu_aip_API_KEY = 'SvW84112ylD9V3EX12345678'
baidu_aip_SECRET_KEY = 'DNt5GsVk3lGxBIN5uyBhzH5F12345678'

alarm_cfg='alarm.cfg' #闹钟的配置文件
audio_dev='hw:0,0' #树莓派下播放音频的设备
alarm_mp3='alarm.mp3' #闹钟的铃声文件


keywords={
    '打开楼下客厅灯':{'topic':'/iot/broadlink','msg':{'item':'楼下客厅灯','op':'灯'},},
    '关闭楼下客厅灯':{'topic':'/iot/broadlink','msg':{'item':'楼下客厅灯','op':'灯'},},
    '打开楼下客厅风扇':{'topic':'/iot/broadlink','msg':{'item':'楼下客厅灯','op':'中'},},
    '关闭楼下客厅风扇':{'topic':'/iot/broadlink','msg':{'item':'楼下客厅灯','op':'风扇停'},},

    '打开楼上客厅灯': {'topic': '/iot/broadlink', 'msg': {'item': '楼上客厅灯','op': '灯'}, },
    '关闭楼上客厅灯': {'topic': '/iot/broadlink', 'msg': {'item': '楼上客厅灯','op': '灯'}, },
    '打开楼上客厅风扇': {'topic': '/iot/broadlink', 'msg': {'item': '楼上客厅灯', 'op': '中'}, },
    '关闭楼上客厅风扇': {'topic': '/iot/broadlink', 'msg': {'item': '楼上客厅灯','op': '风扇停'}, },

    '打开厨房灯': {'topic': '/iot/broadlink', 'msg': {'item': '厨房灯','op': '灯'}, },
    '关闭厨房灯': {'topic': '/iot/broadlink', 'msg': {'item': '厨房灯','op': '灯'}, },
    '打开厨房风扇': {'topic': '/iot/broadlink', 'msg': {'item': '厨房灯', 'op': '中'}, },
    '关闭厨房风扇': {'topic': '/iot/broadlink', 'msg': {'item': '厨房灯','op': '风扇停'}, },

    '打开楼下图图房间灯': {'topic': '/iot/broadlink', 'msg': {'item': '楼下图图房间灯','op': '开关'}, },
    '关闭楼下图图房间灯': {'topic': '/iot/broadlink', 'msg': {'item': '楼下图图房间灯','op': '开关'}, },
    '打开楼上主卧灯': {'topic': '/iot/broadlink', 'msg': {'item': '楼上主卧灯','op': '开关'}, },
    '关闭楼上主卧灯': {'topic': '/iot/broadlink', 'msg': {'item': '楼上主卧灯','op': '开关'}, },

    '减小功放音量': {'topic': '/iot/broadlink', 'msg': {'item': '楼下客厅功放','op': 'vol_down'}, },
    '增加功放音量': {'topic': '/iot/broadlink', 'msg': {'item': '楼下客厅功放','op': 'vol_up'}, },

    '关闭客厅电视': {'topic': '/iot/tv', 'msg': {'item': '客厅电视','op': '关闭'}, },
    '客厅电视向上键': {'topic': '/iot/tv', 'msg': {'item': '客厅电视','op': '向上键'}, },
    '客厅电视向下键': {'topic': '/iot/tv', 'msg': {'item': '客厅电视','op': '向下键'}, },
    '客厅电视向左键': {'topic': '/iot/tv', 'msg': {'item': '客厅电视','op': '向左键'}, },
    '客厅电视向右键': {'topic': '/iot/tv', 'msg': {'item': '客厅电视','op': '向右键'}, },
    '客厅电视确认键': {'topic': '/iot/tv', 'msg': {'item': '客厅电视','op': '确认键'}, },
    '客厅电视主界面': {'topic': '/iot/tv', 'msg': {'item': '客厅电视','op': '主界面'}, },        
    '客厅电视返回键': {'topic': '/iot/tv', 'msg': {'item': '客厅电视','op': '返回键'}, },
    '客厅电视菜单键': {'topic': '/iot/tv', 'msg': {'item': '客厅电视','op': '菜单键'}, },
    '客厅电视大点声': {'topic': '/iot/tv', 'msg': {'item': '客厅电视','op': '大点声'}, },
    '客厅电视小点声': {'topic': '/iot/tv', 'msg': {'item': '客厅电视','op': '小点声'}, },
        
    '打开图图房间空调': {'topic': '/iot/miio', 'msg': {'item': '图图房间空调','op': '打开'}, },
    '关闭图图房间空调': {'topic': '/iot/miio', 'msg': {'item': '图图房间空调','op': '关闭'}, },        
    '打开楼上主卧空调': {'topic': '/iot/miio', 'msg': {'item': '楼上主卧空调','op': '打开'}, },
    '关闭楼上主卧空调': {'topic': '/iot/miio', 'msg': {'item': '楼上主卧空调','op': '关闭'}, },        
    '打开楼上书房空调': {'topic': '/iot/miio', 'msg': {'item': '楼上书房空调','op': '打开'}, },
    '关闭楼上书房空调': {'topic': '/iot/miio', 'msg': {'item': '楼上书房空调','op': '关闭'}, },        
    '打开院子灯笼': {'topic': '/iot/miio', 'msg': {'item': '院子灯笼','op': '打开'}, },
    '关闭院子灯笼': {'topic': '/iot/miio', 'msg': {'item': '院子灯笼','op': '关闭'}, }, 

    '广播：xxxx':  {'topic': '/broadcast/text', 'msg': {'item': 'xx','op': 'xx'}, }, 
    '广播通知：xxxx':  {'topic': '/broadcast/audio', 'msg': {'item': 'xx','op': 'xx'}, }, 

    '图图时间增加xx分钟':  {'topic': '/stanley/time', 'msg': {'item': 'xx','op': 'xx'}, }, 

    '关闭音乐播放':  {'topic': '/iot/mp3', 'msg': {'item': 'mp3','op': 'stop'}, },
    '暂停播放音乐':  {'topic': '/iot/mp3', 'msg': {'item': 'mp3','op': 'pause'}, },
    '继续播放音乐':  {'topic': '/iot/mp3', 'msg': {'item': 'mp3','op': 'resume'}, },
    '随机播放音乐':  {'topic': '/iot/mp3', 'msg': {'item': 'mp3','op': 'play_rand'}, },
    '上一首歌曲':  {'topic': '/iot/mp3', 'msg': {'item': 'mp3','op': 'prev'}, },
    '下一首歌曲':  {'topic': '/iot/mp3', 'msg': {'item': 'mp3','op': 'next'}, },
    '歌曲音量调到xx':  {'topic': '/iot/mp3', 'msg': {'item': 'mp3','op': 'set_vol'}, },
    '播放xx的歌曲':  {'topic': '/iot/mp3', 'msg': {'item': 'mp3','op': 'play_xxx'}, }, 

    'xx分钟后叫我xx':  {'topic': '/iot/alarm', 'msg': {'item': 'minute','op': 'xx'}, }, 
    'xx小时后叫我xx':  {'topic': '/iot/alarm', 'msg': {'item': 'minute','op': 'xx'}, }, 
    'x点钟叫我xx':  {'topic': '/iot/alarm', 'msg': {'item': 'minute','op': 'xx'}, }, 
    '每天xx点叫我xx':  {'topic': '/iot/alarm', 'msg': {'item': 'day','op': 'xx'}, },
    '每周x点叫我xx':  {'topic': '/iot/alarm', 'msg': {'item': 'week','op': 'xx'}, },     
}


#当前程序运行的绝对路径
app_path = os.path.dirname(os.path.abspath(sys.argv[0]))
#程序输出的log名字，这里用了"程序名.log"的格式
log_file = os.path.basename(sys.argv[0]).split('.')[0] + '.log'

#定log输出格式，配置同时输出到标准输出与log文件
logger = logging.getLogger('mylogger')
logger.setLevel(logging.DEBUG)
log_format= logging.Formatter(
    '%(asctime)s - %(name)s - %(filename)s- %(levelname)s - %(message)s')
log_fh = logging.FileHandler(log_file)
log_fh.setLevel(logging.DEBUG)
log_fh.setFormatter(log_format)
log_ch = logging.StreamHandler()
log_ch.setLevel(logging.DEBUG)
log_ch.setFormatter(log_format)
logger.addHandler(log_fh)
logger.addHandler(log_ch)
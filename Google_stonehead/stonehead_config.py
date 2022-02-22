import os,sys,re,json,random,logging

debug=True

#对接微信公众号的相关参数设置
WechatAppID='wxf02565d1b6123456' 
WechatAppSecret='f04b29ee7ef5242f9928194baa123456'
WechatToken='wechatTokenPassword'
WechatEncodingAESKey='AhWkQssrZflDg8ARx9WMKXBdaMxOCteW12345678'

broker = 'localhost' #MQTT服务器地址
port = 1883  #MQTT服务器的端口，要确保防火墙上放开了这个端口，可以访问
username='sunbeat' #MQTT用户名
password='mypassword' #MQTT密码

baidu_ak='IPHDEesBVxQaVxbH1G6SWwok12345678' #百度用ip查地址，用gps查地址的api接口ak（自己申请）
voice_dir='voice' #存放语音消息的本地缓存目录
video_dir='video' #存放视频消息的本地缓存目录
image_dir='image' #存放图片消息的本地缓存目录
wechat_db='stonehead.db'  #存放微信关注用户等信息的sqlite3数据库

mail_params={
    'smtp_server':'smtp.qq.com',  #用于发送邮件的smtp服务器
#	'smtp_port':587,
	'smtp_port':465,   #发邮件服务器端口
	'fr_account':'12345678@qq.com',  #发邮件账号
	'password':'qq_smtp_password', #发邮件账号密码
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
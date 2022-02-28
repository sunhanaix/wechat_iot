import os,sys,re,json,time
from MyTTS import voice_to_word,word_to_voice,myplay

#由于配置文件，可能是xxx_config.py，为了便于移植，这里动态载入下
import glob,importlib
app_path = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.append(app_path)
cfg_file=glob.glob(f'{app_path}/*config.py')[0]
cfg_file=os.path.basename(cfg_file)
cfg_model=os.path.splitext(cfg_file)[0]
cfg=importlib.import_module(cfg_model)

#闹钟的个配置文件格式，参考使用了crontab的文件格式:
#分钟  小时  日期  月份  周几  闹钟描述
#但不支持crontab的逗号(,)或者除号（/）模式，如需要多个时间段，需要多个条目进行设置
#其中周日，这里用0 ， 不用7

mylogger=cfg.logger
AlarmDone={} #全局变量，记录哪些时间已经闹钟广播过了，格式为AlarmDone['02181134']=True，类似这样的标记
def read_alarm_cfg(): #从闹钟配置文件读取配置
    if not os.path.isfile(cfg.alarm_cfg):
        return []
    lines=open(cfg.alarm_cfg,'r',encoding='utf8').readlines()
    res=[]
    for line in lines:
        line=line.lstrip().rstrip()
        if line=='': #空行跳过
            continue
        if re.search(r'^\#',line): #注释开头跳过
            continue
        try:
            minute,hour,day,month,week,desc=line.split()
        except Exception as e:
            mylogger.error(e)
            mylogger.error(f"ERROR: {line}格式不正确，跳过此行")
            continue
        if not re.search(r'^[\d|\*]+$',minute):
            mylogger.error(f"ERROR: 分钟{minute}格式不正确，跳过此行")
            continue
        if not re.search(r'^[\d|\*]+$',hour):
            mylogger.error(f"ERROR: 小时{hour}格式不正确，跳过此行")
            continue
        if not re.search(r'^[\d|\*]+$',day):
            mylogger.error(f"ERROR: 日期{day}格式不正确，跳过此行")
            continue
        if not re.search(r'^[\d|\*]+$',month):
            mylogger.error(f"ERROR: 月份{month}格式不正确，跳过此行")
            continue
        if not re.search(r'^[\d|\*]+$',week):
            mylogger.error(f"ERROR: 周几{week}格式不正确，跳过此行")
            continue
        res.append({'minute':minute,'hour':hour,'day':day,'month':month,'week':week,'desc':desc})
    return res

def write_alarm_cfg(alarms): #把闹钟的配置写入配置文件
    lines=[]
    for alarm in alarms:
        lines.append(f"{alarm['minute']} {alarm['hour']} {alarm['day']} {alarm['month']} {alarm['week']} {alarm['desc']}")
    open(cfg.alarm_cfg,'w',encoding='utf8').write("\n".join(lines))

def check_alarm(alarm):
    '''
    :param alarm: #给定一个闹钟的配置，检查当前时间是否匹配到
    :return:  Bool,Bool的两个值，第一个表示是否这个闹钟要播报，第二个标记，这是否是个一次性闹钟
    '''
    global AlarmDone
    current = time.localtime()
    minute = current.tm_min
    hour = current.tm_hour
    day = current.tm_mday
    month = current.tm_mon
    week = current.tm_wday + 1
    if week==7:
        week=0
    if cfg.debug:
        mylogger.debug(f"current={minute} {hour} {day} {month} {week}")
        mylogger.debug(f"alarm={alarm['minute']} {alarm['hour']} {alarm['day']} {alarm['month']} {alarm['week']}\n")
    time_mark=f"{month:02d}{day:02d}{hour:02d}{minute:02d}"
    if time_mark in AlarmDone: #要是闹钟已经播报过了，就不再播报了
        return False,False
    #mylogger.info(f"time_mark={time_mark}")
    if not alarm['minute'] == '*' and not int(alarm['minute']) == minute:
        return False,False
    if not alarm['hour'] == '*' and not int(alarm['hour']) == hour:
        return False, False
    if not alarm['day'] == '*' and not int(alarm['day']) == day:
        return False, False
    if not alarm['month'] == '*' and not int(alarm['month']) == month:
        return False, False
    if not alarm['week'] == '*' and not int(alarm['week']) == week:
        return False, False
    if alarm['minute'] == '*' or alarm['hour'] == '*' or alarm['day'] == '*' or alarm['month'] == '*' or alarm['week'] == '*':
        return True,False
    return True,True

def do(alarm):
    mylogger.info(f"do alarm action:{alarm}")
    audio_file=word_to_voice(alarm['desc'])
    mylogger.info(f"{alarm['desc']}-->{audio_file}")
    if audio_file:
        myplay(cfg.alarm_mp3,2) #先播放2遍闹钟铃声
        myplay(audio_file,3) #再播放3遍闹钟名字
    else:
        mylogger.error("文字合成语音没有成功，没找到结果音频文件")

def add_alarm_fr_plain(text):
    '''
    :param text: #传进来参考crontab的一行闹钟，对其做校验语法，然后写入文件
    :return:
    '''
    line = text.lstrip().rstrip()
    try:
        minute, hour, day, month, week, desc = line.split()
    except Exception as e:
        mylogger.error(e)
        mylogger.error(f"ERROR: {line}格式不正确，跳过此行")
        return False
    if not re.search(r'^[\d|\*]+$', minute):
        mylogger.error(f"ERROR: 分钟{minute}格式不正确，跳过此行")
        return False
    if not re.search(r'^[\d|\*]+$', hour):
        mylogger.error(f"ERROR: 小时{hour}格式不正确，跳过此行")
        return False
    if not re.search(r'^[\d|\*]+$', day):
        mylogger.error(f"ERROR: 日期{day}格式不正确，跳过此行")
        return False
    if not re.search(r'^[\d|\*]+$', month):
        mylogger.error(f"ERROR: 月份{month}格式不正确，跳过此行")
        return False
    if not re.search(r'^[\d|\*]+$', week):
        mylogger.error(f"ERROR: 周几{week}格式不正确，跳过此行")
        return False
    alarms = read_alarm_cfg()
    alarms.append({'minute':minute,'hour':hour,'day':day,'month':month,'week':week,'desc':desc})
    write_alarm_cfg(alarms)
    return True

def loop(): #执行死循环，监控闹钟配置文件；因为是文件交互，不是线程安全的，大并发下要换成数据库
    global AlarmDone
    mylogger.info("闹钟守护进程启动")
    while True:
        alarms=read_alarm_cfg()
        for alarm in alarms:
            need_alarm,need_del=check_alarm(alarm)
            if need_alarm: #发现要处理闹钟
                do(alarm)  #执行这个闹钟
                time_mark=time.strftime("%m%d%H%M")
                AlarmDone[time_mark]=True
                if need_del: #是否这是个一次性闹钟（不含有*的）
                    alarms.remove(alarm) #删除这个闹钟
                    write_alarm_cfg(alarms)  #更新到闹钟配置文件
        time.sleep(1)
if __name__=='__main__':
    res=read_alarm_cfg()
    #alarm=[{'minute': '25', 'hour': '14', 'day': '17', 'month': '2', 'week': '4', 'desc': '第1个闹钟'}, {'minute': '0', 'hour': '8', 'day': '*', 'month': '*', 'week': '*', 'desc': '第2个闹钟'}]
    #write_alarm_cfg(alarm,cfg.alarm_cfg)
    print(res)
    loop()
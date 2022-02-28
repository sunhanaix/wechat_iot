import os,sys,re,json,requests

#由于配置文件，可能是xxx_config.py，为了便于移植，这里动态载入下
import glob,importlib
app_path = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.append(app_path)
cfg_file=glob.glob(f'{app_path}/*config.py')[0]
cfg_file=os.path.basename(cfg_file)
cfg_model=os.path.splitext(cfg_file)[0]
cfg=importlib.import_module(cfg_model)

#通过模拟http访问控制自己写的那套web歌曲播放系统
mylogger=cfg.logger
s = requests.session()
data ={'username' :cfg.mp3_user ,'password' :cfg.mp3_pass}

def stop_mp3():  # 模拟访问web方式，通知停止mp3音乐播放
    s.post(cfg.mp3_url,data =data)
    r=s.get(f'{cfg.mp3_url}?stop=1')
    mylogger.info(r.json())

def play_rand():  # 随机播放N首歌曲
    mylogger.info(f"trying to post login {cfg.mp3_url}")
    s.post(cfg.mp3_url,data =data)
    mylogger.info("tring to generate rand_N songs list")
    r=s.get(f'{cfg.mp3_url}?rand_N=20')
    mylogger.info("tring to get rand_N songs list")
    r=s.get(f'{cfg.mp3_url}?get_cur_list=1')
    mp3_files=r.json()
    one_mp3=mp3_files.pop()['abs_path']
    mylogger.info(f"tring to play songs list from {one_mp3}")
    r=s.get(f'{cfg.mp3_url}?goto={one_mp3}')
    mylogger.info(one_mp3)

def pause_mp3():  # 暂停播放
    mylogger.info(f"trying to post login {cfg.mp3_url}")
    s.post(cfg.mp3_url,data =data)
    mylogger.info("tring to pause it")
    r=s.get(f'{cfg.mp3_url}?pause=1')
    mylogger.info(r.json())

def resume_mp3():  # 继续播放
    mylogger.info(f"trying to post login {cfg.mp3_url}")
    s.post(cfg.mp3_url,data =data)
    mylogger.info("tring to resume it")
    r=s.get(f'{cfg.mp3_url}?play=1')
    mylogger.info(r.json())

def prev_mp3():  # 上一首
    mylogger.info(f"trying to post login {cfg.mp3_url}")
    s.post(cfg.mp3_url,data =data)
    mylogger.info("tring to previous song")
    r=s.get(f'{cfg.mp3_url}?prev=1')
    mylogger.info(r.json())

def next_mp3():  # 下一首
    mylogger.info(f"trying to post login {cfg.mp3_url}")
    s.post(cfg.mp3_url,data =data)
    mylogger.info("tring to next song")
    r=s.get(f'{cfg.mp3_url}?next=1')
    mylogger.info(r.json())

def set_vol_mp3(vol): #设置播放音乐音量
    mylogger.info(f"trying to post login {cfg.mp3_url}")
    s.post(cfg.mp3_url,data =data)
    mylogger.info(f"tring to set vol to {vol}")
    r=s.get(f'{cfg.mp3_url}?vol_set={vol}')
    mylogger.info(r.json())

def play_xxx_mp3(xxx): #播放某个关键词的歌曲（歌手，歌曲等）
    mylogger.info(f"trying to post login {cfg.mp3_url}")
    s.post(cfg.mp3_url,data =data)
    mylogger.info(f"tring to search {xxx} songs list")
    r=s.get(f'{cfg.mp3_url}?search_num=20&search_type=local&search={xxx}')
    mylogger.info("tring to get searched songs list")
    r=s.get(f'{cfg.mp3_url}?get_cur_list=1')
    mp3_files=r.json()
    one_mp3=mp3_files.pop()['abs_path']
    mylogger.info(f"tring to play songs list from {one_mp3}")
    r=s.get(f'{cfg.mp3_url}?goto={one_mp3}')
    mylogger.info(one_mp3)
    mylogger.info(r.json())

if __name__=='__main__':
    #play_xxx_mp3('刘珂矣')
    stop_mp3()
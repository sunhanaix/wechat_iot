import os,sys,re,json,random,time
from aip import AipSpeech  #百度语音识别库，用pip install baidu-aip安装

#由于配置文件，可能是xxx_config.py，为了便于移植，这里动态载入下
import glob,importlib
app_path = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.append(app_path)
cfg_file=glob.glob(f'{app_path}/*config.py')[0]
cfg_file=os.path.basename(cfg_file)
cfg_model=os.path.splitext(cfg_file)[0]
cfg=importlib.import_module(cfg_model)

APP_ID = cfg.baidu_aip_APP_ID
API_KEY = cfg.baidu_aip_API_KEY
SECRET_KEY = cfg.baidu_aip_SECRET_KEY
client = AipSpeech(APP_ID, API_KEY, SECRET_KEY)

mylogger=cfg.logger

def voice_to_word(audio_file):
    pcm_file=os.path.splitext(audio_file)[0]+'.pcm'
    ffmpeg='ffmpeg'
    #调用ffmpeg，把微信语音amr文件转成百度语音识别可以支持的pcm格式文件
    cmd=f'{ffmpeg} -y -i {audio_file} -acodec pcm_s16le -ac 1 -ar 16000 -f s16le {pcm_file}'
    #注意此pcm格式，直接用ffplay -i xx.pcm无法播放，因为是raw file
    #需要告知ffplay用什么格式来播放：ffplay -ar 16000 -f s16le -i xx.pcm
    if cfg.debug:
        mylogger.info(cmd)
    os.system(cmd)
    ss = open(pcm_file, 'rb').read()
    results = client.asr(ss)  # asr模块，用于把二进制的语音pcm文件内容，转成文字。
    mylogger.info(results)
    return results['result'][0]

def word_to_voice(text): #给定一个文本，用百度api接口，合成语音
    result = client.synthesis(text, 'zh', 1, {
        'vol': 15, 'spd': 5, 'per': 3})
    audio_file = os.path.join(cfg.voice_dir,f'tts_audio{time.strftime("%Y-%m-%d_%H%M%S", time.localtime())}.mp3')
    if not isinstance(result, dict):
        open(audio_file, 'wb').write(result)
        return audio_file
    return None

def myplay(fname,times=1): #调用播放器播放音频
    #player="ffplay -nodisp -autoexit -i"
    #音乐播放系统，用的是ffplay，这里播放器也用ffplay的话，如果已经有音乐在播放时，ffplay会提示设备忙
    #因此这里用omxplayer播放器来播放音频，这样两个播放器可以同时播放
    player="omxplayer"  
    play_cmd=f'{player} {fname}'
    if not os.name=='nt':
        os.environ['SDL_AUDIODRIVER']="alsa"
        os.environ['AUDIODEV']=cfg.audio_dev    
    i=0
    while i<times:
        i+=1
        mylogger.info(f"i={i}, try to execute {play_cmd}")
        os.system(play_cmd)
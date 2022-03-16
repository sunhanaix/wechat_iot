#!/usr/bin/python3
import os, sys, re, json, time, socket
import threading,subprocess
import random
'''
用于找到所有的可能远端树莓派连进来的端口，逐个去socket读几个字节，确保一个活着状态
避免远端树莓派等autossh连接被ISP给把session杀掉了
'''
#由于配置文件，可能是xxx_config.py，为了便于移植，这里动态载入下
import glob,importlib
app_path = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.append(app_path)
cfg_file=glob.glob(f'{app_path}/*config.py')[0]
cfg_file=os.path.basename(cfg_file)
cfg_model=os.path.splitext(cfg_file)[0]
cfg=importlib.import_module(cfg_model)

VERSION='0.2.2022.02.09'
mylogger=cfg.logger

def get_open_ports_by_netstat(): #调用os下的netstat -antl命令，查看当前哪些端口在使用中
    pname = 'netstat -antl'
    result = subprocess.Popen(pname, shell=True, stdout=subprocess.PIPE).stdout
    lines = result.readlines()
    ports=set()
    for line in lines:
        line=line.decode().lstrip().rstrip()
        if not line[:3].lower()=='tcp': #只看开头3个字符是tcp的，也就是tcp、tcp4、tcp6都会统计
            continue
        try:
            fields=line.split()
            port=fields[3].split(':')[-1]
            ports.add(int(port))
        except Exception as e:
            mylogger.error(e)
    return ports

def get_ava_ssh_port(startPort,endPort): #给定端口范围，在当前os中，找到第一个没有使用的，把这个端口返回，否则返回None
    ports=get_open_ports_by_netstat()
    for port in range(startPort,endPort+1):
        if not port in ports:
            return port
                
def readHostPort(host, port):  # 检测主机对应的端口是否活着
    port = int(port)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    #mylogger.info("checking host=%s,port=%s" % (host, port))
    try:
        s.settimeout(2)
        s.connect((host, port))
        s.send("GET /\r\n\r\n".encode())
        buf = s.recv(8)
        #mylogger.info(f"buf={buf}")
    except:
        return False
    return True

if __name__ == '__main__':
    #ports = [46005,46001, 46002, 46003, 46004]
    ssh_ports=[port for port in range(cfg.ssh_start_port,cfg.ssh_end_port+1) ]
    solid_ports=[port for port in range(4000,5001) ]
    need_check_ports=ssh_ports+solid_ports
    host='localhost'
    while True:
        ports=get_open_ports_by_netstat()
        for port in ports:
            if port not in need_check_ports:
                continue
            res = readHostPort(host, port)
            mylogger.info(f"{host}:{port},res={res}")
            time.sleep(random.randint(1,2))
        time.sleep(random.randint(5, 10))
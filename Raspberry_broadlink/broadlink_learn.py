import os, sys, re, json, time
import time
import base64
import broadlink
from broadlink.exceptions import ReadError, StorageError
import configparser
#调用Broadlink的python模块，进行红外线遥控器以及射频遥控器的按键信号识别学习
#识别学习好的指令，存放到MyBroadlink.ini文件中

app_path = os.path.dirname(os.path.abspath(sys.argv[0]))
logname = os.path.basename(sys.argv[0]).split('.')[0] + '.log'
cfg_file = os.path.join(app_path,'MyBroadlink.ini')

def now():
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


def mylog(ss, log=os.path.join(app_path, logname)):
    ss = str(ss)
    print(now() + '  ' + ss)
    f = open(log, 'a+', encoding='utf8')
    f.write(now() + '  ' + ss + "\n")
    f.close()

class MyBroadlink():
    def __init__(self):
        self.device=self.get_broadlink_rm() #先尝试获得broadlin家族的remote系列的模块
        mylog("found devcie: %s" % self.device)
        self.machine_type=None
        self.rf_decode=False
        self.config=configparser.ConfigParser()
        self.config.read(cfg_file, encoding='utf8')

    def get_broadlink_rm(self, timeout=3):
        devices = broadlink.discover(timeout=timeout)
        for device in devices:
            if isinstance(device, broadlink.rm):
                break
        else:
            raise Exception("Not broadlink rm Pro device found !!")
        device.auth()
        return device

    def learn_a_machine(self): #设定一个machine的名字，比如“功放”
        print("请输入设备名字:",end='')
        machine=input()
        print("请输入设备类型(1=红外线，2=射频）:", end='')
        machine_type=input()
        self.rf_decode=False
        if machine_type=='1':
            machine_type=1
        elif machine_type=='2':
            machine_type=2
        else:
            machine_type=1
        self.machine_type=machine_type
        if not machine in self.config:
            self.config[machine]={}
        self.config[machine]['type']=str(machine_type)
        while True:  #死循环，输入该设备下的功能按键的各个名字，输入exit的话，退出
            print("请输入功能按键名字（输入exit退出）:", end='')
            cmd_name=input()
            if cmd_name.lower()=='exit' or cmd_name=='':
                break
            self.learn_and_test_cmd(machine,cmd_name)

    def learn_and_test_cmd(self,machine,cmd_name): #识别一个命令，并测试验证这个命令
        res=self.learn_a_cmd(machine,cmd_name)
        if not res:
            mylog("learn_a_cmd(),failed!")
            return False
        input("尝试回放刚才识别的命令，回车开始发射")
        self.test_a_cmd(machine,cmd_name)
        print("请确认设备是否正确响应?([Y]/N  ",end='')
        action_YN=input()
        if action_YN.lower()=='y' or action_YN=='':
            return True
        else:
            return False

    def learn_a_cmd(self,machine,cmd_name):
        if self.machine_type==1:
            res=self.learn_a_if_cmd(machine,cmd_name)
        elif self.machine_type==2:
            res=self.learn_a_rf_cmd(machine, cmd_name)
        else:
            res=self.learn_a_if_cmd(machine, cmd_name)
        return res

    def learn_a_rf_cmd(self,machine,cmd_name): #识别射频RFID模式遥控器的一个命令，把它给到某个机器下面
        mylog("-- 尝试识别RFID射频信号指令,machine=%s,cmd=%s" % (machine,cmd_name))
        packet = None
        if not self.rf_decode:
            self.device.sweep_frequency()
            print("尝试解码射频指令, 请一直按住一个按键...")
            while not packet:
                print(".",end='')
                if self.device.check_frequency():
                    self.rf_decode=True
                    break
            else:
                print("RF Frequency not found")
                self.device.cancel_sweep_frequency()
                return False
            print("")
        mylog("识别并解码RF射频信号 - 1 of 2 !")
        input("按回车键继续...")
        mylog("为了完成学习, 请单按一下遥控器上的按键")
        try:
            self.device.find_rf_packet()
        except:
            return False
        data=None
        while not data:
            time.sleep(1)
            try:
                data=self.device.check_data()
            except :
                continue
            if data:
                break
        else:
            mylog("没有收到数据")
            return False
        mylog("识别RF按键 2 of 2 !")
        if not machine in self.config:
            self.config[machine]={}
        self.config[machine][cmd_name]=base64.b64encode(data).decode()
        self.config.write( open(cfg_file,'w',encoding='utf8') )
        return base64.b64encode(data).decode()


    def learn_a_if_cmd(self,machine,cmd_name): #识别红外线模式遥控器的一个命令，把它给到某个机器下面
        mylog("-- 尝试识别红外线指令,machine=%s,cmd=%s" % (machine,cmd_name))
        packet = None
        while not packet:
            print(".",end="")
            self.device.enter_learning()
            time.sleep(5)
            try:
                packet = self.device.check_data()
            except:
                pass
            #print(packet)
            if packet:
                mylog(base64.b64encode(packet).decode())
                print("ok")
        print("")
        if not machine in self.config:
            self.config[machine]={}
        self.config[machine][cmd_name]=base64.b64encode(packet).decode()
        self.config.write( open(cfg_file,'w',encoding='utf8') )
        return base64.b64encode(packet).decode()

    def test_a_cmd(self,machine,cmd_name): #读config文件里面对应机器的命令，测试是否正确
        mylog("-- Try to test a command,machine=%s,cmd=%s" % (machine, cmd_name))
        packet_encoded=self.config[machine][cmd_name]
        try:
            mylog("- try to send %s" % packet_encoded)
            self.device.send_data(base64.b64decode(packet_encoded))
        except KeyboardInterrupt:
            return False
        return True


if __name__ == '__main__':
    mb=MyBroadlink()
    mb.learn_a_machine()
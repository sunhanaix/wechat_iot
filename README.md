# wechat_iot
# Use Wechat to control home IOT devices
# 使用微信来控制家里的各种设备
## 实现的用法类似如下：
![image](https://github.com/sunhanaix/wechat_iot/blob/main/%E7%94%A8%E6%B3%951.jpg?raw=true)

## 具体部署方式：

### 一、公网云端部分

#### 1.1 mosquitto部署
把Google_stonehead部分，部署在公网的VPS云主机上，我这里用的google的云主机。  
在有公网地址的云主机上，安装mosquitto，设置相关的用户名、密码才能访问：  
vi /etc/mosquitto/mosquitto.conf   
port 1883  
allow_anonymous false  
password_file /etc/mosquitto/mosquitto.passwd  
下面生成密码文件：  
[root@instance-1 mosquitto]# touch /etc/mosquitto/mosquitto.passwd  
[root@instance-1 mosquitto]# mosquitto_passwd /etc/mosquitto/mosquitto.passwd sunbeat 
Password:   
Reenter password:  
然后启动它  
[root@instance-1 mosquitto]# systemctl enable mosquitto.service   
Created symlink /etc/systemd/system/multi-user.target.wants/mosquitto.service → /usr/lib/systemd/system/mosquitto.service.  
[root@instance-1 mosquitto]# systemctl start mosquitto.service   
[root@instance-1 mosquitto]# systemctl status mosquitto.service   

#### 1.2 部署微信公众号对接程序
修改stonehead_config.py中相关的参数，涉及到百度的接口账号，需要自己申请下  
查验如果有不够的python模块，用pip install它们  
然后chmod 755 stonehead_wechat.py  
./stonehead_wechat.py执行它，确保可以正确执行，并在:8001端口监听了  
#### 1.3 apache上配置反向代理  
在/etc/httpd/conf/httpd.conf中，增加对应的代理指向，这样访问x.x.x.x/wechat时，就会被apache重定向到:8001端口的stonhead_wechat程序上了  
ProxyPreserveHost On  
ProxyRequests Off  
ProxyPass /wechat http://localhost:8001/  
ProxyPassReverse /wechat http://localhost:8001/  
#### 1.4 微信公众号上配置指向咱们的公网服务器  
这个可以用测试账号就够我们自己家用控制了  
### 二、家中树莓派上部分  
#### 1.1 执行broadlink_learn.py的博联学习程序，对家里的射频遥控器，红外线遥控器进行学习  
学习结果，会生成MyBroadlink.ini，我这里面附录的MyBroadlink.ini只是我个人的参考。  
#### 1.2 配置miio.ini和mitv.ini中的相关设置参数  
miio.ini的设置，要先去学习下miservice的使用，具体可以看  
https://github.com/Yonsm/MiService  
#### 1.3 配置MsgAct_config.py中相关的参数  
这个要根据实际情况来了，百度的账号要提前申请  
#### 1.4 启动SubMsgAct.py的主程序  
chmod 755 SubMsgAct.py  
./SubMsgAct.py  
确保没有相关报错，daemon正确启动了。  

### 三、用到的智能设备情况  
(由于零零散散近几年陆续购买的东西，有些价格是几年前的，有些当前可能产品已经更新换代了）  
#### 总控大脑树莓派：  
![image](https://github.com/sunhanaix/wechat_iot/blob/main/%E6%A0%91%E8%8E%93%E6%B4%BE.jpg?raw=true)  
#### 核心的主控，博联RM Pro+  
![image](https://github.com/sunhanaix/wechat_iot/blob/main/%E5%8D%9A%E8%81%94%E9%81%A5%E6%8E%A7.jpg?raw=true)  
#### 小米智能网关  
![image](https://github.com/sunhanaix/wechat_iot/blob/main/%E5%B0%8F%E7%B1%B3%E6%99%BA%E8%83%BD%E7%BD%91%E5%85%B3.jpg?raw=true)
#### 小米智能插座  
![image](https://github.com/sunhanaix/wechat_iot/blob/main/%E5%B0%8F%E7%B1%B3%E6%99%BA%E8%83%BD%E6%8F%92%E5%BA%A7.jpg?raw=true)
#### 小米空调伴侣  
![image](https://github.com/sunhanaix/wechat_iot/blob/main/%E5%B0%8F%E7%B1%B3%E7%A9%BA%E8%B0%83%E4%BC%B4%E4%BE%A32.jpg?raw=true)
![image](https://github.com/sunhanaix/wechat_iot/blob/main/%E5%B0%8F%E7%B1%B3%E7%A9%BA%E8%B0%83%E4%BC%B4%E4%BE%A3Pro.jpg?raw=true)
#### 改家里灯的遥控  
由于家里灯不是智能的，因此把它的单板开关改造下，买个带射频控制的，把它装到灯开关面板里面，刚刚好。
![image](https://github.com/sunhanaix/wechat_iot/blob/main/%E6%94%B9%E5%AE%B6%E9%87%8C%E7%81%AF%E7%9A%84%E9%81%A5%E6%8E%A7.jpg?raw=true)

#### 家里的几个带风扇的灯  
这个风扇灯，本身就带遥控，是射频的，因此可以直接让博联去学习它遥控器的射频信号就可以控制它了。  
![image](https://github.com/sunhanaix/wechat_iot/blob/main/%E9%A3%8E%E6%89%87.jpg?raw=true)  

PS1: 射频的指令码很短，穿墙能力很不错，博联遥控放楼下客厅，还可以很轻松控制楼上最远处屋子里面的灯。而wifi那个屋子就太弱，必须另外延展进去。  
PS2：这个用习惯了，感觉还是挺方便的。  
#### 一定要把这个自己的公众号放在手机桌面上，特别方便。  
#### 一定要把这个自己的公众号放在手机桌面上，特别方便。  
#### 一定要把这个自己的公众号放在手机桌面上，特别方便。  
#### 会提升很大的幸福感  

##  零零散散折腾了好久，感觉是个不小的工程。    

==========3.1=========  
增加了内网树莓派要定期发送心跳信号给MQTT，  
公网服务器检测到超时没收到心跳信号时，就发告警给到微信用户，提醒设备离线  
增加了内网树莓派启动上线，连接到网络时，会发通知给到管理员微信用户，提醒设备上线。  

==========3.1=========  
增加了对内网NAT内树莓派管控的远程调度支持。  
微信发送ssh指令时，公网服务器会查询当前哪个端口可以使用，MQTT发给内网的树莓派。  
树莓派用autossh的端口反弹去连接公网服务器（要提前设置好自动密钥交互，免密登录）。  
autossh -R 12345:192.168.x.x:22 user1@x.x.x.x -N  
这样可以用ssh  x.x.x.x:12345的方式去ssh到内网树莓派上。  

==========3.7=========  
增加了在网络不好时的容错部分  
作为Subscriber时，如果网络不好，设置的keepalive 60s或者600s，会超时，又没反应的情况，调整到30s，实测24小时，还比较稳定；  
另外，增加了Subscriber遇到各个action时，都try ... except ..来进行容错，防止action执行失败到时subscriber线程出问题；  
对于loopHeartBeat时，对PubMsg增加try ... except ..来进行容错，防止网络失败时，心跳部分线程异常退出。  

==========3.9=========   
增加了“准后门”接口的支持，便于后期远程维护  
微信发送cmd ps -ef|grep python之类命令，可以返回该命令执行结果。  
由于微信最多只支持2048bytes的报文，因此只取命令结果的前2048字节的utf8部分。  


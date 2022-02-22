# wechat_iot
# Use Wechat to control home IOT devices
# 使用微信来控制家里的各种设备
## 实现的用法类似如下：
![image](https://github.com/sunhanaix/wechat_iot/blob/main/%E7%94%A8%E6%B3%951.jpg?raw=true)

![image](https://github.com/sunhanaix/wechat_iot/blob/main/%E7%94%A8%E6%B3%952.jpg?raw=true)

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

零零散散折腾了好久，感觉是个不小的工程。  

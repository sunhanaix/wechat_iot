#!/usr/bin/python3
import os,sys,re,json,time
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.header import Header
import smtplib
from email.utils import parseaddr, formataddr

#由于配置文件，可能是xxx_config.py，为了便于移植，这里动态载入下
import glob,importlib
app_path = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.append(app_path)
cfg_file=glob.glob(f'{app_path}/*config.py')[0]
cfg_file=os.path.basename(cfg_file)
cfg_model=os.path.splitext(cfg_file)[0]
cfg=importlib.import_module(cfg_model)

#发送邮件模块，使用配置好的邮件服务器和账号，进行邮件的发送

mylogger=cfg.logger

mail_params=cfg.mail_params

class mail(object):
	def __init__(self,mail_cfg=mail_params):
		self.mail_cfg=mail_cfg
		if cfg.debug:
			mylogger.info("mail_cfg=%s" % json.dumps(mail_cfg))
	def sendmail(self,mail_info):
		if cfg.debug:
			mylogger.info("mail_info=%s" % json.dumps(mail_info))
		mimeBody = MIMEText(mail_info['body'], "plain", 'utf-8')
		msg=MIMEMultipart()
		msg["Subject"] = Header(mail_info['subject'], 'utf-8').encode()
		msg["From"]=self.mail_cfg['fr_account']
		msg['To']=",".join(mail_info['to_accounts'])
		mimeFiles=[]
		if 'files' in mail_info:
			if type(mail_info['files'])==str:
				files=[mail_info['files']]
			else:
				files=mail_info['files']
			for fname in files:
				mimeFile=MIMEApplication(open(fname, 'rb').read())
				mimeFile.add_header('Content-Disposition', 'attachment', filename=os.path.basename(fname))
				mimeFiles.append(mimeFile)
		msg.attach(mimeBody)
		if mimeFiles:
			for mimeFile in mimeFiles:
				msg.attach(mimeFile)
		try:
			smtp = smtplib.SMTP_SSL(self.mail_cfg['smtp_server'],self.mail_cfg['smtp_port'])
			if cfg.debug:
				smtp.set_debuglevel(1)
			smtp.ehlo(self.mail_cfg['smtp_server'])
			smtp.login(self.mail_cfg['fr_account'], self.mail_cfg['password'])			
			smtp.sendmail(self.mail_cfg['fr_account'], mail_info['to_accounts'], msg.as_string())
			smtp.quit()
		except Exception as e:
			return False
		return True

if __name__=='__main__'		:
	m=mail()
	mail_info={'subject':'测试邮件标题',
		'body':'邮件正文部分',
		'to_accounts': ['43233@qq.com','zsan11343@gmail.com'],
#		'files':['wechat_msg_debug.log','MyMail.py','wechat.py'],
		}
	m.sendmail(mail_info)
		




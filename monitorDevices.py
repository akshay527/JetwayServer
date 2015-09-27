#!/usr/bin/python
#-------#--------#-----------#------------#----------------
# Machine Monitoring Script
# (Modified version of measurement script)
# Ensures that all Wemos and Feature machines are on and running
# (Requires SSH key access from server to clients)
# (Requires a Wemo.txt and Machines.txt file in the same directory as the script containing IP address of Wemos and hostnames of machines respectively)
# Product of Synergy labs, Christian Kaestner


# Modules to import 
import urllib2,datetime,socket
import time,sys,os,re,atexit
from signal import SIGTERM
import smtplib
import subprocess
import string
import sys
import os.path
import os
from masterScript import *

#---------------------------------SOAP-BODY-----------------------------------------------------------------

class InsightMethod:
    def __init__(self, fun, service, param, returnParamName=None):
        self.request='''<?xml version="1.0" encoding="utf-8"?>
<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">
    <s:Body>
        <u:'''+fun+''' xmlns:u="urn:Belkin:service:'''+service+''':1">
            '''+param+'''
        </u:'''+fun+'''>
    </s:Body>
</s:Envelope>'''
        self.httpdir="/upnp/control/"+service+"1"
        self.header= {"Accept":"",
                    "Content-Type": "text/xml; charset=\"utf-8\"",
                    "SOAPACTION": "\"urn:Belkin:service:"+service+":1#"+fun+"\""}
        self.returnParamName=returnParamName
 
    def call(self):
        global IP
        global PORT
        global FAILCOUNT
        url = "http://"+IP+":"+PORT+self.httpdir
        try:
            req = urllib2.Request(url, self.request, self.header)
            # error("#send "+url+"\n"+str(self.request))
            data= urllib2.urlopen(req,None,5).read()
            # error("#received "+data)
            FAILCOUNT = 0
            if data!=None and self.returnParamName!=None:
                data = re.search(r'\<'+self.returnParamName+r'\>(.*)\</'+self.returnParamName+r'\>',data).group(1)
            return data
        except Exception, e:
            return handleException(e)



PORT = "49152"
IP = "0"
FAILCOUNT = 0

def read_sensors():
    global FAILCOUNT
    data = getAll.call()
    if data != None:
        return parse_params_getall(data)
    else:
    	return None

     
# measurement or turn_on has just failed.
# do nothing, unless there are more errors in a row.
# after 3 errors, try new ports 
def handleException(exception):
        global PORT
        global FAILCOUNT
        global IP
        global HOST
        FAILCOUNT = FAILCOUNT+1        
        error("#error " + IP +":"+PORT+", " +str(FAILCOUNT)+" tries, "+ str(exception))
        if(FAILCOUNT > 3):
            intport = int(PORT)
            intport+=1
            if(intport == 49157):
                   intport = 49152
            error("#trying new port: "+str(intport))
            PORT = str(intport)
            try:
               newip = socket.gethostbyname(HOST)
               if(newip != IP):
                    IP = newip
                    error("#found new ip: " + IP)
                    FAILCOUNT = 0
            except Exception:
                  error("Error in DNS Lookup from "+HOST+" (keeping old ip)")
            
#-----------------------------*------------------------------*-----------------------------------------------

def parse_params_getall(data):
    try:
        p = data.split("|")
        # r = "state="+p[0]
        # r = r + " secondsSinceStateChange="+p[1]
        # r = r + " lastOn="+str(time.strftime("%Y-%m-%d %H:%M:%S",time.gmtime(int(p[2]))))
        # r = r + " secondsOnToday="+p[3]
        # r = r + " secondsOnTwoWeeks="+p[4]
        # r = r + " secondsOnTotal="+p[5]
        # r = r + " averagePowerW="+p[6]
        # r = r + " instantPowerMW="+p[7]
        # r = r + " powerTodayMWS="+p[8]
        # r = r + " energyTwoWeeksMWS="+p[9]
        # currenttime= time.strftime("%Y-%m-%d %H:%M:%S")
        # string = str(currenttime) + ", " + r
        # return string
        return str(p[7])
    except Exception, e:
        print str(e)
        return None



#----------------------------------------------------------------------------------------------------------------
getAll = InsightMethod("GetInsightParams","insight", "<InsightParams></InsightParams>","InsightParams")
isOn = InsightMethod("GetBinaryState","basicevent","<BinaryState>1</BinaryState>")
turnOn = InsightMethod("SetBinaryState","basicevent","<BinaryState>1</BinaryState>")
getName = InsightMethod("GetFriendlyName","basicevent","","FriendlyName")
getHomeId = InsightMethod("GetHomeId","basicevent","","HomeId")
getMacAddr= InsightMethod("GetMacAddr","basicevent","","MacAddr")
getSerialNo=InsightMethod("GetMacAddr","basicevent","","SerialNo")
getLogFileURL=InsightMethod("GetLogFileURL","basicevent","","LOGURL")
setPowerThreshold0 = InsightMethod("SetPowerThreshold","insight","<PowerThreshold>0</PowerThreshold>","PowerThreshold")  
getPowerThreshold=InsightMethod("GetPowerThreshold","insight","<PowerThreshold></PowerThreshold>","PowerThreshold")
getInsightParams=InsightMethod("GetInsightParams","insight","","InsightParams")
getMetaInfo = InsightMethod("GetMetaInfo","metainfo","","MetaInfo")
getFirmwareVersion = InsightMethod("GetFirmwareVersion","firmwareupdate","","FirmwareVersion")
getAccessPointList = InsightMethod("GetApList","WiFiSetup","")

def isActive():
    global FAILCOUNT
    FAILCOUNT = 0
    try:
	data = None
	while data == None and FAILCOUNT < 100:
	    data = getAll.call()
	if FAILCOUNT < 100:
            p = data.split("|") 
	    return (int(p[0]) != 0)
        else:
            print "Wemo State Unknown"
	    return False		    
    except Exception, e:
	print str(e)
	return False

def sendEmail(message):
    sender = "synergylabserrordaemon@gmail.com"
    receivers = "akshaypa@andrew.cmu.edu"
    username = 'synergylabserrordaemon'
    password = 'synergy_lab'
    server = smtplib.SMTP('smtp.gmail.com:587')
    server.starttls()
    server.login(username,password)
    server.sendmail(sender, receivers, message)

def init():
    r = None
    global HOST
    global PORT
    global FAILCOUNT
    FAILCOUNT = 0
    error("#establishing connection and turning on")
    if not isActive():
	sendEmail("The Wemo connected to " + HOST + "was off and had to be switched on again")	
	while r==None and FAILCOUNT < 100: 
            r=turnOn.call()
    if FAILCOUNT < 100:
    	error("#found device "+getName.call())
    	error("#meta: "+getMetaInfo.call())
  	error("#firmware: "+getFirmwareVersion.call())
    	error("#serialno: "+getSerialNo.call())
    	error("#Connection Established : Wemo is now on")
    else:
	error("#Wemo is not connecting... Skipping.")

def error(msg):
     sys.stderr.write(msg.strip()+"\n")
     sys.stderr.flush()
    
def main(arguments):
    start_todos = time.time()
    start_failsafe = time.time()
    global IP
    global HOST
    global FAILCOUNT
    global PORT
    while True:
        try:
	    with open("Wemos.txt", "r") as f:
	        for line in f:
		    HOST = line
		    IP = socket.gethostbyname(HOST)
		    PORT = "49152"
		    error("listening at "+HOST+" ("+IP+")")
		    try:
		    	init()
		    except Exception, e:
			print e
	    time.sleep(30)
            if (time.time() - start_failsafe) >= 3000:
		print "Failsafe Check Starting"
	        start_failsafe = time.time()
		with open("Machines.txt", "r") as g:
	        	for gline in g:
				subprocess.call('ssh ' + gline.strip() + ' "source /home/feature/energy/.config ; python /home/feature/energy/failsafe.py"', shell=True)
	        print "Failsafe Check Complete"
	    #if (time.time() - start_todos) >= 100:
		#print "Checking Todos"
		#start_todos = time.time()
		#checkTodos()
			
        except IndexError:
            print "Index Error"
   
if __name__ == "__main__":
    main(sys.argv)


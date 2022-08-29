#! /usr/bin/env python3
# Check RBM Settings to see if they comply with standards
# Charlie Sumner csumner@us.ibm.com
# 062122 - Added email when there is a violation found


import sys, http.client
import tempfile
import base64
import os
import time
import csv
import smtplib
from smtplib import SMTP
from email.message import EmailMessage
from xml.dom.minidom import parseString
from xml.dom.minidom import parse
from optparse import OptionParser
from datetime import datetime, date
from DPCommonFunctions36 import getText, showResults, setHeaders, setAMPHeaders
import time, getpass

parser = OptionParser("usage: %prog -u userid -p password -s server {-e expirationdays -o outputFile {-v -c outputcsvfile} -z parameterfile}")
parser.add_option("-u", "--userid", dest="username", help="userid")
parser.add_option("-p", "--password", dest="password", help="password")
parser.add_option("-s", "--server", dest="server", help="datapower server name")
parser.add_option("-z", "--parameterFile", dest="file", help="parameter filename")
(options, args) = parser.parse_args()

if options.file != None:
    try:
        options.read_file(options.file)
    except IOError:
        print ("Could not open '" + options.file + "', exiting.")
        sys.exit(4) 
        

if options.username == None:
    parser.error("no userid supplied")
password = options.password
if options.password == None:
		print ("No password found in options file")
# Query password so it can be kept out of the parameter file
		password = getpass.getpass()    
if options.server == None:
    parser.error("no server name supplied")
    
############################################# 
# Modify the next 3 lines for your location    
emailFrom = 'DataPower@UPSTesting.com'
emailTo = 'msarwar@ups.com'
smtpServer = 'mailhost.unix.us.ams1907.com'
##############################################

tempFile = 'tempfile.txt'
fp = open(tempFile,mode = "w")
        
# Get name of Device using AMP 
        
SoapMessage = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <dp:GetDeviceInfoRequest xmlns:dp="http://www.datapower.com/schemas/appliance/management/1.0"/>
    </soap:Body>
</soap:Envelope>
"""
#print (SoapMessage)

#construct and send the headers
webservice = setAMPHeaders(options.username,password,options.server, len(SoapMessage))
webservice.send(bytes(SoapMessage,'ascii'))

# get the response

#statuscode, statusmessage, header = webservice.getresponse()
wsResponse = webservice.getresponse()

#print "Response: ", wsResponse.status, wsResponse.reason, wsResponse.msg
#print "headers: ", wsResponse.getheaders()

# res contains a SOAP wrapper and DP stuff wrapped around the base64-encoded response
#res = webservice.getfile().read()
#res = webservice.getresponse().read()
res = wsResponse.read()
#print (res)
#webservice.close()

# parse the response into the DOM
dom = parseString(res)

# Retrieve the device name
nameNodes = dom.getElementsByTagName("amp:DeviceName")[:1]
if len(nameNodes) == 0:
	print ('** Error: Device Name retrieval error. Most likely cause is invalid credentials. Response from DataPower is:')
	print (res)
	exit (99)
DeviceName = nameNodes[0].childNodes[0].data


# Get the RBM Settings for this device 
            
SM_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
			<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    	<soap:Body>
        <mgmt:request xmlns:mgmt="http://www.datapower.com/schemas/management" domain="%s">
            <mgmt:get-config  class="RBMSettings" />
        </mgmt:request>
    	</soap:Body>
			</soap:Envelope>
"""
SoapMessage = SM_TEMPLATE%("default")
#     print (SoapMessage)

#		construct and send the headers
webservice = setHeaders(options.username,password,options.server, len(SoapMessage))
webservice.send(bytes(SoapMessage,'ascii'))

#    get the response


# res contains a SOAP wrapper and DP stuff wrapped around the base64-encoded response
res = webservice.getresponse().read()

# print (res)

#  Parse the response into the DOM
dom = parseString(res)

# Todo - Read settings checker file and compare against current settings\
try:
   settingsFile = open('CheckRBMSettings.txt','r')
except:
  print ("Could not open settings file. \n Exiting...")
  exit (28);

settingsContent = csv.reader(settingsFile)
#print (settingsContent)
# 
violationFound = 0
for eachRow in settingsContent:
#   print (len(eachRow))
#   Check for blank lines and skip rest of loop
    if len(eachRow) == 0:
       continue 
    eachNode = eachRow[0]
    eachNodeValue = eachRow[1]
#   print (eachNode +" = " + eachNodeValue)

    settingFromConfig = dom.getElementsByTagName(eachNode)
    if len(settingFromConfig) == 0:
       print("\n** Error - setting not found = "+eachNode+"   (Check case)")
       exit (4)
       
    settingFromConfigValue = settingFromConfig[0].childNodes[0].data

    if settingFromConfigValue != eachNodeValue:
       print ("\n** Device "+DeviceName+" - RBM Security Setting <<Violation>> ** " + eachNode + " currently set to " + settingFromConfigValue)
       violationFound = 1
       fp.write ("\n** Device "+DeviceName+" - RBM Security Setting <<Violation>> ** " + eachNode + " currently set to " + settingFromConfigValue)
    else:
       print ("\n** Device "+DeviceName+" - RBM Security Setting Verified ** " + eachNode + " = " + settingFromConfigValue)
       fp.write ("\n** Device "+DeviceName+" - RBM Security Setting Verified ** " + eachNode + " = " + settingFromConfigValue)
     
# Check to see if there were any violations found. If so, send email      
if violationFound == 1:
   fp.close()
   fp = open(tempFile,mode = "r")
   
   msg = EmailMessage()
   subjectText = 'Violation found on ' + DeviceName
   msg['Subject'] = subjectText 
   msg['From'] = emailFrom
   msg['To'] = emailTo
   msg.set_content(fp.read())
     
   s = smtplib.SMTP(host=smtpServer,port=25,timeout=10)
#  s.set_debuglevel(1)
   s.send_message(msg)
   s.quit()
        
settingsFile.close()
fp.close()
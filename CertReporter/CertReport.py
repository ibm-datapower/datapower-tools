#!/usr/bin/python
# Certificate Report for all domains on DataPower
# Charlie Sumner csumner@us.ibm.com
# Modified for Python Version 2.7.13 (2017-10-13)
# Added prompt for password (2019-02-12)

import sys, httplib
import base64
import os
from xml.dom.minidom import parseString
from optparse import OptionParser
from datetime import datetime
from DPCommonFunctions import getText, showResults, setHeaders, setAMPHeaders
import time, getpass

parser = OptionParser("usage: %prog -u userid -p password -s server {-e expirationdays -o outputFile -z parameterfile}")
parser.add_option("-u", "--userid", dest="username", help="userid")
parser.add_option("-p", "--password", dest="password", help="password")
parser.add_option("-s", "--server", dest="server", help="datapower server name")
parser.add_option("-e", "--expirationwarndays", dest="expWarnDays", default=90, help="Expiration warning days")
parser.add_option("-o", "--outputfile", dest="outputFile", default="certreport.html", help="Output Filename")
parser.add_option("-z", "--parameterFile", dest="file", help="parameter filename")
(options, args) = parser.parse_args()

if options.file != None:
    try:
        options.read_file(options.file)
    except IOError:
        print "Could not open '" + options.file + "', exiting."
        sys.exit(4) 
        

if options.username == None:
    parser.error("no userid supplied")
password = options.password
if options.password == None:
		print "No password found in options file"
# Query password so it can be kept out of the parameter file
		password = getpass.getpass()    
if options.server == None:
    parser.error("no server name supplied")


# Function to return the number of days until the date passed in
def number_of_days_from_today(datestring):
    exp_date_time = datetime.strptime(datestring, "%Y-%m-%dT%H:%M:%SZ")
    utc_now_date_time = datetime.utcnow()

#    print exp_date_time
#    print utc_now_date_time

    td = exp_date_time - utc_now_date_time
#    print td

    return td.days

print "Using ",options.expWarnDays," days for the warning indicator"
        
# Get name of Device using AMP for report header
        
SoapMessage = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <dp:GetDeviceInfoRequest xmlns:dp="http://www.datapower.com/schemas/appliance/management/1.0"/>
    </soap:Body>
</soap:Envelope>
"""
# print SoapMessage

#construct and send the headers
webservice = setAMPHeaders(options.username,password,options.server, len(SoapMessage))
webservice.send(SoapMessage)

# get the response

#statuscode, statusmessage, header = webservice.getresponse()
wsResponse = webservice.getresponse()

#print "Response: ", wsResponse.status, wsResponse.reason, wsResponse.msg
#print "headers: ", wsResponse.getheaders()

# res contains a SOAP wrapper and DP stuff wrapped around the base64-encoded response
#res = webservice.getfile().read()
#res = webservice.getresponse().read()
res = wsResponse.read()
#print res

# parse the response into the DOM
dom = parseString(res)

# Retrieve the device name
nameNodes = dom.getElementsByTagName("amp:DeviceName")[:1]
DeviceName = nameNodes[0].childNodes[0].data

# copy the js snippet after the header to allow sorting by column
sortSnippet = open('CertReportSnip.htm','r')
sortSniptxt = sortSnippet.read()

# Open the HTML file
htmlFile = open(options.outputFile,'w')

# print HTML header
htmlFile.write('<html><head><title>DataPower Certificates</title></head>')
htmlFile.write('<body>')
htmlFile.write (sortSniptxt)
htmlFile.write ('<center><h2>DataPower Certificates for Device ' + DeviceName)
htmlFile.write('</h2></center>Click the column header to sort<table border="1" class="sortable">')
htmlFile.write('  <tr><th>Cert Object</th><th>Domain</th><th>Issuer</th><th>Subject</th><th>NotBefore</th><th>NotAfter</th><th>Days to Expiration</th><th>Filename</th></tr>')


# Get the names of all of the domains on this device

SoapMessage = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <mgmt:request xmlns:mgmt="http://www.datapower.com/schemas/management" domain="default">
            <mgmt:get-status class="DomainStatus" />
        </mgmt:request>
    </soap:Body>
</soap:Envelope>
"""
# print SoapMessage

#construct and send the headers
webservice = setHeaders(options.username,password,options.server, len(SoapMessage))
webservice.send(SoapMessage)

# get the response

#statuscode, statusmessage, header = webservice.getreply()
#print "Response: ", statuscode, statusmessage
#print "headers: ", header

# res contains a SOAP wrapper and DP stuff wrapped around the base64-encoded response
#res = webservice.getfile().read()
res = webservice.getresponse().read()
#print res

# Parse the response in to the DOM
dom = parseString(res)
fileNodes = dom.getElementsByTagName("DomainStatus")
#print "Domain Name" + "\t Save Needed"
domainsFound = 0
for domainNode in fileNodes:
     nameNodes = domainNode.getElementsByTagName("Domain")[:1]
     name = nameNodes[0].childNodes[0].data
     domainsFound = domainsFound + 1
     print "Processing Domain " + name

# This code checks to see if there are is an empty set 
#if len(fileNodes) == 0:
#    resultNodes = dom.getElementsByTagName("dp:result")
#    result = resultNodes[0].childNodes[0].data
#    print result
#
#   What does this do?
#   dom = parse(args.input)

# Get names of all object names in this domain
#
     SM_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
			<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    	<soap:Body>
        <mgmt:request xmlns:mgmt="http://www.datapower.com/schemas/management" domain="%s">
            <mgmt:get-status class="ObjectStatus" />
        </mgmt:request>
    	</soap:Body>
			</soap:Envelope>
"""
     SoapMessage = SM_TEMPLATE%(name)
#     print SoapMessage

#		construct and send the headers
     webservice = setHeaders(options.username,password,options.server, len(SoapMessage))
     webservice.send(SoapMessage)

#    get the response

#    statuscode, statusmessage, header = webservice.getreply()
#    print "Response: ", statuscode, statusmessage
#    print "headers: ", header

# res contains a SOAP wrapper and DP stuff wrapped around the base64-encoded response
#    res = webservice.getfile().read()
     res = webservice.getresponse().read()
#    print res

#  Parse the response into the DOM
     dom = parseString(res)
     allobjects = dom.getElementsByTagName('ObjectStatus')
     for objclass in allobjects:
       classNodes = objclass.getElementsByTagName("Class")[:1]
       allClass = classNodes[0].childNodes[0].data
#      print allClass
       if allClass == "CryptoCertificate":
#       	print "Found one"
       	nameNodes = objclass.getElementsByTagName("Name")[:1]
        certObjName = nameNodes[0].childNodes[0].data
#       print certObjName
       	

#  Request certificate information for each cert based on a class=CrytoCertificate

        SM_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
		<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:man="http://www.datapower.com/schemas/management">
    <soap:Body>
        <man:request domain="%s">
    			<man:do-view-certificate-details>
     				<man:certificate-object>%s</man:certificate-object>
				  </man:do-view-certificate-details>
   		   </man:request>
      </soap:Body>
		  </soap:Envelope>
		  """
        SoapMessage = SM_TEMPLATE%(name,certObjName)

#       print SoapMessage

#	construct and send the headers
        webservice = setHeaders(options.username,password,options.server, len(SoapMessage))
        webservice.send(SoapMessage)

# get the response

#       statustup = webservice.getresponse().getheaders()
#       print statustup
#print "Response: ", statuscode, statusmessage
#print "headers: ", header

# 
#       res = webservice.getfile().read()
        res = webservice.getresponse().read()
#       print res

#exit(1)
#       Parse the response into the DOM
    
        dom = parseString(res)
        certificates = dom.getElementsByTagName("CryptoCertificate")    
#       cert = dom.getElementsByTagName("CryptoCertificate")  

# Check response, if no response, then it's likely not Firmware 7.5.2 or above

#        if len(certificates) == 0:
#        	print "Error: do-view-certificate-details did not return any details."
#        	print "Most likely cause is that the firmware level on the DataPower device is not at 7.5.2 or above"
#        	exit(28)
  
        for cert in certificates:
        	
#  Populate table with information about certificate
          htmlFile.write('  <tr>')

          certObjectNode = cert.getElementsByTagName('CertificateObject')[0]
          htmlFile.write('    <td>' + getText(certObjectNode.childNodes) + '</td>')

          domainNode = cert.getElementsByTagName('Domain')[0]
          htmlFile.write('    <td>' + getText(domainNode.childNodes) + '</td>')

          detailsNode = cert.getElementsByTagName('CertificateDetails')[0]

          issuerNode = detailsNode.getElementsByTagName('Issuer')[0]
          htmlFile.write('    <td>' + getText(issuerNode.childNodes) + '</td>')

          subjectNode = detailsNode.getElementsByTagName('Subject')[0]
          htmlFile.write('    <td>' + getText(subjectNode.childNodes) + '</td>')

          notBeforeNode = detailsNode.getElementsByTagName('NotBefore')[0]
          htmlFile.write('    <td>' + getText(notBeforeNode.childNodes) + '</td>')

          notAfterNode = detailsNode.getElementsByTagName('NotAfter')[0]
          htmlFile.write('    <td>' + getText(notAfterNode.childNodes) + '</td>')
        
# figure out how many days until this cert expires - under 90 days, turn background red for this cell

          ndays = number_of_days_from_today(getText(notAfterNode.childNodes))
          if int(ndays) < int(options.expWarnDays):
            htmlFile.write('<td bgcolor="red">')
          else:
        	  htmlFile.write('<td>')
        	  
          htmlFile.write(str(ndays))
          htmlFile.write('</td>')

#         print ndays        
  

#  Request config information for each cert to get the filename

          SM_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
		<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:man="http://www.datapower.com/schemas/management">
    <soap:Body>
        <man:request domain="%s">
            <man:get-config name="%s" class="CryptoCertificate" />
   		   </man:request>
      </soap:Body>
		  </soap:Envelope>
		  """
          SoapMessage = SM_TEMPLATE%(name,certObjName)

#       print SoapMessage

#	construct and send the headers
          webservice = setHeaders(options.username,password,options.server, len(SoapMessage))
          webservice.send(SoapMessage)

# get the response

#          statuscode, statusmessage, header = webservice.getreply()
#print "Response: ", statuscode, statusmessage
#print "headers: ", header

# 
#         res = webservice.getfile().read()
          res = webservice.getresponse().read()
#         print res

#exit(1)
#         Parse the response into the DOM
    
          certconfig = parseString(res)
        
          fileName = certconfig.getElementsByTagName('Filename')[0]
          htmlFile.write('    <td>' + getText(fileName.childNodes) + '</td>')
        
          htmlFile.write('  </tr>')
    # print HTML tail
htmlFile.write('</table>')
htmlFile.write('</body></html')

#Close the HTML File
htmlFile.close()

# Launch the file in a browser

print "Report generation complete, launching browser to view report file " + options.outputFile
os.system("start " + options.outputFile)
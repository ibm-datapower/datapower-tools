#! /usr/bin/env python3
#
# Import zipped DataPower export to multiple devices using optional deployment policy
# 05/21/2021 Charlie Sumner (csumner@us.ibm.com)
# 

import sys, http.client, os
import base64, getpass
from xml.dom.minidom import parseString
#import StringIO, zipfile
from datetime import date
from optparse import OptionParser
from DPCommonFunctions36 import getText, showResults, setHeaders

# Get commandline options
parser = OptionParser("usage: %prog -s <device> -d <domain> -u <userid> -p <password> -f <Zip Filename> -s <server list> -e <deployment policy name> -z <parameter file name>")
parser.add_option("-d", "--domain", dest="domain", help="domain")
parser.add_option("-u", "--userid", dest="username", help="userid")
parser.add_option("-p", "--password", dest="password", help="password")
parser.add_option("-s", "--serverfile", dest="serverfile", help="file that lists server names")
parser.add_option("-f", "--file", dest="zipFilename", help="zipfile to import")
parser.add_option("-e", "--deployment-policy", dest="depPolicy", help="name of deployment policy")
parser.add_option("-z", "--parameterFile", dest="file", help="parameter filename")
(options, args) = parser.parse_args()

print ("options file = "+ options.file)

if options.file != None:
    try:
        options.read_file(options.file)
    except IOError:
        print ("Could not open '" + options.file + "', exiting.")
        sys.exit(4)
        
if options.domain == None:
    parser.error("no domain name supplied")
if options.username == None:
    parser.error("no userid supplied")
password = options.password
if options.password == None:
		print ("No password found in options file")
# Query password so it can be kept out of the parameter file
		password = getpass.getpass() 
if options.serverfile == None:
    parser.error("no server name list supplied")
if options.zipFilename == None:
    parser.error("no zip filename supplied")

# need to read in the zip file and base64 it
FILE = open(options.zipFilename,'rb')
zipContents = FILE.read()
#encodedZip = base64.encodestring(zipContents)[:-1]
encodedZip = base64.encodestring(zipContents).decode('ascii')[:-1]
FILE.close()

#Read in list of server names and import for each server name
print ("Server list file = ",options.serverfile)
ServerFILE = open(options.serverfile,'r')
Servernames = ServerFILE.readline()

#Loop through for each server name
while Servernames:

	print ("Importing " + options.zipFilename + " into domain " + options.domain + " on server " + Servernames)
		
#sys.exit (1)


# do substitution into the payload XML we're sending to DataPower
	deploymentPolicyAttribute = ''
	if options.depPolicy != None:
 		  deploymentPolicyAttribute = 'deployment-policy="' + options.depPolicy + '"'
	SM_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
	<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:dp="http://www.datapower.com/schemas/management">
 	 <soapenv:Header/>
	    <soapenv:Body>
 	     <dp:request domain="%s">
 	       <dp:do-import source-type="ZIP" overwrite-files="true" overwrite-objects="true" rewrite-local-ip="false" %s>
 	           <dp:input-file>%s</dp:input-file>
 	       </dp:do-import>
 	     </dp:request>  
 	     <dp:request xmlns:dp="http://www.datapower.com/schemas/management" domain="%s">
 	         <dp:do-action>
 	             <SaveConfig/>
 	         </dp:do-action>
 	     </dp:request> 
    </soapenv:Body>
  </soapenv:Envelope>
"""
	SoapMessage = SM_TEMPLATE%(options.domain,deploymentPolicyAttribute,encodedZip,options.domain)

#construct and send the headers
	webservice = setHeaders(options.username,password,Servernames.strip(), len(SoapMessage))
#webservice.send(SoapMessage)
	webservice.send(bytes(SoapMessage,'ascii'))

# get the response

#statuscode, statusmessage, header = webservice.getreply()
#print "Response: ", statuscode, statusmessage
#print "headers: ", header

# res contains SOAP 
#res = webservice.getfile().read()
	resl = webservice.getresponse()
#	print (resl)

	res=resl.read()
#	print(res)
	
	envelopeStart = res.rfind(bytes('<env:Envelope','ascii'))
#	print (envelopeStart)
	importResult = res[:envelopeStart]
#	print (importResult)
	
	saveResult = res[envelopeStart:]
	
	#importResult = res[:res.rfind('<env:Envelope')]
  #	saveResult = res[res.rfind('<env:Envelope'):]

# now to get the results

	importDOM = parseString(importResult)
	saveDOM = parseString(saveResult)
	Nodes = importDOM.getElementsByTagName("exec-script-results")
	print ("\n...Object Import results \n" + Nodes[0].toprettyxml(indent=" "))
	FileNodes = importDOM.getElementsByTagName("file-copy-log")
	print ("...File Import results \n" + FileNodes[0].toprettyxml(indent=" "))
	Nodes = saveDOM.getElementsByTagName("dp:result")
	saveresults=Nodes[0].toprettyxml(indent=" ")
	saveresults=str(saveresults.replace(" ",""))
	print ("...Save configuration results \n" + str(saveresults).replace("\n","") + "\n\n")

	Servernames = ServerFILE.readline()
print ("\n\n Thanks for using MultiImport")
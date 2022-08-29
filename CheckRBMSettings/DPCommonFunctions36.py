#!/usr/bin/python
#
# reused functions for DataPower script library
# Ken Hygh, khygh@us.ibm.com 6/14/2012
import sys, string, time, http.client, ssl
from xml.dom.minidom import parseString
import base64


def getText(nodelist):
    rc = []
    for node in nodelist:
        #print node.lastChild
        #print "Nodetype %d " % node.lastChild.nodeType
        if node.nodeType == node.TEXT_NODE:
            #print "Nodetype %d " % node.nodeType
            rc.append(node.data)
        else:
            lastnode = node.lastChild
            #print  node.lastChild.level
            #print "Nodetype %d " % lastnode.nodeType
            if lastnode.nodeType == lastnode.TEXT_NODE:
#            	print "found lastnode"
            	rc.append(lastnode.data)
            rc.append("Failure")
    return ''.join(rc)

# results can have multiple XML documents when multiple
# dp:request elements are in the request
def showResults(res, actions):
    looper = 0
    start = 39 # length of XML declaration
    index = res.find('</env:Env', start) + 15
    
    while index > 15:
        #print "index %d" % index
        aResult = res[start:index]
        #print "'",aResult,"'"
        if aResult.startswith("<env:Envelope"):
            #print "startswith"
            dom = parseString(aResult)
            #print dom
            Nodes = dom.getElementsByTagName("dp:result")
            
            for node in Nodes:
            	  print (actions[looper], getText(node.childNodes))
                #print actions[looper]
                #print node.childNodes
            start = start + index
            index = res.find('</env:Env', start) + 15
            #print "in loop index = %d" % index
            start = start - 39
            looper += 1
            #print "looper = %d" % looper
        else:
            looper += 1
            #print "else looper = %d" % looper
            
    index = res.find('error-log')
    if index > 0:
    		errorstring = res[index + 35:res.find('/error-log', index) - 13]
    		print ("Error ", errorstring)        
    
    index = res.find('faultstring')
    if index > 0:
        faultstring = res[index + 12:res.find('/faultstring', index) - 1]
        print ("SOAP Fault:", faultstring)



def setHeaders(username,password,server, messageLen):
    #construct and send the headers
    base64string = base64.encodebytes(bytes('%s:%s' % (username, password),'utf-8')).decode('ascii')[:-1]
#    webservice = httplib.HTTPS(server + ":5550")
    webservice = http.client.HTTPSConnection(server,5550,context=ssl._create_unverified_context())
    webservice.putrequest("POST", "/service/mgmt/current")
    webservice.putheader("Host", server)
    webservice.putheader("Authorization", "Basic %s" % base64string)
    webservice.putheader("User-Agent", "Python post")
    webservice.putheader("Content-type", "text/xml; charset=\"UTF-8\"")
    webservice.putheader("Content-length", "%d" % messageLen)
    webservice.putheader("SOAPAction", "\"\"")
    webservice.endheaders()
    return webservice
    
def setAMPHeaders(username,password,server, messageLen):
    #construct and send the headers
    base64string = base64.encodebytes(bytes('%s:%s' % (username, password),'utf-8')).decode('ascii')[:-1]
#   print ("Basic %s" % base64string)
#    webservice = httplib.HTTPS(server + ":5550")
    webservice = http.client.HTTPSConnection(server,5550,context=ssl._create_unverified_context())
    webservice.putrequest("POST", "/service/mgmt/amp/1.0")  
    webservice.putheader("Host", server)
    webservice.putheader("Authorization", "Basic %s" % base64string)
    webservice.putheader("User-Agent", "Python post")
    webservice.putheader("Content-type", "text/xml; charset=\"UTF-8\"")
    webservice.putheader("Content-length", "%d" % messageLen)
    webservice.putheader("SOAPAction", "\"\"")
    webservice.endheaders()
    return webservice

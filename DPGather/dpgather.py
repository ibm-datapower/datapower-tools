#! /usr/bin/env python3
#IBM DataPower Support 2024 Automation Tool v1.2 - Dominic Micale dmmicale (at) us.ibm.com
#Python3 required, Python 3.11 (Linux) and 3.12 (Windows) tested
#Visit https://www.ibm.com/support/pages/node/7145056 for latest mustgather tool
#1) Establish package libraries for required packages
#   ensure  python -m pip --version  returns a pip   (for the python you are going to use)
#2) Connect using SSH or Telnet (native to linux only -- could support windows, but windows does not have telnet by default)
#3) Enable a variety of must gathers, involving commands, configuration of objects
#4) Provide a cleanup to disable must gather, remove debug configuration objects and changes.

#apt-get install pip
#pip install wexpect pexpect setuptools colorama inquirer

#may alternatively need this:
#pip install wexpect pexpect setuptools colorama inquirer --break-system-packages
import platform
import os
import os.path
import datetime
import traceback
import time
import sys
import subprocess
import importlib
import importlib.metadata
import argparse
import re
import threading


version = '1.2'

parser = argparse.ArgumentParser(
                    prog='DPGather',
                    description='Automates Data Collection for DataPower Appliances on multiple platforms',
                    epilog='If you need help reach out to IBM DataPower Support')
parser.add_argument('-t', '--target', help="hostname or containerid")
parser.add_argument('-u', '--user', help="user for datapower login")
parser.add_argument('-p', '--password', help="password for datapower login")
parser.add_argument('-e', '--eventid', help="0x12345678 message id from a log message to use on the network must gather")
parser.add_argument('-r', '--regexp', help="regular expression filter to use on the network must gather")
parser.add_argument('-x' ,'--use_process', help="protocol or container options: ssh|telnet|docker|oc|kubectl")
parser.add_argument('-z', '--pcap_file_size', help="size of packet capture staged in KB")
parser.add_argument('-c', '--cleanup', help="cleanup previous staged mustgathers")
parser.add_argument('-y', '--yes', help="auto accept prompts with 'yes'")
parser.add_argument('-n', '--namespace', help="container namespace")
parser.add_argument('-m',  '--mustgather', nargs='+', help="mustgathers |network|lldiag|mqtrace|rbm|cpu|latency|peering")
parser.add_argument('-cd', '--customdomain', help="domain used for mqtrace to specify where the idg-mq-qm object resides")
parser.add_argument('-co', '--customobject', help="object used for mqtrace")
parser.add_argument('-ci', '--captureinterval', help="capture interval for CPU must gather CLI captures")
parser.add_argument('-ct', '--capturetime', help="Total capture time for CPU must gather CLI captures")
parser.add_argument('-cp', '--customport', help="Used to specify a custom telnet or SSH port to connect")
parser.add_argument('-dm', '--domain', help="domain to use for data collection")
parser.add_argument('-ps', '--peeringsetup', help="Used to specify initial setup of peering logs", action='store_true')
parser.add_argument('-pc', '--peeringcollect', help="Used to specify collection of peering logs", action='store_true')
parser.add_argument('-pd', '--peeringdir', help="Used to specify local directory for collection of status/info")
parser.add_argument('-d',  '--debug', help="Writes detailed and extensive information to the screen", action='store_true')

args = parser.parse_args()

target = ""
login_username = ""
login_password = ""
eventid = "0x0"
regex_filter = ""
use_process = "ssh"
pcap_file_size = 20000 # 20MB
namespace = ""
yes_prompt = 0
cleanup = 0
lldiag_dirtouse = "local:///"
custom_domain = ""
custom_object = ""
mustgather = [ "" ]
capture_interval = 60
capture_time = 300
custom_port = 0
login_usersent = 0
login_passwordsent = 0
default_timeout = 30
logged_in = 0
debug = False
domain = ""
peeringsetup = False
peeringcollect = False
peeringdir = ""

if args.target:
    target = args.target

if args.user:
    login_username = args.user

if args.password:
    login_password = args.password

if args.eventid:
    eventid = args.eventid

if args.regexp:
    regex_filter = args.regexp

if args.use_process:
    use_process = str(args.use_process)

if args.pcap_file_size:
    pcap_file_size = int(args.pcap_file_size)

if args.yes:
    yes_prompt = int(args.yes)

if args.cleanup:
    cleanup = int(args.cleanup)

if args.namespace:
    namespace = args.namespace

if args.mustgather:
    mustgather = args.mustgather

if args.customdomain:
    globals()["custom_domain"] = args.customdomain

if args.customobject:
    globals()["custom_object"] = args.customobject

if args.captureinterval:
    capture_interval = int(args.captureinterval)

if args.capturetime:
    capture_time = int(args.capturetime)

if args.customport:
    custom_port = int(args.customport)

if args.debug:
    debug = args.debug
if args.domain:
    domain = args.domain
if args.peeringsetup:
    peeringsetup = args.peeringsetup
if args.peeringcollect:
    peeringcollect = args.peeringcollect
if args.peeringdir:
    peeringdir = args.peeringdir


def install_and_import(package):
    import importlib
    try:
        importlib.import_module(package)
    except ImportError:
        import pip
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    finally:
        globals()[package] = importlib.import_module(package)

#Load Python Packages
packages = []

if platform.system() == 'Windows':
    packages = ['wexpect', 'pexpect', 'setuptools', 'colorama', 'inquirer']
else:
    packages = ['pexpect', 'setuptools', 'colorama', 'inquirer']

for pkg in packages:
    try:
        if not importlib.metadata.distribution(pkg):
            install_and_import(pkg)
    except importlib.metadata.PackageNotFoundError:
        install_and_import(pkg)

from colorama import Fore, Back, Style
import pexpect
from pexpect.popen_spawn import PopenSpawn
import inquirer
import getpass

#This causes issues if we import to linux
if platform.system() == 'Windows':
    import wexpect #setuptools required

print("DataPower MustGather  Version: "+ version)

if not args.use_process:
    in_message = "DataPower: What platform/endpoint are we connecting to?"

    choicesList = ['ssh', 'telnet', 'docker', 'oc', 'kubectl']
    if platform.system() == 'Windows':
        choicesList = ['ssh', 'plink_ssh', 'plink_telnet', 'docker', 'oc', 'kubectl']

    platform_selection = [
        inquirer.List('datapowerplatform',
            message = in_message,
            choices = choicesList,
        ),
        ]
    results = inquirer.prompt(platform_selection)
    use_process = results['datapowerplatform']



def getMustgather():

    in_message = "DataPower: What must gathers are to be staged (use spacebar to select, enter submits)?"
    if args.cleanup and int(args.cleanup) == 1:
        in_message = "DataPower: What must gathers are to be cleaned up (use spacebar to select, enter submits)?"
    mustgather_selection = [
        inquirer.Checkbox('datapowermustgathers',
            message=in_message,
            choices=['network', 'lldiag', 'mqtrace', 'rbm', 'cpu', 'latency','peering'],
        ),
        ]
    results = inquirer.prompt(mustgather_selection)
    mustgather = results['datapowermustgathers']

    if len(mustgather) == 0:
       return(getMustgather())
    return(mustgather)

if not args.mustgather:
    mustgather = getMustgather()

def PromptForInput(message):
    # print(message)
    sys.stdout.write(message)
    result = input()
    return result

def YesNoPrompt(message, ignore_skip_prompt = 0):
    print(Fore.RED + message)
    print(Style.RESET_ALL)
    if yes_prompt == 1 and ignore_skip_prompt == 0:
        print("yes\n")
        return 1
    yesnoprompt = input()
    reMatch = re.compile('[yY]{1}')
    matchResult = reMatch.search(yesnoprompt)
    if matchResult is not None:
        return 1
    return 0

def getCmd4useProcess(useProcess):

    connectionCmd = useProcess
    if useProcess == "plink_ssh":
       connectionCmd = "plink -ssh"
    elif useProcess == "plink_telnet":
       connectionCmd = "plink -telnet"

    return(connectionCmd)


def PrintText(color, text):
    print(color + text)
    print(Style.RESET_ALL, end="\r")

def SendExpect(child, send_data, expect_data, custom_timeout=60):
    child.sendline(send_data)
    r = child.expect(expect_data, timeout=custom_timeout)
    return r

def printDebug(color, message):
   if debug:
      print(color, message)

def sendGet(child, sendData, expectData, custom_timeout=60):
   printDebug(Fore.CYAN, "sendGet: ("+ sendData +"]")

   if platform.system() == 'Windows':
      TimeoutException = wexpect.TIMEOUT
      EOFexception = wexpect.EOF
   else:
      TimeoutException = pexpect.exceptions.TIMEOUT
      EOFexception = pexpect.exceptions.EOF

   child.sendline(sendData)
   try:
      child.expect(expectData, timeout=custom_timeout)
      output = child.before
   except EOFexception:
      print(Fore.RED, "EOF error on remote command")
      print(Fore.YELLOW, "sendData   ["+ sendData +"]")
      output = ""
   except TimeoutException:
      print(Fore.RED, "TIMEOUT error on remote command")
      print(Fore.YELLOW, "sendData   ["+ sendData +"]")
      print(Fore.YELLOW, "expectData ["+ expectData +"]")
      if platform.system() == 'Windows':
         print(Fore.YELLOW, "output     ["+ output +"]")
      output = ""

   if output != "":
      if type(output) == bytes:
         output = output.decode('utf-8')

      # convert output to one standard newlin per line and strip command from output (first line)
      lines = output.splitlines()
      firstLine = True
      output = ""
      for line in lines:
          if firstLine:
              firstLine = False
          else:
              output = output + line + "\n"

   return(output)

def sendGetField(child, sendData, expectData, fieldName, custom_timeout=60):

   fieldValue = ""
   output = sendGet(child, sendData, expectData, custom_timeout)
   lines = output.splitlines()
   for line in lines:
       line = line.strip()
       if len(line) > len(fieldName):
           if line[0:len(fieldName)] == fieldName:
              fieldValue = line[len(fieldName)+1:]
              fieldValue = fieldValue.strip()

   return(fieldValue)

def isUserAdmin(child, userid):
   printDebug(Fore.CYAN, 'isUserAdmin: userid ['+ userid +']')
   userLabel = "user:"
   accessLabel = " access-level"
   accessLevel = "privileged"

   cmd = "top;show usernames"
   output = sendGet(child, cmd, "idg#")
   printDebug(Fore.CYAN, 'isUserAdmin: output ['+ output +']')
   lines = output.splitlines()
   isAdmin = False
   currentUser = False
   for line in lines:
      if line != "":
         if currentUser:
            if len(line) > len(accessLabel):
               if line[0:len(accessLabel)] == accessLabel:
                  level = line.split()[1].strip()
                  if level == accessLevel:
                     isAdmin = True;

         if len(line) > len(userLabel):
            if line[0:len(userLabel)] == userLabel:
               user = line.split()[1].strip()
               if user == userid:
                     currentUser = True
               else: currentUser = False

   return(isAdmin)

def getFirmware(child):
   firmwareVersion = "";

   output = sendGet(child, "show version", "idg#")
   lines = output.splitlines()
   for line in lines:
      if line != "":
         firstWord = line.split()[0].strip()
         if firstWord == "Version:":
            firmwareVersion = line.split()[1].strip()
   return(firmwareVersion)


def getFirmwareParts(firmwareVersion):

   parts = firmwareVersion.split('.')

   # check for special builds
   s = "1234567890"
   if len(parts) >= 5: s = parts[4]

   sb = ""   # special build letters
   fp = ""   # fix pack
   if not s.isdigit():
      i = 0
      while (i < len(s)) & (s[i].isdigit()):
         fp = fp + s[i]
         i += 1
      sb = s[i:]
      parts[4] = fp

   parts.append(sb)

   return(parts)

def isFirmwareContained(firmwareVersion, modifiedVersions):

   parts = getFirmwareParts(firmwareVersion)
   majorVersion   = int(parts[1])
   minorVersion   = int(parts[2])
   cdVersion      = int(parts[3])
   fixpackVersion = int(parts[4])
   specialBuild = parts[5]

   included = False
   for fw in modifiedVersions:
      parts = getFirmwareParts(fw)
      currentMajorVersion   = int(parts[1])
      currentMinorVersion   = int(parts[2])
      currentCdVersion      = int(parts[3])
      currentFixpackVersion = int(parts[4])
      currentSpecialBuild = parts[5]

      # handle LTS release compares separate from CD releases
      if currentCdVersion == 0:
         if majorVersion == currentMajorVersion:
            if minorVersion == currentMinorVersion:
               if cdVersion == currentCdVersion:
                  if fixpackVersion >= currentFixpackVersion:
                     included = True
      else: # its a CD version
         if majorVersion == currentMajorVersion:
            if minorVersion == currentMinorVersion:
               if cdVersion >= currentCdVersion:
                  if fixpackVersion >= currentFixpackVersion:
                     included = True

   return(included)

def getIsDomainEnabled(child, domain):
   isEnabled = False
   fieldName = "admin-state"
   cmd = "show domain "+ domain
   output = sendGetField(child, cmd, "idg#", fieldName)
   if output == "enabled":
      isEnabled = True

   return(isEnabled)

def getDomains(child):
   domains = []
   enabledDomains = []

   output = sendGet(child, "show domains", "idg#")
   lines = output.splitlines()
   titleSeparator = "--"
   inDomains = False
   for line in lines:
      if line != "":
         firstWord = line.split()[0].strip()
         if inDomains:
            domains.append(firstWord)
         if firstWord[0:len(titleSeparator)] == titleSeparator:
            inDomains = True

   printDebug(Fore.CYAN, "Domains:")
   for domain in domains:
      if getIsDomainEnabled(child, domain):
          enabledDomains.append(domain)
          printDebug(Fore.CYAN, "   "+ str(domain))
      else:
          printDebug(Fore.CYAN, "   "+ str(domain) +" is disabled")

   return(enabledDomains)

def getAPICdomains(child):
   apicDomains = []
   domains = getDomains(child)

   for domain in domains:
      fieldName = "admin-state"
      cmd = "sw "+ domain +"; show apic-gw-service; sw default"
      output = sendGetField(child, cmd, "idg#", fieldName)
      if output == "enabled":
         apicDomains.append(domain)

   printDebug(Fore.CYAN, "APIC Domains:")
   for domain in apicDomains:
      printDebug(Fore.CYAN, "   "+ str(domain))

   return(apicDomains)

def getPeeringsForDomain(child, domain):
   # todo to do replace print calls back to printDebug calls once peerings are found
   printDebug(Fore.CYAN, "getPeeringsForDomain: ["+ domain +"]")
   peerings = []
   cmd = "sw "+ domain +"; config; show gateway-peering-manager; exit; sw default;"
   output = sendGet(child, cmd, "idg#")
   initialLines = output.splitlines()

   # remove any blank lines, and print out the lines if in debug mode
   lines = []
   for line in initialLines:
      printDebug(Fore.CYAN, "|"+ line)
      if line != "": lines.append(line)


   inPeerings = False
   for line in lines:
      printDebug(Fore.CYAN, "  line ["+ line +"]")
      words = line.split()

      firstWord = secondWord = thirdWord = fourthWord =""
      if len(words) >= 2:
         firstWord = words[0].strip()
         secondWord = words[1].strip()
      if len(words) >= 3:
         thirdWord = words[2].strip()
      if len(words) >= 4:
         fourthWord = words[3].strip()
         if secondWord == "(deprecated)":
            secondWord = thirdWord
            thirdWord = fourthWord
            fourthWord = "(deprecated)"
      printDebug(Fore.CYAN, "  words ["+ firstWord +"] ["+ secondWord +"] ["+ thirdWord +"] ["+ fourthWord +"]")

      if inPeerings:
         if thirdWord == "[up]":
            peerings.append(secondWord)
         if thirdWord == "[down]":
            print(Fore.YELLOW, "  "+ secondWord +" peering is down, will not be collected")
      if ((firstWord == "admin-state") and (secondWord == "enabled")):
         inPeerings = True
         printDebug(Fore.CYAN, "  in Peerings = True")

   print(Fore.CYAN, "   Peerings to use:")
   for peering in peerings:
      print(Fore.CYAN, "     "+ str(peering))

   printDebug(Fore.CYAN, "getPeeringsForDomain: end")
   return(peerings)

def getDataPowerInfo(child):

   timeLabel     = "Local time:"
   timeZoneLabel = "Time zone:"
   uptimeLabel   = "Uptime: reload:"
   bootLabel     = "Uptime: reboot:"
   nameLabel     = "name:"
   serNoLabel    = "serial number:"
   firmwareLabel = "Version"

   cmd = "show time;"
   time       = sendGetField(child, cmd, "idg#", timeLabel)
   timezone   = sendGetField(child, cmd, "idg#", timeZoneLabel)
   uptime     = sendGetField(child, cmd, "idg#", uptimeLabel)
   bootuptime = sendGetField(child, cmd, "idg#", bootLabel)

   cmd = "show system;"
   DPname       = sendGetField(child, cmd, "idg#", nameLabel)
   serialNumber = sendGetField(child, cmd, "idg#", serNoLabel)

   cmd = "show version;"
   firmwareVersion = sendGetField(child, cmd, "idg#", firmwareLabel)

   localNow = datetime.datetime.now()

   # convert the DP timstampt to an ansi format, and create a DataPower log format timestamp if timezone is UTC
   # if an error occurs we dont care as it is not critical
   DPtimestamp = ""
   AnsiTimestamp = ""
   try:
      words = time.split()
      dayName   = words[0]
      monthName = words[1]
      day       = int(words[2])
      timePart  = words[3]
      year      = int(words[4])
      month   = datetime.datetime.strptime(monthName, '%b').month
      hours   = int(timePart[0:2])
      minutes = int(timePart[3:5])
      seconds = int(timePart[6:8])

      DPdatetime = datetime.datetime(year, month, day, hours, minutes, seconds)

      if timezone == "UTC":
         DPtimestamp = format(DPdatetime.year, '#04') + format(DPdatetime.month, '#02') + format(DPdatetime.day, '#02') + "T"
         DPtimestamp =  DPtimestamp + format(DPdatetime.hour, '#02') + format(DPdatetime.minute, '#02') + format(DPdatetime.second, '#02')
         DPtimestamp =  DPtimestamp + ".000Z"
      AnsiTimestamp = format(DPdatetime.year, '#04') +"-"+ format(DPdatetime.month, '#02') +"-"+  format(DPdatetime.day, '#02') + " "
      AnsiTimestamp =  AnsiTimestamp + format(DPdatetime.hour, '#02') +":"+ format(DPdatetime.minute, '#02') +":"+ format(DPdatetime.second, '#02')
      AnsiTimestamp =  AnsiTimestamp +" "+ timezone

   except Exception as e:
      # log the error  traceback.format_exc()
      print(Fore.RED, "error with ts: "+ traceback.format_exc())

   output = "DataPower info:\n"
   output = output + "  Time: "+ AnsiTimestamp +"\n"
   if DPtimestamp != "": output = output + "        "+ DPtimestamp +"\n"
   output = output + "        "+ time +" "+ timezone +"\n"
   output = output + "  Name: " + DPname +"\n"
   output = output + "  Serial Number: "+ serialNumber +"\n"
   output = output + "  Firmware: "+ firmwareVersion +"\n"
   output = output + "  Reload Uptime: "+ uptime +" \n"
   output = output + "  Boot Uptime:   "+ bootuptime +"\n"
   output = output + "Local collection machine:\n"
   output = output + "  Time: "+ str(localNow) +"\n"
   printDebug(Fore.CYAN, output+"\n")

   return(output)

def buildPeeringStartTraceCommands(domain, peerings):
   rows = len(peerings) + 4
   cols = 3
   command = 0
   expects = 1
   file    = 2
   commands = [[''] * cols for i in range(rows)]
   timestr = time.strftime("%Y%m%d-%H%M%S")

   row = 0
   commands[row][command] = "top; sw "+ domain +"; config;"
   commands[row][expects] = "idg\\["+ domain +"\\]\\(config\\)#"
   commands[row][file]    = ""

   row += 1
   commands[row][command] = "echo show gateway-peering-status; show gateway-peering-status; echo show interface; show interface; echo show int mode; show int mode;echo show route; show route;"
   commands[row][expects] = "idg\\["+ domain +"\\]\\(config\\)#"
   commands[row][file]    = "peering-status-"+ domain +"-"+ timestr +".txt"

   row += 1
   commands[row][command] = "exit; diag;"
   commands[row][expects] = "idg\\["+ domain +"\\]\\(diag\\)#"
   commands[row][file]    = ""

   for peering in peerings:
      row += 1
      commands[row][command] = "gateway-peering-debug "+ peering +";"
      commands[row][expects] = "idg\\["+ domain +"\\]\\(diag\\)#"
      commands[row][file]    = ""

   row += 1
   commands[row][command] = "exit; sw default; top;"
   commands[row][expects] = "idg# "
   commands[row][file]    = ""

   return(commands)

def buildPeeringEndTraceCommands(domain, peerings, firmwareVersion):

   # if firmware is greater than 10.5.0.7 or 10.6.0.0 then we can collect the info and sentinel info
   firmwares = ["IDG.10.5.0.7",
                "IDG.10.6.0.0",
                "IDG.10.6.1.0",
                "IDG.10.7.0.0"]

   collectInfo = isFirmwareContained(firmwareVersion, firmwares)

   if collectInfo:
      rows = len(peerings) * 4 + 4
   else:
      rows = len(peerings) * 2 + 4
   cols = 3
   command = 0
   expects = 1
   file    = 2
   commands = [[''] * cols for i in range(rows)]
   timestr = time.strftime("%Y%m%d-%H%M%S")

   row = 0
   commands[row][command] = "top;sw "+ domain +"; config"
   commands[row][expects] = "idg\\["+ domain +"\\]\\(config\\)#"
   commands[row][file]    = ""

   row += 1
   commands[row][command] = "echo show gateway-peering-status; show gateway-peering-status; echo show interface; show interface; echo show int mode; show int mode;echo show route; show route;"
   commands[row][expects] = "idg\\["+ domain +"\\]\\(config\\)#"
   commands[row][file]    = "peering-status-"+ domain +"-"+ timestr +".txt"

   row += 1
   commands[row][command] = "exit; diag;"
   commands[row][expects] = "idg\\["+ domain +"\\]\\(diag\\)#"
   commands[row][file]    = ""

   for peering in peerings:
      row += 1
      commands[row][command] = "gateway-peering-dump "+ peering +";"
      commands[row][expects] = "idg\\["+ domain +"\\]\\(diag\\)#"
      commands[row][file]    = ""
      row += 1
      commands[row][command] = "no gateway-peering-debug "+ peering +";"
      commands[row][expects] = "idg\\["+ domain +"\\]\\(diag\\)#"
      commands[row][file]    = ""

      if collectInfo:
         row += 1
         commands[row][command] = "gateway-peering-diag "+ peering +" info;"
         commands[row][expects] = "idg\\["+ domain +"\\]\\(diag\\)#"
         commands[row][file]    = "peering-info-"+ domain +"-"+ peering +"-"+ timestr +".txt"
         row += 1
         commands[row][command] = "gateway-peering-diag "+ peering +" sentinel info;"
         commands[row][expects] = "idg\\["+ domain +"\\]\\(diag\\)#"
         commands[row][file]    = "peering-sentinel-"+ domain +"-"+ peering +"-"+ timestr +".txt"

   row += 1
   commands[row][command] = "exit; sw default; top;"
   commands[row][expects] = "idg# "

   return(commands)

def buildPeeringCollectionArgs(peeringDomain, localMGdir):

   interpreterName = sys.orig_argv[0]
   scriptName      = sys.orig_argv[1]

   printDebug(Fore.GREEN, "buildPeeringCollectionArgs  sys.executable  ["+sys.executable+"]")
   for thing in sys.orig_argv:
      printDebug(Fore.GREEN, "buildPeeringCollectionArgs     sys.orig_argv   ["+thing+"]")

   arguments = interpreterName +" "+ scriptName +" --use_process "+ use_process +" --target "+ target +" --user "+ login_username +" --domain "+ peeringDomain +" --mustgather peering --peeringcollect"
   if custom_port != 0:
      arguments = arguments + " --customport "+ str(custom_port)
   if namespace != '':
      arguments = arguments + " --namespace "+ str(namespace)
   if localMGdir != "":
      arguments = arguments + " --peeringdir "+ localMGdir
   if debug:
      arguments = arguments + " --debug"

   return(arguments)


def getPeeringTraceFilenames(peeringDomain, peerings, firmwareVersion):

   # peering logs changed to pack the peering files into a zip, instead of the 2 separate files.  DPGW-2391
   firmwares = ["IDG.10.5.0.14",
                "IDG.10.6.0.2",
                "IDG.10.6.2.0",
                "IDG.10.7.0.0"]

   collectAsZip = isFirmwareContained(firmwareVersion, firmwares)

   files = []
   prefix = "temporary:///"+ peeringDomain +"/"
   for peering in peerings:
      if collectAsZip:
         filename = prefix + peering + "/gateway-peering-debug.zip"
         files.append(filename)
         printDebug(Fore.GREEN, "getPeeringTraceFilenames: zip file name: "+ filename)
      else:
         filename = prefix + peering + "/gatewaypeering.log"
         files.append(filename)
         printDebug(Fore.GREEN, "getPeeringTraceFilenames: log file name: "+ filename)
         filename = prefix + peering + "/gatewaypeeringmonitor.log"
         files.append(filename)
         printDebug(Fore.GREEN, "getPeeringTraceFilenames: monitor log file name: "+ filename)

   return(files)

def promptForPeeringDomain(domains):
   inMessage = "Which domain do you want to collect peering data for?"
   domainSelection = [
        inquirer.List('domainChoice',
           message=inMessage,
           choices=domains,
        ),
       ]
   results = inquirer.prompt(domainSelection)
   domain = results['domainChoice']

   return(domain)

def promptForPeeringState():
   if peeringsetup:
       state = 'setup'
   elif peeringcollect:
       state = 'collect'
   else:
      inMessage = "What part of the peering data collection are you in?"
      peeringSelection = [
          inquirer.List('peeringstate',
              message=inMessage,
              choices=['setup', 'collect'],
          ),
          ]
      results = inquirer.prompt(peeringSelection)
      state = results['peeringstate']

   return(state)

def getDefaultLogEnabled(child):
   result = False
   fieldName = "admin-state"
   cmd = "top; show logging target default-log"
   fieldValue = sendGetField(child, cmd, "idg#", fieldName)
   if fieldValue == "enabled":
       result = True

   return(result)

def setDefaultLogEnabled(child, enable):

   if enable:
      admSt = "admin-state enabled;"
   else:
      admSt = "admin-state disabled;"

   command = "top; sw default; config"
   ignoreOutput = sendGet(child, command, "#")
   command = "logging target default-log"
   ignoreOutput = sendGet(child, command, "#")
   command = admSt + " exit; top"
   ignoreOutput = sendGet(child, command, "idg#")

def SaveErrorReport(child):
    SendExpect(child, "top; co; save error-report; top", "check the logs for the final result")
    reMatch = re.compile('(([a-zA-Z0-9\\._]+):///error\\-report\\.[0-9]+\\.[0-9a-zA-Z]{18,23}\\.txt\\.gz)')
    matchResult = reMatch.search(str(child.before))
    if matchResult is not None:
        return matchResult.group(0)
    return "temporary:///error-report.txt.gz"

def generateErrorReport(child):  # syncronized version

   beforeFilename = "Error Report creation successfully started to '"
   afterFilename  = "', check the logs for the final result"
   errorMsg = "Cannot write error report to"
   filename = "temporary:///error-report.txt.gz"  #default

   cmd = "top;co;save error-report;top"
   output = sendGet(child, cmd, "idg#")
   lines = output.splitlines()
   for line in lines:
      if line[0:len(beforeFilename)] == beforeFilename:
         filename = line[len(beforeFilename):]
         fnEnd = filename.find(afterFilename)
         filename = filename[0:fnEnd]

   return(filename)

def dpMakeMGdir(child, dirName):
   successMsg = "successfully created"

   MGdir = "temporary:///"+ dirName
   directory = MGdir
   i = 2;
   while (dpCheckDirExists(child, directory)):
      directory = MGdir + str(i)
      i += 1

   cmd = "top;co;mkdir "+ directory +"; top;"
   output = sendGet(child, cmd, "idg#")
   lines = output.splitlines()
   result = False
   for line in lines:
      if line.find(successMsg) >= 0:
         result = True

   if result: newDir = directory
   else: newDir = ""

   return(newDir)

def dpMoveFile(child, filePath, targetDir):
   if dpCheckFileExists(child, filePath):
     # get filename from filePath
     fnStart = filePath.rfind('/') + 1
     filename = filePath[fnStart:]
     targetFilePath = targetDir +"/"+ filename

     cmd = "top; config; move "+ filePath +" "+ targetFilePath +"; top"
     SendExpect(child, cmd, 'idg#')

     return(targetFilePath)

def dpMovePeeringFile(child, filePath, targetDir):

    if dpCheckFileExists(child, filePath):
       # get filename and peering dirname from filePath.
       fnStart = filePath.rfind('/') + 1
       filename = filePath[fnStart:]

       lastDirName = filePath[0:fnStart-1]
       dirStart = lastDirName.rfind('/') + 1
       lastDirName = lastDirName[dirStart:]
       targetFilePath = targetDir +"/"+ lastDirName +"-"+ filename

       cmd = "top; config; move "+ filePath +" "+ targetFilePath +"; top"
       SendExpect(child, cmd, 'idg#')

    return(targetFilePath)

def dpCheckFileExists(child, filePath):
   fnStart = filePath.rfind('/') + 1
   filename = filePath[fnStart:]
   directory = filePath[0:fnStart]

   cmd = "top;co;dir "+ directory +";top;"
   output = sendGet(child, cmd, "idg#")
   lines = output.splitlines()
   result = False
   for line in lines:
      words = line.split()
      if len(words) > 1:
         firstWord = words[0].strip()
         if firstWord == filename:
            result = True

   return(result)

def dpCheckDirExists(child, directory):

   cmd = "top;co;dir "+ directory +";top;"
   output = sendGet(child, cmd, "idg#")
   lines = output.splitlines()
   result = False
   for line in lines:
      if line.find("No such file or directory") >= 0:
         result = False
      if line.find("File Name") >= 0:
         result = True

   return(result)


def sendCmdsToNewWindow(commands):

   if platform.system() == 'Windows':
      child4cp = wexpec.spawn('cmd')
      child4cp.expect('>')
   else:
      child4cp = pexpect.spawn('bash')
      child4cp.expect('#')

   for cmd in commands:
      printDebug(Fore.CYAN, "  Running command: "+cmd)
      SendExpect(child4cp, cmd, "#")


def isLocalUserAuthorized():
   # check if user can create directories on local machine
   access = os.access("./", os.W_OK )
   return(access)

def checkLocalDirExists(dirName):
   exists = os.path.isdir(dirName)
   return(exists)

def checkLocalFileExists(filename):
   exists = os.path.isfile(filename)
   return(exists)

def makeLocalMGdir(dirName):
   directory = dirName
   i = 2;
   while (checkLocalDirExists(directory)):
      directory = dirName + str(i)
      i += 1

   try:
      os.mkdir(directory)
   except OSError as error:
      directory = ""

   return(directory)

def promptForLocalMGdir(rootDirName):

   # if the directory was passed in, use it
   if peeringdir:
      if checkLocalDirExists(peeringdir):
         return(peeringdir)

   # if it was not passed in, or passed in was invalid, get the list of them to chose from
   allFiles = os.listdir("./")
   fileList = []

   for file in allFiles:
      if file[0:len(rootDirName)] == rootDirName:
          fileList.append(file)

   if len(fileList) == 0:
      localMGdir = ""   # use current dir.  or generate one? either way the setup was not run

   if len(fileList) == 1:
      localMGdir = fileList[0]

   if len(fileList) > 1:
      fileList.reverse()
      inMessage = "Which directory name matches the setup for this peering collection?"
      peeringDirSelection = [
          inquirer.List('peeringdir',
              message=inMessage,
              choices=fileList,
          ),
          ]
      results = inquirer.prompt(peeringDirSelection)
      localMGdir = results['peeringdir']

   return(localMGdir)

#-------------------------------------------------------------------------------
def doPeeringMustGather(child):
   print(Fore.GREEN, "Beginning Peering MustGather..")
   rc = 0
   DP_MG_DIR    = "peeringMG"
   LOCAL_MG_DIR = "DPgather_PeeringMG"
   state = "setup"
   uploadInstructions = []
   dataFromDPpulled = False
   pullDataCmds = []

   # check if user can create directories and files on local machine
   if not isLocalUserAuthorized():
       PrintText(Fore.YELLOW, "Must use a local account with file write privileges")
       return(-1)

   # if kubernetes, disable the default log to avoid it messing up the CLI commands outputs in the attach window
   defaultLogDisabledByScript = False
   if ((use_process == "docker") or (use_process == "oc") or (use_process == "kubectl")):
      if getDefaultLogEnabled(child):
         print(Fore.GREEN, "Temporarily disabling the default log, to reduce chaff in attach window")
         setDefaultLogEnabled(child, False);
         defaultLogDisabledByScript = True

   if isUserAdmin(child, login_username):

      DataPowerInfo = getDataPowerInfo(child)

      state = promptForPeeringState()

      print(Fore.GREEN, "   Getting apic domains")
      apicDomains = getAPICdomains(child)

      numberAPICdomains = len(apicDomains)
      if numberAPICdomains > 0:

         # get domain if it was passed in as a parameter
         peeringDomain = domain;
         if peeringDomain != "":
            if peeringDomain not in apicDomains:
               print(Fore.YELLOW, '\nWARNING: No APIC domain "'+peeringDomain+'" exists.')
               peeringDomain = ""
            else: print(Fore.GREEN, "   Using domain "+ peeringDomain)

         # if not passed in, get domain from prompt of list, unless there is only one
         if peeringDomain == "":
            if numberAPICdomains == 1:
               peeringDomain = apicDomains[0]
               print(Fore.GREEN, "   Only one apic domain, using it: "+ peeringDomain)
            else:
               peeringDomain = promptForPeeringDomain(apicDomains)

         peerings = getPeeringsForDomain(child, peeringDomain)

         collectionCmdArgs = "";
         collectFiles = []
         if state == "setup":
            print(Fore.GREEN, "   Building commands to enable peering trace")
            commands = buildPeeringStartTraceCommands(peeringDomain, peerings)

            # create the local directory for output, permissions have already been verifyied
            localMGdir = makeLocalMGdir(LOCAL_MG_DIR)
            print(Fore.GREEN, "   Created local directory "+ localMGdir +" for status command output.  This directory name will be needed for the collection phase.")

            # build the collect command parameters for the user to run after the issue has occurred
            collectionCmdArgs = buildPeeringCollectionArgs(peeringDomain, localMGdir)
            infoFilename = localMGdir +"/setupInfo";
         else:
            print(Fore.GREEN, "   Building commands to collect peering traces and disable them")
            firmwareVersion = getFirmware(child)
            commands = buildPeeringEndTraceCommands(peeringDomain, peerings, firmwareVersion)
            collectFiles = getPeeringTraceFilenames(peeringDomain, peerings, firmwareVersion)

            localMGdir = promptForLocalMGdir(LOCAL_MG_DIR)
            infoFilename = localMGdir +"/collectionInfo";

         # write out some basic DP info
         timestr = time.strftime("%Y%m%d-%H%M%S")
         infoFilename = infoFilename +"-"+ timestr +".txt"
         outputFile = open(infoFilename, 'w')
         WriteDataToFile(outputFile, DataPowerInfo)
         outputFile.close()


         # run the commands
         print(Fore.GREEN, "   Executing the peering commands")

         for row in commands:
            command  = row[0]
            expects  = row[1]
            filename = row[2]
            printDebug(Fore.CYAN, "   "+command)

            if filename == "":  # if no filename then it's just a setting command, otherwise we need the output
               SendExpect(child, command, expects)
            else:
               output = sendGet(child, command, expects)

               filename = localMGdir +"/"+ filename
               outputFile = open(filename, 'w')
               WriteDataToFile(outputFile, filename +"\n")  # write filename as first line of file
               WriteDataToFile(outputFile, output)
               outputFile.close()

         if state == "setup":
            print(Fore.GREEN, "   Setting up peering data collection is complete")
            print(Fore.WHITE, " ")
            print(Fore.WHITE, "Command and arguments for collecting peering data (copy and save somewhere for the collection phase):")
            print(Fore.YELLOW, collectionCmdArgs)
            print(Fore.GREEN, " ")
         else:
            # get a final error report and move all the relevant files to one directory, for ease of offloading
            print(Fore.GREEN, "   Generating error report")
            ER_filename = generateErrorReport(child);

            MGdir = dpMakeMGdir(child, DP_MG_DIR)
            if MGdir != "":
               print(Fore.GREEN, "   Packaging peering data on the DataPower to directory "+ MGdir)
               newCollectFiles = []
               for file in collectFiles:
                  newFilePath = dpMovePeeringFile(child, file, MGdir)
                  newCollectFiles.append(newFilePath)
               newFilePath = dpMoveFile(child, ER_filename, MGdir)
               newCollectFiles.append(newFilePath)

               # if we are kube or oc, pull the files off the DP to the local MG dir
               if ((use_process == "oc") or (use_process == "kubectl")):
                  stripTmpLn = len("temporary:///")
                  stripTmpAndDirLn = len(MGdir) + 1

                  printDebug(Fore.CYAN, "   MGdir    ["+ MGdir +"]")
                  DPtmpDir = MGdir[stripTmpLn:]
                  printDebug(Fore.CYAN, "   DPtmpDir ["+ DPtmpDir +"]")
                  DPpath = target+':opt/ibm/datapower/drouter/temporary/'+ DPtmpDir +"/"
                  printDebug(Fore.CYAN, "   DPpath   ["+ DPpath +"]")

                  # get the DataPower files from their new location
                  for file in newCollectFiles:
                     DPtmpFilename = file[stripTmpAndDirLn:]
                     printDebug(Fore.CYAN, "   DataPower file  ["+ file +"]")
                     printDebug(Fore.CYAN, "   Local file      ["+ DPtmpFilename +"]")
                     cpCmd = getCmd4useProcess(use_process)+" "+'cp "'+ DPpath + DPtmpFilename +'" '+ localMGdir +'/'+ DPtmpFilename +' -n '+ namespace
                     pullDataCmds.append(cpCmd)
                  DPtmpFilename = ER_filename[stripTmpLn:]
                  cpCmd = getCmd4useProcess(use_process)+" "+'cp "'+ DPpath + DPtmpFilename +'" '+ localMGdir +'/'+ DPtmpFilename +' -n '+ namespace
                  pullDataCmds.append(cpCmd)

            print(Fore.GREEN, "   Packaging status files to local directory "+ localMGdir)

            print(Fore.GREEN, "   Collecting the peering data is complete")


            # create the upload instructions to print out at the end
            uploadInstructions.append(" ")
            if pullDataCmds:
               uploadInstructions.append("Upload all of the files in the local "+ localMGdir +" directory to the case.")
            else:
               uploadInstructions.append("Offload all files in the "+ MGdir +" directory.")
               uploadInstructions.append("Upload them to the case, along with all of the files in the local "+ localMGdir +" directory.")

            uploadInstructions.append("You can zip the local directory if you want.")

      else:
         PrintText(Fore.YELLOW, "No APIC domains to collect peering data from.")
         rc = -2
   else:
       PrintText(Fore.YELLOW, "Must use a DataPower admin privileged userid.")
       rc = -1

   # re-enable the default log if it was disabled
   if defaultLogDisabledByScript:
      print(Fore.GREEN, "Re-enabling the default log ...")
      setDefaultLogEnabled(child, True);
      print(Fore.GREEN, "Log enabled")

   # detach from the pod (close the attach)
   if ((use_process == "oc") or (use_process == "kubectl")):
      print(Fore.GREEN, "Detach from pod")
      child.sendcontrol('p')
      child.sendcontrol('q')

   # if we didn't error out
   if (rc == 0):

      # if we can pull the data off the DP, do it
      if pullDataCmds:
         print(Fore.GREEN, "Pulling data from the DataPower")
         sendCmdsToNewWindow(pullDataCmds)

      print(Fore.GREEN, " ")
      for line in uploadInstructions:
         print(Fore.WHITE, line)

      print(Fore.GREEN, "Completed Peering MustGather "+ state)
   else:
      print(Fore.YELLOW, "Peering MustGather failed")

   # reset the terminal colors
   print(Fore.GREEN, "\033[0m")

   return(rc)

def CheckFileDirExists(child, directory, filedirname, minsize):
    r = SendExpect(child, "cancel; top; co", [ 'idg\\(config\\)#', 'idg#'])
    if r == 0:
        wildcard_filename = '.*' + filedirname + '.*'
        wildcard_match = '.*available to ' + directory + '.*'
        found = SendExpect(child, "dir " + directory, [ wildcard_filename, wildcard_match])
        if found == 0: # matched wildcard filename
            return 1
        else: # did not find file only the directory size
            return 0
    else:
        PrintText(Fore.RED, "User cannot access config mode to check if file exists")
        return -1

def CheckDiagEnabled(child, diagtype):
    r = SendExpect(child, "cancel; top; diag", [ 'idg\\(diag\\)#'])
    if r == 0:
        PrintText(Fore.GREEN, "In diag mode")
        enabled = SendExpect(child, diagtype + " show", [ '.*enabled: no.*', '.*enabled: yes.*', 'Unknown command or macro'])
        SendExpect(child, "cancel; top", ['idg#'])
        if enabled == 1:
            return 1
        elif enabled == 0:
            return 0
        else:
            return -1 # no access to command or diag?
    else:
        PrintText(Fore.RED, "User cannot access diag mode to enable " + diagtype)
        return -1

def SetDPMonEnabled(child, setonoff):
    lldiag_cmd = "cancel; top; diag; dpmon " + setonoff
    r = SendExpect(child, lldiag_cmd, 'idg\\(diag\\)#')
    enabled = CheckDiagEnabled(child, "dpmon")
    if enabled == 1:
        PrintText(Fore.GREEN, "DPMon Enabled")
    else:
        PrintText(Fore.RED, "Unable to get dpmon enabled, check user permissions")
        return -1

def WriteDataToFile(file, data):

    if platform.system() != 'Windows':
        file.write(data.replace('\\n','\n').replace('\\t','\t').replace('\\r',''))
    else:
        file.write(data)

def CollectStatisticMustGather():
    stat_child = RunChildProcess()
    if EstablishLogin(stat_child, 0) == 1:
        timestr = time.strftime("%Y%m%d-%H%M%S")
        filestr = 'dpcpumg-' + timestr + '.txt'
        PrintText(Fore.GREEN, "Begin CLI Capture to File " + filestr)
        cpuFile = open('dpcpumg-' + timestr + '.txt', 'w')
        r = SendExpect(stat_child, "top; show clock; show load; show cpu; show memory; show filesystem; show accepted-connections; show tcp-table; show tcp-connections; show throughput; show interface; show link; show gateway-transactions; show crypto-engine; show xml-names; show alias", [ 'Alias Name'])
        WriteDataToFile(cpuFile, str(stat_child.before))
        r = SendExpect(stat_child, "diag; show memory details; show connections; show handles; show activity 100; show task stat", [ '[\\-]{26}'])
        WriteDataToFile(cpuFile, str(stat_child.before))
        cpuFile.close()
        SendExpect(stat_child, "top; exit", [ '.*'])
        PrintText(Fore.GREEN, "CLI Capture Complete to File " + filestr)
        stat_child.terminate()

class setInterval :
    def __init__(self,interval,func):
        self.interval=interval
        self.action=func
        self.lastcall = 0
        self.stopEvent=threading.Event()
        thread=threading.Thread(target=self.__setInterval)
        thread.start()

    def __setInterval(self):
        nextTime=time.time()+self.interval
        while not self.stopEvent.wait(nextTime-time.time()):
            nextTime+=self.interval
            self.action()
            if self.lastcall == 1 and self.action == CollectStatisticMustGather:
                self.stopEvent.set()
                er_child = RunChildProcess()
                report_file = "temporary:///error-report.txt.gz"
                if EstablishLogin(er_child, 0) == 1:
                    report_file = SaveErrorReport(er_child)
                PrintText(Fore.GREEN, "CPU Statistics Complete.. Collect Data:")
                print('- dpcpumg-datetime.txt files on your filesystem.')
                print('- lldiag.txt and lldiag.txt.* iteration files from File Management.')
                print('- ' + report_file + ' from File Management.')
                print('- temporary:///dpmon/dpmon and dpmon.x files from File Management.')
    def cancel(self) :
        self.lastcall = 1

def CheckMQTraceEnabled(child, domain, objectname):
    r = SendExpect(child, "cancel; top; switch " + domain + "; diag", [ 'idg.*\\[' + domain + '\\]\\(diag\\)#.*', 'idg#', 'idg\\(diag\\)#'])
    if r == 0 or (r == 2 and domain == "default"):
        cmd_text = "show mq-trace " + objectname + "; switch default; top"
        enabled = SendExpect(child, cmd_text, [ 'Trace\\s+\\[OFF\\]', 'Trace\\s+\\[ON\\]', 'no such IBM MQ QM found'])
        if enabled == 0 or enabled == 1:
            return enabled
        elif enabled == 2:
            return -2
    else:
        SendExpect(child, "cancel; switch default; top", 'idg.*#')
        PrintText(Fore.RED, "User cannot access diag mode to check mqtrace")
        return -1

def SetMQTraceEnabled(child, domain, objectname, state):
    print("Domain: " + domain + " object " + objectname)
    r = SendExpect(child, "cancel; top; switch " + domain + "; diag", [ '.*idg.*\\[' + domain + '\\]\\(diag\\)#.*'])
    if r == 0:
        cmd_text = "mq-trace " + objectname + "; show mq-trace " + objectname + "; switch default; top"
        if state == 0:
            cmd_text = "no " + cmd_text
        enabled = SendExpect(child, cmd_text, [ '.*Trace\\s+\\[ON\\]', '.*Trace\\s+\\[OFF\\]', '.*no such IBM MQ QM found.*'])
        if enabled == 0 or enabled == 1:
            return enabled
        elif enabled == 2:
            return -2
    else:
        SendExpect(child, "cancel; switch default; top", 'idg.*#')
        PrintText(Fore.RED, "User cannot access diag mode to enable mqtrace")
        return -1

def PromptMQTraceEnabled(child):
    PrintText(Fore.GREEN, "MQ Tracing Must Gather:")
    if not globals()["custom_domain"] or globals()["custom_domain"] == "":
        globals()["custom_domain"] = PromptForInput('DataPower Domain: ')

    if not globals()["custom_object"] or globals()["custom_object"] == "":
        globals()["custom_object"] = PromptForInput('IDG-MQ-QM Object Name: ')
    result = CheckMQTraceEnabled(child, custom_domain, custom_object)
    return result

def CheckLLDiagEnabled(child):
    r = SendExpect(child, "cancel; top; diag", [ 'idg\\(diag\\)#'])
    if r == 0:
        PrintText(Fore.GREEN, "In diag mode")
        enabled = SendExpect(child, "lldiag show", [ '.*enabled: no.*', '.*enabled: yes.*', 'Unknown command or macro'])
        if enabled == 1:
            return 1
        elif enabled == 0:
            return 0
        else:
            return -1 # no access to command or diag?
    else:
        PrintText(Fore.RED, "User cannot access diag mode to enable LLDiag")
        return -1

def SetLLDiagEnabled(child):
    useondisk = CheckFileDirExists(child, "local:", "ondisk/", 4096)
    lldiag_dirtouse = "local:///"
    if useondisk == 1:
        PrintText(Fore.GREEN, "local:///ondisk/ directory exists, using that for lldiag files")
        lldiag_dirtouse = "local:///ondisk/"
    lldiag_cmd = "cancel; top; diag; lldiag dir " + lldiag_dirtouse + "; lldiag check 250; lldiag timeout 500; lldiag monitor 1000; lldiag on miniwd"
    r = SendExpect(child, lldiag_cmd, 'idg\\(diag\\)#')
    enabled = CheckDiagEnabled(child, "lldiag")
    if enabled == 1:
        PrintText(Fore.GREEN, "LLDiag Enabled")
        findlldiagfile = CheckFileDirExists(child, lldiag_dirtouse, "lldiag.txt", 10)
        if findlldiagfile == 1:
            PrintText(Fore.GREEN, "LLdiag file identified.")
        else:
            PrintText(Fore.RED, "Unable to locate lldiag.txt!")
            return -1
    else:
        PrintText(Fore.RED, "Unable to get lldiag enabled, check user permissions")
        return -1

def SetLLDiagDisabled(child):
    r = SendExpect(child, "cancel; top; diag; lldiag off", ['idg\\(diag\\)#', 'idg.#'])
    enabled = CheckDiagEnabled(child, "lldiag")
    if enabled == 0:
        PrintText(Fore.GREEN, "LLDiag Disabled")
        return 1
    else:
        PrintText(Fore.RED, "Unable to get lldiag disabled, check user permissions")
        return 0

def IsRBMLoggingOn(child):
	SendExpect(child, "cancel; top; co", ['idg\\(config\\)#'], 120)
    #RBM Logging never set on the device will not return even an integer value, just the prompt hence 'idg.#' check
	r = SendExpect(child, "get-system-var var://system/map/debug", [ '[3-9]+', '[0-2]', 'idg.#', 'idg\\(config\\)#'], 120)
	if r == 0:
		return 1
	else:
		return 0

def SetRBMLoggingOn(child):
    r = SendExpect(child, "cancel; top; co; logging event default-log webgui debug; set-system-var var://system/map/debug 3; logging event default-log rbm debug", ['idg\\(config\\)#', 'idg.#'], 120)
    enabled = IsRBMLoggingOn(child)
    if enabled == 1:
        PrintText(Fore.GREEN, "RBM Logging Enabled")
        return 1
    else:
        PrintText(Fore.RED, "Unable to get rbm logging enabled, check user permissions")
        return 0

def SetRBMLoggingOff(child):
    r = SendExpect(child, "cancel; top; co; no logging event default-log webgui; set-system-var var://system/map/debug 0; no logging event default-log rbm debug", ['idg\\(config\\)#', 'idg.#'], 120)
    enabled = IsRBMLoggingOn(child)
    if enabled == 0:
        PrintText(Fore.GREEN, "RBM Logging Disabled")
        return 1
    else:
        PrintText(Fore.RED, "Unable to get rbm logging disabled, check user permissions")
        return 0

def DeleteSSLKeyFile(child):
    r = 0
    if "network" in mustgather and YesNoPrompt("Delete SSL Key Log File (yes/no)?") == 1:
        r = SendExpect(child, "cancel; top; co; delete logtemp:///sslkeyfile.log", ['.*No such file or directory named', 'File deletion successful'])
        if r == 0:
            PrintText(Fore.YELLOW, "logtemp:///sslkeyfile.log did not exist.")
        else:
            PrintText(Fore.GREEN, "logtemp:///sslkeyfile.log deleted.")
    return r

def RunCleanup(child, include_lldiag):

    if ("cpu" in mustgather or "lldiag" in mustgather) and include_lldiag == 1:
            lldiag_disabled = CheckDiagEnabled(child, "lldiag")
            if lldiag_disabled == 1 and YesNoPrompt("Disable LLDiag (yes/no)?") == 1:
                SetLLDiagDisabled(child)
            elif lldiag_disabled == 0:
                PrintText(Fore.YELLOW, "LLDiag is already disabled.")

    if "mqtrace" in mustgather:
        result = PromptMQTraceEnabled(child)
        if result == 1 and YesNoPrompt("MQ Tracing is ENABLED on the object, do you wish to DISABLE mq-tracing (yes/no)?") == 1:
            SetMQTraceEnabled(child, globals()["custom_domain"], globals()["custom_object"], 0)
        elif result == 0:
            PrintText(Fore.YELLOW, "MQ Tracing is already disabled on this object.")

    if "rbm" in mustgather:
        rbm_log_on = IsRBMLoggingOn(child)
        if rbm_log_on == 1 and YesNoPrompt("RBM Debug is ENABLED, do you wish to DISABLE RBM debug, please note this can take some time to complete (yes/no)?") == 1:
            SetRBMLoggingOff(child)
        elif rbm_log_on == 0:
            PrintText(Fore.YELLOW, "RBM Debug was already disabled.")

    if "latency" in mustgather:
        DeleteLogTarget(child, "ExtLatencyLogTarget")

    if "network" in mustgather:
        StopPacketCapture(child)
        DeleteSSLKeyFile(child)
        DeleteLogTarget(child, "pmr-log")

def StartPacketCapture(child, restart):
    if restart == 1:
        StopPacketCapture(child)
        DeleteSSLKeyFile(child)
    child.sendline("cancel; top; co; packet-capture-advanced all temporary:///capture.pcap -1 " + str(pcap_file_size) + " 9000 '' on")
    r = child.expect(['Packet capture already running with this file name.', 'Trace begun.', 'Failed to set up packet recording.'], timeout=default_timeout)
    if r == 0: #Packet capture already running with this file name
        if YesNoPrompt("Conflict with existing running packet capture, would you like to disable and restart the capture (yes/no)?") == 1:
            StartPacketCapture(child, 1)
    elif r == 1: #Trace begun
        PrintText(Fore.GREEN, "Packet capture has started.")
    elif r == 2: #Failed to set up packet recording
        print(Fore.RED + "ERROR! There is an issue setting up the packet capture!")
        if use_process == "docker" or use_process == "oc" or use_process == "kubectl":
            print(use_process + " IN USE, CONTAINER MUST BE RUN WITH USER ROOT TO RUN PACKET CAPTURE!")
        print(Style.RESET_ALL)
        child.terminate()
        exit(1)

def StopPacketCapture(child):
    pcap_exist = SendExpect(child, "cancel; top; co; no packet-capture-advanced all temporary:///capture.pcap", ['There is not a packet capture in progress', 'on all stopped\\.'])
    if pcap_exist == 0:
        PrintText(Fore.YELLOW, "Packet capture already disabled.")
        return 0
    else:
        PrintText(Fore.GREEN, "Packet capture disabled.")
        return 1

def DeleteLogTarget(child, logtargetname):
    log_target_exist = SendExpect(child, "no logging target " + logtargetname, ['.*Cannot find configuration object', '.*Configuration deleted\\.'])
    if log_target_exist == 0:
        PrintText(Fore.YELLOW, logtargetname + " logging target did not exist.")
        return 0
    else:
        PrintText(Fore.GREEN, logtargetname + " logging target removed.")
        return 1

def CheckLogTargetState(child):
    child.sendline("cancel; top; co; show logging target pmr-log")
    r = child.expect(['logging target.*\\[down.*', 'logging target.*\\[up.*'], timeout=default_timeout)
    return r

def LoopCheckTargetState(child):
    was_up = 0
    while True:
        r = CheckLogTargetState(child)
        if r == 0:
            if was_up == 1:
                PrintText(Fore.GREEN, "Network Must Gather: Log target went down!!  Use File Management to Collect Data: ")
            else:
                PrintText(Fore.YELLOW, "Log target is already down!!  Check data in File Management and assure a successful capture: ")
            print("- temporary:///capture.pcap and any capture.pcap.### iterations.")
            print("- logtemp:///pmr-log and any pmr-log.### iterations.")
            print("- logtemp:///sslkeyfile.log")
            print("- temporary:///error-report.txt.gz")
            child.terminate()
        if r == 1:
            was_up = 1
            print("Log target remains up.. waiting for log trigger to occur..")
            time.sleep(1.0)

def SendLogTargetConfig(child, overwrite, logtargetname, base_config, addtrigger=1):
    if overwrite == 1:
        SendExpect(child, "reset", "idg.*#")
    SendExpect(child, base_config, "idg.*#")

    if addtrigger == 1:
        SendExpect(child, "trigger '" + eventid + "' '" + regex_filter + "' on on 'no packet-capture-advanced all temporary:///capture.pcap; logging target pmr-log; admin-state disabled; exit;'", "idg.*#")
        SendExpect(child, "exit; loglevel debug", "idg.*#")
    PrintText(Fore.GREEN,"Log Target " + logtargetname + " is running.")

def EstablishLogTarget(child, overwrite, logtargetname, base_config, addtrigger=1):
    if overwrite == 0:
        child.sendline("co; logging target '" + logtargetname + "'")
        r = child.expect(['New Log Target configuration', 'Modify Log Target configuration'], timeout=default_timeout)
        if r == 0: #New Log Target configuration
            SendLogTargetConfig(child, overwrite, logtargetname, base_config, addtrigger)
        if r == 1: #Modify Log Target configuration
            if YesNoPrompt("Existing log target, are you sure you wish to overwrite (yes/no)?") == 1:
                EstablishLogTarget(child, 1, logtargetname, base_config, addtrigger)
            else:
                SendExpect(child, "cancel", "idg.*#")
                PrintText(Fore.RED,"Skipped overwriting log target, log target may not be running!")
    elif overwrite == 1:
        SendLogTargetConfig(child, overwrite, logtargetname, base_config, addtrigger)




def EstablishWindowsExpect():

    execCmd = getCmd4useProcess(use_process)

    if execCmd == "ssh":
       execCmd = execCmd +' '+ target
       if custom_port != 0: execCmd = execCmd +' -p '+ str(custom_port)
    elif execCmd == "plink -ssh":
       execCmd = execCmd +' '+ target
       if custom_port != 0: execCmd = execCmd +' -P '+ str(custom_port)
    elif execCmd == "telnet":
       execCmd = execCmd +' -t vt100 '+ target +' '
       if custom_port == 0:
           execCmd = execCmd + "2300"       # DP telnet defaults to port 2300
       else:
           execCmd = execCmd + str(custom_port)
    elif execCmd == "plink -telnet":
       execCmd = execCmd +' '+ target
       if custom_port == 0:
           execCmd = execCmd + " -P 2300"   # DP telnet defaults to port 2300
       else:
           execCmd = execCmd + " -P "+ str(custom_port)
    elif execCmd == "docker":
        execCmd = execCmd +' attach '+ target
    elif execCmd == "oc" or execCmd == "kubectl":
        execCmd = execCmd +' attach -it '+ target
        if namespace != "": execCmd = execCmd +' -n '+ namespace

    printDebug(Fore.GREEN, "connection command: ["+ execCmd +"]")

    child = wexpect.spawn('cmd')
    child.expect('>')
    child.sendline(execCmd)

    return child

def EstablishLogin(child, exitprocess=1):
    if platform.system() == 'Windows':
       TimeoutException = wexpect.TIMEOUT
    else:
       TimeoutException = pexpect.exceptions.TIMEOUT

    returnList = ['login:',
                  'login as:',
                  'Are you sure you want to continue connecting',
                  'Could not resolve hostname',
                  'no matching host key type found.',
                  'idg.*#',
                  'You cannot attach to a stopped container, start it first',
                  "'ssh' is not recognized as an internal or external command",
                  "'telnet' is not recognized as an internal or external command",
                  ]
    try:
       r = child.expect(returnList, timeout=default_timeout)

    except TimeoutException:
      errorMsg = f"{Fore.RED}*** ERROR: {Fore.YELLOW} Missing except reply while estabishing connection to DataPower {Style.RESET_ALL} "
      print(errorMsg)
      PrintText(Fore.YELLOW, "expect before: ["+ child.before +"]")

      if "The server's host key is not cached in the registry." in child.before:
         lines = child.before.splitlines()
         conectionCmd = lines[0]
         PrintText(Fore.GREEN, "You can try the connection method  on its own, to add the host key.")
         PrintText(Fore.GREEN, conectionCmd)
         PrintText(Fore.GREEN, " ")

      child.terminate()
      exit(1)

    if r == 0: #login: prompt
       login_usersent = 1
       child.sendline(login_username)
    elif r == 1: # login as:  we are getting the initial junk connecting to the DP
       ignoreInitialDPgorp(child, TimeoutException)
       login_usersent = 1
       child.sendline(login_username)
    elif r == 2: #Are you sure you want to continue connecting
       child.sendline('yes')
    elif r == 3: #Could not resolve hostname
       errorMsg = f"{Fore.RED}*** ERROR: {Fore.YELLOW} We failed to resolve the hostname " + target + " perhaps try the IP address instead {Style.RESET_ALL} "
       print(errorMsg)
       child.terminate()
       if exitprocess == 1:
          exit(1)
    elif r == 4: #no matching host key type found
       errorMsg = f"{Fore.RED}*** ERROR: {Fore.YELLOW} We failed to establish a connection due to key types not matching (ssh-rsa) {Style.RESET_ALL} "
       print(errorMsg)
       printSSHalgorithmInstructions()
       child.terminate()
       if exitprocess == 1:
          exit(1)
    elif r == 5: #idg.* base prompt, likely a docker/linux/kubernetes already logged in
        login_usersent = 1
        login_passwordsent = 1
        return 1
    elif r == 6: #You cannot attach to a stopped container, start it first (docker)
       errorMsg = f"{Fore.RED}*** ERROR: {Fore.YELLOW} Container ID " + target + " is a stopped container, it must be started first {Style.RESET_ALL} "
       print(errorMsg)
       child.terminate()
       if exitprocess == 1:
          exit(1)
    elif r == 7: # ssh not found
       errorMsg = f"{Fore.RED}*** ERROR: {Fore.YELLOW} ssh command not found {Style.RESET_ALL} "
       print(errorMsg)
       printSSHinstallInstructions()
       child.terminate()
       if exitprocess == 1:
          exit(1)
    elif r == 8: # telnet not found
       errorMsg = f"{Fore.RED}*** ERROR: {Fore.YELLOW} telnet command not found {Style.RESET_ALL} "
       print(errorMsg)
       child.terminate()
       if exitprocess == 1:
          exit(1)
    else: # should never get here, unless a new reply string was added, and the index not added to the esleif's
       errorMsg = f"{Fore.RED}*** ERROR: {Fore.YELLOW} except error, missing reply {Style.RESET_ALL} "
       print(errorMsg)
       PrintText(Fore.YELLOW, "expect before: ["+ child.before +"]")
       child.terminate()
       exit(1)


    r = child.expect(['login:', 'Password:'], timeout=default_timeout)
    if r == 0:
        login_usersent = 1
        child.sendline(login_username)
    if r == 1:
        login_passwordsent = 1
        child.sendline(login_password)

    r = child.expect(['Domain.*:', 'Password:', 'idg#', 'login:'], timeout=default_timeout)
    if r == 0:
        child.sendline('default')
    if r == 1:
        login_passwordsent = 1
        child.sendline(login_password)
    if r == 2:
        return 1 #no further we are logged in
    if r == 3:
        PrintText(Fore.RED,"Password failed, please try to check your credentials")
        child.terminate()
        if exitprocess == 1:
            exit(1)

    r = child.expect(['idg#', 'Domain.*:', 'login:'], timeout=default_timeout)
    if r == 1:
        child.sendline('default')
    if r == 2:
        PrintText(Fore.RED,"Password failed, please try to check your credentials")
        child.terminate()
        if exitprocess == 1:
            exit(1)
    return 1

def ignoreInitialDPgorp(child, TimeoutException):
# this function will return control after it has read the actual DP login

    # send <ENTER> to continue
    child.sendline("")

    # sometimes there is extra gorp, if a banner is defined
    secondReplies = ["login:",
                     "Access granted. Press Return to begin session.",
                    ]
    try:
       r = child.expect(secondReplies, timeout=default_timeout)
    except TimeoutException:
       PrintText(Fore.RED, "plink except login/banner missing")
       PrintText(Fore.YELLOW, "expect before: ["+ child.before +"]")
       child.terminate()
       exit(1)

    if r == 1: # continued banner
       # send <ENTER> to continue
       child.sendline("")

       try:
          r = child.expect(["login:"], timeout=default_timeout)
       except TimeoutException:
          PrintText(Fore.RED, "plink except 'login:' missing")
          PrintText(Fore.YELLOW, "expect before: ["+ child.before +"]")
          child.terminate()
          exit(1)

    return

def printSSHalgorithmInstructions():
    print("\nTo add the ssh-rsa algorithm:")
    if platform.system() == 'Windows':
       print("In a command prompt, cd to the ~/.ssh directory")
       print('If the "config" file does not exist, create it  (note: no .txt extension)')
       print('Add the following two lines to the "config" file')
       PrintText(Fore.CYAN, "HostkeyAlgorithms +ssh-rsa")
       PrintText(Fore.CYAN, "PubkeyAcceptedAlgorithms +ssh-rsa")
       print("Save the file, and retry the dpgather command")
    else:
       print("Add the following two lines to /etc/ssh/ssh_config")
       PrintText(Fore.CYAN, "HostKeyAlgorithms = +ssh-rsa  ")
       PrintText(Fore.CYAN, "PubkeyAcceptedAlgorithms = +ssh-rsa")
       print("Save the file, and retry the dpgather command")

    return

def printSSHinstallInstructions():

    if platform.system() == 'Windows':
       print("\nTo add openSSH Client:")
       print("Open the Start menu and search for Apps & Features")
       print("Select Optional Features")
       print("If you don't see OpenSSH Client, click the plus sign next to Add a feature")
       print("Select OpenSSH Client")
       print("Click Install")
       print("")
       print('Or if you have putty installed, you can use the "plink" connection type instead of "ssh"')
       print("")

    return

def printTelnetInstallInstructions():

    if platform.system() == 'Windows':
       print("\nTo add telnet:")
       print("From a command window enter the following command:")
       PrintText(Fore.Yellow, 'pkgmgr /iu:"TelnetClient"  ')
       print("")

    return



def RunShell(child):
    EstablishLogin(child)

    logged_in = 1

    if "mqtrace" in mustgather and cleanup == 0:
        result = PromptMQTraceEnabled(child)
        if result == 1:
            PrintText(Fore.GREEN, "MQ Tracing is enabled on the object.")
        elif result == 0 and YesNoPrompt("MQ Tracing is not enabled on the object, do you wish to enable mq-tracing (yes/no)?") == 1:
            SetMQTraceEnabled(child, globals()["custom_domain"], globals()["custom_object"], 1)
            PrintText(Fore.GREEN, 'MQ Trace Must Gather: Recreate the issue, make sure the whole situation has been dumped into the traces.')
            PrintText(Fore.GREEN, 'Use File Management to Collect Data After Replicating Issue:')
            print('- AMQERRxx.log files in temporary:///<domain name>/idgmq/mqobject/errors')
            print('- AMQyyy.0.TRC in temporary:////<domain name>/idgmq/mqobject/trace')
        elif result == -2:
            PrintText(Fore.RED, "Unable to find idg-mq-qm object " + custom_object + " inside of domain " + custom_domain)

    if ("cpu" in mustgather or "lldiag" in mustgather) and cleanup == 0:
        dpmon_enabled = CheckDiagEnabled(child, "dpmon")
        if dpmon_enabled == -1:
            PrintText(Fore.RED, "Check user and permissions, unable to check dpmon state")
        elif dpmon_enabled == 1:
            PrintText(Fore.YELLOW, "DPMon is already enabled")
        else:
            SetDPMonEnabled(child, "on")

        lldiag_enabled = CheckDiagEnabled(child, "lldiag")
        if lldiag_enabled == -1:
            PrintText(Fore.RED, "Check user and permissions, unable to check lldiag state")
        elif lldiag_enabled == 1:
            PrintText(Fore.YELLOW, "LLDiag is already enabled")
        elif YesNoPrompt("Do you wish to enable lldiag (yes/no)?") == 1:
            SetLLDiagEnabled(child)

    if cleanup == 0 and "cpu" in mustgather:
        PrintText(Fore.GREEN, "Beginning CPU Statistics Must Gather..")
        timer=setInterval(capture_interval,CollectStatisticMustGather)
        t=threading.Timer(capture_time,timer.cancel)
        t.start()

    if cleanup == 0:
        if "latency" in mustgather and YesNoPrompt("Setup extended latency log target (yes/no)? ") == 1:
            EstablishLogTarget(child, 0, "ExtLatencyLogTarget", "type file; format text; size 50000; rotate 3; local-file 'logtemp:///Latencylog.txt'; event latency info; event extlatency info; exit;", 0)
            PrintText(Fore.GREEN, "Extended Latency Log Target added.")

        if "network" in mustgather and YesNoPrompt("Begin packet capture (yes/no)? ") == 1:
            StartPacketCapture(child, 0)
            EstablishLogTarget(child, 0, "pmr-log", "type file; format text; size 15000; local-file 'logtemp:///pmr-log'; rotate 3; event all debug;", 1)

        if "peering" in mustgather:
           rc = doPeeringMustGather(child)

        if "network" in mustgather:
            LoopCheckTargetState(child)

    if "rbm" in mustgather and cleanup == 0:
        rbm_log_on = IsRBMLoggingOn(child)
        if rbm_log_on == 0 and YesNoPrompt("Would you like to enable RBM debugging, please note this can take some time to complete (yes/no)?") == 1:
            SetRBMLoggingOn(child)
        elif rbm_log_on == 1:
            PrintText(Fore.YELLOW, "RBM debugging is already enabled.")

        if "network" in mustgather:
            PrintText(Fore.YELLOW, "RBM Must Gather: As Network Must Gather is also selected, packet capture will be staged through that must gather.")
        else:
            StartPacketCapture(child, 0)
            if YesNoPrompt("Confirm the RBM issue is replicated to stop the capture (yes/no)? ", 1) == 1:
                StopPacketCapture(child)
                report_name = SaveErrorReport(child)
                PrintText(Fore.GREEN, "RBM Must Gather, use File Management to Collect Data: ")
                print("- temporary:///capture.pcap and any capture.pcap.### iterations.")
                print("- logtemp:///sslkeyfile.log")
                print("- " + report_name)
            
    if cleanup == 1:
        RunCleanup(child, 1)
        child.terminate()
        exit(0)

    SendExpect(child, "top; exit", [ '.*'])

def OpenDockerShell():
    container_id = ""
    try:
        cmd_exec = subprocess.check_output([use_process, 'ps'], encoding='UTF-8')
        reMatch = re.compile('([a-zA-Z0-9]{12})\\s+([a-zA-Z0-9]{12})\\s+\"/opt/ibm/datapower/')
        matchResult = reMatch.search(cmd_exec)
        if matchResult is not None:
            print("Container ID: " + matchResult.group(1))
            cmd_exec2 = subprocess.check_output([use_process, 'images'], encoding='UTF-8')
            reMatch2 = re.compile('(.*)\\s+[a-zA-Z\\-0-9\\.]+\\s+' + matchResult.group(2))
            matchResult2 = reMatch2.search(cmd_exec2)
            print("Image ID and Container: " + matchResult2.group(0))
            if YesNoPrompt("Is this the correct container id and image id (yes/no)? ") == 1:
                container_id = matchResult.group(1)
            else:
                container_id = PromptForInput('Container ID: ')
        else:
            print("Could not find container, please specify container id:\n")
            container_id = PromptForInput('Container ID: ')
        return container_id
    except FileNotFoundError:
        PrintText(Fore.RED, "Could not open process " + use_process)
        return 0
    return 0

def RunChildProcess():
    try:
        #Run Main Process
        if platform.system() == 'Windows':
            child = EstablishWindowsExpect()
            return child
        else:
            if use_process == "telnet":
                telnet_port = 2300
                if custom_port != 0:
                    telnet_port = custom_port
                exec_cmd = use_process + ' ' + target + ' ' + str(telnet_port)
                child = pexpect.spawn(exec_cmd)
            elif use_process == "docker":
                child = pexpect.spawn(use_process + ' attach ' + target)
                child.sendline("\n")
            elif use_process == "oc" or use_process == "kubectl":
                exec_cmd = use_process + ' attach -it ' + target
                if namespace != "":
                    exec_cmd = exec_cmd + ' -n ' + namespace
                child = pexpect.spawn(exec_cmd)
                child.sendline(" \n")
            else: #ssh
                exec_cmd = use_process + ' ' + target
                if custom_port != 0:
                    exec_cmd = exec_cmd + ' -p ' + str(custom_port)
                child = pexpect.spawn(exec_cmd)
            return child
    except KeyboardInterrupt:
        if logged_in == 1 and YesNoPrompt("Attempt cleanup of log target (yes/no)? ") == 1:
            RunCleanup(child)
    except FileNotFoundError:
        PrintText(Fore.RED, "Could not open process " + use_process)




#Run Process
if use_process == 'docker' and target == '':
    target = OpenDockerShell()
    if target == 0:
        exit(1)
elif target == "":
    target = PromptForInput('Hostname/Container Name (dpgateway.myhost.com): ')

if ((use_process == 'kubectl') or (use_process == 'oc')):
    if (namespace == ''):
       namespace = PromptForInput('namespace: ')

if "network" in mustgather and eventid == '0x0' and not args.cleanup:
    eventid = PromptForInput('Event ID Trigger (0x12345678): ')

if login_username == "":
    login_username = PromptForInput('Username: ')

if login_password == "":
    login_password = getpass.getpass(prompt='Password: ', stream=None)

child = RunChildProcess()
RunShell(child)
child.terminate()

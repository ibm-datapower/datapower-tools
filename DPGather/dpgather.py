#! /usr/bin/env python3
#IBM DataPower Support 2024 Automation Tool v1.01 - Dominic Micale dmmicale (at) us.ibm.com
#Python3 required, Python 3.11 (Linux) and 3.12 (Windows) tested
#Visit https://www.ibm.com/support/pages/node/7145056 for latest mustgather tool
#1) Establish package libraries for required packages
#2) Connect using SSH or Telnet (native to linux only -- could support windows, but windows does not have telnet by default)
#3) Enable a variety of must gathers, involving commands, configuration of objects
#4) Provide a cleanup to disable must gather, remove debug configuration objects and changes.

#apt-get install pip
#pip install wexpect pexpect setuptools colorama inquirer

#may alternatively need this:
#pip install wexpect pexpect setuptools colorama inquirer --break-system-packages
import platform
import time
import sys
import subprocess
import importlib
import importlib.metadata
import argparse
import re
import threading

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
parser.add_argument('-m', '--mustgather', nargs='+', help="mustgathers |network|lldiag|mqtrace|rbm|cpu|latency")
parser.add_argument('-cd', '--customdomain', help="domain used for mqtrace to specify where the idg-mq-qm object resides")
parser.add_argument('-co', '--customobject', help="object used for mqtrace")
parser.add_argument('-ci', '--captureinterval', help="capture interval for CPU must gather CLI captures")
parser.add_argument('-ct', '--capturetime', help="Total capture time for CPU must gather CLI captures")
parser.add_argument('-cp', '--customport', help="Used to specify a custom telnet or SSH port to connect")

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

#flags/static vars
login_usersent = 0
login_passwordsent = 0
default_timeout = 30
logged_in = 0

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

if not args.use_process:
	in_message = "DataPower: What platform/endpoint are we connecting to?"
	platform_selection = [
		inquirer.List('datapowerplatform',
			message=in_message,
			choices=['ssh', 'telnet', 'docker', 'oc', 'kubectl'],
		),
		]
	results = inquirer.prompt(platform_selection)
	use_process = results['datapowerplatform']   

if not args.mustgather:
	in_message = "DataPower: What must gathers are to be staged (use spacebar to select, enter submits)?"
	if args.cleanup and int(args.cleanup) == 1:
		in_message = "DataPower: What must gathers are to be cleaned up (use spacebar to select, enter submits)?"
	mustgather_selection = [
		inquirer.Checkbox('datapowermustgathers',
			message=in_message,
			choices=['network', 'lldiag', 'mqtrace', 'rbm', 'cpu', 'latency'],
		),
		]
	results = inquirer.prompt(mustgather_selection)
	mustgather = results['datapowermustgathers']    

def PromptForInput(message):
	print(message)
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

def PrintText(color, text):
	print(color + text)
	print(Style.RESET_ALL)

def SendExpect(child, send_data, expect_data, custom_timeout=60):
	child.sendline(send_data)
	r = child.expect(expect_data, timeout=custom_timeout)
	return r

def CheckFileDirExists(child, directory, filedirname, minsize):
	r = SendExpect(child, "cancel; top; co", [ 'idg\\(config\\)#', 'idg#'])
	if r == 0:
		wildcard_filename = '.*' + filedirname + '.*'
		wildcard_match = '.*available to ' + directory + '.*'
		found = SendExpect(child, "dir " + directory, [ wildcard_filename, wildcard_match])
		if found == 0: # matched wildcard filename
			return 1
		else: #did not find file only the directory size
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
	r = SendExpect(child, "get-system-var var://system/map/debug", [ '[3-9]+', '[0-2]', 'idg.#'], 120)
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
	child = wexpect.spawn('cmd')
	child.expect('>')

	exec_cmd = use_process + ' ' + target
	if custom_port != 0:
		if use_process == "ssh":
			exec_cmd = exec_cmd + ' -p ' + str(custom_port)
		elif use_process == "telnet":
			exec_cmd = exec_cmd + ' ' + str(custom_port)
		elif use_process == "docker":
			exec_cmd = use_process + ' attach ' + target
		elif use_process == "oc" or use_process == "kubectl":
			exec_cmd = use_process + ' attach -it ' + target
			if namespace != "":
				exec_cmd = exec_cmd + ' -n ' + namespace
	child.sendline(exec_cmd)
	return child

def EstablishLogin(child, exitprocess=1):
	r = child.expect(['login:', 'Are you sure you want to continue connecting', 'Could not resolve hostname', 'no matching host key type found.', 'idg.*#', 'You cannot attach to a stopped container, start it first'], timeout=default_timeout)
	if r == 0: #login: prompt
		login_usersent = 1
		child.sendline(login_username)
	if r == 1: #Are you sure you want to continue connecting
		child.sendline('yes')
	if r == 2: #Could not resolve hostname
		PrintText(Fore.RED, "We failed to resolve the hostname " + target + " perhaps try the IP address instead")
		child.terminate()
		if exitprocess == 1:
			exit(1)
	if r == 3: #no matching host key type found
		PrintText(Fore.RED,"We failed to establish a connection due to key types not matching, modify /etc/ssh/ssh_config to include:")
		print("HostKeyAlgorithms = +ssh-rsa")
		print("PubkeyAcceptedAlgorithms = +ssh-rsa")
		child.terminate()
		if exitprocess == 1:
			exit(1)
	if r == 4: #idg.*# base prompt, likely a docker/linux/kubernetes already logged in
		login_usersent = 1
		login_passwordsent = 1
		return 1
	if r == 5: #You cannot attach to a stopped container, start it first (docker)
		PrintText(Fore.RED,"Container ID " + target + " is a stopped container, it must be started first")
		child.terminate()
		if exitprocess == 1:
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

def SaveErrorReport(child):
	r = SendExpect(child, "top; co; save error-report; top", "check the logs for the final result")
	reMatch = re.compile('(([a-zA-Z0-9\\._]+):///error\\-report\\.[0-9]+\\.[0-9a-zA-Z]{18,23}\\.txt\\.gz)')
	matchResult = reMatch.search(str(child.before))
	if matchResult is not None:
		return matchResult.group(0)
	return "temporary:///error-report.txt.gz"

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

	if "latency" in mustgather and YesNoPrompt("Setup extended latency log target (yes/no)? ") == 1:
		EstablishLogTarget(child, 0, "ExtLatencyLogTarget", "type file; format text; size 50000; rotate 3; local-file 'logtemp:///Latencylog.txt'; event latency info; event extlatency info; exit;", 0)
		PrintText(Fore.GREEN, "Extended Latency Log Target added.")

	if "network" in mustgather and YesNoPrompt("Begin packet capture (yes/no)? ") == 1:
		StartPacketCapture(child, 0)
		EstablishLogTarget(child, 0, "pmr-log", "type file; format text; size 15000; local-file 'logtemp:///pmr-log'; rotate 3; event all debug;", 1)

	if "cpu" in mustgather:
		PrintText(Fore.GREEN, "Beginning CPU Statistics Must Gather..")
		timer=setInterval(capture_interval,CollectStatisticMustGather)
		t=threading.Timer(capture_time,timer.cancel)
		t.start()

	if "network" in mustgather:
		LoopCheckTargetState(child)

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
				child = pexpect.spawn(use_process + ' ' + target + ' ' + str(telnet_port))
			elif use_process == "docker":
				child = pexpect.spawn(use_process + ' attach ' + target)
				child.sendline("\n")
			elif use_process == "oc" or use_process == "kubectl":
				exec_cmd = use_process + ' attach -it ' + target
				if namespace != "":
					exec_cmd = exec_cmd + ' -n ' + namespace
				child = pexpect.spawn(exec_cmd) # todo add namespace
				child.sendline("\n")
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

if "network" in mustgather and eventid == '0x0' and not args.cleanup:
	eventid = PromptForInput('Event ID Trigger (0x12345678): ')

if login_username == "":
	login_username = PromptForInput('Username: ')
    
if login_password == "":
	login_password = getpass.getpass(prompt='Password: ', stream=None) 
    
child = RunChildProcess()
RunShell(child)
child.terminate()
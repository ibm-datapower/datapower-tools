# IBM DataPower Support 2025 DataPower File Manager: dpfilemgr.py

## Pre-Requisites

- **Python3 3.13+** (Tested)

## Deployment Instructions

1.  Download the tool using the following command:
```shell command: curl -L -O https://raw.githubusercontent.com/ibm-datapower/datapower-tools/master/DPFileMgr/dpfilemgr.py```
2.  Run the tool using the command **`python3 dpfilemgr.py --url https://dpip --port 5554 --user user --password password`**.
3.  Additional arguments:
	- --domain : Specify a sub-domain, the default is the "default" domain.
	- --subdir : Specify a sub-directory within the domain, such as local, temporary, logtemp
	- --download-all : Automatically downloads all files without prompting for a numerical or range of files to download.
	- --upload-path : Specify a local file or directory with files to create, upload or replace on the DataPower based on the domain and subdir specified.
	- --overwrite : Overwrite existing files when uploading
	- --skip-ssl : Skip SSL certificate validation
## Need help?

-  Open a ticket with IBM Support in the IBM DataPower product
-  If you do not have access to IBM Support, report an issue to submit any feedback

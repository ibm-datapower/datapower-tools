# How to Use
## Pre-requisites
* genisoimage
* xsltproc
* ovftool


You will need to generate an ovf-env.xml for your machine using gen_ovf_env.sh and redirecting the output to a file. Before running this set the following env variables
ADMIN_PASSWORD
PRIVATE_IP
PRIVATE_NETMASK
PRIVATE_GATEWAY
SEARCH_DOMAIN
NAME_SERVER
An example ovf-env.xml is in the tar as well set up for our lab. Hand edit it if you want changing the values as necessary.
 
Running deploy_ova.sh without options gives a list of all available options with their defaults if they are left out. Also explains what each option is. Most of the options are passed to ovftool unaltered. All files need to exist on the machine where the script is being run from, it isn't smart enough to fetch the OVA from a remote http server. 
### WARNING: This script will overwrite the VM VMname if it already exists. All below invocations will reserve the memory in addition to allocating it to reduce possibility of memory overcommit
 
To deploy with specifying memory and CPU allocation

    ./deploy_ova.sh -c /absolute/path/to/ovf-env.xml -o custom -M <MemoryInMB> -C <#vCPU> -d <DatastoreToStoreIn> -m thin -0 <vSwitchName> -1 <vSwitchName> -2 <vSwitchName> -3 <vSwitchName> /absolute/path/to/ova vi://user:password@esxiIP <VMName>
To deploy using one of the canned resource options

    ./deploy_ova.sh -c /absolute/path/to/ovf-env.xml -o <small|medium|enterprise> -d <DatastoreToStoreIn> -m thin -0 <vSwitchName> -1 <vSwitchName> -2 <vSwitchName> -3 <vSwitchName> /absolute/path/to/ova vi://user:password@esxiIP <VMName>

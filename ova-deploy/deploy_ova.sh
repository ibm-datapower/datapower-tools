#!/bin/bash
set -e

usage() {
cat <<EOF
	usage: $0 [options] ova target name
	ova: path to OVA file
	options:
		-c path to config file 
		-o deployment option (defaults to small)
		-M amount of RAM
		-C number of vCPUs 
        -D comma separated list of interfaces to disable
		-d datastore to create VM on (defaults to 'datastore1')
		-m disk mode (defaults to thin)	
		-0 Network for eth0 (Defaults to VM Network)
		-1 Network for eth1 (Defaults to VM Network)
		-2 Network for eth2 (Defaults to VM Network)
		-3 Network for eth3 (Defaults to VM Network)
EOF
}

if [ $# -lt 5 ]; then
	usage
	exit 1
fi

# set defaults
DISK_MODE=thick
DEPLOYMENT=small
NET0="VM Network"
NET1="VM Network"
NET2="VM Network"
NET3="VM Network"
DATASTORE=datastore1
MEMSIZE=16384
NUMCPUS=16
DISABLEDETHSLIST=()


echo '<?xml version="1.0" encoding="utf-8"?>' >> deployParamFile.xml
echo '<DeploymentParameters>' >> deployParamFile.xml
echo '<Disable>' >> deployParamFile.xml

while getopts "c:d:m:o:M:C:D:0:1:2:3:" OPTION
do
     case $OPTION in
         c)      
            CONFIG=$OPTARG
             ;;
         d)      
            DATASTORE=$OPTARG
             ;;   
         o)      
            DEPLOYMENT=$OPTARG
             ;;
         M)
            MEMSIZE=$OPTARG
             ;;
         C)
            NUMCPUS=$OPTARG
             ;;
         D)
            IFS=","
            read -ra ETHARRAY <<<"$OPTARG"
            for eth in "${ETHARRAY[@]}"; do
                #DISABLEDETHSLIST+=("--stringparam" "disable$eth" "true")
                echo "<EthernetInterface>network.${eth}.caption</EthernetInterface>" >> deployParamFile.xml
            done
             ;;
         m)      
            DISK_MODE=$OPTARG
             ;;
         0)      
            NET0=$OPTARG
             ;;
         1)      
            NET1=$OPTARG
             ;;
         2)      
            NET2=$OPTARG
             ;; 
         3)      
            NET3=$OPTARG
             ;;        
         ?)
             usage
             exit
             ;;
     esac
done
shift $(($OPTIND - 1))
OVA=$1
TARGET=$2
NAME=$3
echo '</Disable>' >> deployParamFile.xml
echo '</DeploymentParameters>' >> deployParamFile.xml


echo "Extracting OVA..."
rm -rf extract
mkdir extract
mv deployParamFile.xml extract	
(cd extract && tar xf $OVA)

if [ "$CONFIG" != "" ]; then
	echo "Generating ISO..."
	rm -rf activation
	mkdir activation
	cp $CONFIG activation/ovf-env.xml
	# create ISO 
	genisoimage -quiet -iso-level 4 -o activation.iso activation
	rm -rf activation	
	# move ISO into root of OVA
	mv activation.iso extract/.

	echo "Adding CD-ROM to OVF..."
	# modify OVF to have ISO attached as CD-ROM, i.e. add ISO file ref, add drive with ref to file
	OVF=`ls extract/*.ovf`
	    xsltproc --stringparam file activation.iso --stringparam size `stat -c%s extract/activation.iso` --stringparam numVCPUs $NUMCPUS --stringparam memsize $MEMSIZE attach_iso_as_cdrom.xsl $OVF > $OVF.new
	mv $OVF.new $OVF	
	
	# TODO: update manifest instead of deleting
	# delete manifest since it is no longer accurate
	rm extract/*.mf
fi

if [ "x${CUSTOMER_NAME}" != "x" ]; then
  CUSTOMER_NAME="_${CUSTOMER_NAME}"
fi

echo "Importing OVA..."
# now import the OVA
ovftool --quiet --skipManifestCheck --noSSLVerify --deploymentOption=$DEPLOYMENT --diskMode=$DISK_MODE --datastore=$DATASTORE --acceptAllEulas --name=$NAME${CUSTOMER_NAME} "--net:eth0=$NET0" "--net:eth1=$NET1" "--net:eth2=$NET2" "--net:eth3=$NET3" --powerOn --powerOffTarget --overwrite $OVF $TARGET
rm -rf extract

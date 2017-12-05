#!/bin/bash
set -e
PRIVATE_INTERFACE=eth0
if [ $# -eq 1 ]; then
    PRIVATE_INTERFACE=$1
fi
cat <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<Environment xmlns="http://schemas.dmtf.org/ovf/environment/1" xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1" xmlns:ovfenv="http://schemas.dmtf.org/ovf/environment/1" xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData" xmlns:vssd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_VirtualSystemSettingData" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ovf:id="DataPowerVirtualAppliance">
	<PropertySection>
	<Property ovfenv:key="ConfigPWD_ROOT.password" ovfenv:value="${ADMIN_PASSWORD}"/>
	<Property ovfenv:key="ConfigSSH.enabled" ovfenv:value="true"/>
	<Property ovfenv:key="ConfigSSH.port" ovfenv:value="22"/>
	<Property ovfenv:key="ConfigSOMA.enabled" ovfenv:value="true"/>
	<Property ovfenv:key="ConfigSOMA.port" ovfenv:value="5550"/>
	<Property ovfenv:key="ConfigWebGui.enabled" ovfenv:value="true"/>
	<Property ovfenv:key="ConfigWebGui.port" ovfenv:value="9090"/>
	<Property ovfenv:key="ConfigRAID.directory" ovfenv:value="raid0"/>

	<Property ovfenv:key="ConfigNET.iface_name.1" ovfenv:value="${PRIVATE_INTERFACE}"/>
	<Property ovfenv:key="ConfigNET.bootproto.1" ovfenv:value="static"/>
	<Property ovfenv:key="ConfigNET.ipaddr.1" ovfenv:value="${PRIVATE_IP}"/>
	<Property ovfenv:key="ConfigNET.netmask.1" ovfenv:value="${PRIVATE_NETMASK}"/>
	<Property ovfenv:key="ConfigNET.gateway.1" ovfenv:value="${PRIVATE_GATEWAY}"/>
	
	<Property ovfenv:key="ConfigNET.domain.1" ovfenv:value="$SEARCH_DOMAIN"/>
	<Property ovfenv:key="ConfigNET.pri_dns.1" ovfenv:value="$NAME_SERVER"/>
	<Property ovfenv:key="SecureBackupRestore.mode" ovfenv:value="secure"/>
	<Property ovfenv:key="ConfigNTP.ntp_0" ovfenv:value="0.pool.ntp.org"/>
	</PropertySection>
</Environment>
EOF

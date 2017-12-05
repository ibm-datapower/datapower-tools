<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" 
	xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1"
	xmlns:rasd="http://schemas.dmtf.org/wbem/wscim/1/cim-schema/2/CIM_ResourceAllocationSettingData">

<xsl:param name="file">UNKNOWN_FILE</xsl:param>
<xsl:param name="size">UNKNOWN_SIZE</xsl:param>
<xsl:param name="numVCPUs">8</xsl:param>
<xsl:param name="memsize">16384</xsl:param>

<xsl:output method="xml" encoding="UTF-8" indent="yes"/>

<xsl:template match="* | @* | node()">
    <xsl:copy>
        <xsl:apply-templates select="* | @* | node()"/>
    </xsl:copy>
</xsl:template>

<xsl:template match="ovf:DeploymentOptionSection">
    <xsl:copy>
        <xsl:apply-templates select="* | @* | node()"/>
        <xsl:element name="ovf:Configuration">
            <xsl:attribute name="ovf:id">custom</xsl:attribute>
            <xsl:element name="ovf:Label">Custom Sized Deployment</xsl:element>
            <xsl:element name="ovf:Description">Custom Sized Deployment</xsl:element>
        </xsl:element>
    </xsl:copy>
</xsl:template>

<xsl:template match="ovf:VirtualSystem/ovf:VirtualHardwareSection">
    <xsl:copy>
        <xsl:apply-templates select="* | @* | node()"/>
        <!--<xsl:apply-templates select="*"/>-->
        <xsl:element name="ovf:Item">
            <xsl:attribute name="ovf:configuration">custom</xsl:attribute>
            <xsl:element name="rasd:Caption"><xsl:value-of select="$numVCPUs"/> virtual CPU(s)</xsl:element>
            <xsl:element name="rasd:Description"><xsl:value-of select="$numVCPUs"/> virtual CPU(s)</xsl:element>
            <xsl:element name="rasd:ElementName"><xsl:value-of select="$numVCPUs"/> virtual CPU(s)</xsl:element>
            <xsl:element name="rasd:InstanceID">23</xsl:element>
            <xsl:element name="rasd:ResourceType">3</xsl:element>
            <xsl:element name="rasd:VirtualQuantity"><xsl:value-of select="$numVCPUs"/></xsl:element>
        </xsl:element>
        <xsl:element name="ovf:Item">
            <xsl:attribute name="ovf:configuration">custom</xsl:attribute>
            <xsl:element name="rasd:AllocationUnits">MegaBytes</xsl:element>
            <xsl:element name="rasd:Caption"><xsl:value-of select="$memsize"/> MB of RAM</xsl:element>
            <xsl:element name="rasd:Description"><xsl:value-of select="$memsize"/> MB of RAM</xsl:element>
            <xsl:element name="rasd:ElementName"><xsl:value-of select="$memsize"/> MB of RAM</xsl:element>
            <xsl:element name="rasd:InstanceID">24</xsl:element>
            <xsl:element name="rasd:Reservation"><xsl:value-of select="$memsize"/></xsl:element>
            <xsl:element name="rasd:ResourceType">4</xsl:element>
            <xsl:element name="rasd:VirtualQuantity"><xsl:value-of select="$memsize"/></xsl:element>
        </xsl:element>
        <xsl:element name="ovf:Item">
            <xsl:element name="rasd:Address">1</xsl:element>
            <xsl:element name="rasd:Description">IDE Controller</xsl:element>
            <xsl:element name="rasd:ElementName">IDE 0</xsl:element>
            <xsl:element name="rasd:InstanceID">21</xsl:element>
            <xsl:element name="rasd:ResourceType">5</xsl:element>
        </xsl:element>
        <xsl:element name="ovf:Item">
            <xsl:element name="rasd:AddressOnParent">0</xsl:element>
            <xsl:element name="rasd:AutomaticAllocation">true</xsl:element>
            <xsl:element name="rasd:ElementName">CD-ROM</xsl:element>
            <xsl:element name="rasd:HostResource">ovf:/file/activation.iso</xsl:element>
            <xsl:element name="rasd:InstanceID">22</xsl:element>
            <xsl:element name="rasd:Parent">21</xsl:element>
            
<xsl:element name="rasd:ResourceType">15</xsl:element>        
            
        </xsl:element>       
    </xsl:copy>
</xsl:template>


<!-- Disable Eths for Secure Restore -->
<xsl:template match="rasd:Caption[@ovf:msgid=document('extract/deployParamFile.xml')/DeploymentParameters/Disable/EthernetInterface]">
        <xsl:element name="rasd:AutomaticAllocation">false</xsl:element>
        <xsl:copy-of select="."/>
</xsl:template> 


<!-- Add file reference -->
<xsl:template match="ovf:References">
    <xsl:copy>
        <xsl:apply-templates select="* | @* | node()"/>
        <xsl:element name="ovf:File">
            <xsl:attribute name="ovf:href"><xsl:value-of select="$file"/></xsl:attribute>
            <xsl:attribute name="ovf:id"><xsl:value-of select="$file"/></xsl:attribute>
            <xsl:attribute name="ovf:size"><xsl:value-of select="$size"/></xsl:attribute>
        </xsl:element>        
    </xsl:copy>
</xsl:template>



</xsl:stylesheet>

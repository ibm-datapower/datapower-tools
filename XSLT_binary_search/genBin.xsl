<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:func="http://exslt.org/functions" xmlns:exslt="http://exslt.org/common" exclude-result-prefixes="exslt" >
    <xsl:output omit-xml-declaration="yes" method="xml" />
    <func:function name="func:gen">
        <xsl:param name="es" />
	<xsl:param name="nf" />
	<xsl:variable name="l" select="count($es)"/>
	<func:result>
    	    <xsl:choose>
		<xsl:when test="$l &gt; 0">
		    <xsl:variable name="mid" select="floor(($l + 1) div 2)"/>
		    <xsl:element name="xsl:choose">
			<xsl:element name="xsl:when">
			    <xsl:attribute name="test">$x &lt; <xsl:value-of select="$es[$mid]/@min" /></xsl:attribute>
			    <xsl:copy-of select="func:gen($es[position() &lt; $mid], $nf)" />
	                </xsl:element>
			<xsl:element name="xsl:when">
			    <xsl:attribute name="test">$x > <xsl:value-of select="$es[$mid]/@max" /></xsl:attribute>
			    <xsl:copy-of select="func:gen($es[position() &gt; $mid], $nf)" />
			</xsl:element>
			<xsl:element name="xsl:otherwise">
			    <xsl:element name="func:result">
			        <xsl:attribute name="select">'<xsl:value-of select="$es[$mid]/@value" />'</xsl:attribute>
		            </xsl:element>
		        </xsl:element>
	            </xsl:element>
    	        </xsl:when>
		<xsl:otherwise>
		    <xsl:element name="func:result">
		        <xsl:attribute name="select">'<xsl:value-of select="$nf"/>'</xsl:attribute>
                    </xsl:element>
                </xsl:otherwise>
           </xsl:choose>
        </func:result>
    </func:function>     

    <xsl:template match="/*">
        <xsl:variable name="notFound" select="'-'"/>
        <xsl:variable name="sorted">
            <xsl:for-each select="*">
                <xsl:sort select="@min" data-type="number"/>
                <xsl:copy-of select="."/>
            </xsl:for-each>
        </xsl:variable>
        <xsl:element name="xsl:stylesheet">
            <xsl:attribute name="version">1.0</xsl:attribute>
            <func:function name="xsl:rangeLookup">
                <xsl:element name="xsl:param">
                    <xsl:attribute name="name">x</xsl:attribute>
                </xsl:element>
                <xsl:copy-of select="func:gen(exslt:node-set($sorted)/*,$notFound)" />
            </func:function>
            <xsl:element name="xsl:template">
                <xsl:attribute name="match">/*/*</xsl:attribute>
                <xsl:element name="xsl:value-of">
                    <xsl:attribute name="select">xsl:rangeLookup(.)</xsl:attribute>
                </xsl:element>
            </xsl:element>
        </xsl:element>
    </xsl:template>
</xsl:stylesheet>

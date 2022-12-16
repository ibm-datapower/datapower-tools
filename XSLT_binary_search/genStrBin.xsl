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
			    <xsl:attribute name="test"><xsl:value-of select="concat('xsl:strcmp($x, ', $es[$mid]/@min, ') = -1')"/></xsl:attribute>
			    <xsl:copy-of select="func:gen($es[position() &lt; $mid], $nf)" />
	                </xsl:element>
			<xsl:element name="xsl:when">
			    <xsl:attribute name="test"><xsl:value-of select="concat('xsl:strcmp($x, ', $es[$mid]/@max, ') = 1')"/></xsl:attribute>
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
                <xsl:sort select="@min" data-type="text"/>
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

            <func:function name="xsl:strcmp">
                <xsl:element name="xsl:param">
                    <xsl:attribute name="name">a</xsl:attribute>
                </xsl:element>
                <xsl:element name="xsl:param">
                    <xsl:attribute name="name">b</xsl:attribute>
                </xsl:element>
		<xsl:element name="func:result">
		    <xsl:element name="xsl:choose">
		        <xsl:element name="xsl:when">
                            <xsl:attribute name="test">$a = $b</xsl:attribute>
                            <xsl:value-of select="0"/>
                        </xsl:element>
		        <xsl:element name="xsl:otherwise">
		            <xsl:element name="xsl:variable">
                                <xsl:attribute name="name">s</xsl:attribute>
			        <e><xsl:element name="xsl:copy-of">
                                       <xsl:attribute name="select">$a</xsl:attribute>
                                   </xsl:element></e>
			        <e><xsl:element name="xsl:copy-of">
                                       <xsl:attribute name="select">$b</xsl:attribute>
                                   </xsl:element></e>
		            </xsl:element>
                            <xsl:element name="xsl:variable">
                                <xsl:attribute name="name">sorted</xsl:attribute>
                                <xsl:element name="xsl:for-each">
                                    <xsl:attribute name="select">$s/*</xsl:attribute>
                                    <xsl:element name="xsl:sort">
                                        <xsl:attribute name="select">text()</xsl:attribute>
                                        <xsl:attribute name="data-type">text</xsl:attribute>
                                    </xsl:element>
                                    <xsl:element name="xsl:copy-of">
                                        <xsl:attribute name="select">.</xsl:attribute>
                                    </xsl:element>
                                </xsl:element>
                            </xsl:element>
                            <xsl:element name="xsl:choose">
                                <xsl:element name="xsl:when">
                                    <xsl:attribute name="test">$sorted/*[1] = $a</xsl:attribute>
                                    <xsl:value-of select="-1"/>
                                </xsl:element>
                                <xsl:element name="xsl:otherwise">
                                    <xsl:value-of select="1"/>
                                </xsl:element>
                            </xsl:element>
                        </xsl:element>
                    </xsl:element>
                </xsl:element>
            </func:function>

            <xsl:element name="xsl:template">
                <xsl:attribute name="match">/*/*</xsl:attribute>
                <xsl:element name="xsl:value-of">
                    <xsl:attribute name="select">xsl:rangeLookup(text())</xsl:attribute>
                </xsl:element>
            </xsl:element>
	</xsl:element>

    </xsl:template>
</xsl:stylesheet>

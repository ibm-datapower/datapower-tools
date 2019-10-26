<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:dp="http://www.datapower.com/extensions"
  extension-element-prefixes="dp"
>
  <xsl:output omit-xml-declaration="yes" />
    
  <xsl:template match="/">
   <out>
    <xsl:copy-of select="."/>
    <xsl:copy-of select="."/>
   </out>
  </xsl:template>
  
</xsl:stylesheet>

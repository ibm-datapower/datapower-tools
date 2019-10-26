<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:dp="http://www.datapower.com/extensions"
  extension-element-prefixes="dp"
>
  <dp:input-mapping  href="store:///pkcs7-convert-input.ffd" type="ffd"/>

  <xsl:output omit-xml-declaration="yes" />
    
  <xsl:template match="/">
    <xsl:variable name="input64"
      select="dp:binary-encode(/object/message/node())"
    />
    <xsl:value-of 
      select="substring(dp:radix-convert(concat('////',$input64), 64, 16), 7)"
    />
  </xsl:template>
  
</xsl:stylesheet>

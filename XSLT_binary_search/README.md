# XSLT binary search

XPath evaluation is done linear, with linear time complexity.  
If for a big number (eg. 20000) ranges it needs to be determined, which range a number falls into, this can be better solved (with logarithmic time complexity) with "binary search".  
Stylesheet genBin.xsl creates a binary search stylesheet from a range input file:  

    $ cat x7.xml 
    <es>
      <e min="1926" max="1990" value="G" />
      <e min="1901" max="1905" value="F" />
      <e min="1521" max="1825" value="E" />
      <e min="1001" max="1010" value="A" />
      <e min="1021" max="1115" value="B" />
      <e min="1131" max="1235" value="C" />
      <e min="1246" max="1248" value="D" />
    </es>
    $ 

This is how binary search stylesheet gets created:

    $ coproc2 genBin.xsl x7.xml http://dp3-l3.boeblingen.de.ibm.com:2223 2>/dev/null >x7.xsl
    $

It can be imported, and "xsl:rangeLookup(\_)" can be used.  
Alternatively you can use the little test template of x7.xsl:  

    $ coproc2 x7.xsl <(echo "<x><y>1000</y><y>1001</y><y>1010</y><y>1011</y><y>1950</y></x>") http://dp3-l3.boeblingen.de.ibm.com:2223; echo
    -AA-G
    $ 


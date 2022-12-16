# XSLT binary search

XPath evaluation is done linear, with linear time complexity.  
Binary search with logarithmic time complexity can help here to reduce DataPower XLST latency.  
DataPower's XSLT 1.0 processor allows for comparison of numbers, see first section for an appplication.  
XSLT 1.0 does not allow for string comparison other than equality and inequality, see second section for an application dispite that.  

The examples make use of coproc2 tool, which is documented here:  
[https://github.com/ibm-datapower/datapower-tools/tree/master/coproc2](https://github.com/ibm-datapower/datapower-tools/tree/master/coproc2)

# Efficient number range search

If for a big number (eg. 20000) of ranges it needs to be determined, which range a (more than 8-digit) number falls into, this can be better solved (with logarithmic time complexity) with "binary search".
This leads to 15 layers of comparisons in generated stylesheet, compared to 20000/2=10000 XPath matches on average in stated example.    

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
Alternatively you can use the [little test template of x7.xsl](https://github.com/ibm-datapower/datapower-tools/blob/master/XSLT_binary_search/genBin.xsl#L52-L57):  

    $ coproc2 x7.xsl <(echo "<x><y>1000</y><y>1001</y><y>1010</y><y>1011</y><y>1950</y></x>") http://dp3-l3.boeblingen.de.ibm.com:2223; echo
    -AA-G
    $ 


# Efficient string range search

My rule of thumb is this:  
- for processing XML, use XSLT and XPath
- for processing JSON or binary data, use GatewayScript

Many customers use big routing XML files for decision against which backend to go.  
As said, if there are many entries in that XML file, on average half of the entries need to be matched.  
Here binary search could help, if XSLT 1.0 would allow for full string comparison.  
Generated function [xsl:strcmp(a, b)](https://github.com/ibm-datapower/datapower-tools/blob/master/XSLT_binary_search/genStrBin.xsl#L55-L103) allows for that:  
- returns -1 if string a is less than string b
- returns 0 if string a is equal to string b
- returns 1 if string a is greater than string b

Stylesheet genStrBin.xsl creates a binary search stylesheet from a string range input file. For routing table like applications, just set @max and @min to the same value:  

    $ cat s.xml 
    <es>
      <e min="'king'"   max="'king'"   value="D" />
      <e min="'rook'"   max="'rook'"   value="F" />
      <e min="'queen'"  max="'queen'"  value="E" />
      <e min="'bishop'" max="'bishop'" value="A" />
      <e min="'knight'" max="'knight'" value="B" />
      <e min="'pawn'"   max="'pawn'"   value="C" />
    </es>
    $ 

This is how binary search stylesheet gets created:

    $ coproc2 genStrBin.xsl s.xml http://dp3-l3.boeblingen.de.ibm.com:2223 > s.xsl 2>/dev/null
    $ 

Again it can be imported, and "xsl:rangeLookup(\_)" can be used.  
Alternatively you can use the [little test template of s.xsl](https://github.com/ibm-datapower/datapower-tools/blob/master/XSLT_binary_search/genStrBin.xsl#L105-L110):  

    $ coproc2 s.xsl <(echo "<x><y>chess</y><y>queen</y><y>king</y><y>pawn</y><y>rook</y><y>bishop</y><y>knight</y></x>") http://dp3-l3.boeblingen.de.ibm.com:2223; echo
    -EDCFAB
    $ 


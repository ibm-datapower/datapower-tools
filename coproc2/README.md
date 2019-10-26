# coproc2

* [Introduction](#introduction)
* [Export](#export)
* [Clients](#clients)
* [Using coproc2 service](#using-coproc2-service)
  * [XSLT processing XML](#xslt-processing-xml)
  * [Transform Binary XSLT processing Non-XML](#transform-binary-xslt-processing-non-xml)
  * [XQuery processing XML](#xquery-processing-xml)
  * [JSONiq processing JSON](#jsoniq-processing-json)
  * [GatewayScript](#gatewayscript)

## Introduction

coproc2 is a system consiting of a DataPower service export and two clients. With the clients you send not only the input for processing, but in addition the transformation file as well (XSLT/XSQuery/...). Then DataPower executes the transformation you sent on the input you provided, and returns the result. This is mainly useful while developing transformations, since use of coproc2 avoids the explicit file upload to DataPowwer, or the editing of file with DataPower editor. In case of errors you will find the details in DataPower log.

## Export

Service export [export-coproc2all.zip](exports/export-coproc2all.zip) contains 4 MPGWs with each having its own XML manager:  
* port 2223: XSLT processing XML
* port 2224: Transform Binary XSLT processing Non-XML
* port 2225: XQuery processing XML
* port 2226: JSONiq processing JSON
* port 2227: GatewayScript (TBD)

## Clients

You could just use the [coproc2](clients/coproc2) bash client, which requires [curl](https://curl.haxx.se/) to be installed.

Or you can use the Java client [coproc2.java](clients/coproc2.java) (coproc2.class has to reside somewhere in $CLASSPATH directories) without dependencies. 

## Using coproc2 service

You can provide input file as 2nd argument instead of "-" which just takes data from standard input.

### XSLT processing XML

Sample [double.xsl](samples/double.xsl):

    $ echo '<x>1</x>' | coproc2 double.xsl - http://firestar:2223 ; echo
    <out><x>1</x><x>1</x></out>
    $
    $ echo '<x>1</x>' | java coproc2 double.xsl - http://firestar:2223 ; echo
    <out><x>1</x><x>1</x></out>
    $

### Transform Binary XSLT processing Non-XML

Sample [toHex.xsl](samples/toHex.xsl):

    $ echo -ne "te\x0t" | coproc2 toHex.xsl - http://firestar:2224 ; echo
    74650074
    $
    $ echo -ne "te\x0t" | java coproc2 toHex.xsl - http://firestar:2224 ; echo
    74650074
    $

### XQuery processing XML

Sample [xml2xml.xq](samples/xml2xml.xq):

    $ echo '<a><b><c/></b></a>' | coproc2 xml2xml.xq - http://firestar:2225 ; echo
    <?xml version="1.0" encoding="UTF-8"?>
    <c/><b><c/></b><a><b><c/></b></a>
    $
    $ echo '<a><b><c/></b></a>' | java coproc2 xml2xml.xq - http://firestar:2225 ; echo
    <?xml version="1.0" encoding="UTF-8"?>
    <c/><b><c/></b><a><b><c/></b></a>
    $

### JSONiq processing JSON

Sample [json2json.xq](samples/json2json.xq):

    $ echo '["a",1,"b"]' | coproc2 json2json.xq - http://firestar:2226 ; echo
    
    [
      "b",
      1,
      "a"
    ]
    $
    $ echo '["a",1,"b"]' | java coproc2 json2json.xq - http://firestar:2226 ; echo
    
    [
      "b",
      1,
      "a"
    ]
    $

### GatewayScript 

TBD


The die represents transformation+input, the robot arm represents DataPower and result is delivered in grey box:      
![die picker](res/die.anim.gif)

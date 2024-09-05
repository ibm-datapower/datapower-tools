
## GET with payload against backend

HTTP GET with payload is bad, from the spec:  
https://www.rfc-editor.org/rfc/rfc9110.html#name-get  

A client **SHOULD NOT** generate content in a GET request unless it is made directly to an origin server that has previously indicated, in or out of band, that such a request has a purpose and will be adequately supported. An origin server **SHOULD NOT** rely on private agreements to receive content, since participants in HTTP communication are often unaware of intermediaries along the request chain.

DataPower has no option to send GET with payload against a backend, and that is good. In case you really need GET with payload against backend, below is a workaround.

### Simple CGI HTTP server for verification

An easy way to prove that DataPower really sends GET with payload is to use a simple HTTP server with CGI capabilities. Here ```python3 -m http.server --cgi``` is used for that. That server avoids the need for taking packet captures and analyze with Wireshark.

This is simple directory structure and <kbd>stat</kbd> script:  
```
~$ cd httproot/
httproot$ ls -l
total 0
drwxrwxr-x 2 stammw stammw 18 Sep  2 07:09 cgi-bin
httproot$ cat cgi-bin/stat 
#!/bin/bash
echo -en "Content-Type: text/plain\r\n"
echo -en "\r\n"
echo "$REQUEST_METHOD"
echo "$CONTENT_LENGTH"
httproot$ 
```
The <kbd>stat</kbd> script creates a HTTP response consisting of the HTTP method and content length for HTTP request. That is all that is needed to verify below GatewayScript.

As said, server is simply started this way:  
```
httproot$ python3 -m http.server --cgi
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
```

### Using tcp: backend protocol with crafted GET request

[js/GET_with_payload.js](js/GET_with_payload.js) script is warning free on jslint.com. It crafts GET request in variable <kbd>req</kbd>, and sets mpgw.skipBackside to <kbd>false</kbd> so that [coproc2](../coproc2/README.md) service can be used. Then it sets backend to <kbd>tcp://dp-hermann-rhel-work.fyre.ibm.com:8000</kbd> so that request is sent against above HTTP server. Finally <kbd>req</kbd> is just written to backend.

This is execution of script with coproc2 client:  
```
$ coproc2 js/GET_with_payload.js <("") http://dp-hermann-work.fyre.ibm.com:2227
HTTP/1.0 200 Script output follows
Server: SimpleHTTP/0.6 Python/3.11.9
Date: Mon, 02 Sep 2024 14:22:07 GMT
Content-Type: text/plain

GET
27
$ 
```
As expected GET is returned as HTTP request method, and 27 proves that indeed payload was sent.

The request gets logged on HTTP server:  
```
httproot$ python3 -m http.server --cgi
Serving HTTP on 0.0.0.0 port 8000 (http://0.0.0.0:8000/) ...
9.46.111.92 - - [02/Sep/2024 10:22:07] "GET /cgi-bin/stat HTTP/1.1" 200 -
```

Since DataPower goes against backend with <kbd>tcp:</kbd> protocol, nothing strips the HTTP response header, so you get that in addition to the response payload. The three lines above Content-type header generated by <kbd>stat</kbd> script are created by the HTTP server.

### Strip HTTP response header

[js/strip_http_header.js](js/strip_http_header.js) just strips the HTTP header, so everything before and including "\r\n\r\n" from HTTP spec. For real use you would reference previous script on request rule of your service, and this script on response rule. Here we use it in 2nd call of coproc2 client:  
```
$ coproc2 js/GET_with_payload.js <("") http://dp-hermann-work.fyre.ibm.com:2227\
>  2>/dev/null |\
> coproc2 js/strip_http_header.js - http://dp-hermann-work.fyre.ibm.com:2227
GET
27
$ 
```
That way only the HTTP response payload is returned.
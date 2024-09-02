/*jslint node*/
/*global session*/
var sm = require("service-metadata");

// HTTP request with CRLF line separators according spec
var payload = "field1=value1&field2=value2";

var req = "GET /cgi-bin/stat HTTP/1.1\r\n";
req += "Host: dp-hermann-work.fyre.ibm.com\r\n";
req += "Content-Type: application/x-www-form-urlencode\r\n";
req += "Content-Length: " + payload.length + "\r\n\r\n" + payload;

// this is true by default for coproc2gatewayscript MPGW
sm.mpgw.skipBackside = false;

// set HTTP backend
sm.routingUrl = "tcp://dp-hermann-rhel-work.fyre.ibm.com:8000";


// send built "GET with payload" request
session.output.write(req);

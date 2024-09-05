
## Usefule linters and formatters

### XML

You can lint XML documents with eg. <kbd>xmllint</kbd>. That will show potential problems with XML checked. Similar to <kbd>lint</kbd> to check for C files or <kbd>cpplint</kbd> to check for C++ files. 

Simple example of a warning (for [xml/version.xml](xml/version.xml)):  
```
stammw:Workarounds$ xmllint xml/version.xml 
xml/version.xml:1: parser warning : Unsupported version '1.9'
<?xml version="1.9"?>
                   ^
<?xml version="1.9"?>
<foo/>
stammw:Workarounds$ 
```

With DataPower XML files linting is perhaps not that important, but <kbd>xmllint</kbd>'s "--format" option might be useful. For exmple for DataPower XML management responses (with [doSoma](scripts/doSoma) tool that easies access to that interface, and [CPUUsage.xml](xml/CPUUsage.xml) example):  
```
$ scripts/doSoma admin:admin xml/CPUUsage.xml dp-hermann-work.fyre.ibm.com:5550 2>/dev/null | \
> xmllint --format -
<?xml version="1.0" encoding="UTF-8"?>
<env:Envelope xmlns:env="http://schemas.xmlsoap.org/soap/envelope/">
  <env:Body>
    <dp:response xmlns:dp="http://www.datapower.com/schemas/management">
      <dp:timestamp>2024-09-05T05:26:28-04:00</dp:timestamp>
      <dp:status>
        <CPUUsage xmlns:env="http://www.w3.org/2003/05/soap-envelope">
          <tenSeconds>3</tenSeconds>
          <oneMinute>3</oneMinute>
          <tenMinutes>5</tenMinutes>
          <oneHour>6</oneHour>
          <oneDay>6</oneDay>
        </CPUUsage>
      </dp:status>
    </dp:response>
  </env:Body>
</env:Envelope>
$ 
```

In case you want to <kbd>diff</kbd> several versions of XML files (eg. different responses from DataPower XML management interface), a simpler "formatter" based on <kbd>sed</kbd> can be helpful, that only inserts newline character between "...><...":  
```
$ scripts/doSoma admin:admin xml/CPUUsage.xml dp-hermann-work.fyre.ibm.com:5550  2>/dev/null | \
> sed "s/></>\n</g" ; echo
<?xml version="1.0" encoding="UTF-8"?>
<env:Envelope xmlns:env="http://schemas.xmlsoap.org/soap/envelope/">
<env:Body>
<dp:response xmlns:dp="http://www.datapower.com/schemas/management">
<dp:timestamp>2024-09-05T08:18:38-04:00</dp:timestamp>
<dp:status>
<CPUUsage xmlns:env="http://www.w3.org/2003/05/soap-envelope">
<tenSeconds>3</tenSeconds>
<oneMinute>3</oneMinute>
<tenMinutes>4</tenMinutes>
<oneHour>3</oneHour>
<oneDay>4</oneDay>
</CPUUsage>
</dp:status>
</dp:response>
</env:Body>
</env:Envelope>
$ 
```

### JSON

For linting JSON <kbd>jsonlint</kbd> package can be installed. Here tested with bad JSON file [json/bad_array.json](json/bad_array.json):  
```
$ jsonlint-php json/bad_array.json 
json/bad_array.json: Parse error on line 1:
[1, 2, 3, ]
---------^
Expected one of: 'STRING', 'NUMBER', 'NULL', 'TRUE', 'FALSE', '{', '[' - It appears you have an extra trailing comma
$
```

For formatting you can either send JSON to a DataPower service just executing [store:///identity-json.xq](xq/identity-json.xq) XQuery script (here with [coproc2](../coproc2/README.md) service) …  
```
$ coproc2 identity-json.xq <(echo '{"foo": 0}') http://dp-hermann-work.fyre.ibm.com:2226; echo
{
  "foo":0
}
$
```

… of use <kbd>jq</kbd> package tool:  
```
$ echo '{"foo": 0}' | jq .
{
  "foo": 0
}
$
```

### GatewayScript

For linting GatewayScript you can just copy into [https://jslint.com](https://jslint.com) in case you have nothing confidential (like done to validate GET_with_payload.js [here](./GET_with_payload.md)).  

Alternatively you can install <kbd>eslint</kbd> package. Once you need to initialize eslint:  
```
$ eslint --init
? How would you like to configure ESLint? Answer questions about your style
? Which version of ECMAScript do you use? ES5
? Where will your code run? Browser
? Do you use CommonJS? Yes
? Do you use JSX? No
? What style of indentation do you use? Spaces
? What quotes do you use for strings? Double
? What line endings do you use? Unix
? Do you require semicolons? Yes
? What format do you want your config file to be in? JSON
Successfully created .eslintrc.json file in /home/stammw/datapower-tools/Workarounds
$
```

No warning raised for that script is no surprise, since script was warning free on jslint.com:  
```
$ eslint js/GET_with_payload.js 
$
```

For formatting GatewayScript I just found [prettier](https://prettier.io/docs/en/install.html) tool, After following the install steps, the prettyfied script looks the same with exception of a newline character:  
```
$ npx prettier js/GET_with_payload.js > G.js
$ diff js/GET_with_payload.js G.js 
19d18
< 
stammw:Workarounds$ 
```


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

### JSON


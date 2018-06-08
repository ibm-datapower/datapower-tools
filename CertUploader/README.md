# README.md for Certificate Reporter

**Certificate Uploader** is a Python script that will upload a certificate file or key file into a specified domain.

I call this a smart loader as it makes some determinations and finds system-wide references to this file when the file is uploaded to a folder:

  If the file is a certificate and is loaded to the default domain, the file is uploaded to the sharedcert folder as it is assumed that there will be no user objects in the default domain. All domains are searched for references to this new file in the sharedcert folder, and if any are found, they are refreshed to acquire the new crypto information

  If the file is upload to an application domain, the file is uploaded to the cert folder as that is the only folder available for crypto objects. The current application domain is searched for references to this new file in the cert folder, and if any are found, they are refreshed to acquire the new crypto information.

/** 
 * coproc2 
 * - send stylesheet and xmlfile to a DataPower appliance;
 * - display DataPower result of applying stylesheet to xmlfile.
 *
 * Modification of SOAPClient4XG from this article:
 * http://www.ibm.com/developerworks/xml/library/x-soapcl/
 * 
 * Added sending of base64(gzip(stylesheet2Send)) as HTTP header. 
 *
 * @author  Hermann Stamm-Wilbrandt
 * @version 1.0
 * @param   stylesheet2Send  stylesheet to be executed on DataPower
 * @param   xmlFile2Send     xmlfile sent to DataPower
 * @param   url              URL of coproc2 Endpoint on DataPower
*/

import java.io.*;
import java.net.*;
import java.util.zip.*;

public class coproc2 {

    public static void main(String[] args) throws Exception {

        if (args.length != 3) {
            System.err.println("Usage:  java coproc2 " +
                               "stylesheet xmlfile http://coproc2endpoint");
            System.exit(1);
        }

        String stylesheet2Send = args[0];
        String xmlFile2Send    = args[1];
        String coproc2endpoint = args[2];

        // Create the connection where we're going to send the file.
        URL url = new URL(coproc2endpoint);
        URLConnection connection = url.openConnection();
        HttpURLConnection httpConn = (HttpURLConnection) connection;

        // Open the input file. After we copy it to a byte array, we can see
        // how big it is so that we can set the HTTP Cotent-Length
        // property. (See complete e-mail below for more on this.)

        FileInputStream fin = new FileInputStream(xmlFile2Send);

        ByteArrayOutputStream bout = new ByteArrayOutputStream();
    
        // Copy the SOAP file to the open connection.
        copy(fin,bout);
        fin.close();

        byte[] b = bout.toByteArray();


    // Read stylesheet2send into b2[]
    InputStream fin2 = new FileInputStream(stylesheet2Send);
      ByteArrayOutputStream bout2 = new ByteArrayOutputStream();
      copy(fin2,bout2);
    fin2.close();

    byte b2[] = bout2.toByteArray();

    // B[] = gzip(b2[])
    ByteArrayOutputStream bos = new ByteArrayOutputStream();
      GZIPOutputStream gz = new GZIPOutputStream(bos);
        gz.write(b2);
      gz.close();
    bos.close();

    byte B[] = bos.toByteArray();

    // base64 encoding characters
    final char b64[] = {
        'A','B','C','D','E','F','G','H','I','J','K','L','M',
        'N','O','P','Q','R','S','T','U','V','W','X','Y','Z',
        'a','b','c','d','e','f','g','h','i','j','k','l','m',
        'n','o','p','q','r','s','t','u','v','w','x','y','z',
        '0','1','2','3','4','5','6','7','8','9','+','/'
    };
    final char pad = '=';

    // strb64 = base64(B[])
    ByteArrayOutputStream bos2 = new ByteArrayOutputStream();
      int i;
      for(i=0; i<B.length-2; i+=3) {
        bos2.write(b64[  ((int)B[i+0]&0xFF)      >>2 ]);
        bos2.write(b64[((((int)B[i+0]&0xFF)&0x03)<<4) | 
                        (((int)B[i+1]&0xFF)      >>4)]);
        bos2.write(b64[((((int)B[i+1]&0xFF)&0x0F)<<2) | 
                        (((int)B[i+2]&0xFF)      >>6)]);
        bos2.write(b64[  ((int)B[i+2]&0xFF)&0x3F     ]);
      }
      if (i < B.length) {
        bos2.write(b64[  ((int)B[i+0]&0xFF)      >>2 ]);

        if (i+2 == B.length) {
          bos2.write(b64[((((int)B[i+0]&0xFF)&0x03)<<4) | 
                          (((int)B[i+1]&0xFF)      >>4)]);
          bos2.write(b64[((((int)B[i+1]&0xFF)&0x0F)<<2)]);
        }
        else {
          bos2.write(b64[((((int)B[i+0]&0xFF)&0x03)<<4)]);
          bos2.write(pad);
        }
        bos2.write(pad);
      }
    bos2.close();

    String strb64 = bos2.toString();


        // Set the appropriate HTTP parameters.
        httpConn.setRequestProperty( "Content-Length",
                                     String.valueOf( b.length ) );
        httpConn.setRequestProperty("Content-Type","text/xml; charset=utf-8");
        httpConn.setRequestProperty("xsl",strb64);
        httpConn.setRequestMethod( "POST" );
        httpConn.setDoOutput(true);
        httpConn.setDoInput(true);

        // Everything's set up; send the XML that was read in to b.
        OutputStream out = httpConn.getOutputStream();
        out.write( b );    
        out.close();

        // Read the response and write it to standard out.

        InputStreamReader isr =
            new InputStreamReader(httpConn.getInputStream());
        BufferedReader in = new BufferedReader(isr);

        String inputLine;

        while ((inputLine = in.readLine()) != null)
            System.out.println(inputLine);

        in.close();
    }

  // copy method from From E.R. Harold's book "Java I/O"
  public static void copy(InputStream in, OutputStream out) 
   throws IOException {

    // do not allow other threads to read from the
    // input or write to the output while copying is
    // taking place

    synchronized (in) {
      synchronized (out) {

        byte[] buffer = new byte[256];
        while (true) {
          int bytesRead = in.read(buffer);
          if (bytesRead == -1) break;
          out.write(buffer, 0, bytesRead);
        }
      }
    }
  } 
}

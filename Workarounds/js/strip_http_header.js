session.input.readAsBuffer(function (err, buf) {
  session.output.write(buf.slice(4+buf.indexOf("\r\n\r\n")));
});

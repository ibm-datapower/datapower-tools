session.input.readAsBuffer(function (error, buffer) {
  if (error)
  {
    // handle error
    session.output.write (error.errorMessage);
  } else {
    for(var i=0, j=buffer.length-1; i<j; ++i, --j) {
      var b     = buffer[i];
      buffer[i] = buffer[j];
      buffer[j] = b;
    } 
    /* write the default output buffer */
    session.output.write (buffer);
  }
});

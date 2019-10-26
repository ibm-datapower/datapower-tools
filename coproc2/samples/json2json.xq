declare namespace output = "http://www.w3.org/2010/xslt-xquery-serialization";

declare option jsoniq-version "0.4.42";
declare option output:method "json";

[
  fn:reverse(
    jn:members(.)
  )
]

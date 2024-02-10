#!/usr/bin/python

import http
import http.server
import pexpect.replwrap
import urllib.parse


FLIRC_UTIL: pexpect.replwrap.REPLWrapper


class Handler(http.server.BaseHTTPRequestHandler):

  def do_POST(self):
    global FLIRC_UTIL
    parts = urllib.parse.urlsplit(self.path)
    flags = urllib.parse.parse_qsl(parts.query)
    cmd = urllib.parse.unquote(parts.path.lstrip('/'))

    def flirc_shell_escape(s):
      return s.replace(' ', '\\ ').replace('\t', '\\\t')
    args = [
      cmd
    ] + [
      f'--{k}={flirc_shell_escape(v)}' for k, v in flags
    ]

    result = FLIRC_UTIL.run_command(' '.join(args))
    self.send_response(200, 'OK')
    self.send_header('Content-Length', str(len(result)))
    self.end_headers()
    self.wfile.write(result.encode('utf8'))


if __name__ == '__main__':
  FLIRC_UTIL = pexpect.replwrap.REPLWrapper('flirc_util shell', 'flirc_util $', None)
  http.server.HTTPServer(('', 8000), Handler).serve_forever()
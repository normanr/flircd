#!/usr/bin/python

import http
import http.server
import threading
import pexpect.replwrap
import urllib.parse


__version__ = '0.1'


FLIRC_UTIL: pexpect.replwrap.REPLWrapper
FLIRC_UTIL_LOCK = threading.Lock()
FLIRC_UTIL_COMMANDS = (
  'settings',
  'sendir',
  'version',
)


class Handler(http.server.SimpleHTTPRequestHandler):
  wbufsize = -1  # http://lautaportti.wordpress.com/2011/04/01/basehttprequesthandler-wastes-tcp-packets/
  protocol_version = 'HTTP/1.1'

  def version_string(self):
    return 'flircd/%s %s' % (
        __version__,
        http.server.SimpleHTTPRequestHandler.version_string(self))

  def do_POST(self):
    global FLIRC_UTIL
    parts = urllib.parse.urlsplit(self.path)
    flags = urllib.parse.parse_qsl(parts.query)
    cmd = urllib.parse.unquote(parts.path.lstrip('/'))

    if cmd in FLIRC_UTIL_COMMANDS:
      def flirc_shell_escape(s):
        return s.replace(' ', '\\ ').replace('\t', '\\\t')
      args = [
        cmd
      ] + [
        f'--{k}={flirc_shell_escape(v)}' for k, v in flags
      ]

      with FLIRC_UTIL_LOCK:
        result = FLIRC_UTIL.run_command(' '.join(args))
      self.send_response(200, 'OK')
      self.send_header('Content-Length', str(len(result)))
      self.end_headers()
      self.wfile.write(result.encode('utf8'))
      return
    elif cmd == 'restart':
      with FLIRC_UTIL_LOCK:
        FLIRC_UTIL.child.sendline('exit')
        FLIRC_UTIL.child.close()
        FLIRC_UTIL = pexpect.replwrap.REPLWrapper('flirc_util shell', 'flirc_util $', None)
      self.send_response(204, 'No Content')
      self.send_header('Content-Length', '0')
      self.end_headers()
      return

    self.send_error(404)

  def list_directory(self, path):
      self.send_error(404, 'No permission to list directory')


if __name__ == '__main__':
  FLIRC_UTIL = pexpect.replwrap.REPLWrapper('flirc_util shell', 'flirc_util $', None)
  http.server.ThreadingHTTPServer(('', 8000), Handler).serve_forever()

#!/usr/bin/python

import argparse
import collections.abc
import http
import http.server
import json
import logging
import os
import paho.mqtt.client
import pexpect.replwrap
import sys
import threading
import toml
import traceback
import urllib.parse


__version__ = '0.2'
logger = logging.getLogger(__name__)



FLIRC_UTIL: pexpect.replwrap.REPLWrapper
FLIRC_UTIL_LOCK = threading.Lock()
FLIRC_UTIL_COMMANDS = (
  'settings',
  'sendir',
  'version',
)
RAW_TO_CSV = str.maketrans(' ', ',', '+-')


def get_raw(keymap, keycode) -> str | None:
  with open(f'/etc/rc_keymaps/{keymap}.toml') as f:
    keymap = toml.load(f)
  for protocol in keymap['protocols']:
    if protocol['protocol'] != 'raw':
      continue
    codes = {raw['keycode']: raw['raw'] for raw in protocol['raw']}
    return codes[keycode]


def flirc(cmd: str, flags: collections.abc.Sequence[tuple[str, str]]):
  global FLIRC_UTIL

  if cmd == 'ir-ctl-send':
    try:
      flag_dict = dict(flags)
      raw = get_raw(flag_dict['keymap'], flag_dict['keycode'])
      if raw:
        csv = raw.translate(RAW_TO_CSV)
        cmd = 'sendir'
        flags = (('csv', csv),)
    except:
      pass

  if cmd in FLIRC_UTIL_COMMANDS:
    def flirc_shell_escape(s):
      return s.replace(' ', '\\ ').replace('\t', '\\\t')
    args = [
      cmd
    ] + [
      f'--{k}={flirc_shell_escape(v)}' for k, v in flags
    ]

    with FLIRC_UTIL_LOCK:
      return FLIRC_UTIL.run_command(' '.join(args))
  elif cmd == 'restart':
    with FLIRC_UTIL_LOCK:
      FLIRC_UTIL.child.sendline('exit')
      FLIRC_UTIL.child.close()
      FLIRC_UTIL = pexpect.replwrap.REPLWrapper('flirc_util shell', 'flirc_util $', None)
    return None

  return False


class Handler(http.server.SimpleHTTPRequestHandler):
  wbufsize = -1  # http://lautaportti.wordpress.com/2011/04/01/basehttprequesthandler-wastes-tcp-packets/
  protocol_version = 'HTTP/1.1'

  def version_string(self):
    return 'flircd/%s %s' % (
        __version__,
        http.server.SimpleHTTPRequestHandler.version_string(self))

  def do_POST(self):
    parts = urllib.parse.urlsplit(self.path)
    flags = urllib.parse.parse_qsl(parts.query)
    cmd = urllib.parse.unquote(parts.path.removeprefix('/').removeprefix('cgi-bin/'))

    result = flirc(cmd, flags)
    if result:
      self.send_response(200, 'OK')
      self.send_header('Content-Length', str(len(result)))
      self.end_headers()
      self.wfile.write(result.encode('utf8'))
      return
    elif result is None:
      self.send_response(204, 'No Content')
      self.send_header('Content-Length', '0')
      self.end_headers()
      return

    self.send_error(404)

  def list_directory(self, path):
      self.send_error(404, 'No permission to list directory')


def mqtt_init(url: str):
  res = urllib.parse.urlsplit(url)
  assert res.scheme in ('mqtt', 'mqtts')
  assert res.hostname
  port = res.port if res.port else 8883 if res.scheme == 'mqtts' else 1883

  # The callback for when the client receives a CONNACK response from the server.
  def on_connect(client, userdata, flags, rc):
    del userdata, flags
    logger.info("Connected with result code %s", rc)

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    logger.info("Subscribing to %r", res.path.removeprefix('/'))
    client.subscribe(res.path.removeprefix('/'))

  # The callback for when a PUBLISH message is received from the server.
  def on_message(client, userdata, msg):
    del client, userdata
    try:
      data = json.loads(msg.payload.decode())
      logger.info('%r: %r', data, flirc('ir-ctl-send', data))
    except:
      traceback.print_exc()

  client = paho.mqtt.client.Client(client_id=f'flircd-{os.getpid()}')
  client.enable_logger()
  client.on_connect = on_connect
  client.on_message = on_message

  client.connect(res.hostname, port, 60)

  client.loop_start()


def configure_logging(verbosity):
  FORMAT = '%(levelname).1s %(asctime)-15.19s %(filename)s:%(lineno)d %(message)s'
  offset = (logging.INFO - logging.WARNING) * verbosity
  logging.basicConfig(format=FORMAT, level=logging.WARNING + offset)


def parse_args(args):
  parser = argparse.ArgumentParser(add_help=False)
  parser.add_argument('--help', action='help', default=argparse.SUPPRESS,
                      help='show this help message and exit')
  parser.add_argument(
      '-q', '--quiet', action='count', default=0, help='quiet output')
  parser.add_argument(
      '-v', '--verbose', action='count', default=0, help='verbose output')
  parser.add_argument('-b', '--bind', default='8000', help='bind HTTP server to this address (default: %(default)r)')
  parser.add_argument('-m', '--mqtt', help='MQTT broker url, in the form mqtt(s)://[username[:password]@]host[:port]/topic')
  return parser.parse_args(args)


def main(args=None):
  args = parse_args(args)
  configure_logging(args.verbose - args.quiet)
  logger.info(args)

  global FLIRC_UTIL
  FLIRC_UTIL = pexpect.replwrap.REPLWrapper('flirc_util shell', 'flirc_util $', None)

  if args.mqtt:
    mqtt_init(args.mqtt)

  host, _, port = args.bind.rpartition(':')
  port = int(port)
  http.server.ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == '__main__':
  sys.exit(main())

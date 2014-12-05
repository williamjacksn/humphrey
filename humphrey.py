import asyncio
import collections
import datetime
import json


class EventEmitter(object):
    def __init__(self):
        self._events = collections.defaultdict(list)

    def on(self, event, func=None):
        def _on(f):
            self._events[event].append(f)
            return f
        if func is None:
            return _on
        return _on(func)

    def emit(self, event, *args, **kwargs):
        handled = False
        for f in self._events[event]:
            f(*args, **kwargs)
            handled = True
        if not handled:
            for f in self._events['catch_all']:
                f(*args, **kwargs)
        return handled


class Config:
    def __init__(self, path, pretty=False):
        self.data = dict()
        self.path = path
        self.pretty = pretty
        if self.path.exists():
            with self.path.open() as f:
                self.data = json.load(f)

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value
        self._flush()

    def _flush(self):
        with self.path.open('w') as f:
            if self.pretty:
                json.dump(self.data, f, indent=4, sort_keys=True)
            else:
                json.dump(self.data, f)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def keys(self):
        return self.data.keys()

    def remove(self, key):
        if key in self.data:
            del self.data[key]
            self._flush()

    def set(self, key, value):
        self[key] = value


class IRCClient(asyncio.Protocol):
    def __init__(self, config_path):
        self.buf = b''
        self.ee = EventEmitter()
        self.c = Config(config_path)
        self.loop = asyncio.get_event_loop()
        self.t = None
        self.debug = False
        self.admins = set()

    def __call__(self):
        return self

    @staticmethod
    def log(message):
        t = datetime.datetime.utcnow()
        print('{} {}'.format(t, message))

    @staticmethod
    def is_irc_channel(s):
        return s and s[0] == '#'

    @staticmethod
    def remove_format_codes(m):
        m = m.replace(b'\x02', b'')  # bold
        m = m.replace(b'\x0f', b'')  # normal
        m = m.replace(b'\x16', b'')  # italic/reversed
        m = m.replace(b'\x1f', b'')  # underline
        while 3 in m:  # color
            idx = m.find(3)
            mark = idx + 1
            if m[mark:mark + 2].isdigit():
                mark += 2
            elif m[mark:mark + 1].isdigit():
                mark += 1
            if len(m) > mark and m[mark] == 44:  # b','
                if m[mark + 1:mark + 3].isdigit():
                    mark += 3
                elif m[mark + 1:mark + 2].isdigit():
                    mark += 2
            m = m.replace(m[idx:mark], b'')
        return m

    def smart_decode(self, m):
        if self.debug:
            self.log('** {}'.format(repr(m)))
        m = self.remove_format_codes(m)
        try:
            return m.decode()
        except UnicodeDecodeError:
            self.log('** Failed decode using utf-8, trying next encoding.')
        try:
            return m.decode('iso-8859-1')
        except:
            self.log('** Failed decode using iso-8859-1.')
            self.log(repr(m))
            raise

    @staticmethod
    def parse_hostmask(hostmask):
        # 'nick!user@host' => ('nick', 'user', 'host')
        nick, _, userhost = hostmask.partition('!')
        user, _, host = userhost.partition('@')
        return nick, user, host

    def add_admin(self, nick):
        self.log('** Added {} to admins list'.format(nick))
        self.admins.add(nick)

    def remove_admin(self, nick):
        self.log('** Removed {} from admins list'.format(nick))
        self.admins.discard(nick)

    def connection_made(self, transport):
        self.t = transport
        self.log('** Connection made')
        self.out('NICK {}'.format(self.c['irc:nick']))
        m = 'USER {} {} x :{}'
        ident = self.c['irc:ident']
        self.out(m.format(ident, self.c['irc:host'], self.c['irc:name']))

    def data_received(self, data):
        self.buf = self.buf + data
        lines = self.buf.split(b'\n')
        self.buf = lines.pop()
        for line in lines:
            line = line.strip()
            self.loop.call_soon(self._in, line)

    def connection_lost(self, exc):
        self.log('** Connection lost')
        self.loop.stop()

    def _in(self, message):
        # convert message from bytes to unicode
        # then emit an appropriate event
        message = self.smart_decode(message)
        tokens = message.split()
        if len(tokens) > 0 and tokens[0] == 'PING':
            self.ee.emit(tokens[0], message, self)
        elif len(tokens) > 3 and tokens[3] == ':\x01ACTION':
            self.ee.emit('ACTION', message, self)
        elif len(tokens) > 1:
            self.ee.emit(tokens[1], message, self)
        else:
            self.ee.emit('catch_all', message, self)

    def out(self, message):
        # log messages then convert from unicode to bytes
        # and write to transport
        if message:
            self.log('=> {}'.format(message))
            self.t.write('{}\r\n'.format(message).encode())

    def send_privmsg(self, target, message):
        self.out('PRIVMSG {} :{}'.format(target, message))

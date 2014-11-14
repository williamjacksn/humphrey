import asyncio
import collections
import config
import datetime


class EventEmitter(object):
    def __init__(self):
        self._events = collections.defaultdict(list)

    def on(self, event, f=None):
        def _on(f):
            self._events[event].append(f)
            return f
        if f is None:
            return _on
        return _on(f)

    def emit(self, event, *args, **kwargs):
        handled = False
        for f in self._events[event]:
            f(*args, **kwargs)
            handled = True
        if not handled:
            for f in self._events['catch_all']:
                f(*args, **kwargs)
        return handled


class IRCClient(asyncio.Protocol):
    c = config.Config()
    buf = b''
    ee = EventEmitter()

    def this(self):
        return self

    def log(self, message):
        t = datetime.datetime.utcnow()
        print('{} {}'.format(t, message))

    def smart_decode(self, message):
        try:
            return message.decode()
        except UnicodeDecodeError:
            pass
        try:
            return message.decode('iso-8859-1')
        except:
            for b in message:
                self.log('{} {}'.format(chr(b), b))
            raise

    def parse_hostmask(self, hostmask):
        # 'nick!user@host' => ('nick', 'user', 'host')
        nick, _, userhost = hostmask.partition('!')
        user, _, host = userhost.partition('@')
        return nick, user, host

    def add_admin(self, nick):
        self.log('** Added {} to admins list'.format(nick))
        c.ADMINS.add(nick)

    def remove_admin(self, nick):
        self.log('** Removed {} from admins list'.format(nick))
        c.ADMINS.discard(nick)

    def connection_made(self, transport):
        self.loop = asyncio.get_event_loop()
        self.t = transport
        self.log('** Connection made')
        self.out(['NICK {}'.format(c.NICK)])
        m = 'USER {} {} x :{}'
        self.out([m.format(c.IDENT, c.HOST, c.REALNAME)])

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
            self.ee.emit(tokens[0], message)
        elif len(tokens) > 1:
            self.ee.emit(tokens[1], message)
        else:
            self.ee.emit('catch_all', message)

    def out(self, messages):
        # log messages then convert from unicode to bytes
        # and write to transport
        if messages:
            for message in messages:
                self.log('=> {}'.format(message))
                self.t.write('{}\r\n'.format(message).encode())

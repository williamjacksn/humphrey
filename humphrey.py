import asyncio
import config
import handlers
import util

class IRCClient(asyncio.Protocol):
    buf = b''

    def connection_made(self, transport):
        self.loop = asyncio.get_event_loop()
        self.t = transport
        util.log('** Connection made')
        self._out(['NICK {}'.format(config.NICK)])
        m = 'USER {} {} x :{}'
        self._out([m.format(config.IDENT, config.HOST, config.REALNAME)])

    def data_received(self, data):
        self.buf = self.buf + data
        lines = self.buf.split(b'\n')
        self.buf = lines.pop()
        for line in lines:
            line = line.strip()
            self.loop.call_soon(self._in, line)

    def connection_lost(self, exc):
        util.log('** Connection lost')
        self.loop.stop()

    def _in(self, message):
        # convert message from bytes to unicode then send to appropriate handler
        message = util.smart_decode(message)
        tokens = message.split()
        if len(tokens) > 1 and tokens[1] == 'JOIN':
            self._out(handlers.JOIN(message))
        elif len(tokens) > 1 and tokens[1] == 'MODE':
            self._out(handlers.MODE(message))
        elif len(tokens) > 1 and tokens[1] == 'NICK':
            self._out(handlers.NICK(message))
        elif len(tokens) > 1 and tokens[1] == 'NOTICE':
            self._out(handlers.NOTICE(message))
        elif len(tokens) > 0 and tokens[0] == 'PING':
            self._out(handlers.PING(message))
        elif len(tokens) > 1 and tokens[1] == 'PRIVMSG':
            self._out(handlers.PRIVMSG(message))
        elif len(tokens) > 1 and tokens[1] == 'QUIT':
            self._out(handlers.QUIT(message))
        elif len(tokens) > 1 and tokens[1] == '001':
            self._out(handlers.RPL_WELCOME(message))
        elif len(tokens) > 1 and tokens[1] == '002':
            self._out(handlers.RPL_YOURHOST(message))
        elif len(tokens) > 1 and tokens[1] == '003':
            self._out(handlers.RPL_CREATED(message))
        elif len(tokens) > 1 and tokens[1] == '004':
            self._out(handlers.RPL_MYINFO(message))
        elif len(tokens) > 1 and tokens[1] == '005':
            self._out(handlers.RPL_ISUPPORT(message))
        elif len(tokens) > 1 and tokens[1] == '251':
            self._out(handlers.RPL_LUSERCLIENT(message))
        elif len(tokens) > 1 and tokens[1] == '252':
            self._out(handlers.RPL_LUSEROP(message))
        elif len(tokens) > 1 and tokens[1] == '253':
            self._out(handlers.RPL_LUSERUNKNOWN(message))
        elif len(tokens) > 1 and tokens[1] == '254':
            self._out(handlers.RPL_LUSERCHANNELS(message))
        elif len(tokens) > 1 and tokens[1] == '255':
            self._out(handlers.RPL_LUSERME(message))
        elif len(tokens) > 1 and tokens[1] == '265':
            self._out(handlers.RPL_LOCALUSERS(message))
        elif len(tokens) > 1 and tokens[1] == '266':
            self._out(handlers.RPL_GLOBALUSERS(message))
        elif len(tokens) > 1 and tokens[1] == '332':
            self._out(handlers.RPL_TOPIC(message))
        elif len(tokens) > 1 and tokens[1] == '333':
            self._out(handlers.RPL_TOPICWHOTIME(message))
        elif len(tokens) > 1 and tokens[1] == '353':
            self._out(handlers.RPL_NAMREPLY(message))
        elif len(tokens) > 1 and tokens[1] == '366':
            self._out(handlers.RPL_ENDOFNAMES(message))
        elif len(tokens) > 1 and tokens[1] == '372':
            self._out(handlers.RPL_MOTD(message))
        elif len(tokens) > 1 and tokens[1] == '375':
            self._out(handlers.RPL_MOTDSTART(message))
        elif len(tokens) > 1 and tokens[1] == '376':
            self._out(handlers.RPL_ENDOFMOTD(message))
        elif len(tokens) > 1 and tokens[1] == '451':
            self._out(handlers.RPL_ENDOFMOTD(message))
        else:
            self._out(handlers.unknown(message))

    def _out(self, messages):
        # log messages then convert from unicode to bytes and write to transport
        if messages:
            for message in messages:
                util.log('=> {}'.format(message))
                self.t.write('{}\r\n'.format(message).encode())


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    coro = loop.create_connection(IRCClient, config.HOST, config.PORT)
    loop.run_until_complete(coro)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.close()

import config
import util


def unknown(message):
    util.log('XX {}'.format(message))


def known(message):
    util.log('<= {}'.format(message))


def command(message):
    message = message.split(' :')[1]
    util.log('** Processing command: {}'.format(message))
    tokens = message.split()
    if len(tokens) > 1 and tokens[0] == '!say':
        response = ' '.join(tokens[1:])
        return ['PRIVMSG {} :{}'.format(config.CHANNEL, response)]

# A message handler should return nothing or an iterable of strings.
# Each string should be a raw IRC message to send back to the server.

ERR_NOTREGISTERED = known
JOIN = known


def MODE(message):
    util.log('<= {}'.format(message))
    tokens = message.split()
    target = tokens[2]
    if target == config.CHANNEL:
        modes = tokens[3]


def NICK(message):
    util.log('<= {}'.format(message))
    tokens = message.split()
    source = tokens[0].lstrip(':')
    nick, _, _ = util.parse_hostmask(source)
    newnick = tokens[2].lstrip(':')
    if nick in config.ADMINS:
        util.add_admin(newnick)
        util.remove_admin(nick)

NOTICE = known


def PING(message):
    util.log('<= {}'.format(message))
    tokens = message.split()
    return ['PONG {}'.format(tokens[1])]


def PRIVMSG(message):
    util.log('<= {}'.format(message))
    tokens = message.split()
    if tokens[2] == config.NICK:
        source = tokens[0].lstrip(':')
        nick, _, _ = util.parse_hostmask(source)
        if nick in config.ADMINS:
            return command(message)


def QUIT(message):
    util.log('<= {}'.format(message))
    tokens = message.split()
    source = tokens[0].lstrip(':')
    nick, _, _ = util.parse_hostmask(source)
    if nick in config.ADMINS:
        util.remove_admin(nick)

RPL_CREATED = known


def RPL_ENDOFMOTD(message):
    util.log('<= {}'.format(message))
    return ['JOIN {}'.format(config.CHANNEL)]

RPL_ENDOFNAMES = known
RPL_GLOBALUSERS = known
RPL_ISUPPORT = known
RPL_LOCALUSERS = known
RPL_LUSERCHANNELS = known
RPL_LUSERCLIENT = known
RPL_LUSERME = known
RPL_LUSEROP = known
RPL_LUSERUNKNOWN = known
RPL_MOTD = known
RPL_MOTDSTART = known
RPL_MYINFO = known


def RPL_NAMREPLY(message):
    util.log('<= {}'.format(message))
    tokens = message.split()
    names = tokens[5:]
    for name in tokens[5:]:
        name = name.lstrip(':')
        if name.startswith(('~', '@', '%')):
            util.add_admin(name.lstrip('~@%'))

RPL_TOPIC = known
RPL_TOPICWHOTIME = known
RPL_WELCOME = known
RPL_YOURHOST = known

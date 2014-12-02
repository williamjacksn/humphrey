import asyncio
import humphrey


bot = humphrey.IRCClient()


def command(message):
    message = message.split(' :')[1]
    tokens = message.split()
    if len(tokens) > 1 and tokens[0] == '!say':
        bot.log('** Processing command: {}'.format(message))
        response = ' '.join(tokens[1:])
        bot.out(['PRIVMSG {} :{}'.format(bot.c.CHANNEL, response)])


@bot.ee.on('PRIVMSG')
def privmsg(message):
    bot.log('<= {}'.format(message))
    tokens = message.split()
    if len(tokens) > 2 and tokens[2] == bot.c.NICK:
        source = tokens[0].lstrip(':')
        nick, _, _ = bot.parse_hostmask(source)
        if nick in bot.c.ADMINS:
            command(message)


@bot.ee.on('MODE')
def on_mode(message):
    bot.log('<= {}'.format(message))
    tokens = message.split()
    target = tokens[2]
    if target == bot.c.CHANNEL:
        modes = tokens[3]


@bot.ee.on('NICK')
def on_nick(message):
    bot.log('<= {}'.format(message))
    tokens = message.split()
    source = tokens[0].lstrip(':')
    nick, _, _ = bot.parse_hostmask(source)
    newnick = tokens[2].lstrip(':')
    if nick in bot.c.ADMINS:
        bot.add_admin(newnick)
        bot.remove_admin(nick)


@bot.ee.on('PING')
def on_ping(message):
    bot.log('<= {}'.format(message))
    tokens = message.split()
    bot.out(['PONG {}'.format(tokens[1])])


@bot.ee.on('QUIT')
def on_quit(message):
    bot.log('<= {}'.format(message))
    tokens = message.split()
    source = tokens[0].lstrip(':')
    nick, _, _ = bot.parse_hostmask(source)
    if nick in bot.c.ADMINS:
        bot.remove_admin(nick)


@bot.ee.on('353')
def on_rpl_namreply(message):
    bot.log('<= {}'.format(message))
    tokens = message.split()
    for name in tokens[5:]:
        name = name.lstrip(':')
        if name.startswith(('~', '@', '%')):
            bot.add_admin(name.lstrip('~@%'))


@bot.ee.on('376')
def on_rpl_endofmotd(message):
    bot.log('<= {}'.format(message))
    bot.out(['JOIN {}'.format(bot.c.CHANNEL)])


@bot.ee.on('001')  # RPL_WELCOME
@bot.ee.on('002')  # RPL_YOURHOST
@bot.ee.on('003')  # RPL_CREATED
@bot.ee.on('004')  # RPL_MYINFO
@bot.ee.on('005')  # RPL_ISUPPORT
@bot.ee.on('251')  # RPL_LUSERCLIENT
@bot.ee.on('252')  # RPL_LUSEROP
@bot.ee.on('253')  # RPL_LUSERUNKNOWN
@bot.ee.on('254')  # RPL_LUSERCHANNELS
@bot.ee.on('255')  # RPL_LUSERME
@bot.ee.on('265')  # RPL_LOCALUSERS
@bot.ee.on('266')  # RPL_GLOBALUSERS
@bot.ee.on('332')  # RPL_TOPIC
@bot.ee.on('333')  # RPL_TOPICWHOTIME
@bot.ee.on('366')  # RPL_ENDOFNAMES
@bot.ee.on('372')  # RPL_MOTD
@bot.ee.on('375')  # RPL_MOTDSTART
@bot.ee.on('451')  # ERR_NOTREGISTERED
@bot.ee.on('ACTION')
@bot.ee.on('JOIN')
@bot.ee.on('NOTICE')
@bot.ee.on('TOPIC')
def known(message):
    bot.log('<= {}'.format(message))


@bot.ee.on('catch_all')
def unknown(message):
    bot.log('XX {}'.format(message))


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    coro = loop.create_connection(bot.this, bot.c.HOST, bot.c.PORT)
    loop.run_until_complete(coro)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        bot.log('** Caught KeyboardInterrupt')
        loop.close()

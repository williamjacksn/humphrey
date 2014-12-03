import asyncio
import humphrey
import importlib
import inspect
import sys


bot = humphrey.IRCClient()


@bot.ee.on('PRIVMSG')
def log_privmsg(message):
    bot.log('<= {}'.format(message))


@bot.ee.on('PRIVMSG')
def handle_help(message):
    tokens = message.split()
    source = tokens[0].lstrip(':')
    source_nick, _, _ = bot.parse_hostmask(source)
    if len(tokens) > 3 and tokens[3] == ':!help':
        bot.log('** Handling !help')
        if len(tokens) < 5:
            m = 'Use \x02!help [<topic>]\x02 with one of these topics:'
            m = '{} {}'.format(m, ', '.join(sorted(bot.c.HELP_TEXT.keys())))
            bot.send_privmsg(source_nick, m)
            return
        topic = tokens[4]
        if topic in bot.c.HELP_TEXT:
            for line in bot.c.HELP_TEXT.get(topic):
                bot.send_privmsg(source_nick, line)
            return
        m = 'I don\'t know anything about {}.'.format(topic)
        bot.send_privmsg(source_nick, m)


@bot.ee.on('PRIVMSG')
def handle_load(message):
    tokens = message.split()
    source = tokens[0].lstrip(':')
    source_nick, _, _ = bot.parse_hostmask(source)
    if len(tokens) > 3 and tokens[3] == ':!load':
        bot.log('** Handling !load')
        if len(tokens) < 5:
            m = 'Please specify a plugin to load.'
            bot.send_privmsg(source_nick, m)
            return
        plug_name = tokens[4]
        module_name = 'plugins.{}'.format(plug_name)
        if module_name in sys.modules:
            module = importlib.reload(module_name)
        else:
            try:
                module = importlib.import_module(module_name)
            except ImportError:
                m = 'Error while loading plugin: {}'.format(plug_name)
                bot.send_privmsg(source_nick, m)
                return
        for plug_handler in inspect.getmembers(module, inspect.isclass):
            cls = plug_handler[1]
            for cmd in cls.cmds:
                bot.c.PLUG_COMMANDS[cmd] = cls.handle
                topic = cmd.lstrip('!')
                bot.c.HELP_TEXT[topic] = cls.help_text
                m = 'Loaded a command: {}'.format(cmd)
                bot.send_privmsg(source_nick, m)


@bot.ee.on('PRIVMSG')
def dispatch_plugin_command(message):
    tokens = message.split()
    source = tokens[0].lstrip(':')
    source_nick, _, _ = bot.parse_hostmask(source)
    command = tokens[3].lstrip(':')
    if command in bot.c.PLUG_COMMANDS:
        handler = bot.c.PLUG_COMMANDS.get(command)
        try:
            text = message.split(' :')[1]
            tt = text.split()
            public, private = handler(source_nick, tokens[2], tt, bot.c)
        except Exception as exc:
            m = 'Exception in {}'.format(command)
            bot.log('** {}'.format(m))
            bot.log(exc)
            bot.send_privmsg(source_nick, m)
            return
        for m in public:
            bot.send_privmsg(bot.c.CHANNEL, m)
        for m in private:
            bot.send_privmsg(source_nick, m)


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
    new_nick = tokens[2].lstrip(':')
    if nick in bot.c.ADMINS:
        bot.add_admin(new_nick)
        bot.remove_admin(nick)


@bot.ee.on('PING')
def on_ping(message):
    bot.log('<= {}'.format(message))
    tokens = message.split()
    bot.out('PONG {}'.format(tokens[1]))


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
    bot.out('JOIN {}'.format(bot.c.CHANNEL))


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
    coro = loop.create_connection(bot, bot.c.HOST, bot.c.PORT)
    loop.run_until_complete(coro)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        bot.log('** Caught KeyboardInterrupt')
        loop.close()

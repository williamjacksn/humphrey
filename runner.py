import asyncio
import humphrey
import importlib
import inspect
import pathlib
import sys

config_file = pathlib.Path(__file__).resolve().with_name('config.json')
gbot = humphrey.IRCClient(config_file)
gbot.c.pretty = True
gbot.plug_commands = dict()
gbot.help_text = dict()


def load_plugin(plug_name, bot):
    loaded_commands = list()
    module_name = 'plugins.{}'.format(plug_name)
    if module_name in sys.modules:
        module = importlib.reload(module_name)
    else:
        try:
            module = importlib.import_module(module_name)
        except ImportError as exc:
            bot.log(exc)
            raise
    plugins = set(bot.c.get('plugins', list()))
    plugins.add(plug_name)
    bot.c['plugins'] = list(plugins)
    for plug_handler in inspect.getmembers(module, inspect.isclass):
        cls = plug_handler[1]
        for cmd in cls.cmds:
            bot.plug_commands[cmd] = cls.handle
            topic = cmd.lstrip('!')
            bot.help_text[topic] = cls.help_text
            loaded_commands.append(cmd)
    return loaded_commands


def initialize_plugins(bot):
    for plug in bot.c.get('plugins', list()):
        try:
            commands = load_plugin(plug, bot)
        except ImportError:
            continue
        for command in commands:
            bot.log('** Loaded a command: {}'.format(command))

initialize_plugins(gbot)


@gbot.ee.on('PRIVMSG')
def log_privmsg(message, bot):
    bot.log('<= {}'.format(message))


@gbot.ee.on('PRIVMSG')
def handle_help(message, bot):
    tokens = message.split()
    source = tokens[0].lstrip(':')
    source_nick, _, _ = bot.parse_hostmask(source)
    if len(tokens) > 3 and tokens[3] == ':!help':
        bot.log('** Handling !help')
        if len(tokens) < 5:
            m = 'Use \x02!help [<topic>]\x02 with one of these topics:'
            m = '{} {}'.format(m, ', '.join(sorted(bot.help_text.keys())))
            bot.send_privmsg(source_nick, m)
            return
        topic = tokens[4]
        if topic in bot.help_text:
            for line in bot.help_text.get(topic):
                bot.send_privmsg(source_nick, line)
            return
        m = 'I don\'t know anything about {}.'.format(topic)
        bot.send_privmsg(source_nick, m)


@gbot.ee.on('PRIVMSG')
def handle_load(message, bot):
    tokens = message.split()
    source = tokens[0].lstrip(':')
    source_nick, _, _ = bot.parse_hostmask(source)
    if source_nick not in bot.c.admins:
        return
    if len(tokens) > 3 and tokens[3] == ':!load':
        bot.log('** Handling !load')
        if len(tokens) < 5:
            m = 'Please specify a plugin to load.'
            bot.send_privmsg(source_nick, m)
            return
        plug_name = tokens[4]
        try:
            commands = load_plugin(plug_name, bot)
        except ImportError:
            m = 'Error loading plugin {}. Check the logs.'.format(plug_name)
            bot.send_privmsg(source_nick, m)
            return
        for command in commands:
            m = 'Loaded a command: {}'.format(command)
            bot.send_privmsg(source_nick, m)


@gbot.ee.on('PRIVMSG')
def dispatch_plugin_command(message, bot):
    tokens = message.split()
    source = tokens[0].lstrip(':')
    source_nick, _, _ = bot.parse_hostmask(source)
    command = tokens[3].lstrip(':')
    if command in bot.plug_commands:
        handler = bot.plug_commands.get(command)
        try:
            text = message.split(' :')[1]
            tt = text.split()
            public, private = handler(source_nick, tokens[2], tt, bot)
        except Exception as exc:
            m = 'Exception in {}'.format(command)
            bot.log('** {}'.format(m))
            bot.log(exc)
            bot.send_privmsg(source_nick, m)
            return
        for m in public:
            bot.send_privmsg(bot.c.get('irc:channel'), m)
        for m in private:
            bot.send_privmsg(source_nick, m)


@gbot.ee.on('MODE')
def on_mode(message, bot):
    bot.log('<= {}'.format(message))
    tokens = message.split()
    target = tokens[2]
    if target == bot.c.get('irc:channel'):
        modes = list()
        modespec = tokens[3]
        mode_action = ''
        for char in modespec:
            if char in ['+', '-']:
                mode_action = char
            else:
                modes.append('{}{}'.format(mode_action, char))
        for mode, nick in zip(modes, tokens[4:]):
            if mode in ['+h', '+o']:
                bot.add_admin(nick)
            elif mode in ['-h', '-o']:
                bot.remove_admin(nick)


@gbot.ee.on('NICK')
def on_nick(message, bot):
    bot.log('<= {}'.format(message))
    tokens = message.split()
    source = tokens[0].lstrip(':')
    nick, _, _ = bot.parse_hostmask(source)
    new_nick = tokens[2].lstrip(':')
    if nick in bot.admins:
        bot.add_admin(new_nick)
        bot.remove_admin(nick)


@gbot.ee.on('PART')
def on_part(message, bot):
    bot.log('<= {}'.format(message))
    tokens = message.split()
    source = tokens[0].lstrip(':')
    nick, _, _ = bot.parse_hostmask(source)
    if nick in bot.admins:
        bot.remove_admin(nick)


@gbot.ee.on('PING')
def on_ping(message, bot):
    bot.log('<= {}'.format(message))
    tokens = message.split()
    bot.out('PONG {}'.format(tokens[1]))


@gbot.ee.on('QUIT')
def on_quit(message, bot):
    bot.log('<= {}'.format(message))
    tokens = message.split()
    source = tokens[0].lstrip(':')
    nick, _, _ = bot.parse_hostmask(source)
    if nick in bot.admins:
        bot.remove_admin(nick)


@gbot.ee.on('353')
def on_rpl_namreply(message, bot):
    bot.log('<= {}'.format(message))
    tokens = message.split()
    for name in tokens[5:]:
        name = name.lstrip(':')
        if name.startswith(('~', '@', '%')):
            bot.add_admin(name.lstrip('~@%'))


@gbot.ee.on('376')
def on_rpl_endofmotd(message, bot):
    bot.log('<= {}'.format(message))
    bot.out('JOIN {}'.format(bot.c['irc:channel']))


@gbot.ee.on('001')  # RPL_WELCOME
@gbot.ee.on('002')  # RPL_YOURHOST
@gbot.ee.on('003')  # RPL_CREATED
@gbot.ee.on('004')  # RPL_MYINFO
@gbot.ee.on('005')  # RPL_ISUPPORT
@gbot.ee.on('251')  # RPL_LUSERCLIENT
@gbot.ee.on('252')  # RPL_LUSEROP
@gbot.ee.on('253')  # RPL_LUSERUNKNOWN
@gbot.ee.on('254')  # RPL_LUSERCHANNELS
@gbot.ee.on('255')  # RPL_LUSERME
@gbot.ee.on('265')  # RPL_LOCALUSERS
@gbot.ee.on('266')  # RPL_GLOBALUSERS
@gbot.ee.on('332')  # RPL_TOPIC
@gbot.ee.on('333')  # RPL_TOPICWHOTIME
@gbot.ee.on('366')  # RPL_ENDOFNAMES
@gbot.ee.on('372')  # RPL_MOTD
@gbot.ee.on('375')  # RPL_MOTDSTART
@gbot.ee.on('451')  # ERR_NOTREGISTERED
@gbot.ee.on('ACTION')
@gbot.ee.on('JOIN')
@gbot.ee.on('NOTICE')
@gbot.ee.on('TOPIC')
def known(message, bot):
    bot.log('<= {}'.format(message))


@gbot.ee.on('catch_all')
def unknown(message, bot):
    bot.log('XX {}'.format(message))


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    host = gbot.c.get('irc:host')
    port = gbot.c.get('irc:port')
    coro = loop.create_connection(gbot, host, port)
    loop.run_until_complete(coro)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        gbot.log('** Caught KeyboardInterrupt')
        loop.close()

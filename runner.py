import asyncio
import humphrey
import importlib
import inspect
import pathlib
import sys
import traceback

config_file = pathlib.Path(__file__).resolve().with_name('_config.json')
gbot = humphrey.IRCClient(config_file)
gbot.c.pretty = True
gbot.plug_commands = dict()
gbot.plug_commands_admin = dict()
gbot.help_text = dict()
gbot.help_text_admin = dict()


def load_plugin(plug_name, bot):
    loaded_commands = list()
    module_name = 'plugins.{}'.format(plug_name)
    if module_name in sys.modules:
        module = importlib.reload(sys.modules[module_name])
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
        help_dict = bot.help_text_admin if cls.admin else bot.help_text
        if hasattr(cls, 'help_topic'):
            help_dict[cls.help_topic] = cls.help_text
        cmd_dict = bot.plug_commands_admin if cls.admin else bot.plug_commands
        for cmd in cls.cmds:
            cmd_dict[cmd.lower()] = cls.handle
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
    if len(tokens) > 3 and tokens[3].lower() == ':!help':
        bot.log('** Handling !help')
        if len(tokens) < 5:
            m = 'Use \x02!help [<topic>]\x02 with one of these topics:'
            topics = list(bot.help_text.keys())
            if source_nick in bot.admins:
                topics += list(bot.help_text_admin.keys())
            m = '{} {}'.format(m, ', '.join(sorted(topics)))
            bot.send_privmsg(source_nick, m)
            return
        topic = tokens[4]
        lines = bot.help_text.get(topic)
        if lines is None and source_nick in bot.admins:
            lines = bot.help_text_admin.get(topic)
        if lines is not None:
            for line in lines:
                bot.send_privmsg(source_nick, line)
            return
        m = 'I don\'t know anything about {}.'.format(topic)
        bot.send_privmsg(source_nick, m)


@gbot.ee.on('PRIVMSG')
def handle_load(message, bot):
    tokens = message.split()
    source = tokens[0].lstrip(':')
    source_nick, _, _ = bot.parse_hostmask(source)
    if source_nick not in bot.admins:
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
    cmd = tokens[3].lstrip(':').lower()
    handler = bot.plug_commands.get(cmd)
    if handler is None and source_nick in bot.admins:
        handler = bot.plug_commands_admin.get(cmd)
    if handler is not None:
        try:
            text = message.split(' :', 1)[1]
            handler(source_nick, tokens[2], text.split(), bot)
        except Exception:
            m = 'Exception in {}. Check the logs.'.format(cmd)
            bot.log('** {}'.format(m))
            bot.log(traceback.format_exc())
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
    bot.add_member(new_nick)
    bot.remove_member(nick)


@gbot.ee.on('JOIN')
def on_join(message, bot):
    bot.log('<= {}'.format(message))
    tokens = message.split()
    source = tokens[0].lstrip(':')
    nick, _, _ = bot.parse_hostmask(source)
    bot.add_member(nick)


@gbot.ee.on('PART')
def on_part(message, bot):
    bot.log('<= {}'.format(message))
    tokens = message.split()
    source = tokens[0].lstrip(':')
    nick, _, _ = bot.parse_hostmask(source)
    bot.remove_member(nick)


@gbot.ee.on('QUIT')
def on_quit(message, bot):
    bot.log('<= {}'.format(message))
    tokens = message.split()
    source = tokens[0].lstrip(':')
    nick, _, _ = bot.parse_hostmask(source)
    bot.remove_member(nick)
    if nick in bot.admins:
        bot.remove_admin(nick)


@gbot.ee.on('353')
def on_rpl_namreply(message, bot):
    bot.log('<= {}'.format(message))
    tokens = message.split()
    for name in tokens[5:]:
        name = name.lstrip(':')
        nick = name.lstrip('~@%+')
        bot.add_member(nick)
        if name.startswith(('~', '@', '%')):
            bot.add_admin(nick)


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

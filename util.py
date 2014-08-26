import config
import datetime

def log(message):
    t = datetime.datetime.utcnow()
    print('{} {}'.format(t, message))

def smart_decode(message):
    try:
        return message.decode()
    except UnicodeDecodeError:
        pass
    try:
        return message.decode('iso-8859-1')
    except:
        for b in message:
            log('{} {}'.format(chr(b), b))
        raise

def parse_hostmask(hostmask):
    # 'nick!user@host' => ('nick', 'user', 'host')
    nick, _, userhost = hostmask.partition('!')
    user, _, host = userhost.partition('@')
    return nick, user, host

def add_admin(nick):
    log('** Added {} to admins list'.format(nick))
    config.ADMINS.add(nick)

def remove_admin(nick):
    log('** Removed {} from admins list'.format(nick))
    config.ADMINS.discard(nick)

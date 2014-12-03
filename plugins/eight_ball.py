import random
import time


def is_irc_channel(s):
    return s and s[0] == '#'


class EightBallHandler:
    cmds = ['!8ball']
    admin = False
    help_text = ['Use \x02!8ball\x02 to ask a question of the magic 8ball.']

    RESPONSES = [
        'As I see it, yes.',
        'Ask again later.',
        'Better not tell you now.',
        'Cannot predict now.',
        'Concentrate and ask again.',
        'Don\'t count on it.',
        'It is certain.',
        'It is decidedly so.',
        'Most likely.',
        'My reply is no.',
        'My sources say no.',
        'Outlook good.',
        'Outlook not so good.',
        'Reply hazy, try again.',
        'Signs point to yes.',
        'Very doubtful.',
        'Without a doubt.',
        'Yes.',
        'Yes - definitely.',
        'You may rely on it.'
    ]

    @classmethod
    def handle(cls, sender, target, tokens, config):
        if not hasattr(config, 'EIGHT_BALL'):
            config.EIGHT_BALL = dict()
        c = config.EIGHT_BALL

        public = list()
        private = list()
        response = random.choice(cls.RESPONSES)

        if not is_irc_channel(target):
            private.append(response)
            return public, private

        now = int(time.time())
        last = int(c.get('8ball:last', 0))
        wait = int(c.get('8ball:wait', 0))
        if last < now - wait:
            public.append(response)
            if 'again' not in response:
                c['8ball:last'] = now
        else:
            private.append(response)
            remaining = last + wait - now
            m = 'I am cooling down. You cannot use {}'.format(tokens[0])
            m = '{} in {} for another'.format(m, target)
            m = '{} {} seconds.'.format(m, remaining)
            private.append(m)

        return public, private

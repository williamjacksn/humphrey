#!/usr/bin/env python3

import asyncio
import humphrey
import pathlib


def main():
    config_file = pathlib.Path(__file__).resolve().with_name("basic.json")
    irc = humphrey.IRCClient(config_file)
    irc.c.pretty = True
    irc.debug = True

    @irc.ee.on("376")
    def on_rpl_endofmotd(_, bot):
        bot.out("JOIN {}".format(bot.c.get("irc:channel")))

    loop = asyncio.get_event_loop()
    host = irc.c.get("irc:host")
    port = irc.c.get("irc:port")
    coro = loop.create_connection(irc, host, port)
    loop.run_until_complete(coro)
    loop.run_forever()


if __name__ == "__main__":
    main()

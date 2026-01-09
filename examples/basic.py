#!/usr/bin/env python3

import asyncio
import logging
import pathlib
import sys

import humphrey


def main() -> None:
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    config_file = pathlib.Path(__file__).resolve().with_name("basic.json")
    irc = humphrey.IRCClient(config_file)
    irc.c.pretty = True
    irc.debug = True

    if "irc:channel" not in irc.c:
        irc.c["irc:channel"] = "#humphrey"
        logging.warning(f'Edit {irc.c.path} and set "irc:channel"')
        return

    @irc.ee.on("376")
    def on_rpl_endofmotd(_: str, bot: humphrey.IRCClient) -> None:
        bot.out("JOIN {}".format(bot.c.get("irc:channel")))

    loop = asyncio.get_event_loop()
    host = irc.c.get("irc:host")
    if host is None:
        host = irc.c["irc:host"] = "irc.synirc.net"
    port = irc.c.get("irc:port")
    if port is None:
        port = irc.c["irc:port"] = 6660
    coro = loop.create_connection(irc, host, port)
    loop.run_until_complete(coro)
    loop.run_forever()


if __name__ == "__main__":
    main()

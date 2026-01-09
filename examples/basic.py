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

    @irc.ee.on("376")
    def on_rpl_endofmotd(_: str, bot: humphrey.IRCClient) -> None:
        bot.out(f"JOIN {bot.c['irc:channel']}")

    loop = asyncio.new_event_loop()
    coro = loop.create_connection(irc, irc.c["irc:host"], irc.c["irc:port"])
    loop.run_until_complete(coro)
    loop.run_forever()


if __name__ == "__main__":
    main()

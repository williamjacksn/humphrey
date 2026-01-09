import asyncio
import collections
import json
import logging
import pathlib
from collections.abc import Callable, KeysView
from typing import Any

log = logging.getLogger(__name__)


class EventEmitter:
    def __init__(self) -> None:
        self._events = collections.defaultdict(list)

    def on(self, event: str, func: Callable | None = None) -> Callable:
        def _on(f: Callable) -> Callable:
            self._events[event].append(f)
            return f

        if func is None:
            return _on
        return _on(func)

    def emit(self, event: str, *args, **kwargs) -> bool:  # noqa: ANN002, ANN003
        handled = False
        for f in self._events[event]:
            f(*args, **kwargs)
            handled = True
        if not handled:
            for f in self._events["catch_all"]:
                f(*args, **kwargs)
        return handled


class Config:
    def __init__(self, path: pathlib.Path, pretty: bool = False) -> None:
        self.data = {}
        self.path = path
        self.pretty = pretty
        if self.path.exists():
            with self.path.open() as f:
                self.data = json.load(f)

    def __contains__(self, item: str) -> bool:
        return item in self.data

    def __getitem__(self, key: str) -> Any:  # noqa: ANN401
        return self.data[key]

    def __setitem__(self, key: str, value: Any) -> None:  # noqa: ANN401
        self.data[key] = value
        self._flush()

    def _flush(self) -> None:
        with self.path.open("w") as f:
            if self.pretty:
                json.dump(self.data, f, indent=2, sort_keys=True)
            else:
                json.dump(self.data, f)

    def get(self, key: str, default: Any = None) -> Any:  # noqa: ANN401
        return self.data.get(key, default)

    def keys(self) -> KeysView:
        return self.data.keys()

    def remove(self, key: str) -> None:
        if key in self.data:
            del self.data[key]
            self._flush()

    def set(self, key: str, value: Any) -> None:  # noqa: ANN401
        self[key] = value


class IRCClient(asyncio.Protocol):
    def __init__(self, config_path: pathlib.Path) -> None:
        self.buf = b""
        self.ee = EventEmitter()
        self.c = Config(config_path)
        self.loop = asyncio.get_event_loop()
        self.t = None
        self.debug = False
        self.admins = collections.defaultdict(set)
        self.members = collections.defaultdict(set)
        self.in_channel = False
        self.topics = {}

    def __call__(self) -> "IRCClient":
        return self

    @staticmethod
    def is_irc_channel(s: str) -> bool:
        return bool(s) and s.startswith("#")

    @staticmethod
    def remove_format_codes(m: bytes) -> bytes:
        m = m.replace(b"\x02", b"")  # bold
        m = m.replace(b"\x0f", b"")  # normal
        m = m.replace(b"\x16", b"")  # italic/reversed
        m = m.replace(b"\x1f", b"")  # underline
        while 3 in m:  # color
            idx = m.find(3)
            mark = idx + 1
            if m[mark : mark + 2].isdigit():
                mark += 2
            elif m[mark : mark + 1].isdigit():
                mark += 1
            if len(m) > mark and m[mark] == 44:  # b','
                if m[mark + 1 : mark + 3].isdigit():
                    mark += 3
                elif m[mark + 1 : mark + 2].isdigit():
                    mark += 2
            m = m.replace(m[idx:mark], b"")
        return m

    def smart_decode(self, m: bytes) -> str:
        m = self.remove_format_codes(m)
        try:
            return m.decode()
        except UnicodeDecodeError:
            log.warning("Failed decode using utf-8, trying next encoding.")
        try:
            return m.decode("iso-8859-1")
        except:
            log.exception("Failed decode using iso-8859-1.")
            log.debug(repr(m))
            raise

    @staticmethod
    def parse_hostmask(hostmask: str) -> tuple[str, str, str]:
        # 'nick!user@host' => ('nick', 'user', 'host')
        nick, _, user_host = hostmask.partition("!")
        user, _, host = user_host.partition("@")
        return nick, user, host

    def is_admin(self, nick: str) -> bool:
        for admins in self.admins.values():
            if nick in admins:
                return True
        return False

    def add_admin(self, channel: str, nick: str) -> None:
        log.debug(f"Added {nick} to {channel} admins list")
        self.admins[channel].add(nick)
        self.members[channel].add(nick)

    def remove_admin(self, channel: str, nick: str) -> None:
        log.debug(f"Removed {nick} from {channel} admins list")
        self.admins[channel].discard(nick)

    def add_member(self, channel: str, nick: str) -> None:
        log.debug(f"Added {nick} to {channel} members list")
        self.members[channel].add(nick)

    def remove_member(self, channel: str, nick: str) -> None:
        log.debug(f"Removed {nick} from {channel} members list")
        self.members[channel].discard(nick)
        self.admins[channel].discard(nick)

    def connection_made(self, transport: asyncio.Transport) -> None:
        self.t = transport
        log.debug("Connection made")
        nick = self.c.get("irc:nick")
        if nick is None:
            self.c["irc:nick"] = "humphrey"
            log.warning("Edit {} and set {!r}".format(self.c.path, "irc:nick"))
            self.loop.stop()
        self.out(f"NICK {nick}")
        m = "USER {} {} x :{}"
        ident = self.c.get("irc:ident")
        if ident is None:
            self.c["irc:ident"] = "humphrey"
            log.warning("Edit {} and set {!r}".format(self.c.path, "irc:ident"))
            self.loop.stop()
        name = self.c.get("irc:name")
        if name is None:
            self.c["irc:name"] = "Humphrey"
            log.warning("Edit {} and set {!r}".format(self.c.path, "irc:name"))
            self.loop.stop()
        self.out(m.format(ident, self.c["irc:host"], name))

    def data_received(self, data: bytes) -> None:
        self.buf = self.buf + data
        lines = self.buf.split(b"\n")
        self.buf = lines.pop()
        for line in lines:
            line = line.strip()
            self.loop.call_soon(self._in, line)

    def connection_lost(self, exc: Exception | None) -> None:
        log.debug("Connection lost")
        self.loop.stop()

    def _in(self, message: bytes) -> None:
        # convert message from bytes to str then emit an appropriate event
        message = self.smart_decode(message)
        log.debug(f"<= {message}")
        tokens = message.split()
        if len(tokens) > 0 and tokens[0] == "PING":
            self.out(f"PONG {tokens[1]}")
            self.ee.emit(tokens[0], message, self)
        elif len(tokens) > 3 and tokens[3] == ":\x01ACTION":
            self.ee.emit("ACTION", message, self)
        elif len(tokens) > 1:
            if tokens[1] == "353":
                self._handle_namreply(tokens)
            elif tokens[1] == "366":
                self.in_channel = True
            elif tokens[1] == "JOIN":
                self._handle_join(tokens)
            elif tokens[1] == "MODE":
                self._handle_mode(tokens)
            elif tokens[1] == "NICK":
                self._handle_nick(tokens)
            elif tokens[1] == "PART":
                self._handle_part(tokens)
            elif tokens[1] == "QUIT":
                self._handle_quit(tokens)
            elif tokens[1] == "TOPIC" or tokens[1] == "332":
                self._handle_topic(message)
            self.ee.emit(tokens[1], message, self)
        else:
            self.ee.emit("catch_all", message, self)

    def out(self, message: str) -> None:
        # log messages, then convert from str to bytes and write to transport
        if message:
            log.debug(f"=> {message}")
            self.t.write(f"{message}\r\n".encode())

    def send_action(self, target: str, message: str) -> None:
        self.out(f"PRIVMSG {target} :\x01ACTION {message}\x01")

    def send_privmsg(self, target: str, message: str) -> None:
        self.out(f"PRIVMSG {target} :{message}")

    def send_topic(self, target: str, topic: str) -> None:
        self.out(f"TOPIC {target} :{topic}")

    def _handle_join(self, tokens: list[str]) -> None:
        source = tokens[0].lstrip(":")
        nick, _, _ = self.parse_hostmask(source)
        channel = tokens[2].lstrip(":")
        self.add_member(channel, nick)

    def _handle_mode(self, tokens: list[str]) -> None:
        target = tokens[2]
        if self.is_irc_channel(target):
            modes = []
            mode_spec = tokens[3]
            mode_action = ""
            for char in mode_spec:
                if char in ["+", "-"]:
                    mode_action = char
                else:
                    modes.append(mode_action + char)
            for mode, nick in zip(modes, tokens[4:]):
                if mode in ["+h", "+o"]:
                    self.add_admin(target, nick)
                elif mode in ["-h", "-o"]:
                    self.remove_admin(target, nick)

    def _handle_namreply(self, tokens: list[str]) -> None:
        channel = tokens[4]
        for name in tokens[5:]:
            name = name.lstrip(":")
            nick = name.lstrip("~@%+")
            self.add_member(channel, nick)
            if name.startswith(("~", "@", "%")):
                self.add_admin(channel, nick)

    def _handle_nick(self, tokens: list[str]) -> None:
        source = tokens[0].lstrip(":")
        nick, _, _ = self.parse_hostmask(source)
        new_nick = tokens[2].lstrip(":")
        for channel, admins in self.admins.items():
            if nick in admins:
                self.add_admin(channel, new_nick)
                self.remove_admin(channel, nick)
        for channel, members in self.members.items():
            if nick in members:
                self.add_member(channel, new_nick)
                self.remove_member(channel, nick)

    def _handle_part(self, tokens: list[str]) -> None:
        source = tokens[0].lstrip(":")
        nick, _, _ = self.parse_hostmask(source)
        channel = tokens[2]
        self.remove_member(channel, nick)

    def _handle_quit(self, tokens: list[str]) -> None:
        source = tokens[0].lstrip(":")
        nick, _, _ = self.parse_hostmask(source)
        for channel in self.members.keys():
            self.remove_member(channel, nick)

    def _handle_topic(self, message: str) -> None:
        tokens = message.split()
        if tokens[1] == "TOPIC":
            channel = tokens[2]
        else:
            channel = tokens[3]
        new_topic = message.split(" :", maxsplit=1)[1]
        self.topics[channel] = new_topic
        log.debug(f"Setting {channel} topic to {new_topic!r}")

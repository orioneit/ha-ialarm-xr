"""Async client for iAlarm-XR panels through the vendor cloud.

The panel keeps an outbound connection to the vendor cloud; the mobile app
reaches the panel through the same server. This client does what the app does.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import logging
import re

_LOGGER = logging.getLogger(__name__)

_KEY = bytes.fromhex(
    "0c384e4e62382d620e384e4e44382d300f382b382b0c5a6234384e304e4c372b"
    "10535a0c20432d171142444e58422c421157322a204036172056446262382b5f"
    "0c384e4e62382d620e385858082e232c0f382b382b0c5a62343830304e2e362b"
    "10545a0c3e432e1711384e625824371c1157324220402c17204c444e624c2e12"
)
_HEADER = re.compile(rb"@ieM(\d{4})(\d{4})0000")

STATUS_ARM = "ARM"
STATUS_DISARM = "DISARM"
STATUS_STAY = "STAY"
STATUS_CLEAR = "CLEAR"

_COMMANDS = {
    STATUS_ARM: 0,
    STATUS_DISARM: 1,
    STATUS_STAY: 2,
    STATUS_CLEAR: 3,
}

# GetByWay zone status bits
ZONE_IN_USE = 1
ZONE_ALARM = 2
ZONE_BYPASS = 4
ZONE_FAULT = 8
ZONE_LOW_BATTERY = 16
ZONE_LOST = 32


def xor(data: bytes) -> bytes:
    """Apply the Meian XOR obfuscation (symmetric)."""
    return bytes(c ^ _KEY[i & 0x7F] for i, c in enumerate(data))


class IAlarmError(Exception):
    """Generic communication error."""


class IAlarmAuthError(IAlarmError):
    """The cloud rejected the panel ID/password."""


@dataclass
class Zone:
    """A configured zone of the panel."""

    number: int
    name: str
    type: str
    enabled: bool
    raw: int | None = None

    def _bit(self, bit: int) -> bool | None:
        return None if self.raw is None else bool(self.raw & bit)

    @property
    def alarm(self) -> bool | None:
        return self._bit(ZONE_ALARM)

    @property
    def bypass(self) -> bool | None:
        return self._bit(ZONE_BYPASS)

    @property
    def fault(self) -> bool | None:
        return self._bit(ZONE_FAULT)

    @property
    def low_battery(self) -> bool | None:
        return self._bit(ZONE_LOW_BATTERY)

    @property
    def lost(self) -> bool | None:
        return self._bit(ZONE_LOST)


@dataclass
class PanelData:
    """Snapshot of the panel state."""

    status: str
    zones: dict[int, Zone] = field(default_factory=dict)

    @property
    def triggered(self) -> bool:
        return any(z.alarm for z in self.zones.values() if z.enabled)


class _Session:
    """One TCP session to the cloud, paired with the panel."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, timeout: float) -> None:
        self._reader = reader
        self._writer = writer
        self._timeout = timeout
        self._seq = 0
        self._buf = b""

    async def close(self) -> None:
        self._writer.close()
        try:
            await self._writer.wait_closed()
        except OSError:
            pass

    async def _send(self, xml: str) -> None:
        body = xor(xml.encode())
        frame = b"@ieM%04d%04d0000%s%04d" % (len(body), self._seq, body, self._seq)
        self._seq = (self._seq + 1) % 10000
        self._writer.write(frame)
        await self._writer.drain()

    async def _recv(self) -> str:
        while True:
            match = _HEADER.search(self._buf)
            if match:
                size = int(match.group(1))
                start = match.end()
                if len(self._buf) >= start + size + 4:
                    body = self._buf[start : start + size]
                    self._buf = self._buf[start + size + 4 :]
                    return xor(body).decode("utf-8", "replace")
            chunk = await asyncio.wait_for(self._reader.read(4096), self._timeout)
            if not chunk:
                raise IAlarmError("Connection closed by the cloud server")
            self._buf += chunk

    async def request(self, xml: str, expect: str) -> str:
        await self._send(xml)
        for _ in range(10):  # skip unrelated messages
            reply = await self._recv()
            if expect in reply:
                return reply
        raise IAlarmError(f"No reply for {expect}")

    async def paged(self, tag: str) -> list[str]:
        items: list[str] = []
        offset = 0
        while True:
            reply = await self.request(
                f"<Root><Host><{tag}><Total/><Offset>S32,0,0|{offset}</Offset><Ln/><Err/></{tag}></Host></Root>",
                f"<{tag}>",
            )
            total = re.search(r"<Total>[^|]*\|(\d+)</Total>", reply)
            count = re.search(r"<Ln>[^|]*\|(\d+)</Ln>", reply)
            if not total or not count:
                raise IAlarmError(f"Unexpected {tag} reply")
            num = int(count.group(1))
            for i in range(num):
                item = re.search(rf"<L{i}>(.*?)</L{i}>", reply)
                items.append(item.group(1) if item else "")
            offset += num
            if num == 0 or offset >= int(total.group(1)):
                return items


class IAlarmXR:
    """High level client."""

    def __init__(
        self,
        device_id: str,
        password: str,
        host: str,
        port: int,
        timeout: float = 10,
    ) -> None:
        self.device_id = device_id
        self._password = password
        self._host = host
        self._port = port
        self._timeout = timeout
        self._lock = asyncio.Lock()
        self._zone_cache: list[str] | None = None

    async def _open(self) -> _Session:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port), self._timeout
            )
        except (OSError, asyncio.TimeoutError) as err:
            raise IAlarmError(f"Cannot connect to {self._host}:{self._port}: {err}") from err
        session = _Session(reader, writer, self._timeout)
        try:
            reply = await session.request(
                "<Root><Pair><Client>"
                f"<Id>STR,10|{self.device_id}</Id><Pwd>PWD,8|{self._password}</Pwd>"
                "<Type>TYP,ANDROID|0</Type><Token>STR,152|</Token><Action>TYP,IN|0</Action>"
                "<PemNum>STR,5|26</PemNum><DevVersion/><DevType/><Err/>"
                "</Client></Pair></Root>",
                "<Pair>",
            )
        except BaseException:
            await session.close()
            raise
        err = re.search(r"<Err>ERR\|(\d+)</Err>", reply)
        if not err or err.group(1) != "00":
            await session.close()
            raise IAlarmAuthError(f"Pairing rejected (error {err.group(1) if err else '?'})")
        return session

    async def validate(self) -> None:
        """Check that ID and password are accepted."""
        async with self._lock:
            session = await self._open()
            await session.close()

    async def fetch(self, refresh_names: bool = False) -> PanelData:
        """Read alarm status and zone states in a single session."""
        async with self._lock:
            session = await self._open()
            try:
                reply = await session.request(
                    "<Root><Host><GetAlarmStatus><DevStatus/><Err/></GetAlarmStatus></Host></Root>",
                    "<GetAlarmStatus>",
                )
                match = re.search(r"<DevStatus>TYP,([A-Z]+)\|", reply)
                status = match.group(1) if match else "UNKNOWN"
                if refresh_names or self._zone_cache is None:
                    self._zone_cache = await session.paged("GetZone")
                states = await session.paged("GetByWay")
            except asyncio.TimeoutError as err:
                raise IAlarmError("Timeout talking to the cloud") from err
            finally:
                await session.close()
        return PanelData(status=status, zones=_parse_zones(self._zone_cache, states))

    async def set_status(self, status: str) -> None:
        """Send an arm/disarm command."""
        code = _COMMANDS[status]
        async with self._lock:
            session = await self._open()
            try:
                reply = await session.request(
                    "<Root><Host><SetAlarmStatus>"
                    f"<DevStatus>TYP,{status}|{code}</DevStatus><Err/>"
                    "</SetAlarmStatus></Host></Root>",
                    "<SetAlarmStatus>",
                )
            except asyncio.TimeoutError as err:
                raise IAlarmError("Timeout talking to the cloud") from err
            finally:
                await session.close()
        if "<Err>ERR|00</Err>" not in reply:
            raise IAlarmError(f"Command {status} rejected")


def _parse_zones(names: list[str], states: list[str]) -> dict[int, Zone]:
    zones: dict[int, Zone] = {}
    for index, item in enumerate(names):
        name = re.search(r"<Name>[^|]*\|([^<]*)</Name>", item)
        if not name or not name.group(1).strip():
            continue  # unnamed zone: not configured
        typ = re.search(r"<Type>TYP,([A-Z0-9]+)\|", item)
        typ_s = typ.group(1) if typ else ""
        raw = None
        if index < len(states):
            value = re.search(r"\|(\d+)$", states[index])
            raw = int(value.group(1)) if value else None
        zones[index + 1] = Zone(
            number=index + 1,
            name=name.group(1).strip(),
            type=typ_s,
            enabled=bool(typ_s) and typ_s != "NO",
            raw=raw,
        )
    return zones

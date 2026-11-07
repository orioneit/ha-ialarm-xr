"""A fake iAlarm cloud server speaking the Meian protocol."""

from __future__ import annotations

import asyncio
import re

from custom_components.ialarm_xr.api import xor

ZONES = [
    ("SI", "Lavanderia"), ("DE", "Portone"), ("SI", "Sala Persiana"), ("SI", "Bagno"),
    ("SI", "CamerinaPersiana"), ("SI", "CucinaPersiana"), ("SI", "Camera"), ("SI", "CameraPersiana"),
    ("NO", "Tunnel Pir"), ("NO", "Retro Cucina"),
] + [("SI", "")] * 30
CODES = {"ARM": 0, "DISARM": 1, "STAY": 2, "CLEAR": 3}


def frame(xml: str, seq: int = 0) -> bytes:
    body = xor(xml.encode())
    return b"@ieM%04d%04d0000%s%04d" % (len(body), seq, body, seq)


class FakeCloud:
    def __init__(self, device_id="0123456789", password="secret") -> None:
        self.device_id = device_id
        self.password = password
        self.status = "DISARM"
        self.zone_raw = [1] * 40
        self.zone_raw[5] = 17  # CucinaPersiana low battery
        self.commands: list[str] = []
        self.server: asyncio.base_events.Server | None = None
        self.port = 0

    async def start(self) -> None:
        self.server = await asyncio.start_server(self._handle, "127.0.0.1", 0)
        self.port = self.server.sockets[0].getsockname()[1]

    async def stop(self) -> None:
        self.server.close()
        await self.server.wait_closed()

    def _reply(self, xml: str) -> str | None:
        if "<Pair>" in xml:
            ok = f"|{self.device_id}<" in xml and f"|{self.password}<" in xml
            return xml.replace("<Err/>", "<Err>ERR|00</Err>" if ok else "<Err>ERR|01</Err>")
        if "<GetAlarmStatus>" in xml:
            code = CODES.get(self.status, 1)
            return (f"<Root><Host><GetAlarmStatus><DevStatus>TYP,{self.status}|{code}</DevStatus>"
                    "<Err>ERR|00</Err></GetAlarmStatus></Host></Root>")
        if "<SetAlarmStatus>" in xml:
            new = re.search(r"TYP,([A-Z]+)\|", xml).group(1)
            self.commands.append(new)
            self.status = "DISARM" if new == "CLEAR" else new
            return xml.replace("<Err/>", "<Err>ERR|00</Err>")
        for tag, per_page in (("GetZone", 2), ("GetByWay", 10)):
            if f"<{tag}>" in xml:
                off = int(re.search(r"\|(\d+)</Offset>", xml).group(1))
                items = ""
                for i in range(per_page):
                    idx = off + i
                    if tag == "GetZone":
                        typ, name = ZONES[idx]
                        items += (f"<L{i}><Type>TYP,{typ}|1</Type><Voice>TYP,CX|1</Voice>"
                                  f"<Name>STR,16|{name}</Name><Bell>BOL|F</Bell></L{i}>")
                    else:
                        items += f"<L{i}>S32,1,255|{self.zone_raw[idx]}</L{i}>"
                return (f"<Root><Host><{tag}><Total>S32,0,40|40</Total><Offset>S32,0,40|{off}</Offset>"
                        f"<Ln>S32,0,40|{per_page}</Ln>{items}<Err>ERR|00</Err></{tag}></Host></Root>")
        return None

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        buf = b""
        try:
            while data := await reader.read(4096):
                buf += data
                while (m := re.search(rb"@ieM(\d{4})(\d{4})0000", buf)) and len(buf) >= m.end() + int(m.group(1)) + 4:
                    n = int(m.group(1))
                    xml = xor(buf[m.end() : m.end() + n]).decode()
                    buf = buf[m.end() + n + 4 :]
                    reply = self._reply(xml)
                    if reply:
                        writer.write(b"%maI" + frame(reply))  # keepalive noise + reply
                        await writer.drain()
        finally:
            writer.close()

import asyncio


class ModbusTCP:
  def __init__(self, host, port):
    self.host = host
    self.port = port
    self.reader = None
    self.writer = None

  async def connect(self, timeout=10):
    try:
      self.reader, self.writer = await asyncio.wait_for(asyncio.open_connection(self.host, self.port), timeout)
      print(f"Connected to {self.host}:{self.port} ")
    except asyncio.TimeoutError:
      print(f"Connection to {self.host}:{self.port} timed out.")
    except OSError as e:
      print(f"OS error occurred: {e}")

  async def main(self):
    await self.connect()


# Example usage
modbus_tcp = ModbusTCP("192.168.2.1", 502)
asyncio.run(modbus_tcp.main())

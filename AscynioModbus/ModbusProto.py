import asyncio
import socket
import struct


class AsyncModbusTCP:
  def __init__(self, host, port=502):
    self.host = host
    self.port = port
    self.transaction_id = 0

  async def build_request(self, unit_id, function_code, start_address, quantity):
    self.transaction_id += 1
    # MBAP Header
    mbap_header = struct.pack(">H H H B", self.transaction_id, 0, 6, unit_id)
    # PDU (Protocol Data Unit)
    pdu = struct.pack(">B H H", function_code, start_address, quantity)
    # Full Modbus TCP request
    request = mbap_header + pdu
    return request

  async def parse_response(self, response):
    if len(response) < 9:
      raise ValueError("Response is too short")
    return response[9:]

  async def read_holding_registers(self, unit_id, start_address, quantity):
    request = await self.build_request(unit_id, 3, start_address, quantity)

    reader, writer = await asyncio.open_connection(self.host, self.port)
    writer.write(request)
    await writer.drain()

    response = await reader.read(1024)
    writer.close()
    await writer.wait_closed()

    return await self.parse_response(response)


# 示例使用
async def main():
  modbus_tcp = AsyncModbusTCP(host="192.168.1.100")
  response = await modbus_tcp.read_holding_registers(unit_id=1, start_address=0, quantity=10)
  print(response)


asyncio.run(main())

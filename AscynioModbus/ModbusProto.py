import asyncio
import struct

from AscynioModbus import LOGGER, DataFormat, Exceptions


class AsyncModbusTCP:
  def __init__(self, host, port=502, data_format: DataFormat = DataFormat.UNSIGNED_16_INT_BIG):
    self.host = host
    self.port = port
    self.transaction_id = 0
    self.writer = None
    self.reader = None
    self.is_connected = False
    self.is_swap = False
    self.data_format = data_format

  async def connect(self, timeout=10):
    try:
      self.reader, self.writer = await asyncio.wait_for(asyncio.open_connection(self.host, self.port), timeout)
      self.is_connected = True
      LOGGER.debug(f"Connected to {self.host}:{self.port}")
    except asyncio.TimeoutError:
      LOGGER.error(f"Connection to {self.host}:{self.port} timed out.")
    except OSError as e:
      LOGGER.error(f"OS error occurred: {e}")

  async def disconnect(self):
    if self.writer:
      self.writer.close()
      await self.writer.wait_closed()
    self.is_connected = False
    LOGGER.debug(f"Disconnected from {self.host}:{self.port}")

  async def build_request(self, unit_id, function_code, start_address, quantity):
    if "SWAP" in self.data_format.name:
      self.is_swap = True

    if self.data_format in {
      DataFormat.UNSIGNED_16_INT_LITTLE,
      DataFormat.SIGNED_16_INT_LITTLE,
      DataFormat.UNSIGNED_16_INT_BIG_BYTE_SWAP,
      DataFormat.SIGNED_16_INT_BIG_BYTE_SWAP,
    }:
      self.format_str = "<" + ("H" * quantity) if "UNSIGNED" in self.data_format.name else "<" + ("h" * quantity)
    elif self.data_format in {
      DataFormat.UNSIGNED_16_INT_BIG,
      DataFormat.SIGNED_16_INT_BIG,
      DataFormat.UNSIGNED_16_INT_LITTLE_BYTE_SWAP,
      DataFormat.SIGNED_16_INT_LITTLE_BYTE_SWAP,
    }:
      self.format_str = ">" + ("H" * quantity) if "UNSIGNED" in self.data_format.name else ">" + ("h" * quantity)

    elif self.data_format in {
      DataFormat.UNSIGNED_32_INT_LITTLE,
      DataFormat.SIGNED_32_INT_LITTLE,
      DataFormat.UNSIGNED_32_INT_BIG_BYTE_SWAP,
      DataFormat.SIGNED_32_INT_BIG_BYTE_SWAP,
    }:
      self.format_str = "<" + ("I" * quantity) if "UNSIGNED" in self.data_format.name else "<" + ("i" * quantity)

    elif self.data_format in {
      DataFormat.UNSIGNED_32_INT_BIG,
      DataFormat.SIGNED_32_INT_BIG,
      DataFormat.UNSIGNED_32_INT_LITTLE_BYTE_SWAP,
      DataFormat.SIGNED_32_INT_LITTLE_BYTE_SWAP,
    }:
      self.format_str = ">" + ("I" * quantity) if "UNSIGNED" in self.data_format.name else ">" + ("i" * quantity)

    elif self.data_format in {
      DataFormat.UNSIGNED_64_INT_LITTLE,
      DataFormat.SIGNED_64_INT_LITTLE,
      DataFormat.UNSIGNED_64_INT_BIG_BYTE_SWAP,
      DataFormat.SIGNED_64_INT_BIG_BYTE_SWAP,
    }:
      self.format_str = "<" + ("Q" * quantity) if "UNSIGNED" in self.data_format.name else "<" + ("q" * quantity)

    elif self.data_format in {
      DataFormat.UNSIGNED_64_INT_BIG,
      DataFormat.SIGNED_64_INT_BIG,
      DataFormat.UNSIGNED_64_INT_LITTLE_BYTE_SWAP,
      DataFormat.SIGNED_64_INT_LITTLE_BYTE_SWAP,
    }:
      self.format_str = ">" + ("Q" * quantity) if "UNSIGNED" in self.data_format.name else ">" + ("q" * quantity)

    elif self.data_format in {DataFormat.FLOAT_32_LITTLE, DataFormat.FLOAT_32_BIG_BYTE_SWAP}:
      self.format_str = "<" + ("f" * quantity)

    elif self.data_format in {DataFormat.FLOAT_32_BIG, DataFormat.FLOAT_32_LITTLE_BYTE_SWAP}:
      self.format_str = ">" + ("f" * quantity)

    elif self.data_format in {DataFormat.DOUBLE_64_LITTLE, DataFormat.DOUBLE_64_BIG_BYTE_SWAP}:
      self.format_str = "<" + ("d" * quantity)

    elif self.data_format in {DataFormat.DOUBLE_64_BIG, DataFormat.DOUBLE_64_LITTLE_BYTE_SWAP}:
      self.format_str = ">" + ("d" * quantity)

    if "32" in self.data_format.name:
      quantity = quantity * 2

    elif "64" in self.data_format.name:
      quantity = quantity * 4

    else:
      raise ValueError(f"Unsupported data format: {self.data_format}")
    LOGGER.debug(f"format_str = {self.format_str}")

    self.transaction_id += 1
    # MBAP Header
    mbap_header = struct.pack(">H H H B", self.transaction_id, 0, 6, unit_id)
    # PDU (Protocol Data Unit)
    LOGGER.debug(f"quantity = {quantity}")
    pdu = struct.pack(">B H H", function_code, start_address, quantity)
    # Full Modbus TCP request
    request = mbap_header + pdu
    return request

  async def byte_swap(self, data):
    if not self.is_swap:
      return data

    # Create a mutable bytearray from the immutable bytes object
    data = bytearray(data)
    swapped_data = bytearray()

    # Swap bytes in groups of 4
    for i in range(0, len(data), 8):
      if i + 8 <= len(data):
        swapped_data.extend(data[i + 4 : i + 8] + data[i : i + 4])
      else:
        swapped_data.extend(data[i:])

    # Convert the bytearray back to bytes
    return bytes(swapped_data)

  async def parse_response(self, response, quantity):
    if len(response) < 9:
      raise ValueError("Response is too short")
    data = response[9:]
    data = await self.byte_swap(data)
    LOGGER.debug(f"Data = {data}")
    try:
      parsed_data = struct.unpack(self.format_str, data)
    except Exception as e:
      LOGGER.error(f"Exception : {e}")
    return parsed_data

  async def read_holding_registers(self, start_address, quantity, unit_id=1):
    if not self.is_connected:
      raise Exceptions.SlaveDeviceFailure("Connection not established")

    request = await self.build_request(unit_id, 3, start_address, quantity)
    self.writer.write(request)
    await self.writer.drain()

    try:
      response = await asyncio.wait_for(self.reader.read(1024), timeout=10)
    except asyncio.TimeoutError:
      LOGGER.error("Read operation timed out.")
      return None
    except Exception as e:
      LOGGER.error(f"Error reading response: {e}")
      return None
    # finally:
    #   await self.disconnect()

    return await self.parse_response(response, quantity)


# 示例使用
async def main():
  modbus_tcp = AsyncModbusTCP(host="192.168.1.100")
  await modbus_tcp.connect()
  if modbus_tcp.is_connected:
    try:
      response = await modbus_tcp.read_holding_registers(start_address=0, quantity=10, unit_id=1)
      LOGGER.debug(f"Response= {response}")
    except Exceptions.SlaveDeviceFailure as e:
      LOGGER.error(f"Failed to read holding registers: {e}")
    finally:
      await modbus_tcp.disconnect()


if __name__ == "__main__":
  asyncio.run(main())

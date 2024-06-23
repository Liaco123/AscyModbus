import asyncio
import struct

from AscynioModbus import Exceptions

from .DataFormat import DataFormat
from .ulitis import LOGGER


class AsyncModbusTCP:
  def __init__(self, host, port=502, data_format: DataFormat = DataFormat.UNSIGNED_16_INT_BIG):
    self.host = host
    self.port = port
    self.transaction_id = 0
    self.writer = None
    self.reader = None
    self.is_connected = False
    self.is_swap = False
    self.quantity = 0
    self.data_format = data_format
    self.read_lock = asyncio.Lock()
    self.init = True

  async def reconnect(self):
    self.is_connected = False
    for _ in range(3):
      try:
        self.reader, self.writer = await asyncio.wait_for(asyncio.open_connection(self.host, self.port), 1)
        self.is_connected = True
      finally:
        if self.is_connected:
          break  # noqa: B012

  async def connect(self, timeout=10):
    if self.is_connected:
      return True
    try:
      self.reader, self.writer = await asyncio.wait_for(asyncio.open_connection(self.host, self.port), timeout)
      self.is_connected = True
      if self.init:
        LOGGER.info(f"Connected to {self.host}:{self.port}")
        self.init = False
    except asyncio.TimeoutError as e:
      # LOGGER.error(f"Connection to {self.host}:{self.port} timed out.")
      raise TimeoutError(f"Connection to {self.host}:{self.port} timed out.") from e
    except OSError as e:
      # LOGGER.error(f"OS error occurred: {e}")
      raise OSError(f"Can not connect to {self.host}:{self.port} {e}") from e

  async def disconnect(self):
    try:
      if self.writer:
        self.writer.close()
        # self.reader.close()
        await self.writer.wait_closed()
      self.is_connected = False
      LOGGER.debug(f"Disconnected from {self.host}:{self.port}")
    except ConnectionResetError as e:
      LOGGER.error(f"ConnectionResetError occurred during disconnect: {e}")
      raise e
    except Exception as e:
      LOGGER.error(f"Error during disconnect: {e}")
      raise e

  async def build_request(self, unit_id, function_code, start_address, dates):
    quantity = dates if "read" in self.func else len(dates)
    if self.data_format in {
      DataFormat.UNSIGNED_16_INT_LITTLE,
      DataFormat.SIGNED_16_INT_LITTLE,
    }:
      self.format_str = "<" + ("H" * quantity) if "UNSIGNED" in self.data_format.name else "<" + ("h" * quantity)
    elif self.data_format in {
      DataFormat.UNSIGNED_16_INT_BIG,
      DataFormat.SIGNED_16_INT_BIG,
    }:
      self.format_str = ">" + ("H" * quantity) if "UNSIGNED" in self.data_format.name else ">" + ("h" * quantity)

    elif self.data_format in {
      DataFormat.UNSIGNED_32_INT_LITTLE,
      DataFormat.SIGNED_32_INT_LITTLE,
      DataFormat.UNSIGNED_32_INT_LITTLE_BYTE_SWAP,
      DataFormat.SIGNED_32_INT_LITTLE_BYTE_SWAP,
    }:
      self.format_str = "<" + ("I" * quantity) if "UNSIGNED" in self.data_format.name else "<" + ("i" * quantity)

    elif self.data_format in {
      DataFormat.UNSIGNED_32_INT_BIG,
      DataFormat.SIGNED_32_INT_BIG,
      DataFormat.UNSIGNED_32_INT_BIG_BYTE_SWAP,
      DataFormat.SIGNED_32_INT_BIG_BYTE_SWAP,
    }:
      self.format_str = ">" + ("I" * quantity) if "UNSIGNED" in self.data_format.name else ">" + ("i" * quantity)

    elif self.data_format in {
      DataFormat.UNSIGNED_64_INT_LITTLE,
      DataFormat.SIGNED_64_INT_LITTLE,
      DataFormat.UNSIGNED_64_INT_LITTLE_BYTE_SWAP,
      DataFormat.SIGNED_64_INT_LITTLE_BYTE_SWAP,
    }:
      self.format_str = "<" + ("Q" * quantity) if "UNSIGNED" in self.data_format.name else "<" + ("q" * quantity)

    elif self.data_format in {
      DataFormat.UNSIGNED_64_INT_BIG,
      DataFormat.SIGNED_64_INT_BIG,
      DataFormat.UNSIGNED_64_INT_BIG_BYTE_SWAP,
      DataFormat.SIGNED_64_INT_BIG_BYTE_SWAP,
    }:
      self.format_str = ">" + ("Q" * quantity) if "UNSIGNED" in self.data_format.name else ">" + ("q" * quantity)

    elif self.data_format in {DataFormat.FLOAT_32_LITTLE, DataFormat.FLOAT_32_LITTLE_BYTE_SWAP}:
      self.format_str = "<" + ("f" * quantity)

    elif self.data_format in {DataFormat.FLOAT_32_BIG, DataFormat.FLOAT_32_BIG_BYTE_SWAP}:
      self.format_str = ">" + ("f" * quantity)

    elif self.data_format in {DataFormat.DOUBLE_64_LITTLE, DataFormat.DOUBLE_64_LITTLE_BYTE_SWAP}:
      self.format_str = "<" + ("d" * quantity)

    elif self.data_format in {DataFormat.DOUBLE_64_BIG, DataFormat.DOUBLE_64_BIG_BYTE_SWAP}:
      self.format_str = ">" + ("d" * quantity)

    if "16" in self.data_format.name:
      des_quantity = quantity

    elif "32" in self.data_format.name:
      des_quantity = quantity * 2

    elif "64" in self.data_format.name:
      des_quantity = quantity * 4

    else:
      LOGGER.error(f"format_str = {self.format_str}")
      raise ValueError(f"Unsupported data format: {self.data_format}")

    self.transaction_id += 1

    if "read" in self.func:
      mbap_header = struct.pack(">H H H B", self.transaction_id, 0, 6, unit_id)
      pdu = struct.pack(">B H H", function_code, start_address, des_quantity)
    elif "write" in self.func:
      mbap_header = struct.pack(">H H H B", self.transaction_id, 0, 7 + 2 * des_quantity, unit_id)
      pdu = struct.pack(
        ">B H H B",
        function_code,
        start_address,
        des_quantity,
        2 * des_quantity,
      )
      datas = struct.pack(self.format_str, *dates)
      datas = await self.byte_swap(datas)
      pdu += datas
      # LOGGER.info(f"pdu = {pdu}")
    # Full Modbus TCP request
    request = mbap_header + pdu
    # LOGGER.debug(f"request = {request}")
    return request

  async def byte_swap(self, datas):
    if "BYTE_SWAP" in self.data_format.name:
      res = bytearray()
      data = bytearray(datas)
      for i in range(0, len(datas), 4):
        if i + 4 <= len(data):
          swapped_data = data[i : i + 4]
          swapped_data.reverse()

        for i in range(0, len(swapped_data), 4):
          if i + 4 <= len(swapped_data):
            swapped_data[i : i + 4] = swapped_data[i + 2 : i + 4] + swapped_data[i : i + 2]
            res.extend(swapped_data)
      return bytes(res)

    return datas

  async def __handle_error(self, pdu):
    error_code = pdu[-2]
    if error_code < 80:
      return True
    exception_code = pdu[-1]
    LOGGER.debug(f"exception_code = {exception_code}")
    match exception_code:
      case 1:
        raise Exceptions.IllegalFunction(self.func)
      case 2:
        raise Exceptions.IllegalDataAddress()
      case 3:
        raise Exceptions.IllegalDataValue()
      case 4:
        raise Exceptions.SlaveDeviceFailure()
      case 5:
        raise Exceptions.Acknowledge()
      case 6:
        raise Exceptions.SlaveDeviceBusy()
      case 8:
        raise Exceptions.MemoryParityError()
      case 11:
        raise Exceptions.GatewayPathUnavailable()
      case 12:
        raise Exceptions.GatewayTargetDeviceFailedToRespond()

  async def parse_response(self, response):
    if len(response) < 9:
      raise ValueError("Response is too short")
    await self.__handle_error(response[0:9])
    data = response[9:]
    data = await self.byte_swap(data)
    LOGGER.debug(f"Data = {data}")
    try:
      parsed_data = struct.unpack(self.format_str, data)
    except Exception as e:
      LOGGER.error(f"Exception : {e}")
    return parsed_data

  async def __read_registers(self, start_address, quantity, unit_id=1, function_code=3):
    if not self.is_connected:
      raise Exceptions.SlaveDeviceFailure()
    request = await self.build_request(unit_id, function_code, start_address, quantity)
    self.writer.write(request)
    await self.writer.drain()

    async with self.read_lock:
      try:
        response = await asyncio.wait_for(self.reader.read(1024), timeout=10)
        # LOGGER.info(f"response = {response}")
      except asyncio.TimeoutError as e:
        # LOGGER.error("Read operation timed out.")
        await self.disconnect()
        raise e
      except Exception as e:
        # LOGGER.error(f"Error reading response: {e}")
        await self.disconnect()
        raise e
      # finally:
    #   await self.disconnect()

    return await self.parse_response(response)

  async def read_holding_registers(self, start_address, quantity, unit_id=1):
    self.quantity = quantity
    self.func = "read_holding_registers"
    return await self.__read_registers(start_address, quantity, unit_id, function_code=3)

  async def read_input_registers(self, start_address, quantity, unit_id=1):
    self.quantity = quantity
    self.func = "read_input_registers"
    return await self.__read_registers(start_address, quantity, unit_id, function_code=4)

  async def __write_register(self, address, value, unit_id=1, function_code=6):
    if not self.is_connected:
      raise Exceptions.SlaveDeviceFailure()

    request = await self.build_request(unit_id, function_code, address, value)
    self.writer.write(request)
    await self.writer.drain()

    async with self.read_lock:
      try:
        response = await asyncio.wait_for(self.reader.read(1024), timeout=10)
        LOGGER.debug(f"response = {response}")
        await self.__handle_error(response[0:9])
        return True
      except asyncio.TimeoutError:
        LOGGER.error("Write operation timed out.")
        return False
      except Exception as e:
        LOGGER.error(f"Error writing register: {e}")
        return False

  async def write_multiple_registers(self, address, value, unit_id=1):
    self.func = "write_multiple_registers"
    return await self.__write_register(address, value, unit_id, function_code=16)

  async def write_single_registers(self, address, value, unit_id=1):
    self.func = "write_single_registers"
    return await self.__write_register(address, (value,), unit_id, function_code=16)

  async def read_coils(self, address, quantity, unit_id=1):
    async with self.read_lock:
      self.func = "read_coils"
      # if not self.is_connected:
      #   raise Exceptions.SlaveDeviceFailure()

      # nums_coils = nums_coils + 1 if quantity % 8 > 0 else nums_coils
      # LOGGER.info(nums_coils)

      self.transaction_id += 1
      await self.connect()
      mbap_header = struct.pack(">H H H B", self.transaction_id, 0, 6, unit_id)
      pdu = struct.pack(">B H H", 1, address, quantity)
      require = mbap_header + pdu
      self.writer.write(require)
      await self.writer.drain()

      try:
        response = await asyncio.wait_for(self.reader.read(100), timeout=10)
        # LOGGER.info(f"response = {response}")

      except Exception as e:
        raise e
      await self.__handle_error(response[0:9])
      # LOGGER.info(response[9:])
      res = self.res2bit(quantity, response[9:])
      # res = bin(res)
      await self.disconnect()
    return res

  def res2bit(self, quantity, response):
    nums_coils = quantity // 8 + 1
    delet_head = quantity % 8
    datas = struct.unpack_from("<" + "B" * nums_coils, response)

    res = []
    length = len(datas)
    for i in range(length):
      if i != length - 1:
        for n in format(datas[i], "08b")[::-1]:
          res.append(int(n))
      else:
        for n in format(datas[i], "08b")[-delet_head:][::-1]:
          res.append(int(n))
    return res

  # async def read_coils(self, address, quantity, unit_id=1):
  #   self.func = "read_coils"
  #   await self.test(address, quantity, unit_id)
  #   async with self.read_lock:
  #     try:
  #       response = await asyncio.wait_for(self.reader.read(100), timeout=10)
  #       LOGGER.info(f"response = {response}")

  #     except Exception as e:
  #       raise e
  #     await self.__handle_error(response[0:9])
  #     res = " "
  #     res = "".join(f"{byte:08b}" for byte in response[9:])
  #   return res

  # async def test(self, address, quantity, unit_id):
  #   self.transaction_id += 1
  #   await self.connect()
  #   mbap_header = struct.pack(">H H H B", self.transaction_id, 0, 6, unit_id)
  #   pdu = struct.pack("B H H", 1, address, quantity)
  #   require = mbap_header + pdu
  #   self.writer.write(require)
  #   await self.writer.drain()


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

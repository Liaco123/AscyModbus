import socket
import struct
import threading

from AscynioModbus import Exceptions

from .DataFormat import DataFormat
from .ulitis import LOGGER


class ModbusTCPClient:
  def __init__(self, host, port=502, data_format: DataFormat = DataFormat.UNSIGNED_16_INT_BIG):
    self.host = host
    self.port = port
    self.transaction_id = 0
    self.socket = None
    self.init = True
    self.is_connected = False
    self.is_swap = False
    self.quantity = 0
    self.data_format = data_format
    self.lock = threading.Lock()

  def __enter__(self):
    self.connect()
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    if self.is_connected:
      self.disconnect()
    return False

  def __del__(self):
    self.disconnect()

  def __build_request(self, unit_id, function_code, start_address, dates):
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
      datas = self.byte_swap(datas)
      pdu += datas

    request = mbap_header + pdu
    return request

  def __build_request_msg(self, values):
    res = bytearray()
    length = len(values)
    padded_length = length + (8 - length % 8) if length % 8 != 0 else length
    for i in range(0, padded_length, 8):
      byte = 0
      for bit_index in range(8):
        if i + bit_index < length and values[i + bit_index]:
          byte |= 1 << bit_index
      res.append(byte)
    return res

  def __read_registers(self, address, quantity, unit_id=1, function_code=3):
    self.connect()
    request = self.__build_request(unit_id, function_code, address, quantity)
    self.socket.sendall(request)

    with self.lock:
      try:
        response = self.socket.recv(1024)
      except Exception as e:
        self.disconnect()
        raise e

    return self.parse_response(response)

  def __write_register(self, address, value, unit_id=1, function_code=6):
    self.connect()
    request = self.__build_request(unit_id, function_code, address, value)
    self.socket.sendall(request)

    with self.lock:
      try:
        response = self.socket.recv(1024)
        LOGGER.debug(f"response = {response}")
        self.__handle_error(response[0:9])
        return f"{self.func} successed"
      except Exception as e:
        self.disconnect()
        LOGGER.error(f"Error writing register: {e}")
        return False

  def __write_coils(self, address, values: list, unit_id=1):
    self.connect()
    length = (colis := len(values)) // 8
    length += 1 if colis % 8 > 0 else 0
    self.transaction_id += 1

    pdu = struct.pack(">B H H B", 15, address, colis, length)
    msg = self.__build_request_msg(values)
    mbap_header = struct.pack(">HHHB", self.transaction_id, 0, 7 + length, unit_id)
    request = mbap_header + pdu + msg
    self.socket.sendall(request)

    with self.lock:
      try:
        response = self.socket.recv(1024)
        LOGGER.debug(f"response = {response}")
        self.__handle_error(response[0:9])
        return f"{self.func} successed"
      except Exception as e:
        self.disconnect()
        LOGGER.error(f"Error writing register: {e}")
        return False

  def __res2bit(self, quantity, response):
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

  def __handle_error(self, pdu):
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

  def connect(self, timeout=10):
    try:
      self.socket = socket.create_connection((self.host, self.port), timeout=timeout)
      self.is_connected = True
      if self.init:
        self.init = False
        LOGGER.info(f"Connected to {self.host}:{self.port}")

    except socket.timeout as e:
      raise TimeoutError(f"Connection to {self.host}:{self.port} timed out.") from e
    except OSError as e:
      raise OSError(f"Cannot connect to {self.host}:{self.port} {e}") from e

  def disconnect(self):
    try:
      if self.is_connected:
        self.socket.close()
        LOGGER.info(f"Disconnected from {self.host}:{self.port}")
        self.is_connected = False
    except Exception as e:
      LOGGER.error(f"Error during disconnect: {e}")
      raise e

  def byte_swap(self, datas):
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

  def parse_response(self, response):
    if len(response) < 9:
      raise ValueError("Response is too short")
    self.__handle_error(response[0:9])
    data = response[9:]
    data = self.byte_swap(data)
    LOGGER.debug(f"Data = {data}")
    try:
      parsed_data = struct.unpack(self.format_str, data)
    except Exception as e:
      LOGGER.error(f"Exception : {e}")
    return parsed_data

  def read_holding_registers(self, start_address, quantity, unit_id=1):
    self.quantity = quantity
    self.func = "read_holding_registers"
    return self.__read_registers(start_address, quantity, unit_id, function_code=3)

  def read_input_registers(self, start_address, quantity, unit_id=1):
    self.quantity = quantity
    self.func = "read_input_registers"
    return self.__read_registers(start_address, quantity, unit_id, function_code=4)

  def write_multiple_registers(self, address, value, unit_id=1):
    self.func = "write_multiple_registers"
    return self.__write_register(address, value, unit_id, function_code=16)

  def write_single_registers(self, address, value, unit_id=1):
    self.func = "write_single_registers"
    return self.__write_register(address, (value,), unit_id, function_code=16)

  def read_coils(self, address, quantity, unit_id=1):
    self.func = "read_coils"
    self.connect()
    self.transaction_id += 1
    mbap_header = struct.pack(">H H H B", self.transaction_id, 0, 6, unit_id)
    pdu = struct.pack(">B H H", 1, address, quantity)
    request = mbap_header + pdu

    with self.lock:
      try:
        self.socket.sendall(request)
        response = self.socket.recv(100)
        self.__handle_error(response[0:9])
        res = self.__res2bit(quantity, response[9:])
        return res
      except Exception as e:
        self.disconnect()
        raise e

  def write_multiple_coils(self, address, value: list, unit_id=1):
    self.func = "write_multiple_coils"
    return self.__write_coils(address, value, unit_id)

  def write_single_coils(self, address, value: int, unit_id=1):
    self.func = "write_multiple_coils"
    return self.__write_coils(address, (value,), unit_id)


# 示例使用
def main():
  modbus_tcp = ModbusTCPClient(host="192.168.1.100")
  modbus_tcp.connect()
  if modbus_tcp.is_connected:
    try:
      response = modbus_tcp.read_holding_registers(start_address=0, quantity=10, unit_id=1)
      LOGGER.debug(f"Response= {response}")
    except Exceptions.SlaveDeviceFailure as e:
      LOGGER.error(f"Failed to read holding registers: {e}")
    finally:
      modbus_tcp.disconnect()


if __name__ == "__main__":
  main()

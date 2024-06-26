"""
# @ Author: Liaco
# @ Create Time: 2024-06-23 16:14:43
# @ Modified by: Liaco
# @ Modified time: 2024-06-23 22:09:50
# @ Description:
"""

import socket
import struct

from ModbusTcp import Exceptions
from ModbusTcp.DataFormat import DataFormat
from ModbusTcp.ulitis import LOGGER, SocketManager, execute


class ModbusTcpClient:
  def __init__(
    self, host: str = "1270.0.1", port: int = 502, data_format: DataFormat = DataFormat.SIGNED_16_INT_BIG, **kwargs
  ):
    """_summary_

    Args:
        host (str, optional): 服务器地址。Defaults to "1270.0.1".
        port (int, optional): 服务器端口号 . Defaults to 502.
        data_format (DataFormat, optional): 数据格式。Defaults to DataFormat.SIGNED_16_INT_BIG.
    """
    self.__host = host
    self.__port = port
    self.__transaction_id = 0
    self.__is_connected = False
    self.__data_format = data_format
    self.__threads = execute(kwargs.get("threads", 10))
    self.__sockets = SocketManager(kwargs.get("sockts", 10))
    self.__wait_writed = True
    self.connect()

  def __enter__(self):
    if not self.__is_connected:
      self.connect()
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.disconnect()
    return False

  def __del__(self):
    self.__threads.shutdown()
    self.__sockets.shutdown()

  def __build_request(self, unit_id, function_code, start_address, dates):
    quantity = dates if "read" in self.__func else len(dates)
    if self.__data_format in {
      DataFormat.UNSIGNED_16_INT_LITTLE,
      DataFormat.SIGNED_16_INT_LITTLE,
    }:
      self.__format_str = "<" + ("H" * quantity) if "UNSIGNED" in self.__data_format.name else "<" + ("h" * quantity)
    elif self.__data_format in {
      DataFormat.UNSIGNED_16_INT_BIG,
      DataFormat.SIGNED_16_INT_BIG,
    }:
      self.__format_str = ">" + ("H" * quantity) if "UNSIGNED" in self.__data_format.name else ">" + ("h" * quantity)

    elif self.__data_format in {
      DataFormat.UNSIGNED_32_INT_LITTLE,
      DataFormat.SIGNED_32_INT_LITTLE,
      DataFormat.UNSIGNED_32_INT_LITTLE_BYTE_SWAP,
      DataFormat.SIGNED_32_INT_LITTLE_BYTE_SWAP,
    }:
      self.__format_str = "<" + ("I" * quantity) if "UNSIGNED" in self.__data_format.name else "<" + ("i" * quantity)

    elif self.__data_format in {
      DataFormat.UNSIGNED_32_INT_BIG,
      DataFormat.SIGNED_32_INT_BIG,
      DataFormat.UNSIGNED_32_INT_BIG_BYTE_SWAP,
      DataFormat.SIGNED_32_INT_BIG_BYTE_SWAP,
    }:
      self.__format_str = ">" + ("I" * quantity) if "UNSIGNED" in self.__data_format.name else ">" + ("i" * quantity)

    elif self.__data_format in {
      DataFormat.UNSIGNED_64_INT_LITTLE,
      DataFormat.SIGNED_64_INT_LITTLE,
      DataFormat.UNSIGNED_64_INT_LITTLE_BYTE_SWAP,
      DataFormat.SIGNED_64_INT_LITTLE_BYTE_SWAP,
    }:
      self.__format_str = "<" + ("Q" * quantity) if "UNSIGNED" in self.__data_format.name else "<" + ("q" * quantity)

    elif self.__data_format in {
      DataFormat.UNSIGNED_64_INT_BIG,
      DataFormat.SIGNED_64_INT_BIG,
      DataFormat.UNSIGNED_64_INT_BIG_BYTE_SWAP,
      DataFormat.SIGNED_64_INT_BIG_BYTE_SWAP,
    }:
      self.__format_str = ">" + ("Q" * quantity) if "UNSIGNED" in self.__data_format.name else ">" + ("q" * quantity)

    elif self.__data_format in {DataFormat.FLOAT_32_LITTLE, DataFormat.FLOAT_32_LITTLE_BYTE_SWAP}:
      self.__format_str = "<" + ("f" * quantity)

    elif self.__data_format in {DataFormat.FLOAT_32_BIG, DataFormat.FLOAT_32_BIG_BYTE_SWAP}:
      self.__format_str = ">" + ("f" * quantity)

    elif self.__data_format in {DataFormat.DOUBLE_64_LITTLE, DataFormat.DOUBLE_64_LITTLE_BYTE_SWAP}:
      self.__format_str = "<" + ("d" * quantity)

    elif self.__data_format in {DataFormat.DOUBLE_64_BIG, DataFormat.DOUBLE_64_BIG_BYTE_SWAP}:
      self.__format_str = ">" + ("d" * quantity)

    if "16" in self.__data_format.name:
      des_quantity = quantity

    elif "32" in self.__data_format.name:
      des_quantity = quantity * 2

    elif "64" in self.__data_format.name:
      des_quantity = quantity * 4

    else:
      LOGGER.error(f"format_str = {self.__format_str}")
      raise ValueError(f"Unsupported data format: {self.__data_format}")

    self.__transaction_id += 1

    if "read" in self.__func:
      mbap_header = struct.pack(">H H H B", self.__transaction_id, 0, 6, unit_id)
      pdu = struct.pack(">B H H", function_code, start_address, des_quantity)
    elif "write" in self.__func:
      mbap_header = struct.pack(">H H H B", self.__transaction_id, 0, 7 + 2 * des_quantity, unit_id)
      pdu = struct.pack(
        ">B H H B",
        function_code,
        start_address,
        des_quantity,
        2 * des_quantity,
      )
      datas = struct.pack(self.__format_str, *dates)
      datas = self.__byte_swap(datas)
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

  def __read_registers(self, sock, address, quantity, unit_id=1, function_code=3):
    request = self.__build_request(unit_id, function_code, address, quantity)
    sock.sendall(request)

    try:
      response = sock.recv(6)
      response += sock.recv(response[-1])
      self.__sockets.release_socket(sock)
    except Exceptions.ModbusException as e:
      raise e
    except Exception as e:
      self.disconnect()
      LOGGER.error(f"Error reading register: {e}")
      raise e

    return self.__parse_response(response)

  def __read_coil(self, sock, start_address, quantity, unit_id=1, function_code=1):
    self.__transaction_id += 1
    mbap_header = struct.pack(">H H H B", self.__transaction_id, 0, 6, unit_id)
    pdu = struct.pack(">B H H", function_code, start_address, quantity)
    request = mbap_header + pdu

    try:
      sock.sendall(request)
      response = sock.recv(6)
      response += sock.recv(response[-1])
      self.__sockets.release_socket(sock)
      self.__handle_error(response[0:9])
      res = self.__res2bit(quantity, response[9:])
      return res
    except Exceptions.ModbusException as e:
      raise e
    except Exception as e:
      self.disconnect()
      LOGGER.error(f"Error reading coils: {e}")
      raise e

  def __write_register(self, sock, address, value, unit_id=1, function_code=6):
    request = self.__build_request(unit_id, function_code, address, value)
    sock.sendall(request)

    try:
      response = sock.recv(6)
      response += sock.recv(response[-1])
      self.__sockets.release_socket(sock)
      LOGGER.debug(f"response = {response}")
      self.__handle_error(response[0:9])
      return f"{self.__func} successed"
    except Exceptions.ModbusException as e:
      raise e
    except Exception as e:
      if self.__is_connected:
        self.disconnect()
        LOGGER.error(f"Error writing register: {e}")
      raise e

  def __write_coils(self, sock, address, values, unit_id=1):
    length = (colis := len(values)) // 8
    length += 1 if colis % 8 > 0 else 0
    self.__transaction_id += 1

    pdu = struct.pack(">B H H B", 15, address, colis, length)
    msg = self.__build_request_msg(values)
    mbap_header = struct.pack(">HHHB", self.__transaction_id, 0, 7 + length, unit_id)
    request = mbap_header + pdu + msg
    sock.sendall(request)

    try:
      response = sock.recv(6)
      response += sock.recv(response[-1])
      self.__sockets.release_socket(sock)
      LOGGER.debug(f"response = {response}")
      self.__handle_error(response[0:9])
      return f"{self.__func} successed"
    except Exceptions.ModbusException as e:
      raise e
    except Exception as e:
      # LOGGER.error(f"Error writing coils: {e}")
      raise e

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
    if not pdu:
      self.disconnect()
      raise Exception("Connect Error")
    error_code = pdu[-2]
    if error_code < 80:
      return True
    exception_code = pdu[-1]
    LOGGER.debug(f"exception_code = {exception_code}")
    match exception_code:
      case 1:
        raise Exceptions.IllegalFunction(self.__func)
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

  def __byte_swap(self, datas):
    if "BYTE_SWAP" in self.__data_format.name:
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

  def __parse_response(self, response):
    if len(response) < 9:
      raise ValueError("Response is too short")
    self.__handle_error(response[0:9])
    data = response[9:]
    data = self.__byte_swap(data)
    LOGGER.debug(f"Data = {data}")
    try:
      parsed_data = struct.unpack(self.__format_str, data)
    except Exception as e:
      LOGGER.error(f"Error : {e}")
      raise e
    return parsed_data

  def connect(self, timeout=10):
    try:
      self.__sockets._initialize_sockets(self.__host, self.__port, timeout=timeout)
      LOGGER.info(f"Connected to {self.__host}:{self.__port}")
      self.__is_connected = True
    except socket.timeout as e:
      raise TimeoutError(f"Connection to {self.__host}:{self.__port} timed out.") from e
    except OSError as e:
      # raise OSError(f"Cannot connect to {self.__host}:{self.__port} {e}") from e
      raise e

  def disconnect(self):
    if not self.__is_connected:
      return None
    try:
      self.__threads.shutdown()
      self.__sockets.shutdown()
      LOGGER.info(f"Disconnected from {self.__host}:{self.__port}")
      self.__is_connected = False
    # except RuntimeError:
    #   pass
    except Exception as e:
      # LOGGER.error(f"Error during disconnect: {e}")
      raise e

  def read_holding_registers(self, start_address, quantity: int, unit_id=1) -> list:
    """读保持寄存器

    Args:
        start_address : 要读取起始地址
        quantity (int): 要读取的数量
        unit_id (int, optional): 设备地址（slave_id）= 1

    Returns:
        list: 读取到的对应的寄存器的值
    """
    self.__func = "read_holding_registers"
    sock = self.__sockets.get_socket()
    return self.__threads.run(self.__read_registers, sock, start_address, quantity, unit_id, 3)

  def read_input_registers(self, start_address, quantity: int, unit_id=1) -> list:
    """读输入寄存器

    Args:
        start_address : 要读取的起始地址
        quantity (int): 要读取的数量
        unit_id (int, optional): 设备地址（slave_id）= 1

    Returns:
        list: 读取到的对应的寄存器的值
    """

    self.__func = "read_input_registers"
    sock = self.__sockets.get_socket()
    return self.__threads.run(self.__read_registers, sock, start_address, quantity, unit_id, function_code=4)

  def read_coils(self, start_address, quantity: int, unit_id=1) -> list:
    """读线圈

    Args:
        start_address : 要读取的起始地址
        quantity (int): 要读取的数量
        unit_id (int, optional): 设备地址（slave_id）= 1

    Returns:
        list: 读取到的对应的线圈的值
    """

    self.__func = "read_coils"
    sock = self.__sockets.get_socket()
    return self.__threads.run(self.__read_coil, sock, start_address, quantity, unit_id)

  def read_input_coils(self, start_address, quantity: int, unit_id=1) -> list:
    """读线圈

    Args:
        start_address : 要读取的起始地址
        quantity (int): 要读取的数量
        unit_id (int, optional): 设备地址（slave_id）= 1

    Returns:
        list: 读取到的对应的线圈的值
    """

    self.__func = "read_input_coils"
    sock = self.__sockets.get_socket()
    return self.__threads.run(self.__read_coil, sock, start_address, quantity, unit_id, 2)

  def write_multiple_registers(self, start_address, value: list, unit_id=1) -> None:
    """写多个寄存器

    Args:
        start_address : 要写入的起始地址
        value (list): 要写入的值
        unit_id (int, optional): 设备地址（slave_id）= 1

    Returns:
        bool: True
    """

    self.__func = "write_multiple_registers"
    sock = self.__sockets.get_socket()
    if self.__wait_writed:
      return self.__threads.run(self.__write_register, sock, start_address, value, unit_id, function_code=16)
    return self.__threads.submit(self.__write_register, sock, start_address, value, unit_id, function_code=16)

  def write_single_registers(self, address, value: int, unit_id=1) -> None:
    """写单个寄存器

    Args:
        address : 要写入的地址
        value (int): 要写入的值
        unit_id (int, optional): 设备地址（slave_id）= 1

    Returns:
        bool: True
    """

    self.__func = "write_single_registers"
    sock = self.__sockets.get_socket()
    if self.__wait_writed:
      return self.__threads.run(self.__write_register, sock, address, (value,), unit_id, function_code=16)
    return self.__threads.submit(self.__write_register, sock, address, (value,), unit_id, function_code=16)

  def write_multiple_coils(self, start_address, value: list, unit_id=1) -> None:
    """写多个线圈

    Args:
        start_address : 要写入的起始地址
        value (list): 要写入的值
        unit_id (int, optional): 设备地址（slave_id）= 1

    Returns:
        bool: True
    """

    self.__func = "write_multiple_coils"
    sock = self.__sockets.get_socket()
    if self.__wait_writed:
      return self.__threads.run(self.__write_coils, sock, start_address, value, unit_id)
    return self.__threads.submit(self.__write_coils, sock, start_address, value, unit_id)

  def write_single_coils(self, address, value: int, unit_id=1) -> None:
    """写单个线圈

    Args:
        address : 要写入的地址
        value (bool): 要写入的值
        unit_id (int, optional): 设备地址（slave_id）= 1

    Returns:
        bool: True
    """

    self.__func = "write_single_coils"
    sock = self.__sockets.get_socket()
    if self.__wait_writed:
      return self.__threads.run(self.__write_coils, sock, address, (value,), unit_id)
    return self.__threads.submit(self.__write_coils, sock, address, (value,), unit_id)

  @property
  def wait_writed(self):
    return self.__wait_writed

  @wait_writed.setter
  def wait_writed(self, data: bool):
    self.__wait_writed = data

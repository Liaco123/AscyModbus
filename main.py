import time

from ModbusTcp import LOGGER, DataFormat, ModbusTcpClient

if __name__ == "__main__":
  modbus_tcp = ModbusTcpClient("127.0.0.1", 502, DataFormat.SIGNED_32_INT_LITTLE_BYTE_SWAP)
  with modbus_tcp as c:
    while True:
      try:
        datas = [0 for _ in range(10)]
        for i in range(10):
          datas[i] = 1
          res = c.write_multiple_coils(0, datas)
          time.sleep(0.1)
          datas = [0 for _ in range(10)]
      except Exception as e:
        LOGGER.error(e)

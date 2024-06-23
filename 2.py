import time

from AscynioModbus import LOGGER, DataFormat, Exceptions, ModbusTCPClient

if __name__ == "__main__":
  modbus_tcp = ModbusTCPClient("127.0.0.1", 502, DataFormat.SIGNED_32_INT_LITTLE_BYTE_SWAP)
  with modbus_tcp as c:
    # while True:
    # try:
    # res = c.read_coils(0, 10)
    # LOGGER.info(f"read_coils = {res}")
    # res = c.write_multiple_registers(0, [-50, 50, 80, 90])
    # LOGGER.info(f"{res}")
    while True:
      try:
        datas = [0 for _ in range(10)]
        for i in range(10):
          datas[i] = 1
          res = c.write_multiple_coils(0, datas)
          time.sleep(0.1)
          datas = [0 for _ in range(10)]
      # LOGGER.info(f"{res}")
      except Exception as e:
        LOGGER.error(e)

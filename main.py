from ModbusTcp import LOGGER, DataFormat, ModbusTcpClient

if __name__ == "__main__":
  modbus_tcp = ModbusTcpClient("127.0.0.1", 502, DataFormat.SIGNED_32_INT_LITTLE_BYTE_SWAP)

  with modbus_tcp as c:
    datas = [0 for _ in range(10)]
    for i in range(10):
      datas[i] = 1
      c.write_multiple_coils(0, datas)
      datas = [0 for _ in range(10)]
    LOGGER.info("Successed!")

from ModbusTcp import LOGGER, DataFormat, ModbusTcpClient

if __name__ == "__main__":
  modbus_tcp = ModbusTcpClient("127.0.0.1", 502, DataFormat.SIGNED_32_INT_LITTLE_BYTE_SWAP)
  modbus_tcp.wait_writed = False
  modbus_tcp.write_multiple_registers(0, [20, 30, -99999999])
  res = modbus_tcp.read_holding_registers(0, 3)
  print(res)
  # with modbus_tcp as c:
  #   c.wait_writed = True
  #   datas = [0 for _ in range(10)]
  #   for i in range(10):
  #     datas[i] = 1
  #     c.write_multiple_coils(0, datas)
  #     res = c.read_coils(0, 10)
  #     LOGGER.info(f"result = {res}")
  #     datas[i] = 0

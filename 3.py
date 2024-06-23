from pymodbus.client.tcp import ModbusTcpClient

# Modbus TCP 连接信息
SERVER_HOST = "127.0.0.1"  # Modbus TCP 服务器的 IP 地址
SERVER_PORT = 502  # Modbus TCP 端口

# Modbus Coil 地址（从 0 开始）
COIL_ADDRESS = 0

# 创建 Modbus TCP 客户端
client = ModbusTcpClient(SERVER_HOST, port=SERVER_PORT)

try:
  # 建立连接
  if client.connect():
    # 读取单个线圈的状态
    # while True:
    response = client.read_coils(0, 10)  # unit 参数为设备地址

    # 检查响应
    if response.isError():
      print(f"Modbus Error: {response}")
    else:
      # 打印线圈状态
      print("Coil value: ")
      for i in response.bits:
        # print(f"{response.bits[i]}", end=" ")
        print(i, end=" ")
      print("\n")
except Exception:
  client.close()

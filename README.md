# 这是一个简单的 ModbusTcp 库

##目的

Modbus 默认使用 16 位的大端格式，经常需要进行大小端，32、64 位数据转换。
为了简化使用过程，在这个库中实现了内置的转换，使用时，只需要在实例化客户端的时候指定数据类型。

目前支持的数据类型：
```python
# 16-bit integer formats
  UNSIGNED_16_INT_LITTLE
  UNSIGNED_16_INT_BIG

  SIGNED_16_INT_LITTL
  SIGNED_16_INT_BI

  # 32-bit integer formats
  UNSIGNED_32_INT_LITTL
  UNSIGNED_32_INT_BI
  UNSIGNED_32_INT_LITTLE_BYTE_SWAP
  UNSIGNED_32_INT_BIG_BYTE_SWAP

  SIGNED_32_INT_LITTLE
  SIGNED_32_INT_BIG
  SIGNED_32_INT_LITTLE_BYTE_SWAP
  SIGNED_32_INT_BIG_BYTE_SWAP

  # 64-bit integer formats
  UNSIGNED_64_INT_LITTLE
  UNSIGNED_64_INT_BIG
  UNSIGNED_64_INT_LITTLE_BYTE_SWAP
  UNSIGNED_64_INT_BIG_BYTE_SWAP

  SIGNED_64_INT_LITTLE
  SIGNED_64_INT_BIG
  SIGNED_64_INT_LITTLE_BYTE_SWAP
  SIGNED_64_INT_BIG_BYTE_SWAP

  # 32-bit float formats
  FLOAT_32_LITTLE
  FLOAT_32_BIG
  FLOAT_32_LITTLE_BYTE_SWAP
  FLOAT_32_BIG_BYTE_SWAP

  # 64-bit double formats
  DOUBLE_64_LITTLE
  DOUBLE_64_BIG
  DOUBLE_64_LITTLE_BYTE_SWAP
  DOUBLE_64_BIG_BYTE_SWAP

```


## 支持的功能码
1. 读线圈 
2. 写单个线圈（使用写多个线圈来实现）
3. 写多个线圈
4. 读输入寄存器 
5. 读保持寄存器
6. 写单个保持寄存器（使用写多个保存寄存器实现）
7. 写多个保持寄存器 


## 错误类型

同时本库支持 ModbusTcp 协议基于异常码的错误提醒（没有基于网关的错误）。

错误类型：
```python
  # 非法功能
  ILLEGAL_FUNCTION = 0x01
  # 非法数据地址
  ILLEGAL_DATA_ADDRESS = 0x02
  # 非法数据值
  ILLEGAL_DATA_VALUE = 0x03
  # 从站设备故障
  SLAVE_DEVICE_FAILURE = 0x04
  # 确认
  ACKNOWLEDGE = 0x05
  # 从属设备忙
  SLAVE_DEVICE_BUSY = 0x06
  # 存储奇偶性差错
  MEMORY_PARITY_ERROR = 0x08

```
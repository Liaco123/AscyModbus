from enum import Enum

from ModbusTcp.ulitis import LOGGER


# 定义 Modbus 异常代码的枚举类
class ModbusError(Enum):
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
  # 不可用网关路径
  GATEWAY_PATH_UNAVAILABLE = 0x0A
  # 网关目标设备响应失败
  GATEWAY_TARGET_DEVICE_FAILED_TO_RESPOND = 0x0B


class Singleton(type):
  _instances = {}

  def __call__(cls, *args, **kwargs):
    if cls not in cls._instances:
      cls._instances[cls] = super().__call__(*args, **kwargs)
    return cls._instances[cls]


# 基础 Modbus 异常类
class ModbusException(Exception, metaclass=Singleton):
  def __init__(self, error_code: ModbusError, message: str) -> None:
    self.error_code = error_code
    super().__init__(f"{error_code.name}: {message}")


# 具体的 Modbus 异常类
class IllegalFunction(ModbusException):
  def __init__(self, msg) -> None:
    super().__init__(ModbusError.ILLEGAL_FUNCTION, f"{msg}")


class IllegalDataAddress(ModbusException):
  def __init__(self) -> None:
    super().__init__(ModbusError.ILLEGAL_DATA_ADDRESS, "Illegal data address")


class IllegalDataValue(ModbusException):
  def __init__(self) -> None:
    super().__init__(ModbusError.ILLEGAL_DATA_VALUE, "Illegal data value ")


class SlaveDeviceFailure(ModbusException):
  def __init__(self) -> None:
    super().__init__(ModbusError.SLAVE_DEVICE_FAILURE, "Slave device failure")


class Acknowledge(ModbusException):
  def __init__(self, msg) -> None:
    super().__init__(ModbusError.ACKNOWLEDGE, f"Error :{msg}")


class SlaveDeviceBusy(ModbusException):
  def __init__(self) -> None:
    super().__init__(ModbusError.SLAVE_DEVICE_BUSY, "Slave device busy")


class MemoryParityError(ModbusException):
  def __init__(self) -> None:
    super().__init__(ModbusError.MEMORY_PARITY_ERROR, "Memory parity error")


class GatewayPathUnavailable(ModbusException):
  def __init__(self) -> None:
    super().__init__(ModbusError.GATEWAY_PATH_UNAVAILABLE, "Gateway path unavailable")


class GatewayTargetDeviceFailedToRespond(ModbusException):
  def __init__(self) -> None:
    super().__init__(ModbusError.GATEWAY_TARGET_DEVICE_FAILED_TO_RESPOND, "Gateway target device failed to respond")


# 示例使用
if __name__ == "__main__":
  try:
    raise IllegalFunction()
  except ModbusException as e:
    LOGGER.debug("Caught an exception: %s", e)

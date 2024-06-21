import asyncio

from AscynioModbus import LOGGER, DataFormat, Exceptions, ModbusProto

if __name__ == "__main__":

  async def main():
    client = ModbusProto.AsyncModbusTCP("192.168.2.1", port=502, data_format=DataFormat.SIGNED_64_INT_BIG_BYTE_SWAP)
    await client.connect()
    if client.is_connected:
      try:
        response = await client.read_holding_registers(start_address=0, quantity=5, unit_id=1)
        LOGGER.debug(f"Response= {response}")
      except Exceptions.SlaveDeviceFailure as e:
        LOGGER.error(f"Failed to read holding registers: {e}")
      # finally:
      #   await client.disconnect()

  asyncio.run(main())

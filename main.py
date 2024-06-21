from AscynioModbus import LOGGER, Exceptions

try:
  raise Exceptions.IllegalDataAddress
except Exceptions.ModbusException as e:
  # LOGGER.debug("Caught an exception: %s", e)
  LOGGER.debug(e)
  pass

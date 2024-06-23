import asyncio

from AscynioModbus import LOGGER, AsyncModbusTCP, DataFormat, Exceptions


async def read_registers(client: AsyncModbusTCP, task_id):
  # response = await client.read_input_registers(start_address=0, quantity=10, unit_id=1)
  # LOGGER.info(f"任务 {task_id}: 响应 1 = {response}")
  # response = await client.write_multiple_registers(0, [-200], unit_id=1)
  # LOGGER.info(f"任务 {task_id}: 响应 2 = {response}")
  # response = await client.read_holding_registers(start_address=0, quantity=5, unit_id=1)
  # LOGGER.info(f"任务 {task_id}: 响应 2 = {response}")
  # response = await client.write_single_registers(0, -200, unit_id=1)
  # LOGGER.info(f"任务 {task_id}: 响应 2 = {response}")
  response = await client.read_coils(0, 10)
  LOGGER.info(f"任务 {task_id}: 响应 2 = {response}")


async def main(client):
  tasks = []
  for i in range(10000):
    tasks.append(asyncio.create_task(read_registers(client, i)))
  try:
    await asyncio.gather(*tasks)
  except Exception as e:
    for task in tasks:
      task.cancel()
      raise e
  # await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
  LOGGER.setLevel("INFO")
  ip = "127.0.0.1"
  client = AsyncModbusTCP(ip, port=502, data_format=DataFormat.SIGNED_32_INT_LITTLE_BYTE_SWAP)

  async def run():
    try:
      await client.connect()
      await main(client)
    except Exception as e:
      raise e
    finally:
      LOGGER.info(f"Disconnect from {ip} ")
      await client.disconnect()

  # try:
  #   asyncio.run(run())
  # except Exception as e:
  #   LOGGER.error(f"Error : {e}")
  asyncio.run(run())

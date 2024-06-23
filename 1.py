import asyncio

from AscynioModbus import LOGGER, AsyncModbusTCP, DataFormat, Exceptions


async def read_registers(client: AsyncModbusTCP, task_id):
  try:
    response = await client.read_coils(0, 10, unit_id=1)
    # response = await client.write_single_registers(0, -200, unit_id=1)
    # response = await client.read_coils(0, 10, unit_id=1)
    LOGGER.info(f"任务 {task_id}: 响应 2 = {response}")
  except Exception as e:
    LOGGER.error(f"任务 {task_id}: 发生异常：{e}")


async def main(client):
  tasks = []
  for i in range(5):
    tasks.append(asyncio.create_task(read_registers(client, i)))
  try:
    await asyncio.gather(*tasks)
  except Exception as e:
    for task in tasks:
      task.cancel()
    LOGGER.error(f"主任务异常：{e}")


if __name__ == "__main__":
  LOGGER.setLevel("INFO")
  ip = "127.0.0.1"
  client = AsyncModbusTCP(ip, port=502, data_format=DataFormat.SIGNED_32_INT_LITTLE_BYTE_SWAP)

  async def run():
    try:
      await client.connect()
      await main(client)
    except Exception as e:
      LOGGER.error(f"运行时发生异常：{e}")
    finally:
      LOGGER.info(f"从 {ip} 断开连接")
      await client.disconnect()

  asyncio.run(run())

import logging
from .DataFormat import DataFormat

# 设置日志格式
formatter = "%(asctime)s - %(name)s - %(levelname)-8s - %(filename)s:%(lineno)d - %(message)s"

# 配置日志系统
logging.basicConfig(format=formatter, level=logging.DEBUG)

# 获取日志记录器
LOGGER = logging.getLogger(__name__)


__all__ = ["LOGGER", "Exceptions", "DataFormat"]



if __name__ == "__main__":
  LOGGER.debug("This is a debug message")
  LOGGER.info("This is an info message")
  LOGGER.warning("This is a warning message")
  LOGGER.error("This is an error message")
  LOGGER.critical("This is a critical message")

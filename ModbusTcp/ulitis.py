"""
# @ Author: Liaco
# @ Create Time: 2024-06-23 16:14:43
# @ Modified by: Liaco
# @ Modified time: 2024-06-23 18:43:53
# @ Description:
"""

import logging

# # 设置日志格式


formatter = "%(asctime)s - %(name)s - %(levelname)-8s - %(filename)s:%(lineno)d - %(message)s"

# 配置日志系统
logging.basicConfig(format=formatter, level=logging.INFO)

# # 获取日志记录器
LOGGER = logging.getLogger(__name__)

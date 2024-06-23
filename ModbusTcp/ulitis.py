"""
# @ Author: Liaco
# @ Create Time: 2024-06-23 16:14:43
# @ Modified by: Liaco
# @ Modified time: 2024-06-23 22:09:35
# @ Description:
"""

import logging
import socket
from concurrent.futures import Future, ThreadPoolExecutor
from threading import Lock
from typing import Any, Callable

from ModbusTcp import Exceptions

formatter = "%(asctime)s - %(name)s - %(levelname)-8s - %(filename)s:%(lineno)d - %(message)s"

logging.basicConfig(format=formatter, level=logging.INFO)
LOGGER = logging.getLogger(__name__)


class SocketManager:
  def __init__(self, max_sockets: int):
    self.max_sockets = max_sockets
    self.available_sockets = []
    self._lock = Lock()
    # self._initialize_sockets()

  def _initialize_sockets(self, host, port, timeout=5):
    self.host = host
    self.port = port
    self.timeout = timeout
    for _ in range(self.max_sockets):
      sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
      # LOGGER.debug("create_connection")
      self.available_sockets.append(sock)

  def get_socket(self):
    LOGGER.debug("get_socket")
    with self._lock:
      if not self.available_sockets:
        sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        # LOGGER.debug("create_connection")
        return sock
      sock = self.available_sockets.pop()
      if self.is_socket_available(sock):
        return sock
      return

  def is_socket_available(self, sock):
    try:
      err = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
      if err == 0:
        return True
      else:
        self.available_sockets.remove(sock)
    except Exception:
      return False

  def release_socket(self, sock):
    with self._lock:
      self.available_sockets.append(sock)
      # LOGGER.info("release_socket")

  def shutdown(self):
    with self._lock:
      for sock in self.available_sockets:
        sock.close()
      self.available_sockets = []


class execute:
  def __init__(self, max_workers: int):
    self.executor = ThreadPoolExecutor(max_workers=max_workers)

  def run(self, func: Callable, *args, **kwargs) -> Any:
    """
    将函数提交到线程池中运行，并返回其结果。

    :param func: 要在线程池中运行的函数
    :param args: 函数的位置参数
    :param kwargs: 函数的关键字参数
    :return: 函数的返回值
    """
    try:
      future: Future = self.executor.submit(func, *args, **kwargs)
      return future.result()
    # except RuntimeError:
    #   pass
    except Exception as e:
      raise e

  def shutdown(self):
    """
    关闭线程池。
    """
    self.executor.shutdown()

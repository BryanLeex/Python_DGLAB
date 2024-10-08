import os
import time

import botpy
from botpy import logging
from botpy.ext.cog_yaml import read
from botpy.message import Message

import socket

import asyncio

import multiprocessing

test_config = read(os.path.join(os.path.dirname(__file__), "config.yaml"))

_log = logging.get_logger()
_log.setLevel(level="DEBUG")


class Client(botpy.Client):

    async def on_ready(self):
        _log.info(f"robot 「{self.robot.name}」 on_ready!")
        self.ss = socket.socket()
        self.ss.bind(("localhost", 5679))

        self.ss.listen(1)

        _log.info(f"服务端已开始监听，正在等待客户端连接...")
        self.conn, self.address = self.ss.accept()
        _log.info(f"接收到了客户端的连接，客户端的信息：{self.address}")

        self.conn.send("connect-sever".encode("UTF-8"))

    async def on_group_at_message_create(self, message: Message):
        self.conn.send(message.content.encode("UTF-8"))


def QQ_Bot():
    intents = botpy.Intents.default()
    client = Client(intents=intents, is_sandbox=True)

    client.run(appid=test_config["appid"], secret=test_config["secret"])


if __name__ == "__main__":
    QQ_Bot()

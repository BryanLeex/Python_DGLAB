# -*- coding: utf-8 -*-
import asyncio
import copy
import os

import qrcode

import multiprocessing

import json
import time
from multiprocessing import Queue

import websockets

import botpy
from botpy import logging
from botpy.ext.cog_yaml import read
from botpy.message import Message

test_config = read(os.path.join(os.path.dirname(__file__), "config.yaml"))

_log = logging.get_logger()
_log.setLevel(level="INFO")


class Message:
    def __init__(self):
        self.type = None
        self.client_id = None
        self.message = None
        self.target_id = None


Q = multiprocessing.Queue()

m_AMaxStrength = 0
m_AStrength = 0

m_BMaxStrength = 0
m_BStrength = 0

m_port = None
m_host = None

m_connectionId = None
m_targetId = None


def loop(self):
    while True:
        self.Q.put("sb")


def setStrength(SA, SB) -> None:
    _log.info(f"strength: {SA}, B: {SB}")

    SA = max(SA, 0)
    SB = max(SB, 0)

    msgA = Message()
    msgB = Message()
    msgA.type = 4
    msgB.type = 4

    msgA.message = f'strength-1+2+{SA}'
    msgB.message = f'strength-2+2+{SB}'

    Q.put(copy.deepcopy(msgA))
    Q.put(copy.deepcopy(msgB))

    print("Queue empty:", Q.empty())
    print("Queue size:", Q.qsize())


async def sendMsg(ws):
    while True:
        print(Q.qsize())
        try:

            msg = Q.get_nowait()

            print("======", msg)

            lst = {
                "clientId": m_connectionId,
                "targetId": m_targetId,
                "message": msg.message,
                "type": msg.type
            }

            _log.info(f"sending Msg: {json.dumps(lst)}")

            await ws.send(json.dumps(lst))
        except asyncio.QueueEmpty:
            await asyncio.sleep(0.1)
        except websockets.exceptions.ConnectionClosed as e:
            _log.error(f"Connection closed: {e}")
            break
        except Exception as e:
            _log.error(f"An error occurred: {e}")
            break


async def receiveMsg(ws):
    try:
        while True:

            response = await ws.recv()

            response = json.loads(response)
            response = dict(response)

            msg = Message()
            msg.type = response['type']
            msg.client_id = response['clientId']
            msg.target_id = response['targetId']
            msg.message = response['message']

            _log.debug(f"type: {msg.type}")
            _log.debug(f"clientId: {msg.client_id}")
            _log.debug(f"targetId: {msg.target_id}")
            _log.debug(f"message: {msg.message}")

            if msg.type == 'bind':

                if msg.target_id == "":
                    m_connectionId = msg.client_id
                    m_targetId = msg.target_id
                    _log.info(f"connecting to {m_connectionId}")

                    QRCode = f"https://www.dungeon-lab.com/app-download.php#DGLAB-SOCKET#ws://{m_host}:{m_port}/{m_connectionId}"

                    _log.info(f"QRCode: {QRCode}")

                    qr = qrcode.QRCode(
                        version=4,  # 控制二维码的大小，范围为1到40，1是最小的二维码
                        error_correction=qrcode.constants.ERROR_CORRECT_L,  # 错误校正
                        box_size=10,  # 控制二维码中每个“箱”的大小
                        border=4,  # 控制周围边框的宽度
                    )

                    qr.add_data(QRCode)
                    qr.make(fit=True)

                    img = qr.make_image(fill='black', back_color='white')
                    print(img)
                    img.save("example_qrcode.png")

                else:
                    if msg.client_id != m_connectionId:
                        _log.error(f"Client receive wrong id: {msg.client_id}")
                    else:
                        m_targetId = msg.target_id

            elif msg.type == "msg":

                # "type":"msg","clientId":"612dbd59-df20-4c76-ac..."strength-0+0+200+200"

                if msg.message.find("strength") != -1:
                    res = msg.message[9:].split("+")

                    m_AStrength = int(res[0])
                    m_BStrength = int(res[1])

                    m_AMaxStrength = int(res[2])
                    m_BMaxStrength = int(res[3])

                    _log.info(f"A: {m_AStrength}, B: {m_BStrength}")
                    _log.info(f"maxA: {m_AMaxStrength}, maxB: {m_BMaxStrength}")

            if msg.type == 'heartbeat':
                _log.info(f"heartbeat: {msg}")

    except websockets.exceptions.ConnectionClosed as e:
        _log.error(f"Connection closed: {e}")

    except json.JSONDecodeError as e:
        _log.error(f"Error decoding JSON: {e}")

    except Exception as e:
        _log.error(f"An error occurred: {e}")


async def connect(host, port):
    _log.setLevel('DEBUG')

    m_host = host
    m_port = port

    while True:
        print(Q.qsize())
        time.sleep(0.1)

    url = f'ws://{host}:{port}'
    async with websockets.connect(url) as ws:
        _log.info(f"{url} is connected")

        # await self.receiveMsg(ws)

        receive_task = asyncio.create_task(self.receiveMsg(ws))

        send_task = asyncio.create_task(self.sendMsg(ws))

        await asyncio.gather(receive_task, send_task)


class Client(botpy.Client):

    async def on_ready(self):
        _log.info(f"robot 「{self.robot.name}」 on_ready!")

    async def on_group_at_message_create(self, message: Message):

        _log.debug(f"received message: {message}")
        _log.debug(f"AStrength: {m_AStrength}, BStrength: {m_BStrength}")

        if message:
            _log.debug(f"content: {message.content}")

            order = message.content.split(" ")

            while order[0] == '':
                order = order[1:]

            order[0] = order[0].upper()

            _log.debug(f"order: {order}")

            if order[0] == 'INC':

                _log.info(f"INC: {order[1]}")
                A = int(order[1]) + m_AStrength
                B = int(order[1]) + m_BStrength
                setStrength(A, B)

            elif order[0] == 'SUB':

                _log.info(f"SUB: {order[1]}")
                A = int(order[1]) - m_AStrength
                B = int(order[1]) - m_BStrength
                setStrength(A, B)

            elif order[0] == 'SET':

                _log.info(f"SET: {order[1]}")
                A = int(order[1])
                B = int(order[1])
                setStrength(A, B)

            else:
                _log.info(f"error: {order[0]}, Unknown order")


def QQ_Bot():
    client.run(appid=test_config["appid"], secret=test_config["secret"])


intents = botpy.Intents.default()
client = Client(intents=intents, is_sandbox=True)


def DGSocket():
    host = "192.168.1.21"
    port = 9999

    asyncio.run(connect(host, port))


if __name__ == "__main__":
    qq_bot_thread = multiprocessing.Process(target=QQ_Bot)
    dg_socket_thread = multiprocessing.Process(target=DGSocket)

    qq_bot_thread.start()
    dg_socket_thread.start()

    qq_bot_thread.join()
    dg_socket_thread.join()

import asyncio
import copy
import multiprocessing
import threading
import time

import json

import os

import logging

import websockets

import socket

import qrcode

host = '192.168.1.21'
port = 9999

logger = logging.getLogger()
logger.setLevel('INFO')

BASIC_FORMAT = "%(asctime)s: %(levelname)s: %(message)s"
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

formatter = logging.Formatter(BASIC_FORMAT, DATE_FORMAT)

chlr = logging.StreamHandler()  # 输出到控制台的handler
chlr.setFormatter(formatter)
chlr.setLevel('DEBUG')  # 也可以不设置，不设置就默认用logger的level
logger.addHandler(chlr)

fhlr = logging.FileHandler('Socket.log')  # 输出到文件的handler
fhlr.setFormatter(formatter)
logger.addHandler(fhlr)


class DGLAB_Bot:
    class Message:
        def __init__(self):
            self.type = None
            self.client_id = None
            self.message = None
            self.target_id = None

    def __init__(self):
        self.connectID = 0
        self.targetID = 0

        self.m_AStrength = 0
        self.m_BStrength = 0
        self.m_AMaxStrength = 0
        self.m_BMaxStrength = 0

    async def receive_tsk(self, ws):
        while True:
            try:
                logger.debug("receive tsk")
                message = await ws.recv()
                logger.debug(f"Received: {message}")

                if message == "":
                    while True:
                        print("-")

                response = dict(json.loads(message))
                logger.debug(response)

                msg = DGLAB_Bot.Message()
                msg.type = response['type']
                msg.client_id = response['clientId']
                msg.target_id = response['targetId']
                msg.message = response['message']

                logger.debug(f"type: {msg.type}")
                logger.debug(f"clientId: {msg.client_id}")
                logger.debug(f"targetId: {msg.target_id}")
                logger.debug(f"message: {msg.message}")

                if msg.type == 'bind':

                    if msg.target_id == "":
                        self.connectID = msg.client_id
                        m_targetId = msg.target_id
                        logger.info(f"connecting to {self.connectID}")

                        QRCode = f"https://www.dungeon-lab.com/app-download.php#DGLAB-SOCKET#ws://{host}:{port}/{self.connectID}"

                        logger.info(f"QRCode: {QRCode}")

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
                        if msg.client_id != self.connectID:
                            logger.error(f"Client receive wrong id: {msg.client_id}")
                        else:
                            self.targetID = msg.target_id

                elif msg.type == "heartbeat":
                    logger.info(f"heartbeat: {msg.message}")

                elif msg.type == "msg":

                    # "type":"msg","clientId":"612dbd59-df20-4c76-ac..."strength-0+0+200+200"

                    if msg.message.find("strength") != -1:
                        res = msg.message[9:].split("+")

                        self.m_AStrength = int(res[0])
                        self.m_BStrength = int(res[1])

                        self.m_AMaxStrength = int(res[2])
                        self.m_BMaxStrength = int(res[3])

                        logger.info(f"A: {self.m_AStrength}, B: {self.m_BStrength}")
                        logger.info(f"maxA: {self.m_AMaxStrength}, maxB: {self.m_BMaxStrength}")

                    else:

                        logger.error(f"=============== ERROR ===========> {msg.message}")

            except websockets.ConnectionClosed as e:
                logger.error(f"Websocket disconnected: {e}")

            except json.decoder.JSONDecodeError as e:
                logger.error(f"JSON decoding error: {e}")

    async def send_tsk(self, ws, Q: multiprocessing.Queue):
        """异步发送消息"""
        while True:

            if Q.empty():
                await asyncio.sleep(0.1)
                continue

            msg = Q.get()

            msg = msg.split(" ")
            while msg[0] == "":
                msg = msg[1:]

            logger.info("========= RECEIVE SOCKET ==========> {}".format(msg))

            if msg[0] in ["inc", "dec", "set", "connect-sever", "get"]:

                if msg[0] == "connect-sever":
                    logger.info("Connected to Server")
                elif msg[0] == "inc":
                    self.m_AStrength += int(msg[1])
                    self.m_BStrength += int(msg[1])
                elif msg[0] == "dec":
                    self.m_AStrength -= int(msg[1])
                    self.m_BStrength -= int(msg[1])
                elif msg[0] == "set":
                    self.m_AStrength = int(msg[1])
                    self.m_BStrength = int(msg[1])
                elif msg[0] == "get":
                    logger.info(
                        f"Strength: ({self.m_AStrength}, {self.m_BStrength}) with Maximum: ({self.m_AMaxStrength}, {self.m_BMaxStrength})")

                self.m_AStrength = min(max(self.m_AStrength, 0), self.m_AMaxStrength)
                self.m_BStrength = min(max(self.m_BStrength, 0), self.m_BMaxStrength)

                Base_lst = {
                    "clientId": self.connectID,
                    "targetId": self.targetID,
                    "message": "",
                    "type": 4
                }

                lst = copy.deepcopy(Base_lst)

                lst["message"] = f'strength-1+2+{self.m_AStrength}'
                logger.info(f"sending MsgA: {json.dumps(lst)}")
                await ws.send(json.dumps(lst))

                lst = copy.deepcopy(Base_lst)
                lst["message"] = f'strength-2+2+{self.m_BStrength}'
                logger.info(f"sending MsgB: {json.dumps(lst)}")
                await ws.send(json.dumps(lst))

            elif msg[0] in ["do", "wave"]:

                wave = '[\\"0A0A0A0A00000000\\",\\"0A0A0A0A0A0A0A0A\\",\\"0A0A0A0A14141414\\",\\"0A0A0A0A1E1E1E1E\\",\\"0A0A0A0A28282828\\",\\"0A0A0A0A32323232\\",\\"0A0A0A0A3C3C3C3C\\",\\"0A0A0A0A46464646\\",\\"0A0A0A0A50505050\\",\\"0A0A0A0A5A5A5A5A\\",\\"0A0A0A0A64646464\\"]'

                channel = "A"
                duration = 5
                res = '{' + f"\"type\":\"clientMsg\",\"message\":\"{channel}:{wave}\",\"time\":{duration},\"channel\":\"{channel}\",\"clientId\":\"{self.connectID}\",\"targetId\":\"{self.targetID}\"" + '}'
                logger.info(f"sending {res}")

                await ws.send(res)

                channel = "B"
                duration = 5
                res = '{' + f"\"type\":\"clientMsg\",\"message\":\"{channel}:{wave}\",\"time\":{duration},\"channel\":\"{channel}\",\"clientId\":\"{self.connectID}\",\"targetId\":\"{self.targetID}\"" + '}'
                logger.info(f"sending {res}")

                await ws.send(res)

    async def connect(self, Q: multiprocessing.Queue):

        url = f'ws://{host}:{port}'

        logger.info(f"connecting to {url}")

        async with websockets.connect(url) as ws:
            logger.info(f"connected to {url}")

            receive_task = asyncio.create_task(self.receive_tsk(ws))

            send_task = asyncio.create_task(self.send_tsk(ws, Q))

            await asyncio.gather(receive_task, send_task)

    def recv_sc(self, Q: multiprocessing.Queue):

        sc = socket.socket()
        sc.connect(("localhost", 5679))

        while True:
            data = sc.recv(1024).decode("utf-8")
            Q.put(str(data))


dg = DGLAB_Bot()

Q = multiprocessing.Queue()

recv_sc_process = multiprocessing.Process(target=dg.recv_sc, args=(Q,))
if __name__ == '__main__':
    recv_sc_process.start()

    loop = asyncio.get_event_loop().run_until_complete(dg.connect(Q))

    recv_sc_process.join()

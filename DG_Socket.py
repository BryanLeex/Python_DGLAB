import asyncio

import websockets

import json

import queue

import logging

logger = logging.getLogger()
logger.setLevel('DEBUG')
BASIC_FORMAT = "%(asctime)s: %(levelname)s: %(message)s"
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
formatter = logging.Formatter(BASIC_FORMAT, DATE_FORMAT)
chlr = logging.StreamHandler()  # 输出到控制台的handler
chlr.setFormatter(formatter)
chlr.setLevel('DEBUG')  # 也可以不设置，不设置就默认用logger的level
fhlr = logging.FileHandler('Socket.log')  # 输出到文件的handler
fhlr.setFormatter(formatter)
logger.addHandler(chlr)
logger.addHandler(fhlr)


class Message:

    def __init__(self):
        self.type = None
        self.client_id = None
        self.message = None
        self.target_id = None


class DG_Socket:
    def __init__(self, host, port) -> None:

        self.m_targetId = None
        self.m_port = port
        self.m_host = host

        self.m_keep_running = True

        self.m_connectionId = None
        self.m_websocket = None

        self.m_isConnect = False

        self.m_AStrength = 0
        self.m_BStrength = 0

        self.m_AMaxStrength = 0
        self.m_BMaxStrength = 0

        self.m_MsgQueue = queue.Queue()

    async def run(self):

        url = f'ws://{self.m_host}:{self.m_port}'
        self.m_websocket = await websockets.connect(url)

    async def connect(self):
        url = f'ws://{self.m_host}:{self.m_port}'
        self.m_websocket = await websockets.connect(url)

        if self.m_websocket is None:
            logger.error('could not connect to websocket')

    async def ReceiveMsg(self):

        while self.m_keep_running:

            post = dict(json.loads(await self.m_websocket.recv()))

            msg = Message()
            msg.type = post['type']
            msg.client_id = post['clientId']
            msg.target_id = post['targetId']
            msg.message = post['message']

            logger.debug(f'Connected to Server, post: {post}')

            logger.debug("====================================================")
            logger.debug(f"type: {msg.type}")
            logger.debug(f"client_id: {msg.client_id}")
            logger.debug(f"target_id: {msg.target_id}")
            logger.debug(f"message: {msg.message}")
            logger.debug("====================================================")

            if msg.type == "bind":

                if msg.target_id == "":

                    self.m_connectionId = msg.client_id
                    self.m_targetId = msg.target_id
                    logger.info(f"connecting to {self.m_connectionId}")

                    QRCode = f"https://www.dungeon-lab.com/app-download.php#DGLAB-SOCKET#ws://{self.m_host}:{self.m_port}/{self.m_connectionId}"

                    logger.info(f"QRCode: {QRCode}")

                else:
                    if msg.client_id != self.m_connectionId:
                        logger.error(f"Client receive wrong id: {msg.client_id}")

            elif msg.type == "msg":

                # "type":"msg","clientId":"612dbd59-df20-4c76-ac..."strength-0+0+200+200"

                if msg.message.find("strength") != -1:
                    res = msg.message[9:].split("+")

                    self.m_AStrength = int(res[0])
                    self.m_BStrength = int(res[1])

                    self.m_AMaxStrength = int(res[2])
                    self.m_BMaxStrength = int(res[3])

            elif msg.type == "heartbeat":

                logger.info("Heartbeat received")

                self.m_isConnect = True

    async def SendMsg(self):

        while True:
            if self.m_MsgQueue.qsize() != 0 and self.m_isConnect:
                msg = await self.m_MsgQueue.get()

                logger.info(f"SendMsg: {msg}")

                await self.m_websocket.sendMsg(msg)

    async def T(self):
        while True:
            a, b = input().split(" ")

            print(f"a, b = {a}, {b}")

            self.SetStrength(a, b)

    def CombineMsg(self, msg: Message):

        dic = dict[
            ('clientId', self.m_connectionId),
            ('targetId', self.m_targetId),
            ("msg", msg.message),
            ("type", msg.type)
        ]

        return json.dumps(dic)

    def SetStrength(self, AStrength, BStrength):

        AStrength = max(min(self.m_AMaxStrength, AStrength), 0)
        BStrength = max(min(self.m_BMaxStrength, BStrength), 0)

        self.m_AStrength = AStrength
        self.m_BStrength = BStrength

        msg = Message()
        msg.type = "4"

        msg.message = f"strength-1+2+{AStrength}"
        self.m_MsgQueue.put(self.CombineMsg(msg))

        msg.message = f"strength-2+2+{BStrength}"
        self.m_MsgQueue.put(self.CombineMsg(msg))

    '''
    wsConn.send(JSON.stringify(
        {
            clientId: connectionId,
            targetId: targetWSId,
            type: 4,
            message: "strength-2+2+201"
        }
    ))
    '''


async def main(p_DG: DG_Socket):
    await asyncio.gather(
        p_DG.ReceiveMsg(),
        p_DG.SendMsg(),
        p_DG.T()
    )


if __name__ == "__main__":
    dg = DG_Socket("192.168.1.21", 9999)
    asyncio.run(dg.connect())

    asyncio.run(dg.ReceiveMsg())
    asyncio.run(main(dg))

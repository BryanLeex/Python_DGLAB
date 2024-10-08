import asyncio

import multiprocessing
import time

s = "abc"

class C:
    def __init__(self):
        self.s = 0
    async def c(self):
        # await asyncio.sleep(2)
        global s
        self.s = "sss"
        print(id(self.s))

    def p(self):
        asyncio.run(self.c())

def pp():
    while True:
        print(id(cc.s))
        time.sleep(0.2)

cc = C()



if __name__ == "__main__":
    print(id(s))
    print("------------")
    tsk2 = multiprocessing.Process(target=pp)
    tsk = multiprocessing.Process(target=cc.p())
    tsk2.start()
    tsk.start()


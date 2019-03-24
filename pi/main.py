#!/usr/bin/env python
# coding: utf-8

import time
import logging

from lib import utils, daemon, connection, commands

class IotConf:
    def __init__(self):
        self.listen_addr = utils.get_conf_pat("xrpl", "address")

class Iot:
    def __init__(self, address=None, log_level=None):
        self.api = None
        self.address = address

    def connect(self):
        self.api = connection.Connection(log_level=logging.ERROR)
        self.api.start()

        utils.log.info("Waiting for connection to be set up...")
        self.api.connected.wait()

        utils.log.info("Send subscription command for account %s..." % (self.address, ))
        self.api.send(payload={'id': 1002, 'command': 'subscribe', 'accounts': [self.address]})

    def handle(self, tx):
            if(len(tx.get('Memos', [])) > 0):
                for m in tx.get('Memos'):
                    try:
                        memo = bytes.fromhex(m.get('Memo').get('MemoData')).decode('utf-8')
                        for command in dir(commands):
                            func = getattr(commands, command)
                            if callable(func) and func.__name__ == memo:
                                utils.log.info("Run '%s' command base on tx %s " % (memo, tx.get('hash') ))
                                func()
                    except Exception as e:
                        print(e)


    def check(self):
        while not self.api.q.empty():
            event = self.api.q.get()
            if (event[0] == 'transaction'):
                if(event[1].get('engine_result') == 'tesSUCCESS'):
                    tx = event[1].get('transaction')
                    if tx.get('Account') == self.address:
                        self.handle(tx)


class IotDaemon(daemon.Daemon):
    def run(self):
        iotc = IotConf()
        iot = Iot()
        while True:
            time.sleep(1)
            iot.check()


if __name__ == "__main__":
    iotc = IotConf()
    iot = Iot(address=iotc.listen_addr)
    iot.connect()
    while True:
        time.sleep(1)
        iot.check()

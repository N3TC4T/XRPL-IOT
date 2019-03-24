#!/usr/bin/env python
# coding: utf-8

import logging
import sys
import time
from lib.connection import Connection


if __name__ == "__main__" :
    iot = Iot()
    iot.connect()
    iot.send()



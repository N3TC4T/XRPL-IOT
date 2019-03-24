#!/usr/bin/env python
# coding: utf-8

import logging
import logging.handlers
from six.moves import configparser
import time
import datetime


class ColorPrint:

    def __init__(self):
        pass

    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARING = '\033[95m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

    @staticmethod
    def log_normal(info):
        print(ColorPrint.OKBLUE + info + ColorPrint.ENDC)

    @staticmethod
    def log_high(info):
        print(ColorPrint.OKGREEN + info + ColorPrint.ENDC)

    @staticmethod
    def log_warn(info):
        print(ColorPrint.WARING + info + ColorPrint.ENDC)

    @staticmethod
    def log_fail(info):
        print(ColorPrint.FAIL + info + ColorPrint.ENDC)


class LoadConf(object):
    def __init__(self):
        self.cfg = configparser.ConfigParser()

    def read_conf(self, ini_file):
        self.cfg.read(ini_file)

    def get_conf_item(self, cm='conf_module', ci='conf_item'):
        try:
            return self.cfg.get(cm, ci)
        except BaseException as e:
            raise e


class Logging:
    def __init__(self, log_filename='logs'):
        self.LOG = logging.getLogger('log')
        loghdlr_wl = logging.handlers.RotatingFileHandler(log_filename, "a", 0, 1)
        log_format_wl = logging.Formatter("%(levelname)s:%(asctime)s:%(message)s")
        loghdlr_wl.setFormatter(log_format_wl)
        self.LOG.addHandler(loghdlr_wl)
        self.LOG.setLevel(logging.INFO)

    def info(self, msg, *args, **kwargs):
        if self.LOG is not None:
            self.LOG.info(msg)

    def error(self, msg, *args, **kwargs):
        if self.LOG is not None:
            self.LOG.error(msg)


log = Logging()


class SaveRes():
    def __init__(self, res_filename):
        self.RES = logging.getLogger('res')
        loghdlr_sr = logging.handlers.RotatingFileHandler(res_filename, "w", 0, 1)
        log_format_sr = logging.Formatter("%(message)s")
        loghdlr_sr.setFormatter(log_format_sr)
        self.RES.addHandler(loghdlr_sr)
        self.RES.setLevel(logging.INFO)

    def sr_save(self, msg, *args, **kwargs):
        if self.RES is not None:
            self.RES.info(msg)


def get_conf_pat(module=None, ci='conf_item'):
    cfg_file = 'iot.conf'
    try:
        lc = LoadConf()
        lc.read_conf(cfg_file)
        return lc.get_conf_item(module, ci)
    except Exception as e:
        raise e


def localtime():
    return int(time.time())


def timetoint(*args):
    return int(time.mktime(datetime.datetime(*args).timetuple()))


def today_time(day=0):
    now = datetime.datetime.now()
    delta = datetime.timedelta(days=int(day) * (-1))
    n_days = now - delta
    return n_days.strftime('%Y%m%d')


def daytimetoint(day=None, times=None):
    day1time = int(time.mktime(time.strptime(today_time(int(day)) + times, "%Y%m%d%H%M%S")))
    return day1time


def today_start_time(offset=0):
    return daytimetoint(day=offset, times='000000')


def today_cur_time(offset=0):
    today_tuple = datetime.datetime.today()
    h = str(today_tuple.hour).zfill(2)
    m = str(today_tuple.minute).zfill(2)
    s = str(today_tuple.second).zfill(2)
    the_times = "%2s%2s%2s" % (h, m, s)
    return daytimetoint(day=offset, times=the_times)


def today_last_time(offset=0):
    return daytimetoint(day=offset, times='235959')

# -*- coding: utf-8 -*-
# __author__ lukasz.g.migas
# Standard library imports
# Standard library imports
# Standard library imports
import time
from datetime import datetime


def getTime():
    return datetime.now().strftime("%d-%m-%Y %H:%M:%S")


def ttime():
    return time.time()


def tsleep(duration=0.1):
    time.sleep(duration)
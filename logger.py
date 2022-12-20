"""
@summary:       Logger library to streamline logging
@run:           import coop.logger as clog
@license:       MIT
@repository:    https://github.com/artineering-io/maya-coop
"""
import logging
import datetime


def logger(name, debug=True):
    """
    Create a logger with name
    name (unicode): Name of the logger
    debug (bool): If log-level should be set to debug
    """
    logging.basicConfig()  # errors and everything else (2 separate log groups)
    log = logging.getLogger(name)
    log.setLevel(logging.INFO)
    if debug:
        log.setLevel(logging.DEBUG)
    return log


def today_as_int():
    """
    Get today's date as int: YYYYMMDD
    Returns:
        (int): Today as an integer: YYYYMMDD
    """
    today = datetime.datetime.now()
    return int(today.strftime("%Y%m%d"))

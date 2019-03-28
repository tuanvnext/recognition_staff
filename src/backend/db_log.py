import logging
import os

CURRENT_FOLDER = os.path.dirname(os.path.abspath(__file__))
LOG_FOLDER = os.path.join(CURRENT_FOLDER, 'logs')
if not os.path.exists(LOG_FOLDER):
    os.mkdir(LOG_FOLDER)
LOG_PATH = os.path.join(LOG_FOLDER, 'db.log')

def set_log_file(logger, file_path, mode='a'):
    handler = logging.FileHandler(file_path, mode)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def set_log_console(logger):
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

def info(mess):
    logger.info(mess)

def error(mess):
    logger.error(mess)

def exception(mess):
    logger.exception(mess)

logger = logging.getLogger('db.log')
logger.setLevel(logging.INFO)
set_log_file(logger, LOG_PATH)
set_log_console(logger)

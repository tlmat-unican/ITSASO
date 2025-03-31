import logging

def setup_custom_logger(name):    
    logger = logging.getLogger(name)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(CustomFormatter())
    logger.addHandler(ch)
    return logger

class CustomFormatter(logging.Formatter):

    grey = "\x1b[38;20m"
    brown = "\x1b[33;20m"
    yellow = "\033[93m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    blue = "\x1b[34;20m"
    magenta = "\x1b[35;20m"
    reset = "\x1b[0m"
    format = "%(asctime)s | %(levelname)s | %(module)s | %(message)s"

    FORMATS = {
        logging.INFO: grey + format + reset,
        logging.DEBUG: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: brown + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
import logging

def configure_logging():
    # Create a logger
    logger = logging.getLogger(__name__)

    # Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    logger.setLevel(logging.INFO)

    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(filename)s:%(lineno)s - %(levelname)s - %(message)s')

    # Create a console handler and set the formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Add the console handler to the logger
    logger.addHandler(console_handler)

    # Optionally, add a file handler to log to a file
    # file_handler = logging.FileHandler('logfile.log')
    # file_handler.setFormatter(formatter)
    # logger.addHandler(file_handler)

    return logger

if __name__ == '__main__':
    # Configure logging
    logger = configure_logging()

    # Example log messages
    logger.debug('This is a debug message')
    logger.info('This is an info message')
    logger.warning('This is a warning message')
    logger.error('This is an error message')
    logger.critical('This is a critical message')

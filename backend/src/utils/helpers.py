from loguru import logger
import sys

def setup_logging():
    logger.remove()  # Clear default handlers
    logger.add(
        "logs/app.log",
        rotation="1 MB",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="DEBUG",
    )
    logger.add(sys.stderr, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}", level="INFO")

setup_logging()
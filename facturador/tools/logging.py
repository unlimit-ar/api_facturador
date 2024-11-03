import logging
import os

logging.basicConfig(level=logging.DEBUG, filename='./app.log', filemode='a',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

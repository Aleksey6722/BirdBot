import logging

logger = logging.getLogger('BirdsLogger')
logger.setLevel(logging.INFO)
handler = logging.FileHandler('Birdsbot.log', mode='w')
formatter = logging.Formatter("%(name)s %(asctime)s %(levelname)s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
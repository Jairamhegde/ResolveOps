import logging
import sys

handlers = [logging.StreamHandler(sys.stdout)]
try:
    handlers.append(logging.FileHandler('log.log'))
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)

logger = logging.getLogger("ResolveOps")


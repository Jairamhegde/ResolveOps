import logging

logging.basicConfig(
    filename='log.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s' 
)

logger = logging.getLogger("ResolveOps")

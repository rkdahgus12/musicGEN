from redis import Redis
from rq import Queue

from .config import QUEUE_NAME, REDIS_URL

redis_conn = Redis.from_url(REDIS_URL)
song_queue = Queue(QUEUE_NAME, connection=redis_conn)

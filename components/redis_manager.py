import os
import redis
from dotenv import load_dotenv

load_dotenv()


def get_redis_client():

    redis_url = os.getenv("REDIS_URL")

    if redis_url:
        return redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=10,
            socket_timeout=10,
            health_check_interval=30,
        )

    redis_host = os.getenv("REDIS_HOST")
    redis_port = os.getenv("REDIS_PORT")
    redis_password = os.getenv("REDIS_PASSWORD")

    if not redis_host:
        raise RuntimeError(
            "REDIS_HOST or REDIS_URL is not configured"
        )

    return redis.Redis(
        host=redis_host,
        port=int(redis_port or 6379),
        password=redis_password or None,
        decode_responses=True,
        socket_connect_timeout=10,
        socket_timeout=10,
        health_check_interval=30,
    )
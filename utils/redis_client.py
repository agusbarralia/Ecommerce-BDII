import redis

def get_redis_client():
    client = redis.Redis(host='127.0.0.1', port=6379, db=0)
    return client



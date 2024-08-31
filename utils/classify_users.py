from utils.redis_client import get_redis_client
import time

def classify_user(username):
    redis_client = get_redis_client()
    current_date = time.strftime("%Y-%m-%d")
    
    key = f"user:{username}:connection_time:{current_date}"
    total_time = float(redis_client.get(key))
    
    if total_time > 240:
        classification = "TOP"
    elif 120  <= total_time <= 240:
        classification = "MEDIUM"
    else:
        classification = "LOW"
    
    redis_client.hset(f"user:{username}", "classification", classification)
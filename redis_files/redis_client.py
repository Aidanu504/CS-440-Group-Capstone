import redis_files
import json
import os
from dotenv import load_dotenv
from redis import Redis 

load_dotenv()

redis_client = Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=0,
    decode_responses=True
)

CACHE_EXPIRY = 300

def cache_product(product_id, product_data):
    try:
        redis_client.setex(
            f"product:{product_id}", 
            CACHE_EXPIRY, 
            json.dumps(product_data)
        )
        return True
    except Exception as e:
        print(f"Redis caching error: {e}")
        return False

def get_cached_product(product_id):
    try:
        cached_data = redis_client.get(f"product:{product_id}")
        if cached_data:
            return json.loads(cached_data)
        return None
    except Exception as e:
        print(f"Redis retrieval error: {e}")
        return None

def cache_product_list(products):
    try:
        redis_client.setex("all_products", CACHE_EXPIRY, json.dumps(products))
        return True
    except Exception as e:
        print(f"Redis caching error: {e}")
        return False

def get_cached_product_list():
    try:
        cached_list = redis_client.get("all_products")
        if cached_list:
            return json.loads(cached_list)
        return None
    except Exception as e:
        print(f"Redis retrieval error: {e}")
        return None

def invalidate_product_cache(product_id=None):
    try:
        if product_id:
            redis_client.delete(f"product:{product_id}")
        redis_client.delete("all_products")
        return True
    except Exception as e:
        print(f"Redis cache invalidation error: {e}")
        return False

def increment_view_counter(product_id):
    try:
        return redis_client.incr(f"views:product:{product_id}")
    except Exception as e:
        print(f"Redis counter error: {e}")
        return None

def get_popular_products(limit=5):
    try:
        all_view_keys = redis_client.keys("views:product:*")
        
        product_views = []
        for key in all_view_keys:
            product_id = key.split(":")[-1]
            views = redis_client.get(key)
            if views:
                product_views.append((product_id, int(views)))

        sorted_products = sorted(product_views, key=lambda x: x[1], reverse=True)
        return [int(p[0]) for p in sorted_products[:limit]]
    except Exception as e:
        print(f"Redis popular products error: {e}")
        return []
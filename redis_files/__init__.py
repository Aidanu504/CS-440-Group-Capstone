from .redis_client import (
    cache_product, get_cached_product, 
    cache_product_list, get_cached_product_list,
    invalidate_product_cache, increment_view_counter,
    get_popular_products
)
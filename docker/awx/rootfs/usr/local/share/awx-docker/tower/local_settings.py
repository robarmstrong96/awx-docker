import os

SYSTEM_UUID = os.environ["AWX_SYSTEM_UUID"]

ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = [os.environ["AWX_CSRF_TRUSTED_ORIGIN"]]
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

BROKER_URL = os.environ["AWX_BROKER_URL"]
CACHES = {
    "default": {
        "BACKEND": "ansible_base.lib.cache.redis_cache.DABRedisCache",
        "LOCATION": os.environ["AWX_CACHE_URL"],
    }
}
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [BROKER_URL],
            "capacity": 10000,
            "group_expiry": 157784760,
        },
    }
}

BROADCAST_WEBSOCKET_PORT = 8013
BROADCAST_WEBSOCKET_VERIFY_CERT = False
BROADCAST_WEBSOCKET_PROTOCOL = "http"

STATIC_URL = "/static/"

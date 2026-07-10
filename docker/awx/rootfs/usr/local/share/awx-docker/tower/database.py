import os

DATABASES = {
    "default": {
        "ATOMIC_REQUESTS": True,
        "ENGINE": "awx.main.db.profiled_pg",
        "NAME": os.environ["AWX_DB_NAME"],
        "USER": os.environ["AWX_DB_USER"],
        "PASSWORD": os.environ["AWX_DB_PASSWORD"],
        "HOST": os.environ["AWX_DB_HOST"],
        "PORT": os.environ["AWX_DB_PORT"],
    }
}

if os.environ.get("AWX_DB_SSLMODE"):
    DATABASES["default"]["OPTIONS"] = {"sslmode": os.environ["AWX_DB_SSLMODE"]}

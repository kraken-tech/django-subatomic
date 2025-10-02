from environs import env


env.read_env()


DATABASES = {
    "default": env.dj_db_url(
        "DEFAULT_DATABASE_URL", default="postgres://localhost/subatomic"
    ),
    "other": env.dj_db_url(
        "OTHER_DATABASE_URL", default="postgres://localhost/subatomic_other"
    ),
}
USE_TZ = True

# It's OK for us to hard-code this secret key for the tests.
SECRET_KEY = "hunter2"  # noqa: S105

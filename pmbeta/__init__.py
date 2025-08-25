# Expose Celery app if Celery is available; otherwise, remain importable without Celery.
try:
    from .celery import app as celery_app  # type: ignore
    __all__ = ('celery_app',)
except Exception:
    __all__ = tuple()

# PMBeta Django Project

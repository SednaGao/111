# coding: utf8

from celery import Celery
from config.config import DevelopmentConfig

broker = DevelopmentConfig.CELERY_BROKER
backend = DevelopmentConfig.CELERY_BACKEND

celery_app = Celery(
    'my-celery',
    broker=broker,
    backend=backend,
    include=['app.job.job_tasks', ]
)

celery_app.conf.timezone = 'Asia/Shanghai'
celery_app.conf.enable_utc = False


if __name__ == '__main__':
    celery_app.start()


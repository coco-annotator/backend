from celery import Celery
import backend.config as Config
from backend.database import connect_mongo

connect_mongo('Celery_Worker')

celery = Celery(
    Config.NAME,
    backend=Config.CELERY_RESULT_BACKEND,
    broker=Config.CELERY_BROKER_URL
)
celery.autodiscover_tasks(['workers.tasks'])


if __name__ == '__main__':
    celery.start()

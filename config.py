import os
import subprocess
import dotenv
import random

dotenv.load_dotenv()


#def get_tag():
#    result = subprocess.run(["git", "describe", "--abbrev=0", "--tags"], stdout=subprocess.PIPE)
#    return str(result.stdout.decode("utf-8")).strip()


def _get_bool(key, default_value):
    if key in os.environ:
        value = os.environ[key]
        if value == 'True' or value == 'true' or value == '1':
            return True
        return False
    return default_value


NAME = os.getenv("NAME", "COCO Annotator")
#VERSION = get_tag()

### File Watcher
FILE_WATCHER = os.getenv("FILE_WATCHER", False)
IGNORE_DIRECTORIES = ["_thumbnail", "_settings"]

# Flask/Gunicorn
#
#   LOG_LEVEL - The granularity of log output
#
#       A string of "debug", "info", "warning", "error", "critical"
#
#   WORKER_CONNECTIONS - limits the maximum number of simultaneous
#       clients that a single process can handle.
#
#       A positive integer generally set to around 1000.
#
#   WORKER_TIMEOUT - If a worker does not notify the master process
#       in this number of seconds it is killed and a new worker is
#       spawned to replace it.
#
SWAGGER_UI_JSONEDITOR = True
DEBUG = os.getenv("DEBUG", 'false').lower() == 'true'
PRELOAD = False

MAX_CONTENT_LENGTH = os.getenv("MAX_CONTENT_LENGTH", 1 * 1024 * 1024 * 1024)  # 1GB
MONGODB_HOST = os.getenv("MONGODB_HOST", "mongodb://127.0.0.1:27018/flask")
SECRET_KEY = os.getenv("SECRET_KEY", "<--- CHANGE THIS KEY --->")

LOG_LEVEL = 'debug'
WORKER_CONNECTIONS = 1000

TESTING = os.getenv("TESTING", False)

### Workers
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "amqp://user:password@messageq:5672//")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "mongodb://database/flask")

### Dataset Options
DATASET_DIRECTORY = os.getenv("DATASET_DIRECTORY", "/datasets/")
INITIALIZE_FROM_FILE = os.getenv("INITIALIZE_FROM_FILE")

### User Options
LOGIN_DISABLED = _get_bool("LOGIN_DISABLED", False)
ALLOW_REGISTRATION = _get_bool('ALLOW_REGISTRATION', True)

### Models
MASK_RCNN_FILE = os.getenv("MASK_RCNN_FILE", "")
MASK_RCNN_CLASSES = os.getenv("MASK_RCNN_CLASSES", "BG")

DEXTR_FILE = os.getenv("DEXTR_FILE", "/models/dextr_pascal-sbd.h5")

### JWT Keys
JWT_SECRET_KEY = os.getenv('JWT_SECRET', str(random.random()))
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
JWT_REFRESH_SECRET_KEY = os.getenv('JWT_REFRESH_SECRET_KEY', str(random.random()))

### Token lifetimes
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30 minutes
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days

REST_IP = os.getenv("REST_IP", "0.0.0.0")
REST_PORT = int(os.getenv("REST_PORT", 5000))

# __all__ = ["Config"]

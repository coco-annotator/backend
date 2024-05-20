import os
import logging

from fastapi_socketio import SocketManager

import backend.config as Config
from backend.database import connect_mongo
from backend.webserver.variables import responses

from backend.webserver.api import (
    admin,
    annotations,
    annotator,
    categories,
    datasets,
    exports,
    images,
    models,
    tasks,
    undo,
    users,
)

from fastapi import FastAPI, HTTPException, Response
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi_socketio import SocketManager

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
socket_manager = SocketManager(app=app)

logger.info('Connecting to MongoDB.')
mongodb = connect_mongo('webserver')

app.include_router(admin.router)
app.include_router(annotator.router)
app.include_router(annotations.router)
app.include_router(categories.router)
app.include_router(datasets.router)
app.include_router(exports.router)
app.include_router(images.router)
app.include_router(models.router)
app.include_router(tasks.router)
app.include_router(undo.router)
app.include_router(users.router)

@app.get("/docs", responses=responses)
async def read_docs():
    return Response(content=get_swagger_ui_html(
        title="api docs",
        openapi_url="/openapi.json"
    ), media_type="text/html")


@app.get("/", responses=responses)
async def ready():
    if Config.DEBUG:
        return os.environ
    return "Hello World!"


if __name__ == "__main__":
    import uvicorn

    logger.info('Starting webserver.')
    uvicorn.run("start:app", host=Config.REST_IP, port=int(Config.REST_PORT), workers=1)

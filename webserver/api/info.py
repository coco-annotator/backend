# # from flask_restplus import Namespace, Resource
# #
# from backend.workers.tasks import long_task
# import backend.config as Config
#
# from werkzeug.security import generate_password_hash
#
# from backend.database import UserModel, TaskModel
# from backend.webserver.variables import responses, PageDataModel
#
# from fastapi import APIRouter, HTTPException
# from pydantic import BaseModel
#
# from ..util.query_util import fix_ids
#
# #api = Namespace('info', description='Software related operations')
#
# router = APIRouter()
#
# #@api.route('/')
# @router.get('/info', responses=responses)
# def get_info():
#     """ Returns information about current version """
#
#     return {
#         "name": "COCO Annotator",
#         "author": "Justin Brooks",
#         "demo": "https://annotator.justinbrooks.ca/",
#         "repo": "https://github.com/jsbroks/coco-annotator",
#         "git": {
#             "tag": Config.VERSION
#         },
#         "login_enabled": not Config.LOGIN_DISABLED,
#         "total_users": UserModel.objects.count(),
#         "allow_registration": Config.ALLOW_REGISTRATION
#     }
#
#
# #@api.route('/long_task')
# @router.get('/info/long_task', responses=responses)
# def get_long_task(self):
#     """ Returns information about current version """
#     task_model = TaskModel(group="test", name="Testing Celery")
#     task_model.save()
#
#     task = long_task.delay(20, task_model.id)
#     return {'id': task.id, 'state': task.state}
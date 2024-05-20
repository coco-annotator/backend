# from flask_restplus import Namespace, Resource
# from flask_login import login_required
#
from ..util import query_util
from backend.database import TaskModel
#
#
# api = Namespace('tasks', description='Task related operations')

from werkzeug.security import generate_password_hash

from backend.database import UserModel
from backend.webserver.variables import responses, PageDataModel
from .users import SystemUser, get_current_user
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel


router = APIRouter()

#@api.route('/')
#@login_required
@router.get("/tasks", responses=responses)
async def get_tasks(user: SystemUser = Depends(get_current_user)):
    """ Returns all tasks """
    query = TaskModel.objects.only(
        'group', 'id', 'name', 'completed', 'progress', 'priority', 'creator', 'desciption', 'errors', 'warnings'
    ).all()
    return query_util.fix_ids(query)


#@api.route('/<int:task_id>')
#@login_required
@router.delete('/tasks/{task_id}', responses=responses)
async def delete(task_id: int, user: SystemUser = Depends(get_current_user)):
    """ Deletes task """
    task = TaskModel.objects(id=task_id).first()

    if task is None:
        return {"message": "Invalid task id"}, 400

    if not task.completed:
        return {"message": "Task is not completed"}, 400

    task.delete()
    return {"success": True}


#@api.route('/<int:task_id>/logs')
#@login_required
@router.get("/tasks/{task_id}/logs", responses=responses)
async def get_logs(task_id: int, user: SystemUser = Depends(get_current_user)):
    """ Deletes task """
    task = TaskModel.objects(id=task_id).first()
    if task is None:
        return {"message": "Invalid task id"}, 400

    return {'logs': task.logs}

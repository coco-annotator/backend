# from flask_restplus import Namespace, Resource, reqparse
# from flask_login import login_required
#
import os
import shutil
import datetime
from backend.database import (
    ImageModel,
    DatasetModel,
    CategoryModel,
    AnnotationModel
)
#
# api = Namespace('undo', description='Undo related operations')

# model_list = reqparse.RequestParser()
# model_list.add_argument('type', type=str, location='args', default="all")
# model_list.add_argument('limit', type=int, location='args', default=50)
#
# model_data = reqparse.RequestParser()
# model_data.add_argument('id', type=int, required=True)
# model_data.add_argument('instance', required=True)

models = [
    (CategoryModel, "category"),
    (AnnotationModel, "annotation"),
    (ImageModel, "image"),
    (DatasetModel, "dataset")
]


from werkzeug.security import generate_password_hash

from backend.database import UserModel
from backend.webserver.variables import responses, PageDataModel
from .users import get_current_user,SystemUser
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..util.query_util import fix_ids

router = APIRouter()


class ModelListModel(BaseModel):
    type: str = 'all'
    limit: int = 50


class ModelDataModel(BaseModel):
    id: int
    instance: str


#@api.route('/list/')
#@api.expect(model_list)
#@login_required
@router.get('/undo/list', responses=responses)
async def get_undo_list(model_list: ModelListModel, user: SystemUser = Depends(get_current_user)):
    """ Returns all partially delete models """
    model_type = model_list.type
    n = max(1, min(model_list.limit, 1000))

    data = []

    for model in models:
        if model_type == "all" or model_type == model[1]:
            data.extend(model_undo(model[0], model[1], limit=n))

    data.sort(key=lambda item: item['date'], reverse=True)

    for model in data:
        model['date'] = str(model['date'])

    if len(data) > n:
        data = data[:n]

    return data


#@api.route('/')
#@api.expect(model_data)
#@login_required
@router.post('/undo', responses=responses)
async def post_undo(model_data: ModelDataModel, user: SystemUser = Depends(get_current_user)):
    """ Undo a partial delete give id and instance """
    model_id = model_data.id
    instance = model_data.instance

    model_instance = None
    for model in models:
        if model[1].lower() == instance:
            model_instance = model[0]

    if model_instance is None:
        return {"message": "Instance not found"}, 400

    model_object = model_instance.objects(id=model_id).first()

    if model_object is None:
        return {"message": "Invalid id"}, 400

    model_object.update(set__deleted=False)

    return {"success": True}


#@api.expect(model_data)
#@login_required
@router.delete('/undo', responses=responses)
async def delete_undo(model_data: ModelDataModel, user: SystemUser = Depends(get_current_user)):
    """ Undo a partial delete give id and instance """
    model_id = model_data.id
    instance = model_data.instance

    model_instance = None
    for model in models:
        if model[1].lower() == instance:
            model_instance = model[0]

    if model_instance is None:
        return {"message": "Instance not found"}, 400

    model_object = model_instance.objects(id=model_id).first()

    if model_object is None:
        return {"message": "Invalid id"}, 400

    if isinstance(model_object, ImageModel):
        if os.path.isfile(model_object.path):
            os.remove(model_object.path)

    if isinstance(model_object, DatasetModel):
        if os.path.isdir(model_object.directory):
            shutil.rmtree(model_object.directory)

    model_object.delete()

    return {"success": True}


def model_undo(model_instance, instance_name, limit=50):
    models = model_instance.objects(deleted=True).order_by('-deleted_date').limit(limit)
    new_models = []

    for model in models:

        if model.deleted_date is None:
            continue

        name = model.name if hasattr(model, 'name') else '-'
        name = model.file_name if hasattr(model, 'file_name') and name == '-' else name

        time_delta = datetime.datetime.now() - model.deleted_date

        new_model = {
            'id': model.id,
            'name': '-' if name is None else name,
            'instance': instance_name,
            'ago': td_format(time_delta),
            'date': model.deleted_date
        }
        new_models.append(new_model)

    return new_models


def td_format(td_object):
    seconds = int(td_object.total_seconds())
    periods = [
        ('year',        60*60*24*365),
        ('month',       60*60*24*30),
        ('day',         60*60*24),
        ('hour',        60*60),
        ('minute',      60),
        ('second',      1)
    ]

    strings = []
    for period_name, period_seconds in periods:
        if seconds > period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            has_s = 's' if period_value > 1 else ''
            strings.append("%s %s%s" % (period_value, period_name, has_s))
            break

    return ", ".join(strings)

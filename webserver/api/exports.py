#from flask import send_file
#from flask_restplus import Namespace, Resource, reqparse
#from flask_login import login_required, current_user

from backend.database import UserModel
from backend.webserver.variables import responses, PageDataModel
from .users import SystemUser, get_current_user
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel

import datetime
from ..util import query_util

from backend.database import (
    ExportModel,
    DatasetModel,
    fix_ids
)


# api = Namespace('export', description='Export related operations')

router = APIRouter()

#@api.route('/<int:export_id>')
#@login_required
@router.get("/export/{export_id}", responses=responses, tags=["exports"])
def get_export(export_id: int, user: SystemUser = Depends(get_current_user)):
    """ Returns exports """
    userdb = UserModel.objects(username__iexact=user.username).first()

    export = ExportModel.objects(id=export_id).first()
    if export is None:
        raise HTTPException(status_code=400, detail="Invalid export ID")

    dataset = userdb.datasets.filter(id=export.dataset_id).first()
    if dataset is None:
        raise HTTPException(status_code=400, detail="Invalid dataset ID")

    time_delta = datetime.datetime.utcnow() - export.created_at
    d = fix_ids(export)
    d['ago'] = query_util.td_format(time_delta)
    return d
    
#@login_required
@router.delete("/export/{export_id}", responses=responses, tags=["exports"])
def delete_export(export_id: int, user: SystemUser = Depends(get_current_user)):
    """ Returns exports """
    userdb = UserModel.objects(username__iexact=user.username).first()

    export = ExportModel.objects(id=export_id).first()
    if export is None:
        raise HTTPException(status_code=400, detail="Invalid export ID")

    dataset = userdb.datasets.filter(id=export.dataset_id).first()
    if dataset is None:
        raise HTTPException(status_code=400, detail="Invalid dataset ID")

    export.delete()
    return {'success': True}


#@api.route('/<int:export_id>/download')
#@login_required
@router.get('/export/{export_id}/download', responses=responses, tags=["exports"])
def download_export(export_id: int, user: SystemUser = Depends(get_current_user)):
    """ Returns exports """
    userdb = UserModel.objects(username__iexact=user.username).first()

    export = ExportModel.objects(id=export_id).first()
    if export is None:
        raise HTTPException(status_code=400, detail="Invalid export ID")

    dataset = userdb.datasets.filter(id=export.dataset_id).first()
    if dataset is None:
        raise HTTPException(status_code=400, detail="Invalid dataset ID")

    if not userdb.can_download(dataset):
        raise HTTPException(status_code=403, detail="You do not have permission to download the dataset's annotations")

    return FileResponse(export.path, filename=f"{dataset.name.encode('utf-8')}-{'-'.join(export.tags).encode('utf-8')}.json")

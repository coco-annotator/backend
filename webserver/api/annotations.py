# from flask_restplus import Namespace, Resource, reqparse
# from flask_login import login_required, current_user

from backend.webserver.variables import responses, PageDataModel
from .users import SystemUser, get_current_user
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from backend.database import AnnotationModel
from ..util import query_util

import datetime
import logging
logger = logging.getLogger('gunicorn.error')

# api = Namespace('annotation', description='Annotation related operations')
#
# create_annotation = reqparse.RequestParser()
# create_annotation.add_argument('image_id', type=int, required=True, location='json')
# create_annotation.add_argument('category_id', type=int, location='json')
# create_annotation.add_argument('isbbox', type=bool, location='json')
# create_annotation.add_argument('metadata', type=dict, location='json')
# create_annotation.add_argument('segmentation', type=list, location='json')
# create_annotation.add_argument('keypoints', type=list, location='json')
# create_annotation.add_argument('color', location='json')
#
# update_annotation = reqparse.RequestParser()
# update_annotation.add_argument('category_id', type=int, location='json')

router = APIRouter()

#@api.route('/')
#@login_required
@router.get('/annotation', responses=responses, tags=["annotation"])
def get_annotations(user: SystemUser = Depends(get_current_user)):
    """ Returns all annotations """
    return query_util.fix_ids(user.annotations.exclude("paper_object").all())

class CreateAnnotationModel(BaseModel):
    image_id: int
    category_id: int
    metadata: dict
    segmentation: list
    keypoints: list
    isbbox: bool


#@api.expect(create_annotation)
#@login_required
@router.post('/annotation', responses=responses, tags=["annotation"])
def create_annotation(create_annotation: CreateAnnotationModel, user: SystemUser = Depends(get_current_user)):
    """ Creates an annotation """

    image_id = create_annotation.image_id

    image = user.images.filter(id=image_id, deleted=False).first()
    if image is None:
        raise HTTPException(status_code=400, detail="Invalid image id")

    logger.info(f'{user.username} has created an annotation for image {image_id} with {create_annotation.isbbox}')
    # logger.info(f'{user.username} has created an annotation for image {image_id}')

    try:
        annotation = AnnotationModel(
            image_id=create_annotation.image_id,
            category_id=create_annotation.category_id,
            metadata=create_annotation.metadata,
            segmentation=create_annotation.segmentation,
            keypoints=create_annotation.keypoints,
            isbbox=create_annotation.isbbox
        )
        annotation.save()
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    return query_util.fix_ids(annotation)


#@api.route('/<int:annotation_id>')
#@login_required
@router.get("/annotation/{annotation_id}", responses=responses, tags=["annotation"])
async def get_annotation(annotation_id: int, user: SystemUser = Depends(get_current_user)):
    """ Returns annotation by ID """
    annotation = user.annotations.filter(id=annotation_id).first()

    if annotation is None:
        raise HTTPException(status_code=400, detail="Invalid annotation id")

    return query_util.fix_ids(annotation)


#@login_required
@router.delete("/annotation/{annotation_id}", responses=responses, tags=["annotation"])
async def delete_annotation(annotation_id, user: SystemUser = Depends(get_current_user)):
    """ Deletes an annotation by ID """
    annotation = user.annotations.filter(id=annotation_id).first()

    if annotation is None:
        raise HTTPException(status_code=400, detail="Invalid annotation id")

    image = user.images.filter(id=annotation.image_id, deleted=False).first()
    image.flag_thumbnail()

    annotation.update(set__deleted=True,
                      set__deleted_date=datetime.datetime.now())
    return {'success': True}


#@api.expect(update_annotation)
#@login_required
@router.put("/annotation/{annotation_id}", responses=responses, tags=["annotation"])
async def update_annotation(annotation_id, user: SystemUser = Depends(get_current_user)):
    """ Updates an annotation by ID """
    annotation = user.annotations.filter(id=annotation_id).first()

    if annotation is None:
        raise HTTPException(status_code=400, detail="Invalid annotation id")

    args = update_annotation.parse_args()

    new_category_id = args.get('category_id')
    annotation.update(category_id=new_category_id)
    logger.info(
        f'{user.username} has updated category for annotation (id: {annotation.id})'
    )
    newAnnotation = user.annotations.filter(id=annotation_id).first()
    return query_util.fix_ids(newAnnotation)

# @api.route('/<int:annotation_id>/mask')
# class AnnotationMask(Resource):
#     def get(self, annotation_id):
#         """ Returns the binary mask of an annotation """
#         return query_util.fix_ids(AnnotationModel.objects(id=annotation_id).first())

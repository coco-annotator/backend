# from flask_restplus import Namespace, Resource, reqparse
# from flask_login import login_required, current_user
from werkzeug.datastructures import FileStorage
# from flask import send_file

from werkzeug.security import generate_password_hash

from backend.database import UserModel
from backend.webserver.variables import responses, PageDataModel
from .users import SystemUser, get_current_user
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from mongoengine.errors import NotUniqueError

from ..util import query_util, coco_util
from backend.database import (
    ImageModel,
    DatasetModel,
    AnnotationModel
)

from PIL import Image
import datetime
import os
import io


# api = Namespace('image', description='Image related operations')
#
#
# image_all = reqparse.RequestParser()
# image_all.add_argument('fields', required=False, type=str)
# image_all.add_argument('page', default=1, type=int)
# image_all.add_argument('per_page', default=50, type=int, required=False)
#
# image_upload = reqparse.RequestParser()
# image_upload.add_argument('image', location='files',
#                           type=FileStorage, required=True,
#                           help='PNG or JPG file')
# image_upload.add_argument('dataset_id', required=True, type=int,
#                           help='Id of dataset to insert image into')
#
# image_download = reqparse.RequestParser()
# image_download.add_argument('asAttachment', type=bool, default=False)
# image_download.add_argument('thumbnail', type=bool, default=False)
# image_download.add_argument('asOriginal', type=bool, default=False)
# image_download.add_argument('width', type=int)
# image_download.add_argument('height', type=int)
#
# copy_annotations = reqparse.RequestParser()
# copy_annotations.add_argument('category_ids', location='json', type=list,
#                               required=False, default=None, help='Categories to copy')

router = APIRouter()


#@api.route('/')
#@api.expect(image_all)
#@login_required
@router.get("/images", responses=responses, tags=["images"])
def get_images(per_page: int, page: int, user: SystemUser = Depends(get_current_user)):
    """ Returns all images """
    userdb = UserModel.objects(username__iexact=user.username).first()
    # args = image_all.parse_args()
    # per_page = args['per_page']
    # page = args['page']-1
    fields = args.get('fields', '')

    images = userdb.images.filter(deleted=False)
    total = images.count()
    pages = int(total/per_page) + 1

    images = images.skip(page*per_page).limit(per_page)
    if fields:
        images = images.only(*fields.split(','))

    return {
        "total": total,
        "pages": pages,
        "page": page,
        "fields": fields,
        "per_page": per_page,
        "images": query_util.fix_ids(images.all())
    }


#@api.expect(image_upload)
#@login_required
@router.post("/images", responses=responses, tags=["images"])
def create_images(user: SystemUser = Depends(get_current_user)):
    """ Creates an image """
    # TODO Reform this endpoint.
    args = image_upload.parse_args()
    image = args['image']

    dataset_id = args['dataset_id']
    try:
        dataset = DatasetModel.objects.get(id=dataset_id)
    except:
        return {'message': 'dataset does not exist'}, 400
    directory = dataset.directory
    path = os.path.join(directory, image.filename)

    if os.path.exists(path):
        return {'message': 'file already exists'}, 400

    pil_image = Image.open(io.BytesIO(image.read()))

    pil_image.save(path)

    image.close()
    pil_image.close()
    try:
        db_image = ImageModel.create_from_path(path, dataset_id).save()
    except NotUniqueError:
        db_image = ImageModel.objects.get(path=path)
    return db_image.id


#@api.route('/<int:image_id>')
#@api.expect(image_download)
#@login_required
@router.get("/images/{image_id}", responses=responses, tags=["images"])
def get_image(image_id: int, user: SystemUser = Depends(get_current_user)):
    """ Returns category by ID """
    userdb = UserModel.objects(username__iexact=user.username).first()
    args = image_download.parse_args()
    as_attachment = args.get('asAttachment')
    thumbnail = args.get('thumbnail')
    as_original = args.get('asOriginal')

    image = userdb.images.filter(id=image_id, deleted=False).first()

    if image is None:
        return {'success': False}, 400

    width = args.get('width')
    height = args.get('height')

    if not width:
        width = image.width
    if not height:
        height = image.height

    if as_original:
        with open(image.path, mode='rb') as f:
            image_io = io.BytesIO(f.read())
            image_io.seek(0)
            res = image_io.getvalue()
        # return SendFile(image_io, download_name=image.file_name, as_attachment=as_attachment)

        async def result():
            yield res

        return StreamingResponse(result(), media_type='image/' + format)

    pil_image = image.open_thumbnail() if thumbnail else Image.open(image.path)

    pil_image.thumbnail((width, height), Image.ANTIALIAS)
    image_io = io.BytesIO()
    pil_image = pil_image.convert("RGB")
    pil_image.save(image_io, "JPEG", quality=90)
    image_io.seek(0)
    res = image_io.getvalue()

    async def result():
        yield res

    # return SendFile(image_io, download_name=image.file_name, as_attachment=as_attachment)
    return StreamingResponse(result(), media_type='image/jpg')

#@login_required
@router.delete("/images/{image_id}", responses=responses, tags=["images"])
def delete_image(image_id: int, user: SystemUser = Depends(get_current_user)):
    """ Deletes an image by ID """
    userdb = UserModel.objects(username__iexact=user.username).first()
    image = userdb.images.filter(id=image_id, deleted=False).first()
    if image is None:
        raise HTTPException(status_code=400, detail="Invalid image id")

    if not userdb.can_delete(image):
        raise HTTPException(status_code=403, detail="You do not have permission to download the image")

    image.update(set__deleted=True, set__deleted_date=datetime.datetime.now())
    return {"success": True}


#@api.route('/copy/<int:from_id>/<int:to_id>/annotations')
#@api.expect(copy_annotations)
#@login_required
@router.post("/images/copy/{from_id}/{to_id}/annotations", responses=responses, tags=["images"])
def post(from_id: int, to_id: int, user: SystemUser = Depends(get_current_user)):
    userdb = UserModel.objects(username__iexact=user.username).first()
    args = copy_annotations.parse_args()
    category_ids = args.get('category_ids')

    image_from = userdb.images.filter(id=from_id).first()
    image_to = userdb.images.filter(id=to_id).first()

    if image_from is None or image_to is None:
        raise HTTPException(status_code=400, detail="Invalid image id")

    if image_from == image_to:
        raise HTTPException(status_code=400, detail='Cannot copy self')

    if image_from.width != image_to.width or image_from.height != image_to.height:
        raise HTTPException(status_code=400, detail='Image sizes do not match')

    if category_ids is None:
        category_ids = DatasetModel.objects(id=image_from.dataset_id).first().categories

    query = AnnotationModel.objects(
        image_id=image_from.id,
        category_id__in=category_ids,
        deleted=False
    )

    return {'annotations_created': image_to.copy_annotations(query)}


#@api.route('/<int:image_id>/coco')
#@login_required
@router.get('/images/{image_id}', responses=responses, tags=["images"])
def get(image_id: int, user: SystemUser = Depends(get_current_user)):
    """ Returns coco of image and annotations """
    userdb = UserModel.objects(username__iexact=user.username).first()
    image = userdb.images.filter(id=image_id).exclude('deleted_date').first()

    if image is None:
        raise HTTPException(status_code=400, detail="Invalid image ID")

    if not userdb.can_download(image):
        raise HTTPException(status_code=403, detail="You do not have permission to download the images's annotations")

    return coco_util.get_image_coco(image_id)

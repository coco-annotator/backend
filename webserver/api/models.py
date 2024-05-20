# from flask_restplus import Namespace, Resource, reqparse
# from werkzeug.datastructures import FileStorage
from imantics import Mask
# from flask_login import login_required
import backend.config as Config
from PIL import Image
from backend.database import ImageModel

from werkzeug.security import generate_password_hash

from backend.database import UserModel
from backend.webserver.variables import responses, PageDataModel
from .users import SystemUser, get_current_user
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..util.query_util import fix_ids

import os
import logging

logger = logging.getLogger('gunicorn.error')

try:
    MASKRCNN_LOADED = os.path.isfile(Config.MASK_RCNN_FILE)
    if MASKRCNN_LOADED:
        from ..util.mask_rcnn import model as maskrcnn
    else:
        logger.warning("MaskRCNN model is disabled.")
except ImportError:
    logger.warning("MaskRCNN model is disabled.")

DEXTR_LOADED = os.path.isfile(Config.DEXTR_FILE)
try:
    from ..util.dextr import model as dextr
except ImportError:
    logger.warning("DEXTR model is disabled.")

# api = Namespace('model', description='Model related operations')


#image_upload = reqparse.RequestParser()
#image_upload.add_argument('image', location='files', type=FileStorage, required=True, help='Image')

#dextr_args = reqparse.RequestParser()
#dextr_args.add_argument('points', location='json', type=list, required=True)
#dextr_args.add_argument('padding', location='json', type=int, default=50)
#dextr_args.add_argument('threshold', location='json', type=int, default=80)

router = APIRouter()

class DextrModel(BaseModel):
    points: str
    padding: int = 50
    threshold: int = 80

#@api.route('/dextr/<int:image_id>')
#@login_required
#@api.expect(dextr_args)
@router.post("/model/dextr/{image_id}")
async def post_dextr(dextr: DextrModel, image_id: int, user: SystemUser = Depends(get_current_user)):
    """ COCO data test """

    if not DEXTR_LOADED:
        return {"disabled": True, "message": "DEXTR is disabled"}, 400

    points = dextr.points
    padding = dextr.padding
    threshold = dextr.threshold

    if len(points) != 4:
        return {"message": "Invalid points entered"}, 400

    image_model = ImageModel.objects(id=image_id).first()
    if not image_model:
        return {"message": "Invalid image ID"}, 400

    image = Image.open(image_model.path)
    result = dextr.predict_mask(image, points)

    return { "segmentaiton": Mask(result).polygons().segmentation }


#@api.route('/maskrcnn')
#@login_required
#@api.expect(image_upload)
@router.post('/model/maskrcnn')
async def post_maskrcnn(user: SystemUser = Depends(get_current_user)):
    """ COCO data test """
    if not MASKRCNN_LOADED:
        return {"disabled": True, "coco": {}}

    args = image_upload.parse_args()
    im = Image.open(args.get('image'))
    coco = maskrcnn.detect(im)
    return {"coco": coco}
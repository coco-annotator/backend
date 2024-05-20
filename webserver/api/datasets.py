#from flask import request
#from flask_restplus import Namespace, Resource, reqparse, inputs
#from flask_login import login_required, current_user
from werkzeug.datastructures import FileStorage
from mongoengine.errors import NotUniqueError
from mongoengine.queryset.visitor import Q
# from threading import Thread

# from google_images_download import google_images_download as gid

from ..util.pagination_util import Pagination
from ..util import query_util, coco_util, profile

from backend.database import (
    ImageModel,
    DatasetModel,
    CategoryModel,
    AnnotationModel,
    ExportModel,
    UserModel,
    # CocoImportModel
)

import datetime
import json
import os

from backend.webserver.variables import responses, PageDataModel
from .users import SystemUser, get_current_user

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

# api = Namespace('dataset', description='Dataset related operations')
#
#
# dataset_create = reqparse.RequestParser()
# dataset_create.add_argument('name', required=True)
# dataset_create.add_argument('categories', type=list, required=False, location='json',
#                             help="List of default categories for sub images")
#
# page_data = reqparse.RequestParser()
# page_data.add_argument('page', default=1, type=int)
# page_data.add_argument('limit', default=20, type=int)
# page_data.add_argument('folder', default='', help='Folder for data')
# page_data.add_argument('order', default='file_name', help='Order to display images')
#
# delete_data = reqparse.RequestParser()
# delete_data.add_argument('fully', default=False, type=bool,
#                          help="Fully delete dataset (no undo)")
#
# coco_upload = reqparse.RequestParser()
# coco_upload.add_argument('coco', location='files', type=FileStorage, required=True, help='Json coco')
#
# export = reqparse.RequestParser()
# export.add_argument('categories', type=str, default=None, required=False, help='Ids of categories to export')
# export.add_argument('with_empty_images', type=inputs.boolean, default=False, required=False, help='Export with un-annotated images')
#
# update_dataset = reqparse.RequestParser()
# update_dataset.add_argument('categories', location='json', type=list, help="New list of categories")
# update_dataset.add_argument('default_annotation_metadata', location='json', type=dict,
#                             help="Default annotation metadata")
#
# dataset_generate = reqparse.RequestParser()
# dataset_generate.add_argument('keywords', location='json', type=list, default=[],
#                               help="Keywords associated with images")
# dataset_generate.add_argument('limit', location='json', type=int, default=100, help="Number of images per keyword")
#
# share = reqparse.RequestParser()
# share.add_argument('users', location='json', type=list, default=[], help="List of users")

router = APIRouter()

def _get_dataset_from_db(dataset_id, user):
    userdb = UserModel.objects(username__iexact=user.username).first()
    dataset = userdb.datasets.filter(id=dataset_id).first()
    if dataset is None:
        raise HTTPException(status_code=400, detail="No datasets found.")
    return dataset, userdb


# @api.route('/dataset')
# @login_required
@router.get('/dataset', responses=responses, tags=["dataset"])
async def get_datasets(user = Depends(get_current_user)):
    """ Returns all datasets """
    userdb = UserModel.objects(username__iexact=user.username).first()
    datasets = list(userdb.datasets.filter(deleted=False).all())

    return query_util.fix_ids(datasets)


class CreateDatasetModel(BaseModel):
    name: str
    categories: list | None = None


#@api.expect(dataset_create)
#@login_required
@router.post('/dataset', responses=responses, tags=["dataset"])
async def create_dataset(dataset_create: CreateDatasetModel, user = Depends(get_current_user)):
    """ Creates a dataset """
    name = dataset_create.name
    categories = dataset_create.categories

    category_ids = CategoryModel.bulk_create(categories)

    try:
        dataset = DatasetModel(name=name, categories=category_ids)
        dataset.save()
    except NotUniqueError:
        return {'message': 'Dataset already exists. Check the undo tab to fully delete the dataset.'}, 400

    return query_util.fix_ids(dataset)


# def download_images(output_dir, args):
#     for keyword in args['keywords']:
#         response = gid.googleimagesdownload()
#         response.download({
#             "keywords": keyword,
#             "limit": args['limit'],
#             "output_directory": output_dir,
#             "no_numbering": True,
#             "format": "jpg",
#             "type": "photo",
#             "print_urls": False,
#             "print_paths": False,
#             "print_size": False
#         })
#
#
# @api.route('/<int:dataset_id>/generate')
# class DatasetGenerate(Resource):
#     @api.expect(dataset_generate)
#     @login_required
#     def post(self, dataset_id):
#         """ Adds images found on google to the dataset """
#         args = dataset_generate.parse_args()
#
#         dataset = current_user.datasets.filter(id=dataset_id, deleted=False).first()
#         if dataset is None:
#             return {"message": "Invalid dataset id"}, 400
#
#         if not dataset.is_owner(current_user):
#             return {"message": "You do not have permission to download the dataset's annotations"}, 403
#
#         thread = Thread(target=download_images, args=(dataset.directory, args))
#         thread.start()
#
#         return {"success": True}

# @login_required
@router.get('/dataset/{dataset_id}/users', responses=responses, tags=["dataset"])
async def get_dataset_users(dataset_id: int, user = Depends(get_current_user)):
    """ All users in the dataset """
    dataset, _ = _get_dataset_from_db(dataset_id, user)

    users = dataset.get_users()
    return query_util.fix_ids(users)


#    @login_required
@router.get('/dataset/{dataset_id}/reset/metadata', responses=responses, tags=["dataset"])
async def get_dataset_metadata(dataset_id: int, user = Depends(get_current_user)):
    """ All users in the dataset """
    dataset, _ = _get_dataset_from_db(dataset_id, user)

    AnnotationModel.objects(dataset_id=dataset.id).update(metadata=dataset.default_annotation_metadata)
    ImageModel.objects(dataset_id=dataset.id).update(metadata={})

    return {'success': True}


# @login_required
@router.get('/dataset/{dataset_id}/stats', responses=responses, tags=["dataset"])
async def get_dataset_stats(dataset_id: int, user = Depends(get_current_user)):
    """ All users in the dataset """
    dataset, _ = _get_dataset_from_db(dataset_id, user)

    images = ImageModel.objects(dataset_id=dataset.id, deleted=False)
    annotated_images = images.filter(annotated=True)
    annotations = AnnotationModel.objects(dataset_id=dataset_id, deleted=False)

    # Calculate annotation counts by category in this dataset
    category_count = dict()
    image_category_count = dict()

    user_stats = dict()

    for user in dataset.get_users():
        user_annots = AnnotationModel.objects(dataset_id=dataset_id, deleted=False, creator=user.username)
        image_count = dict()
        for annot in user_annots:
            image_count[annot.image_id] = image_count.get(annot.image_id, 0) + 1

        user_stats[user.username] = {
            "annotations":  len(user_annots),
            "images": len(image_count)
        }


    for category in dataset.categories:

        # Calculate the annotation count in the current category in this dataset
        cat_name = CategoryModel.objects(id=category).first()['name']
        cat_count = AnnotationModel.objects(dataset_id=dataset_id, category_id=category, deleted=False).count()
        category_count.update({str(cat_name): cat_count})

        # Calculate the annotated images count in the current category in this dataset
        image_count = len(AnnotationModel.objects(dataset_id=dataset_id, category_id=category, deleted=False).distinct('image_id'))
        image_category_count.update({str(cat_name): image_count})

    stats = {
        'total': {
            'Users': dataset.get_users().count(),
            'Images': images.count(),
            'Annotated Images': annotated_images.count(),
            'Annotations': annotations.count(),
            'Categories': len(dataset.categories),
            'Time Annotating (s)': (images.sum('milliseconds') or 0) / 1000
        },
        'average': {
            'Image Size (px)': images.average('width'),
            'Image Height (px)': images.average('height'),
            'Annotation Area (px)': annotations.average('area'),
            'Time (ms) per Image': images.average('milliseconds') or 0,
            'Time (ms) per Annotation': annotations.average('milliseconds') or 0
        },
        'categories': category_count,
        'images_per_category': image_category_count,
        'users': user_stats
    }
    return stats


#@login_required
@router.delete('/dataset/{dataset_id}', responses=responses, tags=["dataset"])
async def delete_dataset(dataset_id: int, user = Depends(get_current_user)):
    """ Deletes dataset by ID (only owners)"""
    dataset, userdb = _get_dataset_from_db(dataset_id, user)

    if not userdb.can_delete(dataset):
        raise HTTPException(status_code=403, detail="You do not have permission to delete the dataset")

    dataset.update(set__deleted=True, set__deleted_date=datetime.datetime.now())
    return {"success": True}


#@login_required
#@api.expect(update_dataset)
@router.post('/dataset/{dataset_id}', responses=responses, tags=["dataset"])
async def update_dataset(dataset_id: int, user = Depends(get_current_user)):
    """ Updates dataset by ID """
    dataset, _ = _get_dataset_from_db(dataset_id, user)

    # TODO! Update this part.
    args = update_dataset.parse_args()
    categories = args.get('categories')
    default_annotation_metadata = args.get('default_annotation_metadata')
    set_default_annotation_metadata = args.get('set_default_annotation_metadata')

    if categories is not None:
        dataset.categories = CategoryModel.bulk_create(categories)

    if default_annotation_metadata is not None:

        update = {}
        for key, value in default_annotation_metadata.items():
            if key not in dataset.default_annotation_metadata:
                update[f'set__metadata__{key}'] = value

        dataset.default_annotation_metadata = default_annotation_metadata

        if len(update.keys()) > 0:
            AnnotationModel.objects(dataset_id=dataset.id, deleted=False)\
                .update(**update)

    dataset.update(
        categories=dataset.categories,
        default_annotation_metadata=dataset.default_annotation_metadata
    )

    return {"success": True}


#@api.expect(share)
#@login_required
#@api.route('/<int:dataset_id>/share')
@router.post('/dataset/{dataset_id}/share', responses=responses, tags=["dataset"])
async def share_dataset(dataset_id, user = Depends(get_current_user)):
    dataset, userdb = _get_dataset_from_db(dataset_id, user)

    if not dataset.is_owner(userdb):
        raise HTTPException(status_code=403, detail="You do not have permission to share this dataset")

    # TODO!
    args = share.parse_args()
    dataset.update(users=args.get('users'))

    return {"success": True}


#@api.expect(page_data)
#@login_required
#@api.route('/data')
@router.get("/dataset/data", responses=responses, tags=["dataset"])
async def get(page: int, limit: int, user = Depends(get_current_user)):
    """ Endpoint called by dataset viewer client """
    userdb = UserModel.objects(username__iexact=user.username).first()
    datasets = userdb.datasets.filter(deleted=False).all()
    if datasets is None:
        raise HTTPException(status_code=400, detail="No datasets found.")

    # args = page_data.parse_args()
    # limit = args['limit']
    # page = args['page']
    folder = args['folder']

    # datasets = current_user.datasets.filter(deleted=False)
    pagination = Pagination(datasets.count(), limit, page)
    datasets = datasets[pagination.start:pagination.end]

    datasets_json = []
    for dataset in datasets:
        dataset_json = query_util.fix_ids(dataset)
        images = ImageModel.objects(dataset_id=dataset.id, deleted=False)

        dataset_json['numberImages'] = images.count()
        dataset_json['numberAnnotated'] = images.filter(annotated=True).count()
        dataset_json['permissions'] = dataset.permissions(userdb)

        first = images.first()
        if first is not None:
            dataset_json['first_image_id'] = images.first().id
        datasets_json.append(dataset_json)

    return {
        "pagination": pagination.export(),
        "folder": folder,
        "datasets": datasets_json,
        "categories": query_util.fix_ids(userdb.categories.filter(deleted=False).all())
    }


#@api.route('/<int:dataset_id>/data')
#@profile
#@api.expect(page_data)
#@login_required
@router.get("/dataset/{dataset_id}/data", responses=responses, tags=["dataset"])
async def get_dataset_data(per_page: int, page: int, dataset_id: int, user = Depends(get_current_user)):
    """ Endpoint called by image viewer client """
    dataset, userdb = _get_dataset_from_db(dataset_id, user)

    # TODO!
    #parsed_args = page_data.parse_args()
    #per_page = parsed_args.get('limit')
    #page = parsed_args.get('page') - 1
    folder = parsed_args.get('folder')
    order = parsed_args.get('order')

    args = dict(request.args)

    # Make sure folder starts with is in proper format
    if len(folder) > 0:
        folder = folder[0].strip('/') + folder[1:]
        if folder[-1] != '/':
            folder = folder + '/'

    # Get directory
    directory = os.path.join(dataset.directory, folder)
    if not os.path.exists(directory):
        return {'message': 'Directory does not exist.'}, 400

    # Remove parsed arguments
    for key in parsed_args:
        args.pop(key, None)

    # Generate query from remaining arugments
    query = {}
    for key, value in args.items():
        lower = value.lower()
        if lower in ["true", "false"]:
            value = json.loads(lower)

        if len(lower) != 0:
            query[key] = value

    # Change category_ids__in to list
    if 'category_ids__in' in query.keys():
        query['category_ids__in'] = [int(x) for x in query['category_ids__in'].split(',')]

    # Initialize mongo query with required elements:
    query_build = Q(dataset_id=dataset_id)
    query_build &= Q(path__startswith=directory)
    query_build &= Q(deleted=False)

    # Define query names that should use complex logic:
    complex_query = ['annotated', 'category_ids__in']

    # Add additional 'and' arguments to mongo query that do not require complex_query logic
    for key in query.keys():
        if key not in complex_query:
            query_dict = {}
            query_dict[key] = query[key]
            query_build &= Q(**query_dict)

    # Add additional arguments to mongo query that require more complex logic to construct
    if 'annotated' in query.keys():

        if 'category_ids__in' in query.keys() and query['annotated']:

            # Only show annotated images with selected category_ids
            query_dict = {}
            query_dict['category_ids__in'] = query['category_ids__in']
            query_build &= Q(**query_dict)

        else:

            # Only show non-annotated images
            query_dict = {}
            query_dict['annotated'] = query['annotated']
            query_build &= Q(**query_dict)

    elif 'category_ids__in' in query.keys():

        # Ahow annotated images with selected category_ids or non-annotated images
        query_dict_1 = {}
        query_dict_1['category_ids__in'] = query['category_ids__in']

        query_dict_2 = {}
        query_dict_2['annotated'] = False
        query_build &= (Q(**query_dict_1) | Q(**query_dict_2))

    # Perform mongodb query
    images = userdb.images \
        .filter(query_build) \
        .order_by(order).only('id', 'file_name', 'annotating', 'annotated', 'num_annotations')

    total = images.count()
    pages = int(total/per_page) + 1

    images = images.skip(page*per_page).limit(per_page)
    images_json = query_util.fix_ids(images)
    # for image in images:
    #     image_json = query_util.fix_ids(image)

    #     query = AnnotationModel.objects(image_id=image.id, deleted=False)
    #     category_ids = query.distinct('category_id')
    #     categories = CategoryModel.objects(id__in=category_ids).only('name', 'color')

    #     image_json['annotations'] = query.count()
    #     image_json['categories'] = query_util.fix_ids(categories)

    #     images_json.append(image_json)

    subdirectories = [f for f in sorted(os.listdir(directory))
                      if os.path.isdir(directory + f) and not f.startswith('.')]

    categories = CategoryModel.objects(id__in=dataset.categories).only('id', 'name')

    return {
        "total": total,
        "per_page": per_page,
        "pages": pages,
        "page": page,
        "images": images_json,
        "folder": folder,
        "directory": directory,
        "dataset": query_util.fix_ids(dataset),
        "categories": query_util.fix_ids(categories),
        "subdirectories": subdirectories
    }


#@api.route('/<int:dataset_id>/exports')
#@login_required
@router.get("/dataset/{dataset_id}/exports", responses=responses, tags=["dataset"])
async def get_exports(dataset_id: int, user = Depends(get_current_user)):
    """ Returns exports of images and annotations in the dataset (only owners) """
    dataset, userdb = _get_dataset_from_db(dataset_id, user)

    if not userdb.can_download(dataset):
        raise HTTPException(status_code=403, detail="You do not have permission to download the dataset's annotations")

    exports = ExportModel.objects(dataset_id=dataset.id).order_by('-created_at').limit(50)

    dict_export = []
    for export in exports:

        time_delta = datetime.datetime.utcnow() - export.created_at
        dict_export.append({
            'id': export.id,
            'ago': query_util.td_format(time_delta),
            'tags': export.tags
        })

    return dict_export


#@api.route('/<int:dataset_id>/export')
#@api.expect(export)
#@login_required
@router.get("/dataset/{dataset_id}/export", responses=responses, tags=["dataset"])
async def get(dataset_id: int, user = Depends(get_current_user)):
    dataset, _ = _get_dataset_from_db(dataset_id, user)

    #TODO!
    args = export.parse_args()
    categories = args.get('categories')
    with_empty_images = args.get('with_empty_images', False)

    if len(categories) == 0:
        categories = []

    if len(categories) > 0 or isinstance(categories, str):
        categories = [int(c) for c in categories.split(',')]

    dataset = DatasetModel.objects(id=dataset_id).first()

    if not dataset:
        return {'message': 'Invalid dataset ID'}, 400

    return dataset.export_coco(categories=categories, with_empty_images=with_empty_images)


#@api.expect(coco_upload)
#@login_required
@router.post("/dataset/{dataset_id}/coco", responses=responses, tags=["dataset"])
async def add_coco(dataset_id: int, user = Depends(get_current_user)):
    """ Adds coco formatted annotations to the dataset """
    dataset, _ = _get_dataset_from_db(dataset_id, user)

    args = coco_upload.parse_args()
    coco = args['coco']

    return dataset.import_coco(json.load(coco))


#@api.route('/<int:dataset_id>/coco')
#@login_required
@router.get("/dataset/{dataset_id}/coco", responses=responses, tags=["dataset"])
async def get(dataset_id: int, user: SystemUser = Depends(get_current_user)):
    """ Returns coco of images and annotations in the dataset (only owners) """
    dataset, _ = _get_dataset_from_db(dataset_id, user)

    if not userdb.can_download(dataset):
        raise HTTPException(status_code=403, detail="You do not have permission to download the dataset's annotations")

    return coco_util.get_dataset_coco(dataset)

#@api.expect(coco_upload)
#@login_required
@router.post("/dataset/{dataset_id}/coco", responses=responses, tags=["dataset"])
async def post(dataset_id: int, user: SystemUser = Depends(get_current_user)):
    """ Adds coco formatted annotations to the dataset """
    dataset, _ = _get_dataset_from_db(dataset_id, user)

    # TODO!
    args = coco_upload.parse_args()
    coco = args['coco']

    return dataset.import_coco(json.load(coco))


#@api.route('/coco/<int:import_id>')
 #@login_required
@router.get("/dataset/coco/{import_id}", responses=responses, tags=["dataset"])
async def get(import_id: int, user: SystemUser = Depends(get_current_user)):
    """ Returns current progress and errors of a coco import """
    userdb = UserModel.objects(username__iexact=user.username).first()
    coco_import = CocoImportModel.objects(id=import_id, creator=user.username).first()

    if not coco_import:
        return {'message': 'No such coco import'}, 400

    return {
        "progress": coco_import.progress,
        "errors": coco_import.errors
    }


#@api.route('/<int:dataset_id>/scan')
#@login_required
@router.get("/dataset/{dataset_id}/scan", responses=responses, tags=["dataset"])
async def get(dataset_id: int, user: SystemUser = Depends(get_current_user)):
    dataset, _ = _get_dataset_from_db(dataset_id, user)

    return dataset.scan()




#from flask_restplus import Namespace, Resource, reqparse
#from flask_login import login_required, current_user
from mongoengine.errors import NotUniqueError

from ..util.pagination_util import Pagination
from ..util import query_util
from backend.database import CategoryModel, AnnotationModel, UserModel
from fastapi import APIRouter, HTTPException, Depends
from backend.webserver.variables import responses, PageDataModel
from pydantic import BaseModel
from .users import SystemUser, get_current_user
import json
import datetime

# api = Namespace('category', description='Category related operations')
#
# create_category = reqparse.RequestParser()
# create_category.add_argument('name', required=True, location='json')
# create_category.add_argument('supercategory', location='json')
# create_category.add_argument('color', location='json')
# create_category.add_argument('metadata', type=dict, location='json')
# create_category.add_argument('keypoint_edges', type=list, default=[], location='json')
# create_category.add_argument('keypoint_labels', type=list, default=[], location='json')
# create_category.add_argument('keypoint_colors', type=list, default=[], location='json')
#
# update_category = reqparse.RequestParser()
# update_category.add_argument('name', required=True, location='json')
# update_category.add_argument('supercategory', location='json')
# update_category.add_argument('color', location='json')
# update_category.add_argument('metadata', type=dict, location='json')
# update_category.add_argument('keypoint_edges', type=list, location='json')
# update_category.add_argument('keypoint_labels', type=list, location='json')
# update_category.add_argument('keypoint_colors', type=list, location='json')
#
# page_data = reqparse.RequestParser()
# page_data.add_argument('page', default=1, type=int)
# page_data.add_argument('limit', default=20, type=int)

router = APIRouter()

#@login_required
@router.get('/category', responses=responses, tags=["category"])
async def get_categories(user: SystemUser = Depends(get_current_user)):
    """ Returns all categories """
    userdb = UserModel.objects(username__iexact=user.username).first()
    categories = list(userdb.categories.all())
    return query_util.fix_ids(categories)


class CreateCategoryModel(BaseModel):
    name: str
    supercategory: str | None = None
    color: str | None = None
    metadata: dict | None = None
    keypoint_edges: list = []
    keypoint_labels: list = []
    keypoint_colors: list = []

#@api.expect(create_category)
#@login_required
@router.post('/category', responses=responses, tags=["category"])
async def create_category(create_category: CreateCategoryModel, user: SystemUser = Depends(get_current_user)):
    """ Creates a category """

    name = create_category.name
    supercategory = create_category.supercategory
    metadata = create_category.metadata
    color = create_category.color
    keypoint_edges = create_category.keypoint_edges
    keypoint_labels = create_category.keypoint_labels
    keypoint_colors = create_category.keypoint_colors

    try:
        category = CategoryModel(
            name=name,
            supercategory=supercategory,
            color=color,
            metadata=metadata,
            keypoint_edges=keypoint_edges,
            keypoint_labels=keypoint_labels,
            keypoint_colors=keypoint_colors,
        )
        category.save()
    except NotUniqueError as e:
        raise HTTPException(status_code=400, detail='Category already exists. Check the undo tab to fully delete the category.')

    return query_util.fix_ids(category)


#@login_required
@router.get('/category/{category_id}', responses=responses, tags=["category"])
async def get_category(category_id: int, user: SystemUser = Depends(get_current_user)):
    """ Returns a category by ID """
    userdb = UserModel.objects(username__iexact=user.username).first()
    category = userdb.categories.filter(id=category_id).first()

    if category is None:
        raise HTTPException(status_code=400, detail='Category does not exist.')

    return query_util.fix_ids(category)


#@login_required
@router.delete('/category/{category_id}', responses=responses, tags=["category"])
async def delete_category(category_id: int, user: SystemUser = Depends(get_current_user)):
    """ Deletes a category by ID """
    userdb = UserModel.objects(username__iexact=user.username).first()
    category = userdb.categories.filter(id=category_id).first()
    if category is None:
        raise HTTPException(status_code=400, detail='Category does not exist.')

    if not user.can_delete(category):
        raise HTTPException(status_code=403, detail="You do not have permission to delete this category")

    category.update(set__deleted=True, set__deleted_date=datetime.datetime.now())
    return {'success': True}


#@api.expect(update_category)
#@login_required
@router.put('/category/{category_id}', responses=responses, tags=["category"])
async def update_category(update_category: CreateCategoryModel, category_id: int, user: SystemUser = Depends(get_current_user)):
    """ Updates a category name by ID """
    userdb = UserModel.objects(username__iexact=user.username).first()
    category = userdb.categories.filter(id=category_id).first()

    # check if the id exits
    if category is None:
        raise HTTPException(status_code=400, detail='Category does not exist.')

    name = update_category.name
    supercategory = update_category.supercategory
    metadata = update_category.metadata
    color = update_category.color
    keypoint_edges = update_category.keypoint_edges
    keypoint_labels = update_category.keypoint_labels
    keypoint_colors = update_category.keypoint_colors

    # check if there is anything to update
    if category.name == name \
            and category.supercategory == supercategory \
            and category.color == color \
            and category.keypoint_edges == keypoint_edges \
            and category.keypoint_labels == keypoint_labels \
            and category.keypoint_colors == keypoint_colors:
        return "Nothing to update"

    # check if the name is empty
    if not name:
        raise HTTPException(status_code=400, detail="Invalid category name to update")

    # update name of the category
    # check if the name to update exits already in db
    # @ToDo: Is it necessary to allow equal category names among different creators?
    category.name = name
    category.supercategory = supercategory
    category.color = color
    category.keypoint_edges = keypoint_edges
    category.keypoint_labels = keypoint_labels
    category.keypoint_colors = keypoint_colors

    try:
        category.update(
            name=category.name,
            supercategory=category.supercategory,
            color=category.color,
            metadata=category.metadata,
            keypoint_edges=category.keypoint_edges,
            keypoint_labels=category.keypoint_labels,
            keypoint_colors=category.keypoint_colors,
        )
    except NotUniqueError:
        # it is only triggered when the name already exists and the creator is the same
        raise HTTPException(status_code=400, detail=f"Category {category.name} already exits")

    return {"success": True}


# TODO: is this needed?
#@login_required
@router.get("/category/{category_id}/data", responses=responses, tags=["category"])
async def get_data(category_id: int, user: SystemUser = Depends(get_current_user)):
    """ Endpoint called by category viewer client """
    limit = 100 # page_data.limit
    page = 1 # page_data.page

    userdb = UserModel.objects(username__iexact=user.username).first()
    categories = userdb.categories.filter(deleted=False)

    pagination = Pagination(categories.count(), limit, page)
    categories = query_util.fix_ids(categories[pagination.start:pagination.end])

    for category in categories:
        category['numberAnnotations'] = AnnotationModel.objects(
            deleted=False, category_id=category.get('id')).count()

    return {
        "pagination": pagination.export(),
        "page": page,
        "categories": categories
    }

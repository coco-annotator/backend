from werkzeug.security import generate_password_hash

from backend.database import UserModel
from backend.webserver.variables import responses, PageDataModel
from .users import SystemUser, get_current_user
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..util.query_util import fix_ids

# api = Namespace('admin', description='Admin related operations')
#
# users = reqparse.RequestParser()
# users.add_argument('limit', type=int, default=50)
# users.add_argument('page', type=int, default=1)
#
# create_user = reqparse.RequestParser()
# create_user.add_argument('name', default="", location='json')
# create_user.add_argument('password', default="", location='json')
#
# register = reqparse.RequestParser()
# register.add_argument('username', required=True, location='json')
# register.add_argument('password', required=True, location='json')
# register.add_argument('email', location='json')
# register.add_argument('name', location='json')
# register.add_argument('isAdmin', type=bool, default=False, location='json')

router = APIRouter()


@router.get('/admin/users', responses=responses, tags=["admin"])
async def get_users(user: SystemUser = Depends(get_current_user)):
    """ Get list of all users """

    if not user.is_admin:
        raise HTTPException(status_code=401, detail="Access denied")
        # return {"success": False, "message": "Access denied"}, 401

    per_page = 100 # page_data.limit
    page = 1 # page_data.page - 1

    user_model = UserModel.objects
    total = user_model.count()
    pages = int(total/per_page) + 1

    # user_model = user_model.skip(page*per_page).limit(per_page).exclude("preferences", "password")
    user_model = user_model.exclude("preferences", "password", "_id")

    return {
        "total": total,
        "pages": pages,
        "page": page,
        "per_page": per_page,
        "users": fix_ids(user_model.all())
    }


class Register(BaseModel):
    username: str
    password: str
    email: str | None = None
    name: str | None = None
    isAdmin: bool = False


@router.post('/admin/user', responses=responses, tags=["admin"])
async def create_user(user: Register, sysuser: SystemUser = Depends(get_current_user)):
        """ Create a new user """

        if not sysuser.is_admin:
            raise HTTPException(status_code=401, detail="Access denied")
            #return {"success": False, "message": "Access denied"}, 401

        if UserModel.objects(username__iexact=user.username).first():
            raise HTTPException(status_code=400, detail='Username already exists.')
            #return {'success': False, 'message': 'Username already exists.'}, 400

        usermodel = UserModel()
        usermodel.username = user.username
        usermodel.password = generate_password_hash(user.password)
        usermodel.name = user.name
        usermodel.email = user.email
        usermodel.is_admin = user.isAdmin
        usermodel.save()

        # user_json = fix_ids(current_user)
        # del user_json['password']

        # return {'success': True, 'user': user_json}
        return {'success': True}


@router.get('/admin/user/{username}', responses=responses, tags=["admin"])
async def get_user(username: str, user: SystemUser = Depends(get_current_user)):
    """ Get a users """

    if not user.is_admin:
        raise HTTPException(status_code=401, detail="Access denied")
        #return {"success": False, "message": "Access denied"}, 401

    user = UserModel.objects(username__iexact=username).first()
    if user is None:
        raise HTTPException(status_code=400, detail='Username already exists.')
        #return {"success": False, "message": "User not found"}, 400

    return fix_ids(user)


class UserData(BaseModel):
    name: str = ""
    password: str = ""


#@api.expect(create_user)
#@login_required
@router.patch('/admin/user/{username}', responses=responses, tags=["admin"])
async def update_user(username: str, user_data: UserData, user: SystemUser = Depends(get_current_user)):
    """ Edit a user """

    if not user.is_admin:
        raise HTTPException(status_code=401, detail="Access denied")
        #return {"success": False, "message": "Access denied"}, 401

    user = UserModel.objects(username__iexact=username).first()
    if user is None:
        raise HTTPException(status_code=400, detail='User not found')
        #return {"success": False, "message": "User not found"}, 400

    name = user_data.name
    if len(name) > 0:
        user.name = name

    password = user_data.password
    if len(password) > 0:
        user.password = generate_password_hash(password)

    user.save()

    return fix_ids(user)


#@login_required
@router.delete('/admin/user/{username}', responses=responses, tags=["admin"])
async def delete_user(username: str, user: SystemUser = Depends(get_current_user)):
    """ Delete a user """

    if not user.is_admin:
        raise HTTPException(status_code=401, detail="Access denied")
        #return {"success": False, "message": "Access denied"}, 401

    user = UserModel.objects(username__iexact=username).first()
    if user is None:
        raise HTTPException(status_code=400, detail='User not found')
        #return {"success": False, "message": "User not found"}, 400

    user.delete()
    return {"success": True}
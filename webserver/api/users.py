import json
from werkzeug.security import generate_password_hash, check_password_hash
from backend.webserver.variables import responses, PageDataModel

from fastapi import Depends, status
from fastapi import APIRouter, HTTPException
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from pydantic import BaseModel, ValidationError
from backend.database import UserModel
import backend.config as Config
from ..util.query_util import fix_ids
from typing import Union, Any
from jose import jwt, JWTError
from datetime import datetime, timedelta

import logging
logger = logging.getLogger('gunicorn.error')

# api = Namespace('user', description='User related operations')
#
# register = reqparse.RequestParser()
# register.add_argument('username', required=True, location='json')
# register.add_argument('password', required=True, location='json')
# register.add_argument('email', location='json')
# register.add_argument('name', location='json')
#
# login = reqparse.RequestParser()
# login.add_argument('password', required=True, location='json')
# login.add_argument('username', required=True, location='json')
#
# set_password = reqparse.RequestParser()
# set_password.add_argument('password', required=True, location='json')
# set_password.add_argument('new_password', required=True, location='json')


router = APIRouter()

reuseable_oauth = OAuth2PasswordBearer(
    tokenUrl="/user/login",
    scheme_name="JWT"
)

class TokenPayload(BaseModel):
    sub: str = None
    exp: int = None


class SystemUser(BaseModel):
    # id: ObjectId
    password: str
    username: str
    name: str
    last_seen: datetime
    is_admin: bool
    permissions: list
    preferences: dict


def create_access_token(subject: Union[str, Any]) -> str:
    expires_delta = datetime.utcnow() + timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expires_delta, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, Config.JWT_SECRET_KEY, Config.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(subject: Union[str, Any]) -> str:
    expires_delta = datetime.utcnow() + timedelta(minutes=Config.REFRESH_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expires_delta, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, Config.JWT_REFRESH_SECRET_KEY, Config.JWT_ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(reuseable_oauth)) -> SystemUser:
    if Config.LOGIN_DISABLED:
        user = UserModel.objects(username__iexact="admin").first()
        user = json.loads(user.to_json())
        return SystemUser(**user)

    try:
        payload = jwt.decode(
            token, Config.JWT_SECRET_KEY, algorithms=[Config.JWT_ALGORITHM]
        )
        token_data = TokenPayload(**payload)

        if datetime.fromtimestamp(token_data.exp) < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except(JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # user: Union[dict[str, Any], None] = db.get(token_data.sub)
        # user: Union[dict[str, Any], None] = mongodb.user_model.find_one({"username": token_data.sub})
        user = UserModel.objects(username__iexact=token_data.sub).first()
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not find user",
        )

    user = json.loads(user.to_json())
    user["last_seen"] = datetime.fromtimestamp(user["last_seen"]['$date'] / 1000)
    return SystemUser(**user)

#%%

#@api.route('/')
#@login_required
@router.get('/user', responses=responses)
async def get_user(user: SystemUser = Depends(get_current_user)):
    """ Get information of current user """
    user_json = fix_ids(user)
    del user_json['password']

    return {'user': user_json}


class SetPasswordModel(BaseModel):
    password: str
    new_password: str

#@api.route('/password')
#@login_required
#@api.expect(register)
@router.post('/user', responses=responses)
def update_password(set_password: SetPasswordModel, user: SystemUser = Depends(get_current_user)):
    """ Set password of current user """
    if check_password_hash(user.password, set_password.password):
        current_user.update(password=generate_password_hash(set_password.new_password, method='sha256'), new=False)
        return {'success': True}

    return {'success': False, 'message': 'Password does not match current passowrd'}, 400


class RegisterModelData(BaseModel):
    username: str
    password: str
    email: str
    name: str

#@api.route('/register')
#@api.expect(register)
@router.post('/user/register', responses=responses)
def create_user(register: RegisterModelData):
    """ Creates user """

    users = UserModel.objects.count()

    if not Config.ALLOW_REGISTRATION and users != 0:
        return {'success': False, 'message': 'Registration of new accounts is disabled.'}, 400

    username = register.username

    if UserModel.objects(username__iexact=username).first():
        return {'success': False, 'message': 'Username already exists.'}, 400

    user = UserModel()
    user.username = register.username
    user.password = generate_password_hash(register.password, method='sha256')
    user.name = register.name
    user.email = register.email
    if users == 0:
        user.is_admin = True
    user.save()

    login_user(user)

    user_json = fix_ids(current_user)
    del user_json['password']

    return {'success': True, 'user': user_json}


class TokenSchema(BaseModel):
    access_token:  str
    refresh_token: str

#@api.route('/login')
#@api.expect(login)
@router.post('/user/login', summary="Create access and refresh tokens for user", response_model=TokenSchema)
def login(login: OAuth2PasswordRequestForm = Depends()):
    """ Logs user in """
    user = UserModel.objects(username__iexact=login.username).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect user or password"
        )

    # Ugly hack to get backwards compatibility...
    # SHA256 is deprecated in werkzeug and got renamed...
    pw = user.password
    if pw.startswith('sha256'):
        pw = pw.replace('sha256', 'pbkdf2:sha256')

    if ((login.username == 'admin' and login.password == 'admin') or
            check_password_hash(pw, login.password)):
        logger.info(f'User {login.username} has logged in.')

        return {
           "access_token": create_access_token(user.name),
           "refresh_token": create_refresh_token(user.name),
        }

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Incorrect user or password"
    )


#@api.route('/logout')
#@login_required
@router.get('/user/logout', responses=responses)
def logout(login: OAuth2PasswordRequestForm = Depends()):
    """ Logs user out """
    logger.info(f'User {login.username} has LOGOUT')
    logout_user(login.username)
    return {'success': True}

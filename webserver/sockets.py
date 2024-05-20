import functools
import time

# from flask import session
# from flask_socketio import (
#     SocketIO,
#     disconnect,
#     join_room,
#     leave_room,
#     emit
# )
# from flask_login import current_user

from ..start import socket_manager as sm

from backend.database import ImageModel, SessionEvent
import backend.config as Config

import logging
logger = logging.getLogger('gunicorn.error')


# socketio = SocketIO()


def authenticated_only(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if current_user.is_authenticated or Config.LOGIN_DISABLED:
            return f(*args, **kwargs)
        else:
            disconnect()
    return wrapped


#@socketio.on('annotation')
#@authenticated_only
@sm.on('annotation')
async def annotation(data):
    await sm.emit('annotation', data, broadcast=True)


#@socketio.on('annotating')
#@authenticated_only
@sm.on('annotating')
async def annotating(data):
    """
    Socket for handling image locking and time logging
    """

    image_id = data.get('image_id')
    active = data.get('active')
    
    image = ImageModel.objects(id=image_id).first()
    if image is None:
        # invalid image ID
        return
    
    await sm.emit('annotating', {
        'image_id': image_id,
        'active': active,
        'username': current_user.username
    }, broadcast=True, include_self=False)

    if active:
        logger.info(f'{current_user.username} has started annotating image {image_id}')
        # Remove user from pervious room
        previous = sm.session.get('annotating')
        if previous is not None:
            sm.leave_room(previous)
            previous_image = ImageModel.objects(id=previous).first()

            if previous_image is not None:

                start = sm.session.get('annotating_time', time.time())
                event = SessionEvent.create(start, current_user)

                previous_image.add_event(event)
                previous_image.update(
                    pull__annotating=current_user.username
                )

                await sm.emit('annotating', {
                    'image_id': previous,
                    'active': False,
                    'username': current_user.username
                }, broadcast=True, include_self=False)

        sm.join_room(image_id)
        sm.session['annotating'] = image_id
        sm.session['annotating_time'] = time.time()
        image.update(add_to_set__annotating=current_user.username)
    else:
        sm.leave_room(image_id)

        start = sm.session.get('annotating_time', time.time())
        event = SessionEvent.create(start, current_user)

        image.add_event(event)
        image.update(
            pull__annotating=current_user.username
        )

        sm.session['annotating'] = None
        sm.session['time'] = None


#@socketio.on('connect')
@sm.on('connect')
async def connect(data):
    logger.info(f'Socket connection created with {current_user.username}')


#@socketio.on('disconnect')
@sm.on('disconnect')
async def disconnect():
    if current_user.is_authenticated:
        logger.info(f'Socket connection has been disconnected with {current_user.username}')
        image_id = sm.session.get('annotating')

        # Remove user from room
        if image_id is not None:
            image = ImageModel.objects(id=image_id).first()
            if image is not None:
                start = sm.session.get('annotating_time', time.time())
                event = SessionEvent.create(start, current_user)
        
                image.add_event(event)
                image.update(
                    pull__annotating=current_user.username
                )
                await sm.emit('annotating', {
                    'image_id': image_id,
                    'active': False,
                    'username': current_user.username
                }, broadcast=True, include_self=False)
               

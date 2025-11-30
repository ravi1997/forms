from app import socketio
from flask_socketio import emit, join_room, leave_room

@socketio.on('join')
def on_join(data):
    """Handle a client joining a room."""
    room = data['room']
    join_room(room)
    emit('status', {'msg': 'User has entered the room.'}, room=room)

@socketio.on('leave')
def on_leave(data):
    """Handle a client leaving a room."""
    room = data['room']
    leave_room(room)
    emit('status', {'msg': 'User has left the room.'}, room=room)

@socketio.on('form_update')
def on_form_update(data):
    """Handle a form update event."""
    room = data['room']
    emit('form_updated', data['data'], room=room, include_self=False)

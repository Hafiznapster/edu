from flask_socketio import emit, join_room, leave_room
from flask import request
from flask_login import current_user
from datetime import datetime, timezone
from app import socketio, db
from app.models import Message, Session

@socketio.on('join_session')
def handle_join_session(data):
    session_id = data['session_id']
    session = Session.query.get(session_id)
    participant = session.participants.filter_by(user_id=current_user.id).first() if session else None
    if participant:
        join_room(str(session_id))
        print(f"{current_user.username} joined session room {session_id}")
        emit('user_joined', {
            'username': current_user.username,
            'is_mentor': participant.role == 'mentor',
            'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        }, room=str(session_id))

@socketio.on('leave_session')
def handle_leave_session(data):
    session_id = data['session_id']
    leave_room(str(session_id))
    print(f"{current_user.username} left session room {session_id}")
    emit('user_left', {
        'username': current_user.username,
        'timestamp': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    }, room=str(session_id))

@socketio.on('new_message')
def handle_new_message(data):
    session_id = data['session_id']
    message = data['message']
    print(f"Received message from {current_user.username} in session {session_id}: {message}")

    try:
        session = Session.query.get(session_id)
        if not session:
            print(f"Error: Session {session_id} not found")
            return

        participant = session.participants.filter_by(user_id=current_user.id).first()
        if not participant:
            print(f"Error: User {current_user.username} is not a participant in session {session_id}")
            return

        # Broadcast the message to all users in the session room
        print(f"Broadcasting message to room {session_id}")
        emit('new_message', {
            'username': current_user.username,
            'message': message,
            'timestamp': datetime.now(timezone.utc).strftime('%H:%M')
        }, room=str(session_id))
    except Exception as e:
        print(f"Error handling message: {str(e)}")

@socketio.on('webrtc_signal')
def handle_webrtc_signal(data):
    session_id = data['session_id']
    session = Session.query.get(session_id)
    participant = session.participants.filter_by(user_id=current_user.id).first() if session else None
    if participant:
        # Log the signal type for debugging
        signal_type = data['signal'].get('type', 'unknown')
        print(f"WebRTC signal: {signal_type} from {current_user.username} for session {session_id}")

        # Emit to all clients in the room except the sender
        emit('webrtc_signal', {
            'username': current_user.username,
            'signal': data['signal']
        }, room=str(session_id), include_self=False)

@socketio.on('screen_share')
def handle_screen_share(data):
    session_id = data['session_id']
    session = Session.query.get(session_id)
    participant = session.participants.filter_by(user_id=current_user.id).first() if session else None
    if participant:
        action = data.get('action', 'unknown')
        print(f"Screen share {action} from {current_user.username} in session {session_id}")
        emit('screen_share_update', {
            'username': current_user.username,
            'action': action,
            'timestamp': datetime.now(timezone.utc).strftime('%H:%M')
        }, room=str(session_id), include_self=False)
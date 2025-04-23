import os
import uuid
from flask import render_template, flash, redirect, url_for, request, jsonify, send_from_directory, current_app
from flask_login import current_user, login_required
from flask_socketio import emit, join_room, leave_room
from werkzeug.utils import secure_filename
from app import db, socketio, csrf
from app.sessions import bp
from app.models import User, Session, Message, Review, SessionFile, SessionParticipant, VideoCallRequest, SessionNote
from app.sessions.forms import SessionBookingForm, ReviewForm, FileUploadForm, EndSessionForm
from datetime import datetime
from config import Config
from app.services.firebase_video import FirebaseVideoService

video_service = FirebaseVideoService()

@bp.route('/join_session/<int:session_id>', methods=['POST'])
@login_required
def join_session(session_id):
    session = Session.query.get_or_404(session_id)

    if session.session_type == 'individual':
        flash('This is an individual session.', 'error')
        return redirect(url_for('sessions.view_session', session_id=session_id))

    success, result = session.add_participant(current_user, 'mentee')
    if success:
        db.session.commit()
        flash('Successfully joined the session!', 'success')
    else:
        flash(result, 'error')

    return redirect(url_for('sessions.view_session', session_id=session_id))

@bp.route('/leave_session/<int:session_id>', methods=['POST'])
@login_required
def leave_session(session_id):
    session = Session.query.get_or_404(session_id)

    if session.remove_participant(current_user):
        db.session.commit()
        flash('Successfully left the session.', 'success')
    else:
        flash('You are not a participant in this session.', 'error')

    return redirect(url_for('sessions.view_session', session_id=session_id))

@bp.route('/messages')
@login_required
def messages():
    try:
        # Try to get messages with the attachment column
        sent_messages = Message.query.filter_by(sender_id=current_user.id).order_by(Message.timestamp.desc()).all()
        received_messages = Message.query.filter_by(recipient_id=current_user.id).order_by(Message.timestamp.desc()).all()
    except Exception as e:
        # If there's an error (likely due to missing attachment column), use a raw SQL query
        print(f"Error fetching messages: {e}")
        # Use raw SQL to get messages without the attachment column
        sent_messages = db.session.execute(
            "SELECT id, sender_id, recipient_id, body, timestamp FROM message WHERE sender_id = :user_id ORDER BY timestamp DESC",
            {"user_id": current_user.id}
        ).fetchall()
        received_messages = db.session.execute(
            "SELECT id, sender_id, recipient_id, body, timestamp FROM message WHERE recipient_id = :user_id ORDER BY timestamp DESC",
            {"user_id": current_user.id}
        ).fetchall()

    # Combine and sort messages by timestamp
    all_messages = sorted(
        sent_messages + received_messages,
        key=lambda x: x.timestamp if hasattr(x, 'timestamp') else x[4],  # Handle both ORM objects and raw tuples
        reverse=True
    )

    # Get unique users that the current user has interacted with
    chat_partners = set()
    for message in all_messages:
        if hasattr(message, 'sender_id'):
            # ORM object
            if message.sender_id == current_user.id:
                chat_partners.add(message.recipient)
            else:
                chat_partners.add(message.author)
        else:
            # Raw tuple from SQL query
            sender_id = message[1]
            recipient_id = message[2]
            if sender_id == current_user.id:
                chat_partners.add(User.query.get(recipient_id))
            else:
                chat_partners.add(User.query.get(sender_id))

    # Get all users categorized by role (excluding current user)
    mentors = User.query.filter_by(role='mentor').filter(User.id != current_user.id).all()
    mentees = User.query.filter_by(role='mentee').filter(User.id != current_user.id).all()

    # Mark users who have chatted with the current user
    for user in mentors + mentees:
        user.has_chatted = user in chat_partners

    # Get active sessions for the current user
    active_sessions = Session.query.join(SessionParticipant).filter(
        SessionParticipant.user_id == current_user.id,
        Session.status.in_(['scheduled', 'active'])
    ).all()

    return render_template('sessions/messages.html',
                          messages=all_messages,
                          chat_partners=list(chat_partners),
                          mentors=mentors,
                          mentees=mentees,
                          active_sessions=active_sessions,
                          User=User)

@bp.route('/send_message/<int:recipient_id>', methods=['GET', 'POST'])
@login_required
@csrf.exempt
def send_message(recipient_id):
    recipient = User.query.get_or_404(recipient_id)

    if request.method == 'POST':
        # Handle text message
        message_content = request.form.get('message')

        # Check if there's a file upload
        file_attachment = None
        if 'attachment' in request.files and request.files['attachment'].filename:
            f = request.files['attachment']
            filename = secure_filename(f.filename)

            # Create upload directory if it doesn't exist
            upload_dir = os.path.join(Config.UPLOAD_FOLDER, f'messages_{current_user.id}_{recipient_id}')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)

            # Add a unique identifier to prevent filename collisions
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            file_path = os.path.join(upload_dir, unique_filename)
            f.save(file_path)

            # Get file size and type
            file_size = os.path.getsize(file_path)
            file_type = filename.split('.')[-1] if '.' in filename else 'unknown'

            # Store file info in the message
            file_attachment = {
                'filename': filename,
                'path': f'messages_{current_user.id}_{recipient_id}/{unique_filename}',
                'type': file_type,
                'size': file_size
            }

        # Create and save the message
        if message_content or file_attachment:
            # Create message without attachment first
            message = Message(
                sender_id=current_user.id,
                recipient_id=recipient_id,
                body=message_content if message_content else '',
                timestamp=datetime.now()
            )

            # Try to set attachment if there is one, but handle the case where the column doesn't exist
            if file_attachment:
                try:
                    # Try to set the attachment property
                    message.attachment = str(file_attachment)
                except Exception as e:
                    # If it fails, just log it and continue without the attachment
                    print(f"Warning: Could not set attachment: {e}")
                    # If there's no message content, add a placeholder
                    if not message_content:
                        message.body = f"[Attachment: {file_attachment.get('filename', 'file')}]"

            db.session.add(message)
            db.session.commit()
            flash('Message sent successfully!', 'success')
            return redirect(url_for('sessions.send_message', recipient_id=recipient_id))

    # Get existing conversation
    sent_messages = Message.query.filter_by(sender_id=current_user.id, recipient_id=recipient_id).all()
    received_messages = Message.query.filter_by(sender_id=recipient_id, recipient_id=current_user.id).all()

    conversation = sorted(
        sent_messages + received_messages,
        key=lambda x: x.timestamp
    )

    return render_template('sessions/send_message.html',
                          recipient=recipient,
                          conversation=conversation)

@bp.route('/message/attachment/<int:message_id>')
@login_required
def download_message_attachment(message_id):
    message = Message.query.get_or_404(message_id)

    # Check if user is either the sender or recipient of the message
    if message.sender_id != current_user.id and message.recipient_id != current_user.id:
        flash('You do not have permission to access this file.', 'error')
        return redirect(url_for('sessions.messages'))

    # Check if message has an attachment
    if not message.attachment:
        flash('This message does not have an attachment.', 'error')
        return redirect(url_for('sessions.send_message', recipient_id=message.sender_id if message.sender_id != current_user.id else message.recipient_id))

    try:
        # Parse the attachment string back to a dictionary
        import ast
        attachment = ast.literal_eval(message.attachment)

        # Get the file path
        file_path = attachment['path']
        original_filename = attachment['filename']

        # Send the file
        directory = os.path.join(Config.UPLOAD_FOLDER, os.path.dirname(file_path))
        filename = os.path.basename(file_path)

        return send_from_directory(directory, filename, as_attachment=True, download_name=original_filename)
    except Exception as e:
        flash(f'Error downloading file: {str(e)}', 'error')
        return redirect(url_for('sessions.send_message', recipient_id=message.sender_id if message.sender_id != current_user.id else message.recipient_id))

@bp.route('/book_session/<int:mentor_id>', methods=['GET', 'POST'])
@login_required
def book_session(mentor_id):
    mentor = User.query.get_or_404(mentor_id)
    if not mentor.is_mentor:
        flash('Invalid mentor selected.', 'error')
        return redirect(url_for('main.search_mentors'))

    form = SessionBookingForm()
    if form.validate_on_submit():
        new_session = Session(
            creator_id=current_user.id,
            topic=form.topic.data,
            description=form.description.data,
            scheduled_time=form.scheduled_time.data,
            duration=form.duration.data,
            status='scheduled',
            session_type=form.session_type.data,
            max_participants=form.max_participants.data
        )
        db.session.add(new_session)
        db.session.commit()

        # Add creator as participant
        new_session.add_participant(current_user, 'mentee')
        # Add mentor as participant
        new_session.add_participant(mentor, 'mentor')

        db.session.commit()

        flash('Session booked successfully!', 'success')
        return redirect(url_for('sessions.session_detail', session_id=new_session.id))

    return render_template('sessions/book_session.html', form=form, mentor=mentor)

@bp.route('/my_sessions')
@login_required
def my_sessions():
    now = datetime.utcnow()
    # Get all sessions where user is a participant
    user_sessions = Session.query.join(SessionParticipant).filter(
        SessionParticipant.user_id == current_user.id
    )

    upcoming_sessions = user_sessions.filter(
        Session.scheduled_time >= now,
        Session.status != 'cancelled'
    ).order_by(Session.scheduled_time).all()

    past_sessions = user_sessions.filter(
        Session.scheduled_time < now
    ).order_by(Session.scheduled_time.desc()).all()

    # For mentors, get pending session requests
    if current_user.is_mentor:
        session_requests = user_sessions.filter_by(status='pending').all()
    else:
        session_requests = []

    return render_template('sessions/my_sessions.html',
                          upcoming_sessions=upcoming_sessions,
                          past_sessions=past_sessions,
                          session_requests=session_requests)

@bp.route('/handle_request/<int:session_id>/<action>', methods=['POST'])
@login_required
def handle_request(session_id, action):
    if not current_user.is_mentor:
        flash('Only mentors can handle session requests.', 'error')
        return redirect(url_for('sessions.my_sessions'))

    session = Session.query.get_or_404(session_id)
    participant = session.participants.filter_by(user_id=current_user.id, role='mentor').first()
    if not participant:
        flash('You can only handle your own session requests.', 'error')
        return redirect(url_for('sessions.my_sessions'))

    if action == 'accept':
        session.status = 'scheduled'
        # Set a proper URL for the meeting link using url_for
        session.meeting_link = url_for('sessions.join_session', session_id=session.id)
        flash('Session request accepted!', 'success')
    elif action == 'reject':
        session.status = 'cancelled'
        flash('Session request rejected.', 'info')
    elif action == 'finish':
        session.status = 'completed'
        flash('Session marked as completed!', 'success')

    db.session.commit()
    return redirect(url_for('sessions.my_sessions'))

@bp.route('/session/<int:session_id>/reviews', methods=['GET'])
@login_required
def session_reviews(session_id):
    session = Session.query.get_or_404(session_id)
    participant = session.participants.filter_by(user_id=current_user.id).first()

    if not participant:
        flash('You can only view reviews for sessions you participated in.', 'error')
        return redirect(url_for('sessions.my_sessions'))

    # Check if the current user has already reviewed this session
    has_reviewed = Review.query.filter_by(
        session_id=session.id,
        reviewer_id=current_user.id
    ).first() is not None

    form = ReviewForm()
    return render_template('sessions/session_reviews.html',
                          session=session,
                          form=form,
                          has_reviewed=has_reviewed)

@bp.route('/add_review/<int:session_id>', methods=['GET', 'POST'])
@login_required
def add_review(session_id):
    session = Session.query.get_or_404(session_id)
    if session.status != 'completed':
        flash('You can only review completed sessions.', 'error')
        return redirect(url_for('sessions.my_sessions'))

    participant = session.participants.filter_by(user_id=current_user.id).first()
    if not participant:
        flash('You can only review sessions you participated in.', 'error')
        return redirect(url_for('sessions.my_sessions'))

    existing_review = Review.query.filter_by(
        session_id=session.id,
        reviewer_id=current_user.id
    ).first()
    if existing_review:
        flash('You have already reviewed this session.', 'error')
        return redirect(url_for('sessions.session_detail', session_id=session.id))

    form = ReviewForm()
    if form.validate_on_submit():
        review = Review(
            session=session,
            reviewer=current_user,
            reviewee_id=next(p.user_id for p in session.participants.all() if p.user_id != current_user.id),
            rating=form.rating.data,
            comment=form.comment.data
        )
        db.session.add(review)
        db.session.commit()
        flash('Review submitted successfully! Thank you for your feedback.', 'success')
        return redirect(url_for('sessions.session_detail', session_id=session.id))

    # If it's a GET request, redirect to the session ended page
    if request.method == 'GET':
        return redirect(url_for('sessions.session_ended', session_id=session.id))

@bp.route('/session/<int:session_id>')
@login_required
def session_room(session_id):
    session = Session.query.get_or_404(session_id)
    participant = session.participants.filter_by(user_id=current_user.id).first()
    if not participant:
        flash('You can only join sessions you are participating in.', 'error')
        return redirect(url_for('sessions.my_sessions'))

    if session.status != 'scheduled':
        flash('This session is not currently active.', 'error')
        return redirect(url_for('sessions.my_sessions'))

    return render_template('sessions/session_room.html', session=session)

@socketio.on('join_session')
def on_join_session(data):
    session_id = data['session_id']
    session = Session.query.get(session_id)
    participant = SessionParticipant.query.filter_by(session_id=session_id, user_id=current_user.id).first() if session else None
    if participant:
        join_room(str(session_id))
        print(f"{current_user.username} joined session room {session_id}")
        emit('user_joined', {
            'username': current_user.username,
            'is_mentor': participant.role == 'mentor',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, room=str(session_id))

@socketio.on('leave_session')
def on_leave_session(data):
    session_id = data['session_id']
    leave_room(str(session_id))
    print(f"{current_user.username} left session room {session_id}")
    emit('user_left', {
        'username': current_user.username,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }, room=str(session_id))

@socketio.on('session_message')
def handle_session_message(data):
    session_id = data['session_id']
    message = data['message']
    session = Session.query.get(session_id)
    participant = session.participants.filter_by(user_id=current_user.id).first() if session else None
    if session and participant:
        emit('new_message', {
            'username': current_user.username,
            'message': message,
            'timestamp': datetime.now().strftime('%H:%M')
        }, room=str(session_id))

@socketio.on('webrtc_signal')
def handle_webrtc_signal(data):
    session_id = data['session_id']
    session = Session.query.get(session_id)
    participant = session.participants.filter_by(user_id=current_user.id).first() if session else None
    if session and participant:
        # Log the signal type for debugging
        signal_type = data['signal'].get('type', 'unknown')
        print(f"WebRTC signal: {signal_type} from {current_user.username} for session {session_id}")

        # Emit to the other participant only
        emit('webrtc_signal', {
            'username': current_user.username,
            'signal': data['signal']
        }, room=str(session_id), include_self=False)

@socketio.on('screen_share')
def handle_screen_share(data):
    session_id = data['session_id']
    session = Session.query.get(session_id)
    participant = session.participants.filter_by(user_id=current_user.id).first() if session else None
    if session and participant:
        emit('screen_share', {
            'username': current_user.username,
            'stream': data['stream']
        }, room=str(session_id))

@bp.route('/session/<int:session_id>/notes', methods=['GET'])
@login_required
def session_notes(session_id):
    session = Session.query.get_or_404(session_id)
    participant = session.participants.filter_by(user_id=current_user.id).first()
    if not participant:
        flash('You can only access notes for sessions you are participating in.', 'error')
        return redirect(url_for('sessions.my_sessions'))

    # Get all notes for this session
    notes = SessionNote.query.filter_by(session_id=session_id).order_by(SessionNote.created_at.desc()).all()

    return render_template('sessions/session_notes.html', session=session, notes=notes)

@bp.route('/session/<int:session_id>/add_note', methods=['POST'])
@login_required
@csrf.exempt
def add_session_note(session_id):
    session = Session.query.get_or_404(session_id)
    participant = session.participants.filter_by(user_id=current_user.id).first()
    if not participant:
        return jsonify({'success': False, 'message': 'You can only add notes to sessions you are participating in.'})

    data = request.get_json()
    if not data or 'content' not in data or not data['content'].strip():
        return jsonify({'success': False, 'message': 'Note content is required.'})

    note = SessionNote(
        session_id=session_id,
        author_id=current_user.id,
        content=data['content'].strip(),
        is_private=data.get('is_private', False)
    )

    db.session.add(note)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Note added successfully.'})

@bp.route('/session/<int:session_id>/delete_note', methods=['DELETE'])
@login_required
@csrf.exempt
def delete_session_note(session_id):
    note_id = request.args.get('note_id')
    if not note_id:
        return jsonify({'success': False, 'message': 'Note ID is required.'})

    note = SessionNote.query.get_or_404(note_id)

    # Check if the user is the author of the note
    if note.author_id != current_user.id:
        return jsonify({'success': False, 'message': 'You can only delete your own notes.'})

    # Check if the note belongs to the specified session
    if note.session_id != session_id:
        return jsonify({'success': False, 'message': 'Note does not belong to this session.'})

    db.session.delete(note)
    db.session.commit()

    return jsonify({'success': True, 'message': 'Note deleted successfully.'})

@bp.route('/session/<int:session_id>/files', methods=['GET', 'POST'])
@login_required
def session_files(session_id):
    session = Session.query.get_or_404(session_id)
    participant = session.participants.filter_by(user_id=current_user.id).first()
    if not participant:
        flash('You can only access files for sessions you are participating in.', 'error')
        return redirect(url_for('sessions.my_sessions'))

    form = FileUploadForm()
    if form.validate_on_submit():
        # Create upload directory if it doesn't exist
        upload_dir = os.path.join(Config.UPLOAD_FOLDER, f'session_{session_id}')
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)

        # Save the file with a secure filename
        f = form.file.data
        filename = secure_filename(f.filename)
        # Add a unique identifier to prevent filename collisions
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(upload_dir, unique_filename)
        f.save(file_path)

        # Get file size and type
        file_size = os.path.getsize(file_path)
        file_type = filename.split('.')[-1] if '.' in filename else 'unknown'

        # Create database record
        file_record = SessionFile(
            session_id=session_id,
            title=form.title.data,
            description=form.description.data,
            file_path=f'session_{session_id}/{unique_filename}',
            file_type=file_type,
            file_size=file_size,
            uploaded_by_id=current_user.id
        )
        db.session.add(file_record)
        db.session.commit()

        flash('File uploaded successfully!', 'success')
        return redirect(url_for('sessions.session_files', session_id=session_id))

    files = SessionFile.query.filter_by(session_id=session_id).order_by(SessionFile.uploaded_at.desc()).all()
    return render_template('sessions/session_files.html', session=session, files=files, form=form)

@bp.route('/download/<int:file_id>')
@login_required
def download_file(file_id):
    file_record = SessionFile.query.get_or_404(file_id)
    session = Session.query.get_or_404(file_record.session_id)

    # Check if the user is a participant in this session
    participant = session.participants.filter_by(user_id=current_user.id).first()
    if not participant:
        flash('You can only download files for sessions you are participating in.', 'error')
        return redirect(url_for('sessions.my_sessions'))

    directory = os.path.join(Config.UPLOAD_FOLDER, os.path.dirname(file_record.file_path))
    filename = os.path.basename(file_record.file_path)

    # Check if this is a view request for a PDF
    view_mode = request.args.get('view') == '1'
    if view_mode and file_record.file_type.lower() == 'pdf':
        # For viewing PDFs, redirect to the PDF viewer
        pdf_path = f"uploads/{os.path.dirname(file_record.file_path)}/{filename}"
        return redirect(url_for('main.pdf_viewer', pdf_path=pdf_path))

    # Otherwise, download the file as an attachment
    return send_from_directory(directory, filename, as_attachment=True, download_name=file_record.title + '.' + file_record.file_type)

@bp.route('/session/<int:session_id>/end')
@login_required
def end_session(session_id):
    session_obj = Session.query.get_or_404(session_id)

    # Check if user is the mentor for this session
    participant = session_obj.participants.filter_by(user_id=current_user.id, role='mentor').first()
    if not participant:
        flash('Only mentors can end sessions.', 'error')
        return redirect(url_for('sessions.session_detail', session_id=session_id))

    # Show confirmation page
    return render_template('sessions/end_session.html', session=session_obj)

@bp.route('/session/<int:session_id>/complete')
@login_required
def complete_session(session_id):
    session_obj = Session.query.get_or_404(session_id)

    participant = session_obj.participants.filter_by(user_id=current_user.id).first()
    if not participant:
        flash('Only participants of this session can mark it as completed.', 'error')
        return redirect(url_for('sessions.session_detail', session_id=session_id))

    # Check if session is in a valid state to be completed
    if session_obj.status not in ['scheduled']:
        flash('This session cannot be marked as completed in its current state.', 'warning')
        return redirect(url_for('sessions.session_room', session_id=session_id))

    # Mark session as completed
    session_obj.status = 'completed'
    db.session.commit()
    flash('Session has been marked as completed successfully!', 'success')
    return redirect(url_for('sessions.session_ended', session_id=session_id))

@bp.route('/session/<int:session_id>/ended')
@login_required
def session_ended(session_id):
    session = Session.query.get_or_404(session_id)

    participant = session.participants.filter_by(user_id=current_user.id).first()
    if not participant:
        flash('You do not have permission to view this session.', 'error')
        return redirect(url_for('sessions.my_sessions'))

    form = ReviewForm()
    return render_template('sessions/session_ended.html', session=session, form=form)

@bp.route('/session/<int:session_id>/detail')
@login_required
def session_detail(session_id):
    session = Session.query.get_or_404(session_id)

    participant = session.participants.filter_by(user_id=current_user.id).first()
    if not participant:
        flash('You do not have permission to view this session.', 'error')
        return redirect(url_for('sessions.my_sessions'))

    # Check if the current user has already reviewed this session
    has_reviewed = Review.query.filter_by(
        session_id=session.id,
        reviewer_id=current_user.id
    ).first() is not None

    # Calculate average rating
    avg_rating = session.reviews.with_entities(db.func.avg(Review.rating)).scalar()

    return render_template('sessions/session_detail.html',
                         session=session,
                         avg_rating=avg_rating,
                         has_reviewed=has_reviewed,
                         now=datetime.now())  # Pass the current datetime

@bp.route('/session/<int:session_id>/request-video')
@login_required
def request_video_call(session_id):
    # 1. Verify session access
    session = Session.query.get_or_404(session_id)

    # Check if user is a participant in this session
    requester = SessionParticipant.query.filter_by(session_id=session_id, user_id=current_user.id).first()

    if not requester:
        flash('Access denied', 'error')
        return redirect(url_for('sessions.my_sessions'))

    # Find the other participant
    recipient = SessionParticipant.query.filter_by(session_id=session_id).filter(SessionParticipant.user_id != current_user.id).first()

    if not recipient:
        flash('No other participant found in this session', 'error')
        return redirect(url_for('main.session_detail', id=session_id))

    # Check if there's already an active request
    existing_request = VideoCallRequest.query.filter_by(
        session_id=session_id,
        status='pending'
    ).first()

    if existing_request:
        if existing_request.requester_id == current_user.id:
            flash('You already have a pending video call request for this session', 'info')
        else:
            # If the other person requested, accept it automatically
            existing_request.status = 'accepted'
            db.session.commit()
            flash('Video call request accepted', 'success')
            return redirect(url_for('sessions.join_video_session', session_id=session_id, request_id=existing_request.id))

        return redirect(url_for('main.session_detail', id=session_id))

    # Create a new video call request
    from datetime import timedelta
    expires_at = datetime.now() + timedelta(minutes=15)  # Request expires in 15 minutes

    video_request = VideoCallRequest(
        session_id=session_id,
        requester_id=current_user.id,
        recipient_id=recipient.user_id,
        status='pending',
        expires_at=expires_at
    )

    db.session.add(video_request)
    db.session.commit()

    flash('Video call request sent. Waiting for the other participant to accept.', 'success')
    return redirect(url_for('main.session_detail', id=session_id))


@bp.route('/video-request/<int:request_id>/<action>')
@login_required
def handle_video_request(request_id, action):
    # Get the video call request
    video_request = VideoCallRequest.query.get_or_404(request_id)

    # Verify the user is the recipient of the request
    if video_request.recipient_id != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('sessions.my_sessions'))

    if action == 'accept':
        video_request.status = 'accepted'
        db.session.commit()
        flash('Video call request accepted', 'success')
        return redirect(url_for('sessions.join_video_session', session_id=video_request.session_id, request_id=request_id))

    elif action == 'decline':
        video_request.status = 'declined'
        db.session.commit()
        flash('Video call request declined', 'info')
        return redirect(url_for('main.session_detail', id=video_request.session_id))

    else:
        flash('Invalid action', 'error')
        return redirect(url_for('main.session_detail', id=video_request.session_id))


@bp.route('/session/<int:session_id>/join')
@login_required
def join_video_session(session_id):
    # 1. Verify session access
    session = Session.query.get_or_404(session_id)

    # Check if user is a participant in this session
    participant = SessionParticipant.query.filter_by(session_id=session_id, user_id=current_user.id).first()

    if not participant:
        flash('Access denied. You are not a participant in this session.', 'error')
        return redirect(url_for('sessions.my_sessions'))

    # Check if session is scheduled for today
    today = datetime.now().date()
    if session.scheduled_time.date() != today and session.status == 'scheduled':
        flash('This session is not scheduled for today.', 'warning')
        # Still allow joining, but show warning

    # 2. Initialize Firebase room
    try:
        video_service.create_call_room(session_id)

        # 3. Add participant to room
        video_service.join_call(session_id, current_user.id, {
            'username': current_user.username,
            'is_mentor': participant.role == 'mentor',
            'joined_at': datetime.now().isoformat()
        })
    except Exception as e:
        # Log the error but continue - the video call can still work with local Firebase config
        print(f"Firebase error in join_video_session: {str(e)}")
        # Don't flash an error to avoid confusing the user - the UI will handle fallbacks

    # 4. Prepare Firebase config for frontend
    firebase_config = {
        'api_key': current_app.config['FIREBASE_API_KEY'],
        'auth_domain': current_app.config['FIREBASE_AUTH_DOMAIN'],
        'database_url': current_app.config['FIREBASE_DATABASE_URL'],
        'project_id': current_app.config['FIREBASE_PROJECT_ID'],
        'storage_bucket': current_app.config['FIREBASE_STORAGE_BUCKET'],
        'messaging_sender_id': current_app.config['FIREBASE_MESSAGING_SENDER_ID'],
        'app_id': current_app.config['FIREBASE_APP_ID']
    }

    # Get mentor and mentee information
    mentor = None
    mentee = None
    for p in session.participants:
        if p.role == 'mentor':
            mentor = User.query.get(p.user_id)
        elif p.role == 'mentee':
            mentee = User.query.get(p.user_id)

    return render_template('sessions/video_call.html',
                         title='Learning Session',
                         session=session,
                         mentor=mentor,
                         mentee=mentee,
                         firebase_config=firebase_config)

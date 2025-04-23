from flask import jsonify, request
from flask_login import current_user, login_required
from app import db
from app.mentorship import bp
from app.models import (User, GroupSession, GroupSessionParticipant,
                       MentorAvailability, RecurringSession, CancellationPolicy)
from datetime import datetime, timedelta, date

# API route for updating meeting link
@bp.route('/api/group-sessions/<int:session_id>/update-link', methods=['POST'])
@login_required
def api_update_meeting_link(session_id):
    """API to update meeting link for a group session"""
    session = GroupSession.query.get_or_404(session_id)

    # Check if the user is the mentor
    if session.mentor_id != current_user.id:
        return jsonify({'success': False, 'message': 'Only the session mentor can update the meeting link.'})

    data = request.get_json()
    meeting_link = data.get('meeting_link', '')

    session.meeting_link = meeting_link
    db.session.commit()

    return jsonify({'success': True})

# API route for starting a session
@bp.route('/api/group-sessions/<int:session_id>/start', methods=['POST'])
@login_required
def api_start_session(session_id):
    """API to start a group session"""
    session = GroupSession.query.get_or_404(session_id)

    # Check if the user is the mentor
    if session.mentor_id != current_user.id:
        return jsonify({'success': False, 'message': 'Only the session mentor can start the session.'})

    # Check if the session is scheduled
    if session.status != 'scheduled':
        return jsonify({'success': False, 'message': f'Cannot start a session with status: {session.status}.'})

    session.status = 'in_progress'
    db.session.commit()

    return jsonify({'success': True})

# API route for cancelling a session
@bp.route('/api/group-sessions/<int:session_id>/cancel', methods=['POST'])
@login_required
def api_cancel_session(session_id):
    """API to cancel a group session"""
    session = GroupSession.query.get_or_404(session_id)

    # Check if the user is the mentor
    if session.mentor_id != current_user.id:
        return jsonify({'success': False, 'message': 'Only the session mentor can cancel the session.'})

    # Check if the session is scheduled
    if session.status != 'scheduled':
        return jsonify({'success': False, 'message': f'Cannot cancel a session with status: {session.status}.'})

    session.status = 'cancelled'
    db.session.commit()

    return jsonify({'success': True})

# API route for updating user timezone
@bp.route('/api/user/update-timezone', methods=['POST'])
@login_required
def api_update_timezone():
    """API to update user timezone"""
    data = request.get_json()
    timezone = data.get('timezone', 'UTC')

    # Update user timezone
    current_user.timezone = timezone
    db.session.commit()

    return jsonify({'success': True})

# API route for getting upcoming instances of a recurring session
@bp.route('/api/recurring-sessions/<int:recurring_id>/instances', methods=['GET'])
@login_required
def api_get_recurring_instances(recurring_id):
    """API to get upcoming instances of a recurring session"""
    recurring_session = RecurringSession.query.get_or_404(recurring_id)

    # Check if the user has access to this recurring session
    if recurring_session.group_session_id:
        group_session = GroupSession.query.get(recurring_session.group_session_id)
        if group_session.mentor_id != current_user.id and not GroupSessionParticipant.query.filter_by(
            session_id=group_session.id, user_id=current_user.id).first():
            return jsonify({'success': False, 'message': 'You do not have access to this recurring session.'})
    else:
        from app.models import Session, SessionParticipant
        individual_session = Session.query.get(recurring_session.original_session_id)
        participant = SessionParticipant.query.filter_by(session_id=individual_session.id, user_id=current_user.id).first()
        if not participant:
            return jsonify({'success': False, 'message': 'You do not have access to this recurring session.'})

    # Get upcoming instances
    instances = []

    # Only generate instances if the recurring session is active
    if recurring_session.status == 'active':
        # Start from today
        current_date = date.today()

        # If start date is in the future, use that instead
        if recurring_session.start_date > current_date:
            current_date = recurring_session.start_date

        # Generate the next 10 instances
        count = 0
        while count < 10:
            # Check if we've reached the end date
            if recurring_session.end_date and current_date > recurring_session.end_date:
                break

            # Check if this date matches the recurrence pattern
            is_match = False

            if recurring_session.frequency == 'weekly':
                # For weekly, check if the day of week matches
                if current_date.weekday() == recurring_session.day_of_week:
                    is_match = True

            elif recurring_session.frequency == 'bi-weekly':
                # For bi-weekly, check if the day of week matches and it's an even number of weeks from the start
                if current_date.weekday() == recurring_session.day_of_week:
                    weeks_diff = ((current_date - recurring_session.start_date).days // 7)
                    if weeks_diff % 2 == 0:
                        is_match = True

            elif recurring_session.frequency == 'monthly':
                # For monthly, check if it's the same week of month and day of week
                if current_date.weekday() == recurring_session.day_of_week:
                    # Calculate week of month
                    day = current_date.day
                    week_of_month = (day - 1) // 7 + 1

                    # Handle "last week" (week 5)
                    if recurring_session.week_of_month == 5:
                        # Check if this is the last occurrence of this day in the month
                        next_week = current_date + timedelta(days=7)
                        if next_week.month != current_date.month:
                            is_match = True
                    elif week_of_month == recurring_session.week_of_month:
                        is_match = True

            if is_match:
                # Create a datetime combining the date and time
                session_datetime = datetime.combine(
                    current_date,
                    recurring_session.time
                )

                # Check if this instance already exists in the database
                status = 'scheduled'

                if recurring_session.group_session_id:
                    existing_session = GroupSession.query.filter_by(
                        mentor_id=group_session.mentor_id,
                        scheduled_time=session_datetime,
                        is_recurring=True
                    ).first()

                    if existing_session:
                        status = existing_session.status
                else:
                    from app.models import Session
                    # Get mentor and mentee from participants
                    mentor_id = None
                    mentee_id = None
                    for participant in individual_session.participants:
                        if participant.role == 'mentor':
                            mentor_id = participant.user_id
                        elif participant.role == 'mentee':
                            mentee_id = participant.user_id

                    # Find existing session with same participants
                    existing_sessions = Session.query.filter_by(
                        scheduled_time=session_datetime,
                        is_recurring=True
                    ).all()

                    existing_session = None
                    for session in existing_sessions:
                        has_mentor = False
                        has_mentee = False
                        for participant in session.participants:
                            if participant.role == 'mentor' and participant.user_id == mentor_id:
                                has_mentor = True
                            elif participant.role == 'mentee' and participant.user_id == mentee_id:
                                has_mentee = True
                        if has_mentor and has_mentee:
                            existing_session = session
                            break

                    if existing_session:
                        status = existing_session.status

                # Add to instances
                instances.append({
                    'date': current_date.strftime('%B %d, %Y'),
                    'time': recurring_session.time.strftime('%I:%M %p'),
                    'status': status
                })

                count += 1

            # Move to next day
            current_date += timedelta(days=1)

    return jsonify({'success': True, 'instances': instances})

# Progress Tracking API Routes - Removed

# API route for deleting a session note
@bp.route('/api/notes/<int:note_id>/delete', methods=['POST'])
@login_required
def api_delete_note(note_id):
    """API to delete a session note"""
    from app.models import SessionNote

    note = SessionNote.query.get_or_404(note_id)

    # Check if the user is the author
    if note.author_id != current_user.id:
        return jsonify({'success': False, 'message': 'Only the author can delete this note.'})

    db.session.delete(note)
    db.session.commit()

    return jsonify({'success': True})

# API route for deleting a session recording
@bp.route('/api/recordings/<int:recording_id>/delete', methods=['POST'])
@login_required
def api_delete_recording(recording_id):
    """API to delete a session recording"""
    from app.models import SessionRecording
    import os

    recording = SessionRecording.query.get_or_404(recording_id)

    # Check if the user is the one who recorded it
    if recording.recorded_by_id != current_user.id:
        return jsonify({'success': False, 'message': 'Only the person who recorded this can delete it.'})

    # Delete the file if it exists
    if recording.file_path:
        from flask import current_app
        file_path = os.path.join(current_app.root_path, 'static', recording.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)

    db.session.delete(recording)
    db.session.commit()

    return jsonify({'success': True})

# API route for liking a resource
@bp.route('/api/resources/<int:resource_id>/like', methods=['POST'])
@login_required
def api_like_resource(resource_id):
    """API to like a resource"""
    from app.models import Resource

    resource = Resource.query.get_or_404(resource_id)

    # Increment like count
    resource.likes += 1
    db.session.commit()

    return jsonify({'success': True, 'likes': resource.likes})

# API route for deleting a resource
@bp.route('/api/resources/<int:resource_id>/delete', methods=['POST'])
@login_required
def api_delete_resource(resource_id):
    """API to delete a resource"""
    from app.models import Resource, GroupSessionResource
    import os

    resource = Resource.query.get_or_404(resource_id)

    # Check if the user is the creator
    if resource.creator_id != current_user.id:
        return jsonify({'success': False, 'message': 'Only the creator can delete this resource.'})

    # Delete file if it exists
    if resource.file_path:
        from flask import current_app
        file_path = os.path.join(current_app.root_path, 'static', resource.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)

    # Delete associations with group sessions
    GroupSessionResource.query.filter_by(resource_id=resource_id).delete()

    # Delete the resource
    db.session.delete(resource)
    db.session.commit()

    return jsonify({'success': True})

# API route for deleting a resource library
@bp.route('/api/resources/library/<int:library_id>/delete', methods=['POST'])
@login_required
def api_delete_library(library_id):
    """API to delete a resource library"""
    from app.models import ResourceLibrary, Resource, GroupSessionResource
    import os

    library = ResourceLibrary.query.get_or_404(library_id)

    # Check if the user is the creator
    if library.creator_id != current_user.id:
        return jsonify({'success': False, 'message': 'Only the creator can delete this library.'})

    # Get all resources in this library
    resources = Resource.query.filter_by(library_id=library_id).all()

    # Delete each resource
    for resource in resources:
        # Delete file if it exists
        if resource.file_path:
            from flask import current_app
            file_path = os.path.join(current_app.root_path, 'static', resource.file_path)
            if os.path.exists(file_path):
                os.remove(file_path)

        # Delete associations with group sessions
        GroupSessionResource.query.filter_by(resource_id=resource.id).delete()

    # Delete all resources in this library
    Resource.query.filter_by(library_id=library_id).delete()

    # Delete the library
    db.session.delete(library)
    db.session.commit()

    return jsonify({'success': True})

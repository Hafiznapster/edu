from flask import render_template, flash, redirect, url_for, request, jsonify, current_app, send_from_directory
from flask_login import current_user, login_required
from app import db
from app.mentorship import bp
from app.models import (User, GroupSession, GroupSessionParticipant, ResourceLibrary,
                       Resource, GroupSessionResource, SessionNote, SessionRecording,
                       MentorshipAgreement, SessionFeedback, MentorAvailability,
                       RecurringSession, CancellationPolicy)
from app.mentorship.forms import ResourceLibraryForm, GroupSessionForm, ResourceForm
from datetime import datetime, timedelta, time
import pytz
import os
import uuid

# Test route
@bp.route('/test')
def test():
    return "Test route is working!"

@bp.route('/resources/library/create-form', methods=['GET', 'POST'])
@login_required
def create_library_form():
    """Create a new resource library using form"""
    form = ResourceLibraryForm()
    if form.validate_on_submit():
        library = ResourceLibrary(
            title=form.title.data,
            description=form.description.data,
            category=form.category.data,
            creator_id=current_user.id,
            is_public=form.is_public.data,
            tags=form.tags.data
        )
        db.session.add(library)
        db.session.commit()
        flash('Resource library created successfully!', 'success')
        return redirect(url_for('mentorship.library_detail', library_id=library.id))

    return render_template('mentorship/create_library.html', title='Create Library', form=form)

@bp.route('/find-mentors')
@login_required
def find_mentors():
    """View available mentors"""
    mentors = User.query.filter_by(role='mentor', is_verified=True).all()

    # Transform mentor data to include required fields
    formatted_mentors = []
    for mentor in mentors:
        mentor_data = {
            'id': mentor.id,
            'name': mentor.username,
            'title': mentor.department or 'Mentor',
            'profile_image': mentor.profile_pic,
            'bio': mentor.bio or 'No bio available',
            'rating': 4.5,  # Placeholder - implement actual rating system
            'reviews_count': 0,  # Placeholder - implement actual review count
            'skills': mentor.skills.split(',') if mentor.skills else []
        }
        formatted_mentors.append(mentor_data)

    return render_template('mentorship/find_mentors.html',
                          title='Find Mentors',
                          mentors=formatted_mentors)

# Group Sessions Routes
@bp.route('/group-sessions')
@login_required
def group_sessions():
    """View all available group sessions"""
    upcoming_sessions = GroupSession.query.filter(
        GroupSession.scheduled_time > datetime.utcnow(),
        GroupSession.status == 'scheduled'
    ).order_by(GroupSession.scheduled_time).all()

    # For mentors, also show their created sessions
    my_sessions = []
    if current_user.is_mentor:
        my_sessions = GroupSession.query.filter_by(
            mentor_id=current_user.id
        ).order_by(GroupSession.scheduled_time.desc()).all()

    # For mentees, show sessions they've registered for
    registered_sessions = []
    if current_user.is_mentee:
        participant_records = GroupSessionParticipant.query.filter_by(
            user_id=current_user.id
        ).all()
        session_ids = [record.session_id for record in participant_records]
        registered_sessions = GroupSession.query.filter(
            GroupSession.id.in_(session_ids)
        ).order_by(GroupSession.scheduled_time).all()

    return render_template('mentorship/group_sessions.html',
                          title='Group Sessions',
                          upcoming_sessions=upcoming_sessions,
                          my_sessions=my_sessions,
                          registered_sessions=registered_sessions)

@bp.route('/group-sessions/create', methods=['GET', 'POST'])
@login_required
def create_group_session():
    """Create a new group session (mentors only)"""
    if not current_user.is_mentor:
        flash('Only mentors can create group sessions.', 'warning')
        return redirect(url_for('mentorship.group_sessions'))

    form = GroupSessionForm()
    if form.validate_on_submit():
        # Combine date and time
        scheduled_datetime = datetime.combine(
            form.scheduled_date.data,
            form.scheduled_time.data
        )

        # Calculate end time
        end_datetime = scheduled_datetime + timedelta(minutes=form.duration.data)

        # Create new group session
        session = GroupSession(
            title=form.title.data,
            description=form.description.data,
            mentor_id=current_user.id,
            max_participants=form.max_participants.data,
            scheduled_time=scheduled_datetime,
            end_time=end_datetime,
            status='scheduled',
            is_recurring=form.is_recurring.data,
            recurrence_pattern=form.recurrence_pattern.data if form.is_recurring.data else '',
            tags=form.tags.data
        )

        db.session.add(session)
        db.session.commit()

        flash('Group session created successfully!', 'success')
        return redirect(url_for('mentorship.group_session_detail', session_id=session.id))

    return render_template('mentorship/create_group_session.html', title='Create Group Session', form=form)

@bp.route('/group-sessions/<int:session_id>')
@login_required
def group_session_detail(session_id):
    """View details of a specific group session"""
    session = GroupSession.query.get_or_404(session_id)

    # Check if user is registered
    is_registered = False
    if current_user.is_mentee:
        participant = GroupSessionParticipant.query.filter_by(
            session_id=session_id,
            user_id=current_user.id
        ).first()
        is_registered = participant is not None

    # Get participants
    participants = GroupSessionParticipant.query.filter_by(
        session_id=session_id
    ).all()

    # Get session resources
    session_resources = GroupSessionResource.query.filter_by(
        session_id=session_id
    ).all()

    resources = []
    for sr in session_resources:
        resource = Resource.query.get(sr.resource_id)
        if resource:
            resources.append(resource)

    return render_template('mentorship/group_session_detail.html',
                          title=session.title,
                          session=session,
                          is_registered=is_registered,
                          participants=participants,
                          resources=resources)

@bp.route('/group-sessions/<int:session_id>/register', methods=['POST'])
@login_required
def register_for_session(session_id):
    """Register for a group session"""
    if not current_user.is_mentee:
        flash('Only mentees can register for group sessions.', 'warning')
        return redirect(url_for('mentorship.group_session_detail', session_id=session_id))

    session = GroupSession.query.get_or_404(session_id)

    # Check if session is full
    participant_count = GroupSessionParticipant.query.filter_by(
        session_id=session_id
    ).count()

    if participant_count >= session.max_participants:
        flash('This session is already full.', 'warning')
        return redirect(url_for('mentorship.group_session_detail', session_id=session_id))

    # Check if user is already registered
    existing_registration = GroupSessionParticipant.query.filter_by(
        session_id=session_id,
        user_id=current_user.id
    ).first()

    if existing_registration:
        flash('You are already registered for this session.', 'info')
        return redirect(url_for('mentorship.group_session_detail', session_id=session_id))

    # Register user
    participant = GroupSessionParticipant(
        session_id=session_id,
        user_id=current_user.id,
        status='registered'
    )

    db.session.add(participant)
    db.session.commit()

    flash('You have successfully registered for this session!', 'success')
    return redirect(url_for('mentorship.group_session_detail', session_id=session_id))

@bp.route('/group-sessions/<int:session_id>/cancel-registration', methods=['POST'])
@login_required
def cancel_registration(session_id):
    """Cancel registration for a group session"""
    participant = GroupSessionParticipant.query.filter_by(
        session_id=session_id,
        user_id=current_user.id
    ).first_or_404()

    db.session.delete(participant)
    db.session.commit()

    flash('Your registration has been cancelled.', 'info')
    return redirect(url_for('mentorship.group_session_detail', session_id=session_id))

@bp.route('/group-sessions/<int:session_id>/add-resource', methods=['POST'])
@login_required
def add_session_resource(session_id):
    """Add a resource to a group session"""
    session = GroupSession.query.get_or_404(session_id)

    # Only the mentor who created the session can add resources
    if session.mentor_id != current_user.id:
        flash('Only the session mentor can add resources.', 'warning')
        return redirect(url_for('mentorship.group_session_detail', session_id=session_id))

    resource_id = request.form.get('resource_id')

    # Check if resource exists
    resource = Resource.query.get(resource_id)
    if not resource:
        flash('Resource not found.', 'error')
        return redirect(url_for('mentorship.group_session_detail', session_id=session_id))

    # Check if resource is already added
    existing = GroupSessionResource.query.filter_by(
        session_id=session_id,
        resource_id=resource_id
    ).first()

    if existing:
        flash('This resource is already added to the session.', 'info')
        return redirect(url_for('mentorship.group_session_detail', session_id=session_id))

    # Add resource to session
    session_resource = GroupSessionResource(
        session_id=session_id,
        resource_id=resource_id,
        added_by_id=current_user.id
    )

    db.session.add(session_resource)
    db.session.commit()

    flash('Resource added to session successfully!', 'success')
    return redirect(url_for('mentorship.group_session_detail', session_id=session_id))

# Resource Library Routes
@bp.route('/resources')
@login_required
def resource_library():
    """View resource libraries"""
    # Get public libraries
    public_libraries = ResourceLibrary.query.filter_by(is_public=True).all()

    # Get user's created libraries
    my_libraries = []
    if current_user.is_authenticated:
        my_libraries = ResourceLibrary.query.filter_by(
            creator_id=current_user.id
        ).all()

    return render_template('mentorship/resource_library.html',
                          title='Resource Library',
                          public_libraries=public_libraries,
                          my_libraries=my_libraries)

@bp.route('/resources/library/create', methods=['GET', 'POST'])
@login_required
def create_library():
    """Create a new resource library"""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        is_public = 'is_public' in request.form
        tags = request.form.get('tags', '')

        library = ResourceLibrary(
            title=title,
            description=description,
            category=category,
            creator_id=current_user.id,
            is_public=is_public,
            tags=tags
        )

        db.session.add(library)
        db.session.commit()

        flash('Resource library created successfully!', 'success')
        return redirect(url_for('mentorship.library_detail', library_id=library.id))

    return render_template('mentorship/create_library.html', title='Create Resource Library')

@bp.route('/resources/library/<int:library_id>')
@login_required
def library_detail(library_id):
    """View details of a specific resource library"""
    library = ResourceLibrary.query.get_or_404(library_id)

    # Check if user has access to this library
    if not library.is_public and library.creator_id != current_user.id:
        flash('You do not have access to this library.', 'warning')
        return redirect(url_for('mentorship.resource_library'))

    # Get resources in this library
    resources = Resource.query.filter_by(library_id=library_id).all()

    return render_template('mentorship/library_detail.html',
                          title=library.title,
                          library=library,
                          resources=resources)

@bp.route('/resources/library/<int:library_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_library(library_id):
    """Edit an existing resource library"""
    library = ResourceLibrary.query.get_or_404(library_id)

    # Check if user is the creator of the library
    if library.creator_id != current_user.id:
        flash('You can only edit libraries you created.', 'warning')
        return redirect(url_for('mentorship.library_detail', library_id=library_id))

    if request.method == 'POST':
        library.title = request.form.get('title')
        library.description = request.form.get('description')
        library.category = request.form.get('category')
        library.is_public = 'is_public' in request.form
        library.tags = request.form.get('tags', '')

        db.session.commit()

        flash('Resource library updated successfully!', 'success')
        return redirect(url_for('mentorship.library_detail', library_id=library.id))

    return render_template('mentorship/edit_library.html',
                          title='Edit Resource Library',
                          library=library)

@bp.route('/resources/create/<int:library_id>', methods=['GET', 'POST'])
@login_required
def create_resource(library_id):
    """Create a new resource in a library"""
    library = ResourceLibrary.query.get_or_404(library_id)

    # Only the library creator can add resources
    if library.creator_id != current_user.id:
        flash('Only the library creator can add resources.', 'warning')
        return redirect(url_for('mentorship.library_detail', library_id=library_id))

    form = ResourceForm()
    if form.validate_on_submit():
        # Handle file upload if resource type is document
        file_path = None
        if form.resource_type.data == 'document' and form.file.data:
            file = form.file.data
            if file and file.filename:
                # Generate unique filename
                filename = str(uuid.uuid4()) + '_' + file.filename
                file_path = os.path.join('uploads', 'resources', filename)

                # Ensure directory exists
                os.makedirs(os.path.join(current_app.root_path, 'static', 'uploads', 'resources'), exist_ok=True)

                # Save file
                file.save(os.path.join(current_app.root_path, 'static', file_path))

        resource = Resource(
            library_id=library_id,
            title=form.title.data,
            description=form.description.data,
            resource_type=form.resource_type.data,
            content=form.content.data,
            file_path=file_path,
            creator_id=current_user.id
        )

        db.session.add(resource)
        db.session.commit()

        flash('Resource created successfully!', 'success')
        return redirect(url_for('mentorship.library_detail', library_id=library_id))

    return render_template('mentorship/create_resource.html',
                          title='Create Resource',
                          library=library,
                          form=form)

@bp.route('/resources/view/<int:resource_id>')
@login_required
def view_resource(resource_id):
    """View a specific resource"""
    resource = Resource.query.get_or_404(resource_id)
    library = ResourceLibrary.query.get(resource.library_id)

    # Check if user has access to this resource
    if not library.is_public and library.creator_id != current_user.id:
        flash('You do not have access to this resource.', 'warning')
        return redirect(url_for('mentorship.resource_library'))

    # Increment view count
    resource.views += 1
    db.session.commit()

    # If it's a PDF and the user wants to view it directly
    if resource.resource_type == 'document' and resource.file_path and resource.file_path.endswith('.pdf') and request.args.get('direct') == '1':
        try:
            # Print debug information
            print(f"Resource file path: {resource.file_path}")

            # Split the file path to get the directory and filename
            file_dir = os.path.dirname(resource.file_path)
            filename = os.path.basename(resource.file_path)

            # Construct the full directory path
            full_dir_path = os.path.join(current_app.root_path, 'static', file_dir)

            print(f"Full directory path: {full_dir_path}")
            print(f"Filename: {filename}")

            # Check if the file exists
            full_file_path = os.path.join(full_dir_path, filename)
            if os.path.exists(full_file_path):
                print(f"File exists at: {full_file_path}")
            else:
                print(f"File does not exist at: {full_file_path}")

            return send_from_directory(
                full_dir_path,
                filename,
                mimetype='application/pdf',
                as_attachment=False
            )
        except Exception as e:
            print(f"Error serving PDF: {str(e)}")
            flash(f"Error viewing PDF: {str(e)}", 'error')
            return redirect(url_for('mentorship.view_resource', resource_id=resource_id))

    return render_template('mentorship/view_resource.html',
                          title=resource.title,
                          resource=resource,
                          library=library)

@bp.route('/resources/edit/<int:resource_id>', methods=['GET', 'POST'])
@login_required
def edit_resource(resource_id):
    """Edit a resource"""
    resource = Resource.query.get_or_404(resource_id)
    library = ResourceLibrary.query.get(resource.library_id)

    # Check if user is the creator of the resource
    if resource.creator_id != current_user.id:
        flash('You can only edit resources you created.', 'warning')
        return redirect(url_for('mentorship.view_resource', resource_id=resource_id))

    form = ResourceForm()

    if request.method == 'GET':
        # Populate form with existing data
        form.title.data = resource.title
        form.description.data = resource.description
        form.resource_type.data = resource.resource_type
        form.content.data = resource.content

    if form.validate_on_submit():
        resource.title = form.title.data
        resource.description = form.description.data
        resource.resource_type = form.resource_type.data

        # Handle content based on resource type
        if resource.resource_type == 'document':
            # Handle file upload if a new file is provided
            if form.file.data:
                file = form.file.data
                if file and file.filename:
                    # Generate unique filename
                    filename = str(uuid.uuid4()) + '_' + file.filename
                    file_path = os.path.join('uploads', 'resources', filename)

                    # Ensure directory exists
                    os.makedirs(os.path.join(current_app.root_path, 'static', 'uploads', 'resources'), exist_ok=True)

                    # Save file
                    file.save(os.path.join(current_app.root_path, 'static', file_path))

                    # Update file path
                    resource.file_path = file_path
        else:
            # Update content for non-document resources
            resource.content = form.content.data

        resource.updated_at = datetime.utcnow()
        db.session.commit()

        flash('Resource updated successfully!', 'success')
        return redirect(url_for('mentorship.view_resource', resource_id=resource.id))

    return render_template('mentorship/edit_resource.html',
                          title='Edit Resource',
                          form=form,
                          resource=resource,
                          library=library)

# Session Notes and Recordings Routes
@bp.route('/sessions/notes/<int:session_id>', methods=['GET', 'POST'])
@login_required
def session_notes(session_id):
    """View and add notes for a session"""
    # Check if it's a group session or individual session
    group_session = GroupSession.query.get(session_id)

    if group_session:
        # For group sessions
        if group_session.mentor_id != current_user.id and not GroupSessionParticipant.query.filter_by(
            session_id=session_id, user_id=current_user.id).first():
            flash('You do not have access to these notes.', 'warning')
            return redirect(url_for('mentorship.group_sessions'))

        notes = SessionNote.query.filter_by(group_session_id=session_id).all()
        session_obj = group_session
        is_group = True
    else:
        # For individual sessions
        from app.models import Session, SessionParticipant
        individual_session = Session.query.get_or_404(session_id)

        participant = SessionParticipant.query.filter_by(session_id=session_id, user_id=current_user.id).first()
        if not participant:
            flash('You do not have access to these notes.', 'warning')
            return redirect(url_for('main.dashboard'))

        notes = SessionNote.query.filter_by(session_id=session_id).all()
        session_obj = individual_session
        is_group = False

    if request.method == 'POST':
        content = request.form.get('content')
        is_private = 'is_private' in request.form

        note = SessionNote(
            session_id=session_id if not is_group else None,
            group_session_id=session_id if is_group else None,
            author_id=current_user.id,
            content=content,
            is_private=is_private
        )

        db.session.add(note)
        db.session.commit()

        flash('Note added successfully!', 'success')
        return redirect(url_for('mentorship.session_notes', session_id=session_id))

    return render_template('mentorship/session_notes.html',
                          title='Session Notes',
                          notes=notes,
                          session=session_obj,
                          is_group=is_group)

@bp.route('/sessions/recordings/<int:session_id>', methods=['GET', 'POST'])
@login_required
def session_recordings(session_id):
    """View and add recordings for a session"""
    # Check if it's a group session or individual session
    group_session = GroupSession.query.get(session_id)

    if group_session:
        # For group sessions
        if group_session.mentor_id != current_user.id and not GroupSessionParticipant.query.filter_by(
            session_id=session_id, user_id=current_user.id).first():
            flash('You do not have access to these recordings.', 'warning')
            return redirect(url_for('mentorship.group_sessions'))

        recordings = SessionRecording.query.filter_by(group_session_id=session_id).all()
        session_obj = group_session
        is_group = True
    else:
        # For individual sessions
        from app.models import Session, SessionParticipant
        individual_session = Session.query.get_or_404(session_id)

        participant = SessionParticipant.query.filter_by(session_id=session_id, user_id=current_user.id).first()
        if not participant:
            flash('You do not have access to these recordings.', 'warning')
            return redirect(url_for('main.dashboard'))

        recordings = SessionRecording.query.filter_by(session_id=session_id).all()
        session_obj = individual_session
        is_group = False

    if request.method == 'POST':
        title = request.form.get('title')
        is_public = 'is_public' in request.form

        # Handle file upload
        if 'recording_file' in request.files:
            file = request.files['recording_file']
            if file and file.filename:
                # Generate unique filename
                filename = str(uuid.uuid4()) + '_' + file.filename
                file_path = os.path.join('uploads', 'recordings', filename)

                # Ensure directory exists
                os.makedirs(os.path.join(current_app.root_path, 'static', 'uploads', 'recordings'), exist_ok=True)

                # Save file
                file.save(os.path.join(current_app.root_path, 'static', file_path))

                # Create recording entry
                recording = SessionRecording(
                    session_id=session_id if not is_group else None,
                    group_session_id=session_id if is_group else None,
                    title=title,
                    file_path=file_path,
                    recorded_by_id=current_user.id,
                    is_public=is_public
                )

                db.session.add(recording)
                db.session.commit()

                flash('Recording uploaded successfully!', 'success')
                return redirect(url_for('mentorship.session_recordings', session_id=session_id))
            else:
                flash('No file selected.', 'error')

    return render_template('mentorship/session_recordings.html',
                          title='Session Recordings',
                          recordings=recordings,
                          session=session_obj,
                          is_group=is_group)

# Progress Tracking Routes - Removed


# Availability Management Routes
@bp.route('/availability')
@login_required
def availability_management():
    """View and manage mentor availability"""
    if not current_user.is_mentor:
        flash('Only mentors can access availability management.', 'warning')
        return redirect(url_for('main.dashboard'))

    # Get mentor's availability slots
    availability_slots = MentorAvailability.query.filter_by(
        mentor_id=current_user.id
    ).order_by(MentorAvailability.day_of_week, MentorAvailability.start_time).all()

    # Get all timezones for the dropdown
    all_timezones = pytz.common_timezones

    # Get mentor's current timezone
    mentor_timezone = current_user.timezone if hasattr(current_user, 'timezone') and current_user.timezone else 'UTC'

    return render_template('mentorship/availability_management.html',
                          title='Availability Management',
                          availability_slots=availability_slots,
                          all_timezones=all_timezones,
                          mentor_timezone=mentor_timezone,
                          days_of_week=['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])

@bp.route('/availability/add', methods=['POST'])
@login_required
def add_availability():
    """Add a new availability slot"""
    if not current_user.is_mentor:
        flash('Only mentors can manage availability.', 'warning')
        return redirect(url_for('main.dashboard'))

    day_of_week = int(request.form.get('day_of_week'))
    start_time_str = request.form.get('start_time')
    end_time_str = request.form.get('end_time')
    timezone = request.form.get('timezone')
    is_recurring = 'is_recurring' in request.form
    specific_date_str = request.form.get('specific_date') if not is_recurring else None

    # Convert time strings to time objects
    start_time = datetime.strptime(start_time_str, '%H:%M').time()
    end_time = datetime.strptime(end_time_str, '%H:%M').time()

    # Convert specific date string to date object if provided
    specific_date = None
    if specific_date_str:
        specific_date = datetime.strptime(specific_date_str, '%Y-%m-%d').date()

    # Check if the time slot overlaps with existing slots
    existing_slots = MentorAvailability.query.filter_by(
        mentor_id=current_user.id,
        day_of_week=day_of_week
    ).all()

    for slot in existing_slots:
        if (start_time < slot.end_time and end_time > slot.start_time):
            flash('This time slot overlaps with an existing availability slot.', 'warning')
            return redirect(url_for('mentorship.availability_management'))

    # Create new availability slot
    availability = MentorAvailability(
        mentor_id=current_user.id,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
        timezone=timezone,
        is_recurring=is_recurring,
        specific_date=specific_date,
        status='active'
    )

    db.session.add(availability)
    db.session.commit()

    flash('Availability slot added successfully!', 'success')
    return redirect(url_for('mentorship.availability_management'))

@bp.route('/availability/<int:slot_id>/delete', methods=['POST'])
@login_required
def delete_availability(slot_id):
    """Delete an availability slot"""
    slot = MentorAvailability.query.get_or_404(slot_id)

    # Check if the slot belongs to the current user
    if slot.mentor_id != current_user.id:
        flash('You do not have permission to delete this availability slot.', 'warning')
        return redirect(url_for('mentorship.availability_management'))

    db.session.delete(slot)
    db.session.commit()

    flash('Availability slot deleted successfully!', 'success')
    return redirect(url_for('mentorship.availability_management'))

@bp.route('/availability/<int:slot_id>/update', methods=['POST'])
@login_required
def update_availability(slot_id):
    """Update an availability slot"""
    slot = MentorAvailability.query.get_or_404(slot_id)

    # Check if the slot belongs to the current user
    if slot.mentor_id != current_user.id:
        flash('You do not have permission to update this availability slot.', 'warning')
        return redirect(url_for('mentorship.availability_management'))

    start_time_str = request.form.get('start_time')
    end_time_str = request.form.get('end_time')
    timezone = request.form.get('timezone')
    status = request.form.get('status')

    # Convert time strings to time objects
    start_time = datetime.strptime(start_time_str, '%H:%M').time()
    end_time = datetime.strptime(end_time_str, '%H:%M').time()

    # Update slot
    slot.start_time = start_time
    slot.end_time = end_time
    slot.timezone = timezone
    slot.status = status

    db.session.commit()

    flash('Availability slot updated successfully!', 'success')
    return redirect(url_for('mentorship.availability_management'))


# Recurring Sessions Routes
@bp.route('/recurring-sessions')
@login_required
def recurring_sessions():
    """View recurring sessions"""
    if current_user.is_mentor:
        # For mentors, show their created recurring sessions
        recurring_sessions = RecurringSession.query.join(
            GroupSession, RecurringSession.group_session_id == GroupSession.id
        ).filter(
            GroupSession.mentor_id == current_user.id
        ).all()
    else:
        # For mentees, show recurring sessions they're registered for
        participant_records = GroupSessionParticipant.query.filter_by(
            user_id=current_user.id
        ).all()
        session_ids = [record.session_id for record in participant_records]
        recurring_sessions = RecurringSession.query.filter(
            RecurringSession.group_session_id.in_(session_ids)
        ).all()

    return render_template('mentorship/recurring_sessions.html',
                          title='Recurring Sessions',
                          recurring_sessions=recurring_sessions)

@bp.route('/recurring-sessions/create/<int:session_id>', methods=['GET', 'POST'])
@login_required
def create_recurring_session(session_id):
    """Create a recurring pattern for a session"""
    # Check if it's a group session or individual session
    group_session = GroupSession.query.get(session_id)

    if group_session:
        # For group sessions
        if group_session.mentor_id != current_user.id:
            flash('Only the session mentor can create recurring patterns.', 'warning')
            return redirect(url_for('mentorship.group_sessions'))

        session_obj = group_session
        is_group = True
    else:
        # For individual sessions
        from app.models import Session, SessionParticipant
        individual_session = Session.query.get_or_404(session_id)

        participant = SessionParticipant.query.filter_by(session_id=session_id, user_id=current_user.id, role='mentor').first()
        if not participant:
            flash('Only the session mentor can create recurring patterns.', 'warning')
            return redirect(url_for('sessions.my_sessions'))

        session_obj = individual_session
        is_group = False

    if request.method == 'POST':
        frequency = request.form.get('frequency')
        day_of_week = int(request.form.get('day_of_week')) if request.form.get('day_of_week') else None
        week_of_month = int(request.form.get('week_of_month')) if request.form.get('week_of_month') else None
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        time_str = request.form.get('time')
        duration = int(request.form.get('duration'))
        timezone = request.form.get('timezone')

        # Parse dates and time
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        session_time = datetime.strptime(time_str, '%H:%M').time()

        # Create recurring session
        recurring_session = RecurringSession(
            original_session_id=None if is_group else session_id,
            group_session_id=session_id if is_group else None,
            frequency=frequency,
            day_of_week=day_of_week,
            week_of_month=week_of_month,
            start_date=start_date,
            end_date=end_date,
            time=session_time,
            duration=duration,
            timezone=timezone,
            status='active'
        )

        db.session.add(recurring_session)
        db.session.commit()

        flash('Recurring session pattern created successfully!', 'success')
        if is_group:
            return redirect(url_for('mentorship.group_session_detail', session_id=session_id))
        else:
            return redirect(url_for('sessions.session_detail', session_id=session_id))

    # Get all timezones for the dropdown
    all_timezones = pytz.common_timezones

    return render_template('mentorship/create_recurring_session.html',
                          title='Create Recurring Session',
                          session=session_obj,
                          is_group=is_group,
                          all_timezones=all_timezones)

@bp.route('/recurring-sessions/<int:recurring_id>/update', methods=['POST'])
@login_required
def update_recurring_session(recurring_id):
    """Update a recurring session pattern"""
    recurring_session = RecurringSession.query.get_or_404(recurring_id)

    # Check if the user has permission to update this recurring session
    if recurring_session.group_session_id:
        group_session = GroupSession.query.get(recurring_session.group_session_id)
        if group_session.mentor_id != current_user.id:
            flash('You do not have permission to update this recurring session.', 'warning')
            return redirect(url_for('mentorship.recurring_sessions'))
    else:
        from app.models import Session, SessionParticipant
        individual_session = Session.query.get(recurring_session.original_session_id)
        participant = SessionParticipant.query.filter_by(session_id=individual_session.id, user_id=current_user.id, role='mentor').first()
        if not participant:
            flash('You do not have permission to update this recurring session.', 'warning')
            return redirect(url_for('mentorship.recurring_sessions'))

    # Update recurring session
    status = request.form.get('status')
    end_date_str = request.form.get('end_date')

    recurring_session.status = status
    if end_date_str:
        recurring_session.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

    db.session.commit()

    flash('Recurring session updated successfully!', 'success')
    return redirect(url_for('mentorship.recurring_sessions'))


# Cancellation Policy Routes
@bp.route('/cancellation-policy')
@login_required
def cancellation_policy():
    """View and manage cancellation policy"""
    if not current_user.is_mentor:
        flash('Only mentors can access cancellation policy management.', 'warning')
        return redirect(url_for('main.dashboard'))

    # Get mentor's cancellation policy
    policy = CancellationPolicy.query.filter_by(mentor_id=current_user.id).first()

    return render_template('mentorship/cancellation_policy.html',
                          title='Cancellation Policy',
                          policy=policy)

@bp.route('/cancellation-policy/update', methods=['POST'])
@login_required
def update_cancellation_policy():
    """Update cancellation policy"""
    if not current_user.is_mentor:
        flash('Only mentors can manage cancellation policies.', 'warning')
        return redirect(url_for('main.dashboard'))

    notice_period = int(request.form.get('notice_period'))
    penalty_type = request.form.get('penalty_type')
    penalty_amount = float(request.form.get('penalty_amount')) if request.form.get('penalty_amount') else None
    max_reschedules = int(request.form.get('max_reschedules'))
    policy_text = request.form.get('policy_text')

    # Check if policy already exists
    policy = CancellationPolicy.query.filter_by(mentor_id=current_user.id).first()

    if policy:
        # Update existing policy
        policy.notice_period = notice_period
        policy.penalty_type = penalty_type
        policy.penalty_amount = penalty_amount
        policy.max_reschedules = max_reschedules
        policy.policy_text = policy_text
        policy.updated_at = datetime.now()
    else:
        # Create new policy
        policy = CancellationPolicy(
            mentor_id=current_user.id,
            notice_period=notice_period,
            penalty_type=penalty_type,
            penalty_amount=penalty_amount,
            max_reschedules=max_reschedules,
            policy_text=policy_text
        )
        db.session.add(policy)

    db.session.commit()

    flash('Cancellation policy updated successfully!', 'success')
    return redirect(url_for('mentorship.cancellation_policy'))
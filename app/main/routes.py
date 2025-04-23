from flask import render_template, flash, redirect, url_for, request, jsonify, current_app
from flask_login import current_user, login_required
from app import db
from app.main import bp
from app.models import User, Session, Review
from app.main.forms import SessionBookingForm, MentorSearchForm
from datetime import datetime, timedelta
from sqlalchemy import func
import os

@bp.route('/')
@bp.route('/index')
def index():
    featured_mentors = User.query.filter_by(role='mentor').limit(4).all()
    return render_template('main/index.html', title='Welcome', mentors=featured_mentors)

@bp.route('/dashboard')
@login_required
def dashboard():
    now = datetime.utcnow()

    # Debug information
    all_mentor_sessions = None
    if current_user.is_mentor:
        # Get sessions where user is a mentor
        mentor_session_ids = db.session.query(Session.id).join(Session.participants).filter(
            Session.participants.any(user_id=current_user.id, role='mentor')
        ).all()
        mentor_session_ids = [id[0] for id in mentor_session_ids]
        all_mentor_sessions = Session.query.filter(Session.id.in_(mentor_session_ids)).all()

        # Get upcoming sessions with any status except 'cancelled' and 'completed'
        upcoming_sessions = Session.query.join(Session.participants).filter(
            Session.participants.any(user_id=current_user.id, role='mentor'),
            Session.scheduled_time >= now,
            Session.status.notin_(['cancelled', 'completed'])
        ).order_by(Session.scheduled_time).limit(5).all()
    else:
        # Get sessions where user is a mentee
        upcoming_sessions = Session.query.join(Session.participants).filter(
            Session.participants.any(user_id=current_user.id, role='mentee'),
            Session.scheduled_time >= now,
            Session.status == 'scheduled'
        ).order_by(Session.scheduled_time).limit(5).all()

    today = now.date()
    return render_template('main/dashboard.html',
                           title='Dashboard',
                           upcoming_sessions=upcoming_sessions,
                           all_mentor_sessions=all_mentor_sessions,
                           func=func,
                           Review=Review,
                           today=today)

@bp.route('/search_mentors', methods=['GET', 'POST'])
def search_mentors():
    form = MentorSearchForm()
    mentors = User.query.filter_by(role='mentor')

    if form.validate_on_submit():
        if form.skills.data:
            mentors = mentors.filter(User.skills.contains(form.skills.data))

    mentors = mentors.order_by(User.username).all()
    return render_template('main/search_mentors.html',
                           title='Find Mentors',
                           mentors=mentors,
                           form=form,
                           func=func,
                           Review=Review)

@bp.route('/mentor/<int:id>')
def mentor_profile(id):
    mentor = User.query.filter_by(id=id, role='mentor').first_or_404()
    reviews = Review.query.filter_by(reviewee_id=id).order_by(Review.timestamp.desc()).all()
    return render_template('main/mentor_profile.html',
                           title=f'Mentor - {mentor.username}',
                           mentor=mentor,
                           reviews=reviews)

@bp.route('/book_session/<int:mentor_id>', methods=['GET', 'POST'])
@login_required
def book_session(mentor_id):
    # Redirect to the sessions blueprint's book_session route with the sessions prefix
    return redirect(url_for('sessions.book_session', mentor_id=mentor_id))

@bp.route('/session/<int:id>')
@login_required
def session_detail(id):
    session = Session.query.filter_by(id=id).first_or_404()
    participant = session.participants.filter_by(user_id=current_user.id).first()
    if not participant:
        flash('You do not have permission to view this session.')
        return redirect(url_for('main.dashboard'))

    today = datetime.utcnow().date()
    now = datetime.utcnow()
    return render_template('main/session_detail.html',
                           title='Session Details',
                           session=session,
                           today=today,
                           now=now,
                           timedelta=timedelta,
                           Review=Review)

@bp.route('/session/<int:id>/join')
@login_required
def join_session(id):
    # Redirect to the sessions.join_video_session route
    return redirect(url_for('sessions.join_video_session', session_id=id))

@bp.route('/pdf-viewer/<path:pdf_path>')
def pdf_viewer(pdf_path):
    # Clean the path - replace backslashes with forward slashes
    pdf_path = pdf_path.replace('\\', '/')

    # Extract the filename from the path
    filename = os.path.basename(pdf_path)

    return render_template('pdf_viewer.html',
                           title='PDF Viewer',
                           pdf_path=pdf_path,
                           filename=filename)
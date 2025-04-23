from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.admin import bp
from app.models import User, Session, SessionParticipant, Review, Task, LearningPath, ForumThread
from datetime import datetime, timedelta

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/dashboard')
@login_required
@admin_required
def admin_dashboard():
    total_users = User.query.count()
    total_sessions = Session.query.count()
    total_mentors = User.query.filter_by(role='mentor').count()
    total_mentees = User.query.filter_by(role='mentee').count()

    # Recent users
    recent_users = User.query.order_by(User.id.desc()).limit(5).all()

    # Active sessions
    active_sessions = Session.query.filter_by(status='active').all()

    # Recent reviews
    recent_reviews = Review.query.order_by(Review.timestamp.desc()).limit(5).all()

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           total_sessions=total_sessions,
                           total_mentors=total_mentors,
                           total_mentees=total_mentees,
                           recent_users=recent_users,
                           active_sessions=active_sessions,
                           recent_reviews=recent_reviews)

@bp.route('/users')
@login_required
@admin_required
def manage_users():
    # Get users by role
    mentors = User.query.filter_by(role='mentor').all()
    mentees = User.query.filter_by(role='mentee').all()
    admins = User.query.filter_by(role='admin').all()

    return render_template('admin/users.html',
                           mentors=mentors,
                           mentees=mentees,
                           admins=admins)

@bp.route('/user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.role = request.form.get('role')
        user.is_verified = 'is_verified' in request.form
        db.session.commit()
        flash('User updated successfully.', 'success')
        return redirect(url_for('admin.manage_users'))
    return render_template('admin/edit_user.html', user=user)

@bp.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user == current_user:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin.manage_users'))

    try:
        # Get user's role for the success message
        user_role = user.role
        username = user.username

        # Delete the user (SQLAlchemy cascade will handle related records)
        db.session.delete(user)
        db.session.commit()

        flash(f'{user_role.capitalize()} "{username}" has been deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')

    return redirect(url_for('admin.manage_users'))

@bp.route('/sessions')
@login_required
@admin_required
def manage_sessions():
    sessions = Session.query.all()
    return render_template('admin/sessions.html', sessions=sessions)

@bp.route('/session/<int:session_id>')
@login_required
@admin_required
def view_session(session_id):
    session = Session.query.get_or_404(session_id)
    participants = session.participants.all()
    return render_template('admin/view_session.html', session=session, participants=participants)

@bp.route('/analytics')
@login_required
@admin_required
def analytics():
    # User statistics
    user_growth = User.query.with_entities(
        db.func.date(User.last_seen).label('date'),
        db.func.count(User.id).label('count')
    ).group_by('date').all()

    # Session statistics
    session_stats = Session.query.with_entities(
        Session.status,
        db.func.count(Session.id).label('count')
    ).group_by(Session.status).all()

    # Mentor-Mentee ratio
    role_distribution = User.query.with_entities(
        User.role,
        db.func.count(User.id).label('count')
    ).group_by(User.role).all()

    return render_template('admin/analytics.html',
                           user_growth=user_growth,
                           session_stats=session_stats,
                           role_distribution=role_distribution)
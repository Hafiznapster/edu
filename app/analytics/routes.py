from flask import render_template, flash, redirect, url_for, request, jsonify, current_app
from flask_login import current_user, login_required
from app import db
from app.analytics import bp
from app.models import (User, Session, GroupSession, GroupSessionParticipant,
                       SessionAnalytics, UserEngagement, Badge, UserBadge,
                       Leaderboard, LeaderboardEntry, SystemHealth, SystemBackup)
from datetime import datetime, timedelta
import json
import pandas as pd
import numpy as np
from sqlalchemy import func, desc, and_
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio

# Session Analytics Routes
@bp.route('/session-analytics')
@login_required
def session_analytics():
    """View session analytics dashboard"""
    if not current_user.is_mentor:
        flash('Only mentors can access session analytics.', 'warning')
        return redirect(url_for('main.dashboard'))

    # Get mentor's sessions
    # For individual sessions, find through SessionParticipant
    individual_sessions = Session.query.join(Session.participants).filter(
        Session.participants.any(user_id=current_user.id, role='mentor')
    ).all()
    group_sessions = GroupSession.query.filter_by(mentor_id=current_user.id).all()

    # Calculate basic metrics
    total_sessions = len(individual_sessions) + len(group_sessions)
    completed_sessions = sum(1 for s in individual_sessions if s.status == 'completed')
    completed_sessions += sum(1 for s in group_sessions if s.status == 'completed')

    total_hours = sum((s.end_time - s.scheduled_time).total_seconds() / 3600 for s in individual_sessions if s.status == 'completed')
    total_hours += sum((s.end_time - s.scheduled_time).total_seconds() / 3600 for s in group_sessions if s.status == 'completed')

    # Count unique mentees from individual sessions
    mentee_ids = set()
    for session in individual_sessions:
        mentee_participants = session.participants.filter_by(role='mentee').all()
        for participant in mentee_participants:
            mentee_ids.add(participant.user_id)

    total_students = len(mentee_ids)
    # Add group session participants
    total_students += sum(GroupSessionParticipant.query.filter_by(session_id=s.id).count() for s in group_sessions)

    # Get session analytics data
    individual_analytics = SessionAnalytics.query.filter(
        SessionAnalytics.session_id.in_([s.id for s in individual_sessions])
    ).all()

    group_analytics = SessionAnalytics.query.filter(
        SessionAnalytics.group_session_id.in_([s.id for s in group_sessions])
    ).all()

    all_analytics = individual_analytics + group_analytics

    # Calculate engagement metrics
    avg_engagement = sum(a.engagement_score for a in all_analytics) / len(all_analytics) if all_analytics else 0

    # Generate session trend data (last 6 months)
    six_months_ago = datetime.utcnow() - timedelta(days=180)

    session_dates = [s.scheduled_time.date() for s in individual_sessions if s.scheduled_time > six_months_ago]
    session_dates += [s.scheduled_time.date() for s in group_sessions if s.scheduled_time > six_months_ago]

    # Count sessions by month
    session_counts = {}
    for date in session_dates:
        month_key = date.strftime('%Y-%m')
        session_counts[month_key] = session_counts.get(month_key, 0) + 1

    # Sort by month
    sorted_months = sorted(session_counts.keys())
    trend_data = {
        'months': [m.replace('-', ' ') for m in sorted_months],
        'counts': [session_counts[m] for m in sorted_months]
    }

    # Generate topic distribution data
    topics = {}
    for a in all_analytics:
        if a.topics_covered:
            for topic in a.topics_covered:
                topics[topic] = topics.get(topic, 0) + 1

    # Sort topics by frequency
    sorted_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)
    topic_data = {
        'topics': [t[0] for t in sorted_topics[:10]],  # Top 10 topics
        'counts': [t[1] for t in sorted_topics[:10]]
    }

    return render_template('analytics/session_analytics.html',
                          title='Session Analytics',
                          total_sessions=total_sessions,
                          completed_sessions=completed_sessions,
                          total_hours=round(total_hours, 1),
                          total_students=total_students,
                          avg_engagement=round(avg_engagement * 100, 1),
                          trend_data=trend_data,
                          topic_data=topic_data)

@bp.route('/session-details/<int:session_id>')
@login_required
def session_details(session_id):
    """View detailed analytics for a specific session"""
    # Check if it's a group session or individual session
    group_session = GroupSession.query.get(session_id)

    if group_session:
        # For group sessions
        if group_session.mentor_id != current_user.id:
            flash('You do not have access to these analytics.', 'warning')
            return redirect(url_for('analytics.session_analytics'))

        session_obj = group_session
        is_group = True
        analytics = SessionAnalytics.query.filter_by(group_session_id=session_id).first()
        participants = GroupSessionParticipant.query.filter_by(session_id=session_id).all()
    else:
        # For individual sessions
        individual_session = Session.query.get_or_404(session_id)

        # Check if current user is a mentor for this session
        is_mentor = False
        for participant in individual_session.participants:
            if participant.user_id == current_user.id and participant.role == 'mentor':
                is_mentor = True
                break

        if not is_mentor:
            flash('You do not have access to these analytics.', 'warning')
            return redirect(url_for('analytics.session_analytics'))

        session_obj = individual_session
        is_group = False
        analytics = SessionAnalytics.query.filter_by(session_id=session_id).first()

        # Get mentee participants
        mentee_participants = []
        for participant in individual_session.participants:
            if participant.role == 'mentee':
                mentee_participants.append({
                    'user': User.query.get(participant.user_id),
                    'status': 'attended' if individual_session.status == 'completed' else 'registered'
                })
        participants = mentee_participants

    if not analytics:
        flash('No analytics data available for this session.', 'info')
        if is_group:
            return redirect(url_for('mentorship.group_session_detail', session_id=session_id))
        else:
            return redirect(url_for('sessions.session_detail', session_id=session_id))

    return render_template('analytics/session_details.html',
                          title='Session Details',
                          session=session_obj,
                          is_group=is_group,
                          analytics=analytics,
                          participants=participants)

# Progress Metrics Routes - Removed

# User Engagement Routes
@bp.route('/engagement-tracking')
@login_required
def engagement_tracking():
    """View user engagement tracking dashboard"""
    if not current_user.is_mentor:
        flash('Only mentors can access engagement tracking.', 'warning')
        return redirect(url_for('main.dashboard'))

    # Get mentees
    mentee_ids = [s.mentee_id for s in Session.query.filter_by(mentor_id=current_user.id).all()]
    mentee_ids = list(set(mentee_ids))  # Remove duplicates
    mentees = User.query.filter(User.id.in_(mentee_ids)).all()

    # Get engagement metrics for each mentee
    engagement_data = []
    for mentee in mentees:
        # Get last 30 days of engagement
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        engagement_records = UserEngagement.query.filter_by(
            user_id=mentee.id
        ).filter(
            UserEngagement.date >= thirty_days_ago.date()
        ).order_by(UserEngagement.date).all()

        if engagement_records:
            # Calculate average metrics
            avg_sessions = sum(r.sessions_attended for r in engagement_records) / len(engagement_records)
            avg_resources = sum(r.resources_viewed for r in engagement_records) / len(engagement_records)
            avg_time = sum(r.total_time_spent for r in engagement_records) / len(engagement_records)

            # Calculate engagement score (simple weighted average)
            engagement_score = (
                (avg_sessions * 0.4) +
                (avg_resources * 0.3) +
                (avg_time / 60 * 0.3)  # Convert minutes to hours
            ) / 0.1  # Scale to 0-100

            engagement_score = min(100, engagement_score)  # Cap at 100

            # Get activity trend
            activity_trend = []
            for record in engagement_records:
                activity = record.sessions_attended + record.resources_viewed + record.tasks_completed
                activity_trend.append({
                    'date': record.date.strftime('%Y-%m-%d'),
                    'activity': activity
                })

            engagement_data.append({
                'mentee': mentee,
                'avg_sessions': round(avg_sessions, 1),
                'avg_resources': round(avg_resources, 1),
                'avg_time': round(avg_time / 60, 1),  # Convert to hours
                'engagement_score': round(engagement_score, 1),
                'activity_trend': activity_trend
            })

    return render_template('analytics/engagement_tracking.html',
                          title='Engagement Tracking',
                          engagement_data=engagement_data)

# Success Rate Monitoring Routes
@bp.route('/success-rates')
@login_required
def success_rates():
    """View success rate monitoring dashboard"""
    if not current_user.is_mentor:
        flash('Only mentors can access success rate monitoring.', 'warning')
        return redirect(url_for('main.dashboard'))

    # Get completed sessions
    individual_sessions = Session.query.filter_by(
        mentor_id=current_user.id, status='completed').all()

    group_sessions = GroupSession.query.filter_by(
        mentor_id=current_user.id, status='completed').all()

    # Calculate session completion rate
    total_scheduled = Session.query.filter_by(mentor_id=current_user.id).count()
    total_scheduled += GroupSession.query.filter_by(mentor_id=current_user.id).count()

    total_completed = len(individual_sessions) + len(group_sessions)

    completion_rate = (total_completed / total_scheduled * 100) if total_scheduled > 0 else 0

    # Goal achievement rate calculation removed
    goal_achievement_rate = 0
    total_milestones = 0
    completed_milestones = 0

    # Calculate feedback satisfaction rate
    from app.models import SessionFeedback

    individual_feedback = SessionFeedback.query.filter(
        SessionFeedback.session_id.in_([s.id for s in individual_sessions])).all()

    group_feedback = SessionFeedback.query.filter(
        SessionFeedback.group_session_id.in_([s.id for s in group_sessions])).all()

    all_feedback = individual_feedback + group_feedback

    total_ratings = len(all_feedback)
    positive_ratings = sum(1 for f in all_feedback if f.rating >= 4)

    satisfaction_rate = (positive_ratings / total_ratings * 100) if total_ratings > 0 else 0

    # Calculate mentee retention rate
    # (Mentees who had more than one session)
    mentee_session_counts = {}

    for session in individual_sessions:
        mentee_session_counts[session.mentee_id] = mentee_session_counts.get(session.mentee_id, 0) + 1

    total_mentees = len(mentee_session_counts)
    retained_mentees = sum(1 for count in mentee_session_counts.values() if count > 1)

    retention_rate = (retained_mentees / total_mentees * 100) if total_mentees > 0 else 0

    return render_template('analytics/success_rates.html',
                          title='Success Rate Monitoring',
                          completion_rate=round(completion_rate, 1),
                          goal_achievement_rate=round(goal_achievement_rate, 1),
                          satisfaction_rate=round(satisfaction_rate, 1),
                          retention_rate=round(retention_rate, 1),
                          total_completed=total_completed,
                          total_scheduled=total_scheduled,
                          total_milestones=total_milestones,
                          completed_milestones=completed_milestones,
                          total_ratings=total_ratings,
                          positive_ratings=positive_ratings,
                          total_mentees=total_mentees,
                          retained_mentees=retained_mentees)

# ROI Calculations Routes
@bp.route('/roi-calculator')
@login_required
def roi_calculator():
    """View ROI calculator dashboard"""
    if not current_user.is_mentor:
        flash('Only mentors can access the ROI calculator.', 'warning')
        return redirect(url_for('main.dashboard'))

    # Get session data
    individual_sessions = Session.query.filter_by(
        mentor_id=current_user.id, status='completed').all()

    group_sessions = GroupSession.query.filter_by(
        mentor_id=current_user.id, status='completed').all()

    # Calculate total hours
    total_individual_hours = sum((s.end_time - s.scheduled_time).total_seconds() / 3600 for s in individual_sessions)

    total_group_hours = sum((s.end_time - s.scheduled_time).total_seconds() / 3600 for s in group_sessions)

    # Calculate total students
    total_individual_students = len(set(s.mentee_id for s in individual_sessions))

    total_group_students = 0
    for session in group_sessions:
        participants = GroupSessionParticipant.query.filter_by(session_id=session.id).count()
        total_group_students += participants

    # Default hourly rates
    default_individual_rate = 50  # $50/hour for individual sessions
    default_group_rate = 30  # $30/hour per student for group sessions

    # Calculate potential earnings
    potential_individual_earnings = total_individual_hours * default_individual_rate
    potential_group_earnings = total_group_hours * default_group_rate * (total_group_students / len(group_sessions) if group_sessions else 0)

    # Calculate time investment
    # Assume 1 hour of prep for every 2 hours of sessions
    prep_time = (total_individual_hours + total_group_hours) / 2

    # Assume 30 minutes of admin time per session
    admin_time = (len(individual_sessions) + len(group_sessions)) * 0.5

    total_time_investment = total_individual_hours + total_group_hours + prep_time + admin_time

    # Calculate ROI
    total_potential_earnings = potential_individual_earnings + potential_group_earnings

    # Assume opportunity cost of $25/hour
    opportunity_cost = total_time_investment * 25

    roi = ((total_potential_earnings - opportunity_cost) / opportunity_cost * 100) if opportunity_cost > 0 else 0

    return render_template('analytics/roi_calculator.html',
                          title='ROI Calculator',
                          total_individual_hours=round(total_individual_hours, 1),
                          total_group_hours=round(total_group_hours, 1),
                          total_individual_students=total_individual_students,
                          total_group_students=total_group_students,
                          default_individual_rate=default_individual_rate,
                          default_group_rate=default_group_rate,
                          potential_individual_earnings=round(potential_individual_earnings, 2),
                          potential_group_earnings=round(potential_group_earnings, 2),
                          prep_time=round(prep_time, 1),
                          admin_time=round(admin_time, 1),
                          total_time_investment=round(total_time_investment, 1),
                          total_potential_earnings=round(total_potential_earnings, 2),
                          opportunity_cost=round(opportunity_cost, 2),
                          roi=round(roi, 1))

@bp.route('/calculate-roi', methods=['POST'])
@login_required
def calculate_roi():
    """Calculate ROI based on user inputs"""
    if not current_user.is_mentor:
        return jsonify({'success': False, 'message': 'Only mentors can access the ROI calculator.'})

    # Get form data
    individual_rate = float(request.form.get('individual_rate', 50))
    group_rate = float(request.form.get('group_rate', 30))
    prep_ratio = float(request.form.get('prep_ratio', 0.5))  # Prep time as ratio of session time
    admin_time = float(request.form.get('admin_time', 0.5))  # Hours per session
    opportunity_cost = float(request.form.get('opportunity_cost', 25))  # Hourly rate

    # Get session data
    individual_sessions = Session.query.filter_by(
        mentor_id=current_user.id, status='completed').all()

    group_sessions = GroupSession.query.filter_by(
        mentor_id=current_user.id, status='completed').all()

    # Calculate total hours
    total_individual_hours = sum((s.end_time - s.scheduled_time).total_seconds() / 3600 for s in individual_sessions)

    total_group_hours = sum((s.end_time - s.scheduled_time).total_seconds() / 3600 for s in group_sessions)

    # Calculate average group size
    total_participants = 0
    for session in group_sessions:
        participants = GroupSessionParticipant.query.filter_by(session_id=session.id).count()
        total_participants += participants

    avg_group_size = total_participants / len(group_sessions) if group_sessions else 0

    # Calculate potential earnings
    potential_individual_earnings = total_individual_hours * individual_rate
    potential_group_earnings = total_group_hours * group_rate * avg_group_size

    # Calculate time investment
    prep_time = (total_individual_hours + total_group_hours) * prep_ratio
    total_admin_time = (len(individual_sessions) + len(group_sessions)) * admin_time

    total_time_investment = total_individual_hours + total_group_hours + prep_time + total_admin_time

    # Calculate ROI
    total_potential_earnings = potential_individual_earnings + potential_group_earnings
    total_opportunity_cost = total_time_investment * opportunity_cost

    roi = ((total_potential_earnings - total_opportunity_cost) / total_opportunity_cost * 100) if total_opportunity_cost > 0 else 0

    # Calculate hourly rate
    effective_hourly_rate = total_potential_earnings / total_time_investment if total_time_investment > 0 else 0

    return jsonify({
        'success': True,
        'potential_individual_earnings': round(potential_individual_earnings, 2),
        'potential_group_earnings': round(potential_group_earnings, 2),
        'total_potential_earnings': round(total_potential_earnings, 2),
        'prep_time': round(prep_time, 1),
        'admin_time': round(total_admin_time, 1),
        'total_time_investment': round(total_time_investment, 1),
        'opportunity_cost': round(total_opportunity_cost, 2),
        'roi': round(roi, 1),
        'effective_hourly_rate': round(effective_hourly_rate, 2)
    })

# Performance Reports Routes
@bp.route('/performance-reports')
@login_required
def performance_reports():
    """View performance reports dashboard"""
    if not current_user.is_mentor:
        flash('Only mentors can access performance reports.', 'warning')
        return redirect(url_for('main.dashboard'))

    # Get date range (default: last 6 months)
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=180)

    date_range = request.args.get('range', 'last_6_months')

    if date_range == 'last_month':
        start_date = end_date - timedelta(days=30)
    elif date_range == 'last_3_months':
        start_date = end_date - timedelta(days=90)
    elif date_range == 'last_year':
        start_date = end_date - timedelta(days=365)
    elif date_range == 'all_time':
        start_date = datetime(2000, 1, 1).date()  # Arbitrary early date

    # Get sessions in date range
    individual_sessions = Session.query.filter(
        Session.mentor_id == current_user.id,
        Session.scheduled_time >= start_date,
        Session.scheduled_time <= end_date
    ).all()

    group_sessions = GroupSession.query.filter(
        GroupSession.mentor_id == current_user.id,
        GroupSession.scheduled_time >= start_date,
        GroupSession.scheduled_time <= end_date
    ).all()

    # Calculate session metrics
    total_sessions = len(individual_sessions) + len(group_sessions)
    completed_sessions = sum(1 for s in individual_sessions if s.status == 'completed')
    completed_sessions += sum(1 for s in group_sessions if s.status == 'completed')

    completion_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0

    # Calculate student metrics
    individual_students = set(s.mentee_id for s in individual_sessions)

    group_students = set()
    for session in group_sessions:
        participants = GroupSessionParticipant.query.filter_by(session_id=session.id).all()
        for participant in participants:
            group_students.add(participant.user_id)

    total_students = len(individual_students.union(group_students))

    # Calculate feedback metrics
    from app.models import SessionFeedback

    individual_feedback = SessionFeedback.query.filter(
        SessionFeedback.session_id.in_([s.id for s in individual_sessions])).all()

    group_feedback = SessionFeedback.query.filter(
        SessionFeedback.group_session_id.in_([s.id for s in group_sessions])).all()

    all_feedback = individual_feedback + group_feedback

    avg_rating = sum(f.rating for f in all_feedback) / len(all_feedback) if all_feedback else 0

    # Generate monthly trend data
    monthly_data = {}

    for session in individual_sessions + group_sessions:
        month_key = session.scheduled_time.strftime('%Y-%m')

        if month_key not in monthly_data:
            monthly_data[month_key] = {
                'sessions': 0,
                'completed': 0,
                'students': set(),
                'hours': 0
            }

        monthly_data[month_key]['sessions'] += 1

        if session.status == 'completed':
            monthly_data[month_key]['completed'] += 1

            # Add hours
            hours = (session.end_time - session.scheduled_time).total_seconds() / 3600
            monthly_data[month_key]['hours'] += hours

        # Add students
        if hasattr(session, 'mentee_id'):  # Individual session
            monthly_data[month_key]['students'].add(session.mentee_id)
        else:  # Group session
            participants = GroupSessionParticipant.query.filter_by(session_id=session.id).all()
            for participant in participants:
                monthly_data[month_key]['students'].add(participant.user_id)

    # Convert to lists for the template
    months = sorted(monthly_data.keys())
    sessions_trend = [monthly_data[m]['sessions'] for m in months]
    completion_trend = [monthly_data[m]['completed'] / monthly_data[m]['sessions'] * 100 if monthly_data[m]['sessions'] > 0 else 0 for m in months]
    students_trend = [len(monthly_data[m]['students']) for m in months]
    hours_trend = [round(monthly_data[m]['hours'], 1) for m in months]

    # Format months for display
    display_months = [datetime.strptime(m, '%Y-%m').strftime('%b %Y') for m in months]

    return render_template('analytics/performance_reports.html',
                          title='Performance Reports',
                          date_range=date_range,
                          total_sessions=total_sessions,
                          completed_sessions=completed_sessions,
                          completion_rate=round(completion_rate, 1),
                          total_students=total_students,
                          avg_rating=round(avg_rating, 1),
                          months=display_months,
                          sessions_trend=sessions_trend,
                          completion_trend=[round(r, 1) for r in completion_trend],
                          students_trend=students_trend,
                          hours_trend=hours_trend)

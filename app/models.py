from datetime import datetime, timedelta
from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import json
import pytz
from sqlalchemy.ext.mutable import MutableDict, MutableList

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='mentee')  # admin, mentor, mentee
    is_verified = db.Column(db.Boolean, default=False)
    verification_badges = db.Column(db.JSON)  # Store badge information
    points = db.Column(db.Integer, default=0)  # For gamification
    achievements = db.Column(db.JSON)  # Store achievement badges
    # Profile Information
    bio = db.Column(db.Text)
    skills = db.Column(db.String(200))
    interests = db.Column(db.String(200))
    education = db.Column(db.JSON)  # Store education history
    experience = db.Column(db.JSON)  # Store work experience
    department = db.Column(db.String(100))
    year = db.Column(db.String(20))
    availability = db.Column(db.Text)
    profile_pic = db.Column(db.String(100))
    calendar_connected = db.Column(db.Boolean, default=False)
    github_username = db.Column(db.String(100))
    drive_connected = db.Column(db.Boolean, default=False)
    timezone = db.Column(db.String(50), default='UTC')
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    # Session relationships are now handled through SessionParticipant
    session_participations = db.relationship('SessionParticipant', backref='user', lazy='dynamic')
    messages_sent = db.relationship('Message', foreign_keys='Message.sender_id', backref='author', lazy='dynamic')
    messages_received = db.relationship('Message', foreign_keys='Message.recipient_id', backref='recipient', lazy='dynamic')
    reviews_given = db.relationship('Review', foreign_keys='Review.reviewer_id', backref='reviewer', lazy='dynamic')
    reviews_received = db.relationship('Review', foreign_keys='Review.reviewee_id', backref='reviewee', lazy='dynamic')

    # Task relationships
    tasks_created = db.relationship('Task', foreign_keys='Task.mentor_id', backref='mentor', lazy='dynamic')
    tasks_assigned = db.relationship('Task', foreign_keys='Task.mentee_id', backref='mentee', lazy='dynamic')

    # Resource Library relationship
    resource_libraries = db.relationship('ResourceLibrary', backref=db.backref('creator', overlaps='created_libraries'), lazy='dynamic')


    # Learning path relationships
    learning_paths_created = db.relationship('LearningPath', backref='creator', lazy='dynamic')
    assessment_results = db.relationship('AssessmentResult', backref='user', lazy='dynamic')
    # Progress tracking relationships removed

    @property
    def is_mentor(self):
        return self.role == 'mentor'

    @property
    def is_mentee(self):
        return self.role == 'mentee'

    @property
    def is_admin(self):
        return self.role == 'admin'

    # Forum relationships
    forum_threads = db.relationship('ForumThread', backref='author', lazy='dynamic')
    forum_replies = db.relationship('ForumReply', backref='author', lazy='dynamic')

    # Notification relationship
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')

    # Announcement relationship
    announcements = db.relationship('Announcement', backref='author', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class SessionParticipant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    role = db.Column(db.String(20))  # mentor, mentee
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, declined

class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    topic = db.Column(db.String(140))
    description = db.Column(db.Text)
    scheduled_time = db.Column(db.DateTime)
    duration = db.Column(db.Integer)  # in minutes
    status = db.Column(db.String(20))  # scheduled, active, completed, cancelled
    meeting_link = db.Column(db.String(200))
    session_type = db.Column(db.String(20), default='individual')  # individual, group
    max_participants = db.Column(db.Integer, default=2)  # 2 for individual, more for group
    reviews = db.relationship('Review', backref='session', lazy='dynamic')
    participants = db.relationship('SessionParticipant', backref='session', lazy='dynamic')

    creator = db.relationship('User', foreign_keys=[creator_id], backref='created_sessions')

    def add_participant(self, user, role='mentee'):
        if self.participants.count() >= self.max_participants:
            return False, 'Session is full'
        participant = SessionParticipant(session_id=self.id, user_id=user.id, role=role)
        db.session.add(participant)
        return True, participant

    def remove_participant(self, user):
        participant = self.participants.filter_by(user_id=user.id).first()
        if participant:
            db.session.delete(participant)
            return True
        return False

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    body = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    # Property to handle attachment data without requiring the column
    @property
    def attachment(self):
        return None

    @attachment.setter
    def attachment(self, value):
        # This is a no-op since we don't have the column yet
        pass

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    reviewee_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'))
    rating = db.Column(db.Integer)  # 1-5
    comment = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    mentor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    mentee_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    due_date = db.Column(db.DateTime)
    status = db.Column(db.String(20))  # assigned, in_progress, completed
    attachments = db.Column(db.JSON)  # Store file paths
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LearningPath(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    skills = db.Column(db.String(200))
    resources = db.Column(db.JSON)  # Store learning materials
    milestones = db.Column(db.JSON)  # Store milestone information
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Progress tracking relationship removed

class SkillAssessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    skill_category = db.Column(db.String(100))
    questions = db.Column(db.JSON)  # Store quiz questions
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AssessmentResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey('skill_assessment.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    score = db.Column(db.Float)
    answers = db.Column(db.JSON)  # Store user's answers
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

class ForumThread(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    category = db.Column(db.String(100))
    tags = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_pinned = db.Column(db.Boolean, default=False)
    views = db.Column(db.Integer, default=0)

class ForumReply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('forum_thread.id'))
    content = db.Column(db.Text)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_solution = db.Column(db.Boolean, default=False)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    type = db.Column(db.String(50))  # message, session, task, forum
    content = db.Column(db.Text)
    link = db.Column(db.String(200))  # Related URL
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    category = db.Column(db.String(50))  # event, update, news
    priority = db.Column(db.String(20))  # normal, important, urgent
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

# New models for mentorship features

class GroupSession(db.Model):
    """Model for group mentoring sessions"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    mentor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    max_participants = db.Column(db.Integer, default=10)
    scheduled_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.String(20))  # scheduled, in_progress, completed, cancelled
    meeting_link = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_recurring = db.Column(db.Boolean, default=False)
    recurrence_pattern = db.Column(db.String(50))  # weekly, bi-weekly, monthly
    tags = db.Column(db.String(200))

    # Relationships
    participants = db.relationship('GroupSessionParticipant', backref='session', lazy='dynamic')
    resources = db.relationship('GroupSessionResource', backref='session', lazy='dynamic')
    notes = db.relationship('SessionNote', backref='group_session', lazy='dynamic')
    recordings = db.relationship('SessionRecording', backref='group_session', lazy='dynamic')
    mentor = db.relationship('User', foreign_keys=[mentor_id])

class GroupSessionParticipant(db.Model):
    """Model for participants in group sessions"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('group_session.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20))  # registered, attended, no_show
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    feedback_submitted = db.Column(db.Boolean, default=False)

    # Relationship to user
    user = db.relationship('User', backref=db.backref('group_sessions', lazy='dynamic'))

class ResourceLibrary(db.Model):
    """Model for knowledge base/resource library"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    category = db.Column(db.String(100))
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    is_public = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    tags = db.Column(db.String(200))

    # Relationships
    resources = db.relationship('Resource', backref='library', lazy='dynamic')
    # creator relationship is defined in the User model with backref

class Resource(db.Model):
    """Model for individual resources in the library"""
    id = db.Column(db.Integer, primary_key=True)
    library_id = db.Column(db.Integer, db.ForeignKey('resource_library.id'))
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    resource_type = db.Column(db.String(50))  # document, video, link, code_snippet
    content = db.Column(db.Text)  # For direct content or links
    file_path = db.Column(db.String(255))  # For uploaded files
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    views = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)

    # Relationships
    creator = db.relationship('User', backref='created_resources')
    group_sessions = db.relationship('GroupSessionResource', backref='resource', lazy='dynamic')

class GroupSessionResource(db.Model):
    """Association model between group sessions and resources"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('group_session.id'))
    resource_id = db.Column(db.Integer, db.ForeignKey('resource.id'))
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    added_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    # Relationship to user who added the resource
    added_by = db.relationship('User', backref='added_session_resources')

class SessionNote(db.Model):
    """Model for meeting notes"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=True)
    group_session_id = db.Column(db.Integer, db.ForeignKey('group_session.id'), nullable=True)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    content = db.Column(db.Text)
    is_private = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    author = db.relationship('User', backref='session_notes')
    individual_session = db.relationship('Session', backref='notes', foreign_keys=[session_id])

class SessionRecording(db.Model):
    """Model for session recordings"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=True)
    group_session_id = db.Column(db.Integer, db.ForeignKey('group_session.id'), nullable=True)
    title = db.Column(db.String(200))
    file_path = db.Column(db.String(255))
    duration = db.Column(db.Integer)  # in seconds
    recorded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_public = db.Column(db.Boolean, default=False)

    # Relationships
    recorded_by = db.relationship('User', backref='recorded_sessions')
    individual_session = db.relationship('Session', backref='recordings', foreign_keys=[session_id])

class SessionFile(db.Model):
    """Model for session files (study materials)"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'))
    title = db.Column(db.String(200))
    description = db.Column(db.Text, nullable=True)
    file_path = db.Column(db.String(255))
    file_type = db.Column(db.String(50))  # e.g., pdf, doc, ppt, etc.
    file_size = db.Column(db.Integer)  # in bytes
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    session = db.relationship('Session', backref='files')
    uploaded_by = db.relationship('User', backref='uploaded_files')

class VideoCallRequest(db.Model):
    """Model for video call requests"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'))
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(20), default='pending')  # pending, accepted, declined, expired
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = db.Column(db.DateTime)

    # Relationships
    session = db.relationship('Session', backref='video_call_requests')
    requester = db.relationship('User', foreign_keys=[requester_id], backref='sent_video_requests')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_video_requests')

# Progress Tracker model removed

# Progress Milestone model removed

class MentorshipAgreement(db.Model):
    """Model for mentorship agreements/contracts"""
    id = db.Column(db.Integer, primary_key=True)
    mentor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    mentee_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)
    goals = db.Column(db.Text)
    expectations = db.Column(db.Text)
    meeting_frequency = db.Column(db.String(100))
    communication_preferences = db.Column(db.String(200))
    confidentiality_terms = db.Column(db.Text)
    termination_terms = db.Column(db.Text)
    mentor_signed = db.Column(db.Boolean, default=False)
    mentee_signed = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20))  # draft, active, completed, terminated
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    mentor = db.relationship('User', foreign_keys=[mentor_id], backref='mentor_agreements')
    mentee = db.relationship('User', foreign_keys=[mentee_id], backref='mentee_agreements')

class SessionFeedback(db.Model):
    """Model for session feedback templates and responses"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=True)
    group_session_id = db.Column(db.Integer, db.ForeignKey('group_session.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Who provided the feedback
    feedback_type = db.Column(db.String(20))  # mentor_to_mentee, mentee_to_mentor, participant_to_session
    rating = db.Column(db.Integer)  # 1-5 overall rating
    responses = db.Column(db.JSON)  # Structured feedback responses
    comments = db.Column(db.Text)  # Additional comments
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='session_feedback')
    individual_session = db.relationship('Session', backref='feedback', foreign_keys=[session_id])
    group_session = db.relationship('GroupSession', backref='feedback', foreign_keys=[group_session_id])

class MentorAvailability(db.Model):
    """Model for mentor availability management"""
    id = db.Column(db.Integer, primary_key=True)
    mentor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    day_of_week = db.Column(db.Integer)  # 0-6 (Monday-Sunday)
    start_time = db.Column(db.Time)
    end_time = db.Column(db.Time)
    timezone = db.Column(db.String(50), default='UTC')
    is_recurring = db.Column(db.Boolean, default=True)
    specific_date = db.Column(db.Date, nullable=True)  # For non-recurring availability
    status = db.Column(db.String(20), default='active')  # active, blocked

    # Relationship
    mentor = db.relationship('User', backref='availability_slots')

class RecurringSession(db.Model):
    """Model for recurring sessions"""
    id = db.Column(db.Integer, primary_key=True)
    original_session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=True)
    group_session_id = db.Column(db.Integer, db.ForeignKey('group_session.id'), nullable=True)
    frequency = db.Column(db.String(20))  # weekly, bi-weekly, monthly
    day_of_week = db.Column(db.Integer, nullable=True)  # 0-6 (Monday-Sunday)
    week_of_month = db.Column(db.Integer, nullable=True)  # 1-5, for monthly recurrence
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date, nullable=True)
    time = db.Column(db.Time)
    duration = db.Column(db.Integer)  # in minutes
    timezone = db.Column(db.String(50), default='UTC')
    status = db.Column(db.String(20), default='active')  # active, paused, completed

    # Relationships
    individual_session = db.relationship('Session', foreign_keys=[original_session_id], backref='recurring_pattern')
    group_session = db.relationship('GroupSession', foreign_keys=[group_session_id], backref='recurring_pattern')
    instances = db.relationship('Session', backref='recurring_parent')

class CancellationPolicy(db.Model):
    """Model for cancellation and rescheduling policies"""
    id = db.Column(db.Integer, primary_key=True)
    mentor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    notice_period = db.Column(db.Integer)  # Hours of notice required
    penalty_type = db.Column(db.String(20))  # none, partial_charge, full_charge
    penalty_amount = db.Column(db.Float, nullable=True)  # For partial charges
    max_reschedules = db.Column(db.Integer, default=3)  # Maximum number of reschedules allowed
    policy_text = db.Column(db.Text)  # Full policy description
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    mentor = db.relationship('User', backref='cancellation_policy')

class SessionAnalytics(db.Model):
    """Model for session analytics"""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id'), nullable=True)
    group_session_id = db.Column(db.Integer, db.ForeignKey('group_session.id'), nullable=True)
    duration_actual = db.Column(db.Integer)  # Actual duration in minutes
    participant_count = db.Column(db.Integer, default=1)  # For group sessions
    topics_covered = db.Column(db.JSON)  # List of topics
    resources_shared = db.Column(db.Integer, default=0)  # Count of resources shared
    engagement_score = db.Column(db.Float)  # Calculated engagement metric
    technical_issues = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    individual_session = db.relationship('Session', backref='analytics', foreign_keys=[session_id])
    group_session = db.relationship('GroupSession', backref='analytics', foreign_keys=[group_session_id])

class UserEngagement(db.Model):
    """Model for tracking user engagement"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    date = db.Column(db.Date, default=datetime.utcnow().date)
    sessions_attended = db.Column(db.Integer, default=0)
    sessions_hosted = db.Column(db.Integer, default=0)
    resources_viewed = db.Column(db.Integer, default=0)
    resources_created = db.Column(db.Integer, default=0)
    forum_posts = db.Column(db.Integer, default=0)
    messages_sent = db.Column(db.Integer, default=0)
    tasks_completed = db.Column(db.Integer, default=0)
    login_count = db.Column(db.Integer, default=0)
    total_time_spent = db.Column(db.Integer, default=0)  # in minutes

    # Relationship
    user = db.relationship('User', backref='engagement_metrics')

class Badge(db.Model):
    """Model for skill badges and achievements"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.Text)
    badge_type = db.Column(db.String(20))  # skill, achievement, level
    icon = db.Column(db.String(200))  # Path to badge icon
    criteria = db.Column(db.JSON)  # Requirements to earn the badge
    xp_value = db.Column(db.Integer, default=0)  # XP awarded for earning
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    users = db.relationship('UserBadge', backref='badge', lazy='dynamic')

class UserBadge(db.Model):
    """Association model between users and badges"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    badge_id = db.Column(db.Integer, db.ForeignKey('badge.id'))
    awarded_date = db.Column(db.DateTime, default=datetime.utcnow)
    progress = db.Column(db.Float, default=0.0)  # For partially completed badges
    is_featured = db.Column(db.Boolean, default=False)  # For displaying on profile

    # Relationship
    user = db.relationship('User', backref='badges')

class Leaderboard(db.Model):
    """Model for leaderboards"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.Text)
    leaderboard_type = db.Column(db.String(20))  # mentors, mentees, overall
    metric = db.Column(db.String(50))  # points, sessions, ratings
    time_period = db.Column(db.String(20))  # weekly, monthly, all_time
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    entries = db.relationship('LeaderboardEntry', backref='leaderboard', lazy='dynamic')

class LeaderboardEntry(db.Model):
    """Model for leaderboard entries"""
    id = db.Column(db.Integer, primary_key=True)
    leaderboard_id = db.Column(db.Integer, db.ForeignKey('leaderboard.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    score = db.Column(db.Float)
    rank = db.Column(db.Integer)
    previous_rank = db.Column(db.Integer, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = db.relationship('User', backref='leaderboard_entries')

class SystemHealth(db.Model):
    """Model for system health monitoring"""
    id = db.Column(db.Integer, primary_key=True)
    check_time = db.Column(db.DateTime, default=datetime.utcnow)
    component = db.Column(db.String(100))  # database, storage, video, etc.
    status = db.Column(db.String(20))  # healthy, warning, error
    response_time = db.Column(db.Float)  # in milliseconds
    error_message = db.Column(db.Text, nullable=True)
    details = db.Column(db.JSON, nullable=True)  # Additional diagnostic info

class SystemBackup(db.Model):
    """Model for system backups"""
    id = db.Column(db.Integer, primary_key=True)
    backup_time = db.Column(db.DateTime, default=datetime.utcnow)
    backup_type = db.Column(db.String(20))  # full, incremental
    file_path = db.Column(db.String(255))
    file_size = db.Column(db.Integer)  # in bytes
    status = db.Column(db.String(20))  # completed, failed
    retention_period = db.Column(db.Integer)  # days to keep backup
    notes = db.Column(db.Text, nullable=True)


# Gamification Models already defined above
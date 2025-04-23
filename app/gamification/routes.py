from flask import render_template, request, jsonify
from flask_login import current_user, login_required
from app.gamification import bp
from app.models import Badge, UserBadge, Leaderboard, LeaderboardEntry
import random

# Gamification Dashboard
@bp.route('/')
@login_required
def dashboard():
    """View gamification dashboard"""
    # Get user's badges
    user_badges = UserBadge.query.filter_by(user_id=current_user.id).all()

    # Get all badges
    all_badges = Badge.query.all()
    earned_badge_ids = [ub.badge_id for ub in user_badges]
    available_badges = [badge for badge in all_badges if badge.id not in earned_badge_ids]

    # Get leaderboard entries
    leaderboards = Leaderboard.query.filter_by(is_active=True).all()

    # Calculate user's total XP and level
    total_xp = sum(badge.badge.xp_value for badge in user_badges)
    xp_per_level = 1000  # Base XP needed per level
    level = 1 + (total_xp // xp_per_level)
    xp_for_next_level = (level + 1) * xp_per_level
    progress_to_next_level = ((total_xp % xp_per_level) / xp_per_level) * 100

    # Get recent activity
    recent_activity = []

    # Add badge awards to activity
    for badge in user_badges:
        recent_activity.append({
            'type': 'badge',
            'title': f"Earned the {badge.badge.name} badge",
            'description': badge.badge.description,
            'date': badge.awarded_date,
            'icon': 'bi-award-fill',
            'color': 'text-warning'
        })

    # Sort activity by date
    recent_activity.sort(key=lambda x: x['date'], reverse=True)

    return render_template('gamification/dashboard.html',
                          title='Gamification Dashboard',
                          user_badges=user_badges,
                          level=level,
                          progress_to_next_level=progress_to_next_level,
                          available_badges=available_badges,
                          leaderboards=leaderboards,
                          recent_activity=recent_activity[:20],  # Limit to 20 most recent activities
                          total_xp=total_xp,
                          xp_for_next_level=xp_for_next_level)

# Badges Routes
@bp.route('/badges')
@login_required
def badges():
    """View badges"""
    # Get user's badges
    user_badges = UserBadge.query.filter_by(user_id=current_user.id).all()
    earned_badge_ids = [ub.badge_id for ub in user_badges]

    # Get all badges
    all_badges = Badge.query.all()

    # Separate badges into categories
    badge_categories = {}

    for badge in all_badges:
        if badge.category not in badge_categories:
            badge_categories[badge.category] = []

        badge_data = {
            'badge': badge,
            'earned': badge.id in earned_badge_ids,
            'user_badge': next((ub for ub in user_badges if ub.badge_id == badge.id), None)
        }

        badge_categories[badge.category].append(badge_data)

    return render_template('gamification/badges.html',
                          title='Badges',
                          badge_categories=badge_categories,
                          user_badges=user_badges)

@bp.route('/badge/<int:badge_id>')
@login_required
def badge_detail(badge_id):
    """View badge details"""
    badge = Badge.query.get_or_404(badge_id)
    user_badge = UserBadge.query.filter_by(user_id=current_user.id, badge_id=badge_id).first()

    # Get users who earned this badge
    badge_holders = UserBadge.query.filter_by(badge_id=badge_id).all()

    return render_template('gamification/badge_detail.html',
                          title=f'Badge: {badge.name}',
                          badge=badge,
                          user_badge=user_badge,
                          badge_holders=badge_holders)

# Achievements Routes
@bp.route('/achievements')
@login_required
def achievements():
    """View achievements"""
    # Define achievement categories
    achievement_categories = {
        'Learning': [
            {
                'achievement': {
                    'id': 1,
                    'name': 'First Steps',
                    'description': 'Complete your first learning path',
                    'xp_reward': 100,
                    'icon': 'bi-mortarboard-fill',
                    'progress_type': 'count'
                },
                'earned': False
            },
            {
                'achievement': {
                    'id': 2,
                    'name': 'Knowledge Seeker',
                    'description': 'Complete 5 learning paths',
                    'xp_reward': 500,
                    'icon': 'bi-book-fill',
                    'progress_type': 'count'
                },
                'earned': False
            },
            {
                'achievement': {
                    'id': 3,
                    'name': 'Master Learner',
                    'description': 'Complete 10 learning paths',
                    'xp_reward': 1000,
                    'icon': 'bi-award-fill',
                    'progress_type': 'count'
                },
                'earned': False
            }
        ],
        'Mentorship': [
            {
                'achievement': {
                    'id': 4,
                    'name': 'Mentor Connection',
                    'description': 'Have your first mentorship session',
                    'xp_reward': 100,
                    'icon': 'bi-people-fill',
                    'progress_type': 'count'
                },
                'earned': False
            },
            {
                'achievement': {
                    'id': 5,
                    'name': 'Active Mentor',
                    'description': 'Complete 10 mentorship sessions',
                    'xp_reward': 500,
                    'icon': 'bi-star-fill',
                    'progress_type': 'count'
                },
                'earned': False
            },
            {
                'achievement': {
                    'id': 6,
                    'name': 'Mentorship Pro',
                    'description': 'Maintain a 4.5+ rating as a mentor',
                    'xp_reward': 1000,
                    'icon': 'bi-trophy-fill',
                    'progress_type': 'rating'
                },
                'earned': False
            }
        ],
        'Community': [
            {
                'achievement': {
                    'id': 7,
                    'name': 'Community Helper',
                    'description': 'Answer 5 forum questions',
                    'xp_reward': 100,
                    'icon': 'bi-chat-dots-fill',
                    'progress_type': 'count'
                },
                'earned': False
            },
            {
                'achievement': {
                    'id': 8,
                    'name': 'Forum Expert',
                    'description': 'Have 10 answers marked as solutions',
                    'xp_reward': 500,
                    'icon': 'bi-check-circle-fill',
                    'progress_type': 'count'
                },
                'earned': False
            },
            {
                'achievement': {
                    'id': 9,
                    'name': 'Community Leader',
                    'description': 'Reach 1000 reputation points',
                    'xp_reward': 1000,
                    'icon': 'bi-person-fill',
                    'progress_type': 'points'
                },
                'earned': False
            }
        ]
    }
    
    # Get user's earned achievements (placeholder for now)
    user_achievements = []
    
    return render_template('gamification/achievements.html',
                          title='Achievements',
                          achievement_categories=achievement_categories,
                          user_achievements=user_achievements)

@bp.route('/achievement/<int:achievement_id>')
@login_required
def achievement_detail(achievement_id):
    """View achievement details"""
    # For now, we'll just show a placeholder page
    return render_template('gamification/achievement_detail.html',
                          title='Achievement Details')

# Leaderboard Routes
@bp.route('/leaderboards')
@login_required
def leaderboards():
    """View leaderboards"""
    # Get all leaderboards
    all_leaderboards = Leaderboard.query.all()

    # Get entries for each leaderboard
    leaderboard_data = {}

    for leaderboard in all_leaderboards:
        entries = LeaderboardEntry.query.filter_by(
            leaderboard_id=leaderboard.id).order_by(LeaderboardEntry.score.desc()).all()

        # Find current user's rank
        user_rank = next((i + 1 for i, entry in enumerate(entries) if entry.user_id == current_user.id), None)

        leaderboard_data[leaderboard.id] = {
            'leaderboard': leaderboard,
            'entries': entries,
            'user_rank': user_rank
        }

    return render_template('gamification/leaderboards.html',
                          title='Leaderboards',
                          leaderboard_data=leaderboard_data)

@bp.route('/leaderboard/<int:leaderboard_id>')
@login_required
def leaderboard_detail(leaderboard_id):
    """View leaderboard details"""
    leaderboard = Leaderboard.query.get_or_404(leaderboard_id)

    # Get entries for this leaderboard
    entries = LeaderboardEntry.query.filter_by(
        leaderboard_id=leaderboard_id).order_by(LeaderboardEntry.score.desc()).all()

    # Find current user's entry and rank
    user_entry = LeaderboardEntry.query.filter_by(
        leaderboard_id=leaderboard_id, user_id=current_user.id).first()

    user_rank = next((i + 1 for i, entry in enumerate(entries) if entry.user_id == current_user.id), None)

    return render_template('gamification/leaderboard_detail.html',
                          title=f'Leaderboard: {leaderboard.name}',
                          leaderboard=leaderboard,
                          entries=entries,
                          user_entry=user_entry,
                          user_rank=user_rank)

# Rewards Routes
@bp.route('/rewards')
@login_required
def rewards():
    """View rewards"""
    # For now, we'll just show a placeholder page
    return render_template('gamification/rewards.html',
                          title='Rewards',
                          available_points=100)

@bp.route('/reward/<int:reward_id>')
@login_required
def reward_detail(reward_id):
    """View reward details"""
    # For now, we'll just show a placeholder page
    return render_template('gamification/reward_detail.html',
                          title='Reward Details',
                          available_points=100,
                          can_afford=True)

# API Routes
@bp.route('/api/check-achievements', methods=['POST'])
@login_required
def check_achievements():
    """Check if user has earned any new achievements"""
    # This would be called via AJAX after certain actions
    # For demo purposes, we'll return a random achievement

    if random.random() < 0.3:  # 30% chance
        # Simulate a new achievement
        achievement = {
            'name': 'Active Participant',
            'description': 'Participated in platform activities',
            'xp_reward': 50,
            'icon': 'bi-trophy-fill'
        }

        return jsonify({
            'success': True,
            'achievement': achievement
        })

    return jsonify({'success': False})

@bp.route('/api/award-xp', methods=['POST'])
@login_required
def award_xp():
    """Award XP to user"""
    data = request.get_json()

    points = data.get('points', 0)
    description = data.get('description', 'XP awarded')

    if points <= 0:
        return jsonify({'success': False, 'message': 'Points must be greater than 0'})

    # Simulate awarding XP
    # In a real implementation, this would store the XP in the database

    # Calculate level based on a simple formula
    total_xp = 100  # Simulated total XP
    level = 1
    xp_for_next_level = 100
    progress_to_next_level = 50  # Simulated progress

    return jsonify({
        'success': True,
        'points_awarded': points,
        'total_xp': total_xp,
        'level': level,
        'progress_to_next_level': progress_to_next_level,
        'xp_for_next_level': xp_for_next_level
    })

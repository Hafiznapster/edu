from flask import Blueprint

bp = Blueprint('gamification', __name__, url_prefix='/gamification')

from app.gamification import routes

from flask import Blueprint

bp = Blueprint('sessions', __name__, url_prefix='/sessions')

from app.sessions import routes
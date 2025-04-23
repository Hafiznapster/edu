from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_socketio import SocketIO
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from config import Config
import os
import markupsafe

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
login.login_view = 'auth.login'
socketio = SocketIO(async_mode='eventlet', ping_timeout=60, ping_interval=25, logger=True, engineio_logger=True)
csrf = CSRFProtect()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", ping_timeout=60, ping_interval=25, max_http_buffer_size=10e6, async_mode='threading')
    csrf.init_app(app)

    # Session handling is managed by Flask-Login

    # Add cache control for static files
    @app.route('/static/<path:filename>')
    def serve_static(filename):
        cache_timeout = 31536000  # 1 year in seconds
        # Replace backslashes with forward slashes for Windows compatibility
        filename = filename.replace('\\', '/')
        return send_from_directory(app.static_folder, filename,
                                 cache_timeout=cache_timeout,
                                 conditional=True)

    # Add a dedicated route for PDF files
    @app.route('/view-pdf/<path:filename>')
    def view_pdf(filename):
        # Replace backslashes with forward slashes for Windows compatibility
        filename = filename.replace('\\', '/')
        # Determine the directory based on the filename structure
        if filename.startswith('uploads/'):
            # The filename already includes the 'uploads' directory
            directory = os.path.join(app.static_folder, os.path.dirname(filename))
            basename = os.path.basename(filename)
        else:
            # The filename is just the basename, assume it's in the uploads directory
            directory = os.path.join(app.static_folder, 'uploads')
            basename = filename

        return send_from_directory(directory, basename, mimetype='application/pdf')

    # Register custom Jinja2 filters
    @app.template_filter('nl2br')
    def nl2br_filter(s):
        if s is None:
            return ''
        s = str(s)
        return markupsafe.Markup(s.replace('\n', '<br>'))

    @app.template_filter('from_json')
    def from_json_filter(s):
        if s is None or s == '':
            return {}
        try:
            import json
            return json.loads(s)
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            return {}

    from app.auth import bp as auth_bp
    from app.main import bp as main_bp
    from app.sessions import bp as sessions_bp
    from app.mentorship import bp as mentorship_bp
    from app.analytics import bp as analytics_bp
    from app.gamification import bp as gamification_bp
    from app.admin import bp as admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(sessions_bp)
    app.register_blueprint(mentorship_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(gamification_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app import models

    return app
from datetime import datetime
from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect, generate_csrf
from config import Config
from app.models import db, User, Booking

login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Init extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Пожалуйста, войдите в систему для доступа к этой странице.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app.client import bp as client_bp
    app.register_blueprint(client_bp)

    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    # CSRF token global
    @app.template_global()
    def csrf_token():
        return generate_csrf()

    @app.route('/favicon.ico')
    def favicon():
        return '', 204

    # Template filters
    @app.template_filter('format_time')
    def format_time_filter(t):
        if t is None:
            return ''
        if hasattr(t, 'strftime'):
            return t.strftime('%H:%M')
        return str(t)

    @app.template_filter('format_date')
    def format_date_filter(d):
        if d is None:
            return ''
        if hasattr(d, 'strftime'):
            return d.strftime('%d.%m.%Y')
        return str(d)

    @app.template_filter('format_price')
    def format_price_filter(p):
        if p is None:
            return '0'
        return f"{float(p):,.0f}".replace(',', ' ')

    @app.template_global()
    def stars_range():
        return range(1, 6)

    @app.context_processor
    def inject_globals():
        pending_count = 0
        try:
            pending_count = Booking.query.filter_by(status=Booking.STATUS_PENDING).count()
        except Exception:
            pending_count = 0
        return {
            'now': datetime.utcnow(),
            'pending_count': pending_count
        }

    return app

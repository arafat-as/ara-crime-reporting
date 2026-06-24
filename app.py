"""
Crime Reporting and Alert System — Flask Application Factory.
"""
import os
from flask import Flask, render_template, send_from_directory
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_socketio import SocketIO
from config import config
from models import db, bcrypt

migrate = Migrate()
jwt = JWTManager()
socketio = SocketIO(cors_allowed_origins="*", async_mode='threading')


def create_app(config_name='default'):
    """Application factory."""
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Ensure upload directory exists
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'static/uploads'), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app)
    socketio.init_app(app)

    # Register blueprints
    from routes.auth import auth_bp
    from routes.reports import reports_bp
    from routes.alerts import alerts_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(admin_bp)

    # --- Page routes (serve HTML templates) ---
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/map')
    def map_page():
        return render_template('map.html')

    @app.route('/login')
    def login_page():
        return render_template('login.html')

    @app.route('/register')
    def register_page():
        return render_template('register.html')

    @app.route('/dashboard')
    def dashboard_page():
        return render_template('dashboard.html')

    @app.route('/report/new')
    def report_form_page():
        return render_template('report_form.html')

    @app.route('/report/<int:report_id>')
    def report_detail_page(report_id):
        return render_template('report_detail.html')

    @app.route('/officer')
    def officer_dashboard_page():
        return render_template('officer_dashboard.html')

    @app.route('/admin')
    def admin_dashboard_page():
        return render_template('admin_dashboard.html')

    # --- Error handlers ---
    @app.errorhandler(404)
    def not_found(e):
        return render_template('base.html'), 404

    # --- SocketIO events ---
    @socketio.on('connect')
    def handle_connect():
        print('Client connected')

    @socketio.on('disconnect')
    def handle_disconnect():
        print('Client disconnected')

    # Create database tables
    with app.app_context():
        db.create_all()

    return app


# Create app instance
# Uses FLASK_CONFIG env var if set (e.g. 'production' on Render), otherwise defaults to development
app = create_app(os.environ.get('FLASK_CONFIG', 'development'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_CONFIG', 'development') != 'production'
    socketio.run(app, host='0.0.0.0', port=port, debug=debug)

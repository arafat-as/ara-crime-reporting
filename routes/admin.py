"""
Admin routes — dashboard stats, user management, activity logs.
"""
import os
from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import text
from models import db, User, CrimeReport, Alert, CrimeCategory, ActivityLog
from utils.decorators import role_required, admin_required
from utils.helpers import log_activity, logger

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/api/admin/run-migration', methods=['POST'])
def run_migration():
    """
    One-time, idempotent schema fix for environments without shell access
    (e.g. Render's free tier). Adds the latitude/longitude columns to the
    users table if they don't already exist. Safe to call more than once.

    Protected by a secret key (not login) because a missing column can
    break login itself, creating a chicken-and-egg problem otherwise.

    NOTE: this route is intentionally temporary — remove it once the schema
    has been confirmed updated in production.
    """
    provided_key = request.headers.get('X-Migration-Key', '')
    expected_key = os.environ.get('SECRET_KEY', '')
    if not expected_key or provided_key != expected_key:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        db.session.execute(text(
            'ALTER TABLE users ADD COLUMN IF NOT EXISTS latitude FLOAT'
        ))
        db.session.execute(text(
            'ALTER TABLE users ADD COLUMN IF NOT EXISTS longitude FLOAT'
        ))
        db.session.commit()
        logger.info("Migration run: added latitude/longitude columns to users table.")
        return jsonify({'message': 'Migration applied successfully.'}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Migration failed: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/admin/run-seed', methods=['POST'])
def run_seed():
    """
    One-time, idempotent demo-data seeder for production, used because the
    free Render tier has no shell access to run seed.py directly. Creates
    the standard demo accounts (and categories/citizens with coordinates
    for geofencing demos) only if they don't already exist.

    Protected by the same secret-key pattern as run_migration, for the
    same reason — this needs to work even if login is currently broken.

    NOTE: this route is intentionally temporary — remove it once production
    has been confirmed seeded.
    """
    provided_key = request.headers.get('X-Migration-Key', '')
    expected_key = os.environ.get('SECRET_KEY', '')
    if not expected_key or provided_key != expected_key:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        created = []

        categories_data = [
            ('Robbery', '🔫', 'Theft using force or threat of force'),
            ('Assault', '👊', 'Physical attack on a person'),
            ('Burglary', '🏠', 'Unlawful entry into a building to commit theft'),
            ('Fraud', '💳', 'Deception for financial or personal gain'),
            ('Vandalism', '🔨', 'Deliberate destruction of property'),
            ('Kidnapping', '🚨', 'Unlawful abduction of a person'),
            ('Drug Offense', '💊', 'Illegal possession, use, or sale of drugs'),
            ('Domestic Violence', '🏚️', 'Violence within a household'),
            ('Cybercrime', '💻', 'Crimes committed using computers or the internet'),
            ('Public Disturbance', '📢', 'Disorderly conduct in public'),
            ('Traffic Violation', '🚗', 'Violation of traffic laws'),
            ('Other', '⚠️', 'Other crimes not listed above'),
        ]
        for name, icon, desc in categories_data:
            if not CrimeCategory.query.filter_by(name=name).first():
                db.session.add(CrimeCategory(name=name, icon=icon, description=desc))
                created.append(f'category:{name}')

        demo_users = [
            ('admin', 'admin@crimealert.ng', 'Admin@123', 'System Administrator', 'admin', '08012345670', None, None),
            ('officer_john', 'john.officer@police.ng', 'Officer@123', 'John Adeyemi', 'officer', '08012345671', None, None),
            ('citizen_mike', 'mike@gmail.com', 'Citizen@123', 'Michael Eze', 'citizen', '08012345673', 6.6018, 3.3515),
            ('citizen_ada', 'ada@gmail.com', 'Citizen@123', 'Adaeze Nwosu', 'citizen', '08012345674', 6.4474, 3.4737),
        ]
        for uname, email, pw, full_name, role, phone, lat, lng in demo_users:
            if not User.query.filter_by(username=uname).first():
                user = User(
                    username=uname, email=email, full_name=full_name,
                    phone=phone, role=role, latitude=lat, longitude=lng,
                )
                user.set_password(pw)
                db.session.add(user)
                created.append(f'user:{uname}')

        db.session.commit()
        logger.info(f"Seed run: created {len(created)} new records.")
        return jsonify({'message': 'Seed applied successfully.', 'created': created}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Seed failed: {str(e)}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/admin/stats', methods=['GET'])
@role_required('officer', 'admin')
def get_stats():
    """Get dashboard statistics."""
    total_reports = CrimeReport.query.count()
    pending = CrimeReport.query.filter_by(status='pending').count()
    investigating = CrimeReport.query.filter_by(status='investigating').count()
    resolved = CrimeReport.query.filter_by(status='resolved').count()
    dismissed = CrimeReport.query.filter_by(status='dismissed').count()
    total_users = User.query.filter_by(is_active=True).count()
    total_citizens = User.query.filter_by(role='citizen', is_active=True).count()
    total_officers = User.query.filter_by(role='officer', is_active=True).count()
    active_alerts = Alert.query.filter_by(is_active=True).count()

    resolution_rate = round((resolved / total_reports * 100), 1) if total_reports > 0 else 0

    # Reports by category
    categories = CrimeCategory.query.all()
    by_category = []
    for cat in categories:
        count = CrimeReport.query.filter_by(category_id=cat.id).count()
        if count > 0:
            by_category.append({'name': cat.name, 'icon': cat.icon, 'count': count})
    by_category.sort(key=lambda x: x['count'], reverse=True)

    # Reports by severity
    by_severity = {}
    for sev in ['low', 'medium', 'high', 'critical']:
        by_severity[sev] = CrimeReport.query.filter_by(severity=sev).count()

    return jsonify({
        'total_reports': total_reports,
        'pending': pending,
        'investigating': investigating,
        'resolved': resolved,
        'dismissed': dismissed,
        'total_users': total_users,
        'total_citizens': total_citizens,
        'total_officers': total_officers,
        'active_alerts': active_alerts,
        'resolution_rate': resolution_rate,
        'by_category': by_category,
        'by_severity': by_severity,
    }), 200


@admin_bp.route('/api/admin/users', methods=['GET'])
@admin_required
def get_users():
    """List all users (admin only)."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    role = request.args.get('role')
    search = request.args.get('search', '')

    query = User.query
    if role:
        query = query.filter_by(role=role)
    if search:
        query = query.filter(
            (User.username.ilike(f'%{search}%')) |
            (User.full_name.ilike(f'%{search}%')) |
            (User.email.ilike(f'%{search}%'))
        )

    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)

    return jsonify({
        'users': [u.to_dict() for u in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
    }), 200


@admin_bp.route('/api/admin/users/<int:user_id>/role', methods=['PUT'])
@admin_required
def change_role(user_id):
    """Change a user's role (admin only)."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    new_role = data.get('role')
    if new_role not in ('citizen', 'officer', 'admin'):
        return jsonify({'error': 'Invalid role'}), 400

    old_role = user.role
    user.role = new_role
    db.session.commit()
    log_activity(int(get_jwt_identity()), 'role_change',
                 f'User {user.username}: {old_role} → {new_role}')
    return jsonify({'message': 'Role updated', 'user': user.to_dict()}), 200


@admin_bp.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required
def deactivate_user(user_id):
    """Deactivate a user account (admin only)."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    admin_id = int(get_jwt_identity())
    if user.id == admin_id:
        return jsonify({'error': 'Cannot deactivate your own account'}), 400

    user.is_active = not user.is_active
    db.session.commit()
    status = 'activated' if user.is_active else 'deactivated'
    log_activity(admin_id, f'user_{status}', f'User {user.username} {status}')
    return jsonify({'message': f'User {status}', 'user': user.to_dict()}), 200


@admin_bp.route('/api/admin/logs', methods=['GET'])
@admin_required
def get_logs():
    """Get activity logs (admin only)."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    pagination = ActivityLog.query.order_by(ActivityLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)

    return jsonify({
        'logs': [l.to_dict() for l in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
    }), 200

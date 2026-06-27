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

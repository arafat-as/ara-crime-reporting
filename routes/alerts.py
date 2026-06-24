"""
Alert and notification routes.
"""
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Alert, Notification, User
from utils.decorators import role_required
from utils.helpers import log_activity, logger

alerts_bp = Blueprint('alerts', __name__)


@alerts_bp.route('/api/alerts', methods=['POST'])
@role_required('officer', 'admin')
def create_alert():
    """Create a new area alert (officer/admin only)."""
    user_id = get_jwt_identity()
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required = ['title', 'message', 'severity']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    try:
        alert = Alert(
            title=data['title'],
            message=data['message'],
            severity=data['severity'],
            area_latitude=float(data['area_latitude']) if data.get('area_latitude') else None,
            area_longitude=float(data['area_longitude']) if data.get('area_longitude') else None,
            area_radius=float(data.get('area_radius', 5.0)),
            created_by=user_id,
            is_active=True,
            expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None,
        )
        db.session.add(alert)
        db.session.commit()

        citizens = User.query.filter_by(role='citizen', is_active=True).all()
        for citizen in citizens:
            notif = Notification(user_id=citizen.id, alert_id=alert.id,
                                 message=f"🚨 {alert.title}: {alert.message}")
            db.session.add(notif)
        db.session.commit()

        log_activity(user_id, 'alert_created', f'Alert #{alert.id}: {alert.title}')
        try:
            from app import socketio
            socketio.emit('new_alert', alert.to_dict(), namespace='/')
        except Exception:
            pass

        return jsonify({'message': 'Alert created and broadcast', 'alert': alert.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Alert creation error: {e}")
        return jsonify({'error': 'Failed to create alert'}), 500


@alerts_bp.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Get all active alerts."""
    alerts = Alert.query.filter_by(is_active=True).order_by(Alert.created_at.desc()).all()
    now = datetime.now(timezone.utc)
    active = []
    for a in alerts:
        if a.expires_at and a.expires_at.replace(tzinfo=timezone.utc) < now:
            a.is_active = False
            db.session.commit()
        else:
            active.append(a)
    return jsonify({'alerts': [a.to_dict() for a in active]}), 200


@alerts_bp.route('/api/alerts/<int:alert_id>', methods=['PUT'])
@role_required('officer', 'admin')
def update_alert(alert_id):
    alert = Alert.query.get(alert_id)
    if not alert:
        return jsonify({'error': 'Alert not found'}), 404
    data = request.get_json()
    for field in ['title', 'message', 'severity']:
        if field in data:
            setattr(alert, field, data[field])
    if 'is_active' in data:
        alert.is_active = data['is_active']
    db.session.commit()
    log_activity(get_jwt_identity(), 'alert_updated', f'Alert #{alert.id} updated')
    return jsonify({'message': 'Alert updated', 'alert': alert.to_dict()}), 200


@alerts_bp.route('/api/alerts/<int:alert_id>', methods=['DELETE'])
@role_required('officer', 'admin')
def deactivate_alert(alert_id):
    alert = Alert.query.get(alert_id)
    if not alert:
        return jsonify({'error': 'Alert not found'}), 404
    alert.is_active = False
    db.session.commit()
    return jsonify({'message': 'Alert deactivated'}), 200


@alerts_bp.route('/api/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    user_id = get_jwt_identity()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    unread_only = request.args.get('unread', 'false').lower() == 'true'
    query = Notification.query.filter_by(user_id=user_id)
    if unread_only:
        query = query.filter_by(is_read=False)
    pagination = query.order_by(Notification.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    unread_count = Notification.query.filter_by(user_id=user_id, is_read=False).count()
    return jsonify({
        'notifications': [n.to_dict() for n in pagination.items],
        'unread_count': unread_count, 'total': pagination.total,
        'pages': pagination.pages, 'current_page': page,
    }), 200


@alerts_bp.route('/api/notifications/<int:nid>/read', methods=['PUT'])
@jwt_required()
def mark_notification_read(nid):
    user_id = get_jwt_identity()
    notif = Notification.query.filter_by(id=nid, user_id=user_id).first()
    if not notif:
        return jsonify({'error': 'Notification not found'}), 404
    notif.is_read = True
    db.session.commit()
    return jsonify({'message': 'Notification marked as read'}), 200


@alerts_bp.route('/api/notifications/read-all', methods=['PUT'])
@jwt_required()
def mark_all_read():
    user_id = get_jwt_identity()
    Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'message': 'All notifications marked as read'}), 200

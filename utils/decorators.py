"""
Custom decorators for role-based access control.
"""
from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from models import User


def role_required(*roles):
    """
    Decorator that restricts access to users with specific roles.
    Usage: @role_required('admin', 'officer')
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            user = User.query.get(user_id)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            if user.role not in roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            if not user.is_active:
                return jsonify({'error': 'Account deactivated'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def admin_required(fn):
    """Shortcut decorator for admin-only endpoints."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        if not user or user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return fn(*args, **kwargs)
    return wrapper

"""
Authentication routes — register, login, profile management.
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt_identity
)
from models import db, User
from utils.helpers import log_activity, logger
import re

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user account."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required = ['username', 'email', 'password', 'full_name']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    # Validate email format
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, data['email']):
        return jsonify({'error': 'Invalid email format'}), 400

    # Validate password strength
    if len(data['password']) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    # Check for existing user
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already taken'}), 409
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 409

    try:
        user = User(
            username=data['username'],
            email=data['email'],
            full_name=data['full_name'],
            phone=data.get('phone', ''),
            role='citizen',  # Default role
        )
        user.set_password(data['password'])
        db.session.add(user)
        db.session.commit()

        access_token = create_access_token(identity=user.id)
        log_activity(user.id, 'register', f'New user registered: {user.username}')

        logger.info(f"New user registered: {user.username}")
        return jsonify({
            'message': 'Registration successful',
            'token': access_token,
            'user': user.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Registration error: {e}")
        return jsonify({'error': 'Registration failed. Please try again.'}), 500


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    """Authenticate user and return JWT token."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    # Allow login with username or email
    user = User.query.filter(
        (User.username == username) | (User.email == username)
    ).first()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401

    if not user.is_active:
        return jsonify({'error': 'Account has been deactivated'}), 403

    access_token = create_access_token(identity=user.id)
    log_activity(user.id, 'login', f'User logged in: {user.username}')

    logger.info(f"User logged in: {user.username}")
    return jsonify({
        'message': 'Login successful',
        'token': access_token,
        'user': user.to_dict()
    }), 200


@auth_bp.route('/api/auth/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get the current user's profile."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({'user': user.to_dict()}), 200


@auth_bp.route('/api/auth/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update the current user's profile."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    if 'full_name' in data:
        user.full_name = data['full_name']
    if 'phone' in data:
        user.phone = data['phone']
    if 'email' in data:
        existing = User.query.filter(User.email == data['email'], User.id != user.id).first()
        if existing:
            return jsonify({'error': 'Email already in use'}), 409
        user.email = data['email']

    try:
        db.session.commit()
        log_activity(user.id, 'profile_update', 'Profile updated')
        return jsonify({'message': 'Profile updated', 'user': user.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Profile update error: {e}")
        return jsonify({'error': 'Update failed'}), 500

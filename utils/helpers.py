"""
Utility helpers for the Crime Reporting System.
"""
import os
import uuid
import logging
from datetime import datetime, timezone
from flask import request
from werkzeug.utils import secure_filename
from models import db, ActivityLog

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crime_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('CrimeReportingSystem')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    """Check if a file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file, upload_folder):
    """Save an uploaded file and return its URL path."""
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, unique_name)
        file.save(filepath)
        return f"/static/uploads/{unique_name}"
    return None


def log_activity(user_id, action, details=None):
    """Record an activity in the audit log."""
    try:
        log = ActivityLog(
            user_id=user_id,
            action=action,
            details=details,
            ip_address=request.remote_addr if request else None,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to log activity: {e}")
        db.session.rollback()


def get_severity_color(severity):
    """Return a CSS color for a severity level."""
    colors = {
        'low': '#10b981',
        'medium': '#f59e0b',
        'high': '#f97316',
        'critical': '#ef4444',
    }
    return colors.get(severity, '#6b7280')


def get_status_color(status):
    """Return a CSS color for a report status."""
    colors = {
        'pending': '#f59e0b',
        'investigating': '#3b82f6',
        'resolved': '#10b981',
        'dismissed': '#6b7280',
    }
    return colors.get(status, '#6b7280')

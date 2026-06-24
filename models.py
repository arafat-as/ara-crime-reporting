"""
SQLAlchemy ORM models for the Crime Reporting and Alert System.
Defines: User, CrimeCategory, CrimeReport, Alert, Notification, ActivityLog.
"""
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt()


class User(db.Model):
    """User accounts — citizens, officers, and administrators."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='citizen')  # citizen, officer, admin
    is_active = db.Column(db.Boolean, default=True)
    avatar_color = db.Column(db.String(7), default='#00d4ff')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    reports = db.relationship('CrimeReport', backref='reporter', lazy='dynamic',
                              foreign_keys='CrimeReport.reporter_id')
    assigned_reports = db.relationship('CrimeReport', backref='assigned_officer', lazy='dynamic',
                                       foreign_keys='CrimeReport.assigned_officer_id')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
    activity_logs = db.relationship('ActivityLog', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.full_name,
            'phone': self.phone,
            'role': self.role,
            'is_active': self.is_active,
            'avatar_color': self.avatar_color,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class CrimeCategory(db.Model):
    """Pre-defined crime categories."""
    __tablename__ = 'crime_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    icon = db.Column(db.String(50), default='⚠️')
    description = db.Column(db.Text, nullable=True)
    reports = db.relationship('CrimeReport', backref='category', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'icon': self.icon,
            'description': self.description,
        }


class CrimeReport(db.Model):
    """Individual crime reports submitted by citizens."""
    __tablename__ = 'crime_reports'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('crime_categories.id'), nullable=False)
    severity = db.Column(db.String(20), nullable=False, default='medium')  # low, medium, high, critical
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, investigating, resolved, dismissed
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    address = db.Column(db.String(300), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_officer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_anonymous = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'category': self.category.to_dict() if self.category else None,
            'severity': self.severity,
            'status': self.status,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'address': self.address,
            'image_url': self.image_url,
            'reporter': self.reporter.to_dict() if self.reporter and not self.is_anonymous else None,
            'is_anonymous': self.is_anonymous,
            'assigned_officer': self.assigned_officer.to_dict() if self.assigned_officer else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'comments': [c.to_dict() for c in self.comments]
        }


class ReportComment(db.Model):
    """Comments on a crime report for updates/details."""
    __tablename__ = 'report_comments'

    id = db.Column(db.Integer, primary_key=True)
    report_id = db.Column(db.Integer, db.ForeignKey('crime_reports.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    report = db.relationship('CrimeReport', backref=db.backref('comments', lazy='dynamic', order_by='ReportComment.created_at.desc()'))
    user = db.relationship('User', backref='comments')

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'user': {
                'id': self.user.id,
                'username': self.user.username,
                'full_name': self.user.full_name,
                'avatar_color': self.user.avatar_color,
                'role': self.user.role
            } if self.user else None
        }


class Alert(db.Model):
    """Area-based alerts broadcast by officers/admins."""
    __tablename__ = 'alerts'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), nullable=False, default='medium')  # low, medium, high, critical
    area_latitude = db.Column(db.Float, nullable=True)
    area_longitude = db.Column(db.Float, nullable=True)
    area_radius = db.Column(db.Float, default=5.0)  # radius in km
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=True)

    creator = db.relationship('User', backref='created_alerts')
    notifications = db.relationship('Notification', backref='alert', lazy='dynamic')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'severity': self.severity,
            'area_latitude': self.area_latitude,
            'area_longitude': self.area_longitude,
            'area_radius': self.area_radius,
            'created_by': self.creator.to_dict() if self.creator else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }


class Notification(db.Model):
    """Per-user notifications triggered by reports or alerts."""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    alert_id = db.Column(db.Integer, db.ForeignKey('alerts.id'), nullable=True)
    report_id = db.Column(db.Integer, db.ForeignKey('crime_reports.id'), nullable=True)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    report = db.relationship('CrimeReport', backref='notifications')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'alert_id': self.alert_id,
            'report_id': self.report_id,
            'message': self.message,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class ActivityLog(db.Model):
    """Audit trail of significant system events."""
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user': self.user.to_dict() if self.user else None,
            'action': self.action,
            'details': self.details,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

"""
Crime report routes — CRUD operations and map data.
"""
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, CrimeReport, CrimeCategory, User
from utils.decorators import role_required
from utils.helpers import log_activity, save_upload, logger

reports_bp = Blueprint('reports', __name__)


@reports_bp.route('/api/reports', methods=['POST'])
@jwt_required()
def create_report():
    """Submit a new crime report."""
    user_id = int(get_jwt_identity())

    # Handle both JSON and form-data (for file uploads)
    if request.content_type and 'multipart/form-data' in request.content_type:
        data = request.form.to_dict()
        image = request.files.get('image')
    else:
        data = request.get_json() or {}
        image = None

    required = ['title', 'description', 'category_id']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    # Validate category exists
    category = CrimeCategory.query.get(data['category_id'])
    if not category:
        return jsonify({'error': 'Invalid crime category'}), 400

    try:
        image_url = None
        if image:
            image_url = save_upload(image, current_app.config['UPLOAD_FOLDER'])

        report = CrimeReport(
            title=data['title'],
            description=data['description'],
            category_id=int(data['category_id']),
            severity=data.get('severity', 'medium'),
            latitude=float(data['latitude']) if data.get('latitude') else None,
            longitude=float(data['longitude']) if data.get('longitude') else None,
            address=data.get('address', ''),
            image_url=image_url,
            reporter_id=user_id,
            is_anonymous=data.get('is_anonymous', 'false').lower() == 'true' if isinstance(data.get('is_anonymous'), str) else bool(data.get('is_anonymous', False)),
        )
        db.session.add(report)
        db.session.commit()

        log_activity(user_id, 'report_created', f'Crime report #{report.id}: {report.title}')
        logger.info(f"New crime report #{report.id} by user #{user_id}")

        # Emit real-time event (handled by app.py socketio)
        try:
            from app import socketio
            socketio.emit('new_report', report.to_dict(), namespace='/')
        except Exception:
            pass

        return jsonify({
            'message': 'Crime report submitted successfully',
            'report': report.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Report creation error: {e}")
        return jsonify({'error': 'Failed to submit report'}), 500


@reports_bp.route('/api/reports', methods=['GET'])
def get_reports():
    """List crime reports with filtering and pagination."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    status = request.args.get('status')
    category_id = request.args.get('category_id', type=int)
    severity = request.args.get('severity')
    search = request.args.get('search', '')

    query = CrimeReport.query

    if status:
        query = query.filter(CrimeReport.status == status)
    if category_id:
        query = query.filter(CrimeReport.category_id == category_id)
    if severity:
        query = query.filter(CrimeReport.severity == severity)
    if search:
        query = query.filter(
            (CrimeReport.title.ilike(f'%{search}%')) |
            (CrimeReport.description.ilike(f'%{search}%')) |
            (CrimeReport.address.ilike(f'%{search}%'))
        )

    query = query.order_by(CrimeReport.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'reports': [r.to_dict() for r in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
    }), 200


@reports_bp.route('/api/reports/map', methods=['GET'])
def get_reports_for_map():
    """Get reports with coordinates for map display."""
    reports = CrimeReport.query.filter(
        CrimeReport.latitude.isnot(None),
        CrimeReport.longitude.isnot(None)
    ).order_by(CrimeReport.created_at.desc()).limit(200).all()

    return jsonify({
        'reports': [r.to_dict() for r in reports]
    }), 200


@reports_bp.route('/api/reports/<int:report_id>', methods=['GET'])
def get_report(report_id):
    """Get a single report by ID."""
    report = CrimeReport.query.get(report_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404
    return jsonify({'report': report.to_dict()}), 200


@reports_bp.route('/api/reports/<int:report_id>/comments', methods=['POST'])
@jwt_required()
def add_comment(report_id):
    """Add a comment to a report."""
    from models import ReportComment
    user_id = int(get_jwt_identity())
    report = CrimeReport.query.get(report_id)
    
    if not report:
        return jsonify({'error': 'Report not found'}), 404
        
    data = request.get_json()
    if not data or not data.get('content'):
        return jsonify({'error': 'Comment content is required'}), 400
        
    comment = ReportComment(
        report_id=report_id,
        user_id=user_id,
        content=data['content']
    )
    db.session.add(comment)
    db.session.commit()
    
    return jsonify({
        'message': 'Comment added successfully',
        'comment': comment.to_dict()
    }), 201


@reports_bp.route('/api/reports/<int:report_id>', methods=['PUT'])
@jwt_required()
def update_report(report_id):
    """Update a report (officer/admin can change status, assign)."""
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    report = CrimeReport.query.get(report_id)

    if not report:
        return jsonify({'error': 'Report not found'}), 404

    # Citizens can only edit their own pending reports
    if user.role == 'citizen':
        if report.reporter_id != user_id or report.status != 'pending':
            return jsonify({'error': 'Cannot edit this report'}), 403

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    try:
        if 'status' in data and user.role in ('officer', 'admin'):
            old_status = report.status
            report.status = data['status']
            log_activity(user_id, 'report_status_change',
                         f'Report #{report.id}: {old_status} → {data["status"]}')

            # Emit real-time update
            try:
                from app import socketio
                socketio.emit('report_update', report.to_dict(), namespace='/')
            except Exception:
                pass

        if 'assigned_officer_id' in data and user.role in ('officer', 'admin'):
            report.assigned_officer_id = data['assigned_officer_id']

        if 'title' in data:
            report.title = data['title']
        if 'description' in data:
            report.description = data['description']
        if 'severity' in data and user.role in ('officer', 'admin'):
            report.severity = data['severity']

        db.session.commit()
        return jsonify({'message': 'Report updated', 'report': report.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Report update error: {e}")
        return jsonify({'error': 'Update failed'}), 500


@reports_bp.route('/api/reports/<int:report_id>', methods=['DELETE'])
@role_required('admin')
def delete_report(report_id):
    """Delete a report (admin only)."""
    report = CrimeReport.query.get(report_id)
    if not report:
        return jsonify({'error': 'Report not found'}), 404

    try:
        db.session.delete(report)
        db.session.commit()
        log_activity(int(get_jwt_identity()), 'report_deleted', f'Report #{report_id} deleted')
        return jsonify({'message': 'Report deleted'}), 200
    except Exception as e:
        db.session.rollback()
        logger.error(f"Report delete error: {e}")
        return jsonify({'error': 'Delete failed'}), 500


@reports_bp.route('/api/reports/my', methods=['GET'])
@jwt_required()
def get_my_reports():
    """Get reports submitted by the current user."""
    user_id = int(get_jwt_identity())
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    pagination = CrimeReport.query.filter_by(reporter_id=user_id)\
        .order_by(CrimeReport.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'reports': [r.to_dict() for r in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page,
    }), 200


@reports_bp.route('/api/categories', methods=['GET'])
def get_categories():
    """List all crime categories."""
    categories = CrimeCategory.query.order_by(CrimeCategory.name).all()
    return jsonify({'categories': [c.to_dict() for c in categories]}), 200

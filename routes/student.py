import io
import os
import re
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, send_file
from werkzeug.security import check_password_hash
import qrcode

from models import db, Student, GatepassRequest, Notice

student_bp = Blueprint('student', __name__)

BRANCHES = ["CO", "IT", "ENTC", "EJ", "DD", "CE"]
YEARS = ["FY", "SY", "TY"]


# ===================== LOGIN =====================
@student_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        enrollment = request.form.get('enrollment', '').strip()
        password = request.form.get('password', '').strip()
        branch = request.form.get('branch', '').strip()
        year = request.form.get('year', '').strip()

        errors = []
        if not enrollment:
            errors.append('Enrollment number is required.')
        if not password:
            errors.append('Password is required.')
        if not branch:
            errors.append('Branch is required.')
        if not year:
            errors.append('Year is required.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('student/login.html', branches=BRANCHES, years=YEARS)

        student = Student.query.filter_by(
            enrollment=enrollment, branch=branch, year=year
        ).first()

        if not student or not check_password_hash(student.password, password):
            flash('Invalid Enrollment or Password.', 'error')
            return render_template('student/login.html', branches=BRANCHES, years=YEARS)

        session.permanent = True
        session['student_enrollment'] = student.enrollment
        session['student_name'] = student.student_name
        session['student_branch'] = student.branch
        session['student_year'] = student.year
        flash(f'Welcome, {student.student_name}!', 'success')
        return redirect(url_for('student.dashboard'))

    return render_template('student/login.html', branches=BRANCHES, years=YEARS)


# ===================== DASHBOARD =====================
@student_bp.route('/dashboard')
def dashboard():
    if 'student_enrollment' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('student.login'))
    return render_template('student/dashboard.html',
                           student_name=session['student_name'])


# ===================== GATEPASS REQUEST =====================
@student_bp.route('/gatepass-request', methods=['GET', 'POST'])
def gatepass_request():
    if 'student_enrollment' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('student.login'))

    if request.method == 'POST':
        reason = request.form.get('reason', '').strip()
        out_date = request.form.get('out_date', '').strip()
        in_date = request.form.get('in_date', '').strip()
        place = request.form.get('place', '').strip()

        errors = []
        if not reason:
            errors.append('Reason is required.')
        if not out_date:
            errors.append('Out Date & Time is required.')
        if not in_date:
            errors.append('In Date & Time is required.')
        if not place:
            errors.append('Place is required.')

        # Validate date format
        date_pattern = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$'
        if out_date and not re.match(date_pattern, out_date):
            errors.append('Out Date must be in YYYY-MM-DD HH:MM format.')
        if in_date and not re.match(date_pattern, in_date):
            errors.append('In Date must be in YYYY-MM-DD HH:MM format.')

        # Validate in_date > out_date
        if out_date and in_date and not errors:
            try:
                out_dt = datetime.strptime(out_date, '%Y-%m-%d %H:%M')
                in_dt = datetime.strptime(in_date, '%Y-%m-%d %H:%M')
                if in_dt <= out_dt:
                    errors.append('In Date must be after Out Date.')
            except ValueError:
                errors.append('Invalid date format.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('student/gatepass_request.html')

        enrollment = session['student_enrollment']
        student_name = session['student_name']
        branch = session['student_branch']
        year = session['student_year']

        new_request = GatepassRequest(
            enrollment=enrollment,
            student_name=student_name,
            branch=branch,
            year=year,
            reason=reason,
            out_date=out_date,
            in_date=in_date,
            place=place,
            status='Pending',
            qr_file='',
            actual_out_date='',
            actual_in_date='',
            late_days=0,
            fine=0,
            fine_status='No Fine',
            reject_reason='',
            request_datetime=datetime.now().strftime('%Y-%m-%d %H:%M')
        )
        db.session.add(new_request)
        db.session.commit()

        flash('✅ Gatepass request submitted successfully! Staff approval pending.', 'success')
        return redirect(url_for('student.dashboard'))

    return render_template('student/gatepass_request.html')


# ===================== REQUEST STATUS =====================
@student_bp.route('/request-status')
def request_status():
    if 'student_enrollment' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('student.login'))

    enrollment = session['student_enrollment']
    requests_list = GatepassRequest.query.filter_by(enrollment=enrollment).order_by(
        GatepassRequest.id.desc()
    ).all()
    return render_template('student/request_status.html', requests=requests_list)


# ===================== DOWNLOAD QR =====================
@student_bp.route('/download-qr/<int:req_id>')
def download_qr(req_id):
    if 'student_enrollment' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('student.login'))

    gatepass = GatepassRequest.query.get(req_id)
    if not gatepass or gatepass.enrollment != session['student_enrollment']:
        flash('Request not found.', 'error')
        return redirect(url_for('student.request_status'))

    if gatepass.status != 'Approved':
        flash('QR code only available for approved requests.', 'error')
        return redirect(url_for('student.request_status'))

    # Generate QR code in-memory (not saved to disk)
    from urllib.parse import urlencode
    qr_params = urlencode({
        'enrollment': gatepass.enrollment,
        'out_date': gatepass.out_date,
        'in_date': gatepass.in_date,
        'place': gatepass.place
    })
    qr_url = f"{request.host_url.rstrip('/')}/security/gatepass-entry?{qr_params}"
    qr_img = qrcode.make(qr_url)

    # Save to in-memory buffer and send directly
    buffer = io.BytesIO()
    qr_img.save(buffer, format='PNG')
    buffer.seek(0)

    filename = f"QR_{gatepass.enrollment}_{gatepass.id}.png"
    return send_file(buffer, mimetype='image/png', as_attachment=True, download_name=filename)


# ===================== NOTICE BOARD =====================
@student_bp.route('/notices')
def notices():
    if 'student_enrollment' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('student.login'))

    notices_list = Notice.query.order_by(Notice.id.desc()).all()
    return render_template('student/notices.html', notices=notices_list)


# ===================== LOGOUT =====================
@student_bp.route('/logout')
def logout():
    session.pop('student_enrollment', None)
    session.pop('student_name', None)
    session.pop('student_branch', None)
    session.pop('student_year', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('home.index'))

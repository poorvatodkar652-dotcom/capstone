import os
import re
import random
import string
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app, send_file
from werkzeug.security import check_password_hash

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
            enrollment_no=enrollment, branch=branch, year=year
        ).first()

        if not student or not check_password_hash(student.password_hash, password):
            flash('Invalid Enrollment or Password.', 'error')
            return render_template('student/login.html', branches=BRANCHES, years=YEARS)

        session.permanent = True
        session['student_enrollment'] = student.enrollment_no
        session['student_name'] = student.full_name
        session['student_branch'] = student.branch
        session['student_year'] = student.year
        flash(f'Welcome, {student.full_name}!', 'success')
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

        # Simple duplicate-submission guard: if the same payload was just submitted,
        # do not create another request.
        payload_key = f"{reason}|{out_date}|{in_date}|{place}"
        if session.get('last_gatepass_request') == payload_key:
            flash('This gatepass request was already submitted.', 'info')
            return redirect(url_for('student.request_status'))

        errors = []
        if not reason:
            errors.append('Reason is required.')
        if not out_date:
            errors.append('Out Date & Time is required.')
        if not in_date:
            errors.append('In Date & Time is required.')
        if not place:
            errors.append('Place is required.')

        # Validate date format (accept both 'YYYY-MM-DD HH:MM' and HTML datetime-local 'YYYY-MM-DDTHH:MM')
        date_pattern = r'^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}$'
        if out_date and not re.match(date_pattern, out_date):
            errors.append('Out Date must be in YYYY-MM-DD HH:MM format.')
        if in_date and not re.match(date_pattern, in_date):
            errors.append('In Date must be in YYYY-MM-DD HH:MM format.')

        # Validate in_date > out_date
        if out_date and in_date and not errors:
            try:
                out_dt = datetime.strptime(out_date.replace('T', ' '), '%Y-%m-%d %H:%M')
                in_dt = datetime.strptime(in_date.replace('T', ' '), '%Y-%m-%d %H:%M')
                if in_dt <= out_dt:
                    errors.append('In Date must be after Out Date.')
            except ValueError:
                errors.append('Invalid date format.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('student/gatepass_request.html')

        enrollment = session['student_enrollment']
        
        # We don't save branch, year, student_name in GatepassRequest anymore
        # We just link enrollment_no.

        # Generate 6-char auth code
        auth_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        new_request = GatepassRequest(
            enrollment_no=enrollment,
            reason=reason,
            out_date=datetime.strptime(out_date.replace('T', ' '), '%Y-%m-%d %H:%M'),
            in_date=datetime.strptime(in_date.replace('T', ' '), '%Y-%m-%d %H:%M'),
            place=place,
            status='Pending',
            auth_code=auth_code,
            request_datetime=datetime.utcnow()
        )
        db.session.add(new_request)
        db.session.commit()

        # Remember last successfully created payload to prevent immediate duplicates
        session['last_gatepass_request'] = payload_key

        # --- Email Notification to Warden ---
        try:
            from models import Staff
            from utils.email import send_email
            
            # Find warden for this student's branch and year
            student_branch = session['student_branch']
            student_year = session['student_year']
            student_name = session['student_name']
            
            warden = Staff.query.filter_by(role='Warden', branch=student_branch, year=student_year).first()
            if warden and warden.email:
                subject = f"New Gatepass Request: {student_name} ({enrollment})"
                body = f"""
                <h3>New Gatepass Request</h3>
                <p><strong>Student:</strong> {student_name} ({enrollment})</p>
                <p><strong>Place:</strong> {place}</p>
                <p><strong>Out Date:</strong> {out_date}</p>
                <p><strong>In Date:</strong> {in_date}</p>
                <p><strong>Reason:</strong> {reason}</p>
                <br>
                <p>Please login to the portal to approve or reject this request.</p>
                """
                send_email(warden.email, subject, body)
        except Exception as e:
            print(f"Error sending email to Warden: {e}")
        # ------------------------------------

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
    requests_list = GatepassRequest.query.filter_by(enrollment_no=enrollment).order_by(
        GatepassRequest.request_id.desc()
    ).all()
    return render_template('student/request_status.html', requests=requests_list)



# ===================== NOTICE BOARD =====================
@student_bp.route('/notices')
def notices():
    if 'student_enrollment' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('student.login'))

    notices_raw = Notice.query.order_by(Notice.notice_id.desc()).all()

    # Build view-friendly objects with time and sender name/role
    notices_list = []
    for n in notices_raw:
        # Format timestamp
        dt_str = n.sent_at.strftime('%Y-%m-%d %H:%M') if n.sent_at else ''

        # Resolve sender display label
        sender_label = 'Unknown'
        if n.sender_type == 'Staff' and n.staff_sender:
            sender_label = f"{n.staff_sender.full_name} ({n.staff_sender.role})"
        elif n.sender_type == 'Security' and n.guard_sender:
            sender_label = f"{n.guard_sender.full_name} (Security)"

        notices_list.append({
            'datetime_posted': dt_str,
            'sender_role': sender_label,
            'message': n.message,
        })

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

import re
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, SecurityGuard, GatepassRequest, GatepassEntry, Notice

security_bp = Blueprint('security', __name__)

FINE_PER_DAY = 50


def calculate_late_and_fine(expected_in_dt, actual_in_dt):
    """Calculate late days and fine based on expected vs actual in datetime."""
    try:
        late_delta = actual_in_dt - expected_in_dt
        late_days = late_delta.days
        if late_days > 0:
            return late_days, late_days * FINE_PER_DAY, 'Unpaid'
        return 0, 0, 'No Fine'
    except Exception:
        return 0, 0, 'No Fine'


# ===================== LOGIN =====================
@security_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        mobile = request.form.get('mobile', '').strip()
        password = request.form.get('password', '').strip()

        errors = []
        if not mobile:
            errors.append('Mobile number is required.')
        elif not re.match(r'^\d{10}$', mobile):
            errors.append('Mobile number must be exactly 10 digits.')
        if not password:
            errors.append('Password is required.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('security/login_register.html', mode='login')

        try:
            guard = SecurityGuard.query.filter_by(
                mobile_no=mobile
            ).first()
        except Exception:
            db.session.rollback()
            flash('Something went wrong. Please try again.', 'error')
            return render_template('security/login_register.html', mode='login')

        if not guard or not check_password_hash(guard.password_hash, password):
            flash('Invalid mobile number or password.', 'error')
            return render_template('security/login_register.html', mode='login')

        session.permanent = True
        session['guard_id'] = guard.guard_id
        session['security_mobile'] = guard.mobile_no
        session['security_name'] = guard.full_name
        flash(f'Welcome, {guard.full_name}!', 'success')
        return redirect(url_for('security.dashboard'))

    return render_template('security/login_register.html', mode='login')


# ===================== DASHBOARD =====================
@security_bp.route('/dashboard')
def dashboard():
    if 'security_mobile' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('security.login'))
        
    today = datetime.utcnow().date()
    
    # 1. Students Not Returned
    # Approved requests with actual_out_datetime but no actual_in_datetime
    pending_return_entries = GatepassEntry.query.filter(
        GatepassEntry.actual_out_datetime != None,
        GatepassEntry.actual_in_datetime == None
    ).all()
    
    pending_return = [entry.request for entry in pending_return_entries]

    # 2. Total Out Today
    out_today = GatepassEntry.query.filter(
        db.func.date(GatepassEntry.actual_out_datetime) == today
    ).count()

    # 3. Total In Today
    in_today = GatepassEntry.query.filter(
        db.func.date(GatepassEntry.actual_in_datetime) == today
    ).count()
        
    metrics = {
        'out_today': out_today,
        'in_today': in_today
    }

    return render_template('security/dashboard.html',
                           security_name=session['security_name'],
                           metrics=metrics,
                           pending_return=pending_return)


# ===================== GATEPASS ENTRY =====================
@security_bp.route('/gatepass-entry', methods=['GET', 'POST'])
def gatepass_entry():
    if 'security_mobile' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('security.login'))

    # Pre-fill from QR scan URL parameters
    prefill = {
        'request_id': request.args.get('request_id', ''),
        'enrollment': request.args.get('enrollment', ''),
        'out_date': request.args.get('out_date', ''),
        'in_date': request.args.get('in_date', ''),
        'place': request.args.get('place', ''),
    }

    if request.method == 'POST':
        request_id = request.form.get('request_id', '').strip()
        enrollment = request.form.get('enrollment', '').strip()
        actual_out = request.form.get('actual_out', '').strip()
        actual_in = request.form.get('actual_in', '').strip()
        payment_mode = request.form.get('payment_mode', '').strip()
        verified_by = request.form.get('verified_by', '').strip()

        errors = []
        if not enrollment:
            errors.append('Enrollment number is required.')

        date_pattern = r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$'
        if not actual_out:
            errors.append('Actual OUT DateTime is required.')
        elif not re.match(date_pattern, actual_out):
            errors.append('OUT DateTime must be in YYYY-MM-DD HH:MM format.')
        if not actual_in:
            errors.append('Actual IN DateTime is required.')
        elif not re.match(date_pattern, actual_in):
            errors.append('IN DateTime must be in YYYY-MM-DD HH:MM format.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('security/gatepass_entry.html', prefill=prefill)

        if not request_id:
            # Fallback to finding latest if request_id isn't provided
            gatepass = GatepassRequest.query.filter_by(
                enrollment_no=enrollment, status='Approved'
            ).order_by(GatepassRequest.request_id.desc()).first()
        else:
            gatepass = GatepassRequest.query.get(request_id)

        if not gatepass or gatepass.status != 'Approved':
            flash('No approved gatepass request found for this input.', 'error')
            return render_template('security/gatepass_entry.html', prefill=prefill)

        actual_out_dt = datetime.strptime(actual_out, '%Y-%m-%d %H:%M')
        actual_in_dt = datetime.strptime(actual_in, '%Y-%m-%d %H:%M')

        late_days, fine, fine_status = calculate_late_and_fine(gatepass.in_date, actual_in_dt)

        # Create or update GatepassEntry
        entry = gatepass.entry
        if not entry:
            entry = GatepassEntry(
                request_id=gatepass.request_id,
                guard_id=session['guard_id'],
            )
            db.session.add(entry)
            
        entry.actual_out_datetime = actual_out_dt
        entry.actual_in_datetime = actual_in_dt
        entry.late_days = late_days
        entry.fine_amount = fine
        entry.fine_status = fine_status
        entry.payment_mode = payment_mode
        # Verified by is no longer a separate field, implicitly verified by guard_id

        db.session.commit()

        flash(f'OUT/IN marked successfully! Late: {late_days} days | Fine: ₹{fine} | Status: {fine_status}', 'success')
        return redirect(url_for('security.dashboard'))

    return render_template('security/gatepass_entry.html', prefill=prefill)


# ===================== GATEPASS REGISTER =====================
@security_bp.route('/gatepass-register')
def gatepass_register():
    if 'security_mobile' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('security.login'))

    search = request.args.get('search', '').strip()
    if search:
        requests_list = GatepassRequest.query.filter(
            GatepassRequest.enrollment_no.ilike(f'%{search}%')
        ).order_by(GatepassRequest.request_id.desc()).all()
    else:
        requests_list = GatepassRequest.query.order_by(GatepassRequest.request_id.desc()).all()

    return render_template('security/gatepass_register.html',
                           requests=requests_list, search=search)


# ===================== SEND NOTICE =====================
@security_bp.route('/send-notice', methods=['GET', 'POST'])
def send_notice():
    if 'security_mobile' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('security.login'))

    if request.method == 'POST':
        message = request.form.get('message', '').strip()
        if not message:
            flash('Notice message is required.', 'error')
            return render_template('security/send_notice.html')

        notice = Notice(
            sender_id=session['guard_id'],
            sender_type='Security',
            message=message,
            sent_at=datetime.utcnow()
        )
        db.session.add(notice)
        db.session.commit()

        # --- Email Notification to Students ---
        try:
            from models import Student
            from utils.email import send_email
            security_name = session.get('security_name')
            
            # Security notices usually go to everyone, or we can just blast it to all active students
            target_students = Student.query.all()
            receivers = [s.email for s in target_students if s.email]
            
            if receivers:
                subject = f"Security Notice from {security_name}"
                body = f"""
                <h3>New Security Notice</h3>
                <p><strong>From:</strong> {security_name} (Security Guard)</p>
                <p><strong>Message:</strong></p>
                <blockquote style="border-left: 4px solid #f87171; padding-left: 10px; color: #555;">
                    {message}
                </blockquote>
                <br>
                <p>Please ensure you comply with the hostel security guidelines.</p>
                """
                # Send to all relevant students
                for email in receivers:
                    send_email(email, subject, body)
        except Exception as e:
            print(f"Error sending security notice emails: {e}")
        # ----------------------------------------

        flash('Notice sent successfully!', 'success')
        return redirect(url_for('security.dashboard'))

    return render_template('security/send_notice.html')


# ===================== VIEW NOTICES =====================
@security_bp.route('/notices')
def view_notices():
    if 'security_mobile' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('security.login'))

    notices_list = Notice.query.order_by(Notice.notice_id.desc()).all()
    return render_template('security/notices.html', notices=notices_list)


# ===================== LOGOUT =====================
@security_bp.route('/logout')
def logout():
    for key in ['guard_id', 'security_mobile', 'security_name']:
        session.pop(key, None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('home.index'))

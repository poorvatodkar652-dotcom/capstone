import re
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from models import db, SecurityGuard, GatepassRequest, Notice

security_bp = Blueprint('security', __name__)

FINE_PER_DAY = 50


def calculate_late_and_fine(expected_in, actual_in):
    """Calculate late days and fine based on expected vs actual in date."""
    try:
        exp = datetime.strptime(expected_in.split()[0], '%Y-%m-%d')
        act = datetime.strptime(actual_in.split()[0], '%Y-%m-%d')
        late = (act - exp).days
        if late > 0:
            return late, late * FINE_PER_DAY, 'Unpaid'
        return 0, 0, 'No Fine'
    except (ValueError, IndexError):
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

        guard = SecurityGuard.query.filter_by(
            mobile_number=mobile, password=password
        ).first()

        if not guard:
            flash('Invalid mobile number or password.', 'error')
            return render_template('security/login_register.html', mode='login')

        session['security_mobile'] = guard.mobile_number
        session['security_name'] = guard.name
        flash(f'Welcome, {guard.name}!', 'success')
        return redirect(url_for('security.dashboard'))

    return render_template('security/login_register.html', mode='login')


# ===================== REGISTER =====================
@security_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        mobile = request.form.get('mobile', '').strip()
        dob = request.form.get('dob', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        gender = request.form.get('gender', '').strip()

        errors = []
        if not name:
            errors.append('Name is required.')
        elif len(name) < 2:
            errors.append('Name must be at least 2 characters.')
        if not mobile:
            errors.append('Mobile number is required.')
        elif not re.match(r'^\d{10}$', mobile):
            errors.append('Mobile number must be exactly 10 digits.')
        if not dob:
            errors.append('Date of Birth is required.')
        elif not re.match(r'^\d{4}-\d{2}-\d{2}$', dob):
            errors.append('DOB must be in YYYY-MM-DD format.')
        if not password:
            errors.append('Password is required.')
        elif len(password) < 4:
            errors.append('Password must be at least 4 characters.')
        if password != confirm_password:
            errors.append('Passwords do not match.')
        if not gender:
            errors.append('Gender is required.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('security/login_register.html', mode='register')

        existing = SecurityGuard.query.get(mobile)
        if existing:
            flash('This mobile number is already registered.', 'error')
            return render_template('security/login_register.html', mode='register')

        new_guard = SecurityGuard(
            mobile_number=mobile,
            name=name,
            dob=dob,
            password=password,
            gender=gender
        )
        db.session.add(new_guard)
        db.session.commit()

        flash('Security guard registered successfully! You can now login.', 'success')
        return redirect(url_for('security.login'))

    return render_template('security/login_register.html', mode='register')


# ===================== DASHBOARD =====================
@security_bp.route('/dashboard')
def dashboard():
    if 'security_mobile' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('security.login'))
    return render_template('security/dashboard.html',
                           security_name=session['security_name'])


# ===================== GATEPASS ENTRY =====================
@security_bp.route('/gatepass-entry', methods=['GET', 'POST'])
def gatepass_entry():
    if 'security_mobile' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('security.login'))

    # Pre-fill from QR scan URL parameters
    prefill = {
        'enrollment': request.args.get('enrollment', ''),
        'actual_out': request.args.get('out_date', ''),
        'actual_in': request.args.get('in_date', ''),
        'place': request.args.get('place', ''),
    }

    if request.method == 'POST':
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

        # Find the latest approved request for this student
        gatepass = GatepassRequest.query.filter_by(
            enrollment=enrollment, status='Approved'
        ).order_by(GatepassRequest.id.desc()).first()

        if not gatepass:
            flash('No approved gatepass request found for this enrollment.', 'error')
            return render_template('security/gatepass_entry.html', prefill=prefill)

        late_days, fine, fine_status = calculate_late_and_fine(gatepass.in_date, actual_in)

        gatepass.actual_out_date = actual_out
        gatepass.actual_in_date = actual_in
        gatepass.late_days = late_days
        gatepass.fine = fine
        gatepass.fine_status = fine_status
        gatepass.payment_mode = payment_mode
        gatepass.verified_by = verified_by
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
            GatepassRequest.enrollment.ilike(f'%{search}%')
        ).order_by(GatepassRequest.id.desc()).all()
    else:
        requests_list = GatepassRequest.query.order_by(GatepassRequest.id.desc()).all()

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
            datetime_posted=datetime.now().strftime('%Y-%m-%d %H:%M'),
            sender_role='Security',
            message=message
        )
        db.session.add(notice)
        db.session.commit()
        flash('Notice sent successfully!', 'success')
        return redirect(url_for('security.dashboard'))

    return render_template('security/send_notice.html')


# ===================== VIEW NOTICES =====================
@security_bp.route('/notices')
def view_notices():
    if 'security_mobile' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('security.login'))

    notices_list = Notice.query.order_by(Notice.id.desc()).all()
    return render_template('security/notices.html', notices=notices_list)


# ===================== LOGOUT =====================
@security_bp.route('/logout')
def logout():
    session.pop('security_mobile', None)
    session.pop('security_name', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('home.index'))

import re
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

from models import db, SecurityGuard, GatepassRequest, GatepassEntry, Notice

security_bp = Blueprint('security', __name__)

FINE_PER_DAY = 50

@security_bp.before_request
def block_student_access():
    # Prevent logged-in students from accessing security module routes
    if session.get('student_enrollment') and not session.get('guard_id'):
        flash('Access denied.', 'error')
        return redirect(url_for('student.dashboard'))


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


# ===================== VERIFY CODE =====================
@security_bp.route('/verify-code', methods=['POST'])
def verify_code():
    if 'security_mobile' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('security.login'))

    auth_code = request.form.get('auth_code', '').strip().upper()
    if not auth_code:
        flash('Please enter an authorization code.', 'error')
        return redirect(url_for('security.dashboard'))

    gatepass = GatepassRequest.query.filter_by(auth_code=auth_code).first()

    if not gatepass:
        flash('Invalid Authorization Code.', 'error')
        return redirect(url_for('security.dashboard'))

    if gatepass.status != 'Approved':
        flash('Gatepass Request is not approved or has already been used.', 'error')
        return redirect(url_for('security.dashboard'))

    # Redirect to gatepass entry with pre-filled details
    from urllib.parse import urlencode
    qr_params = urlencode({
        'request_id': gatepass.request_id,
        'enrollment': gatepass.enrollment_no,
        'out_date': gatepass.out_date.strftime('%Y-%m-%d %H:%M:%S'),
        'in_date': gatepass.in_date.strftime('%Y-%m-%d %H:%M:%S'),
        'place': gatepass.place
    })
    return redirect(f"{url_for('security.gatepass_entry')}?{qr_params}")



# ===================== GATEPASS ENTRY =====================
@security_bp.route('/gatepass-entry', methods=['GET', 'POST'])
def gatepass_entry():
    if 'security_mobile' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('security.login'))

    # Pre-fill from QR scan URL parameters (and database)
    prefill = {
        'request_id': request.args.get('request_id', '').strip(),
        'enrollment': request.args.get('enrollment', '').strip(),
        'actual_out': '',
        'actual_in': '',
        'place': request.args.get('place', '').strip(),
        'expected_in': '',
        'entry_state': 'none',  # none | out (out recorded, waiting for in) | done
    }

    # If we have a request_id, use it to pull expected out/in from DB and
    # prefill the OUT datetime from gatepass.out_date and IN as current time.
    if prefill['request_id']:
        try:
            gp = GatepassRequest.query.get(int(prefill['request_id']))
        except Exception:
            gp = None

        if gp:
            prefill['enrollment'] = gp.enrollment_no
            prefill['place'] = gp.place
            # Expected OUT from request
            if gp.out_date:
                prefill['actual_out'] = gp.out_date.strftime('%Y-%m-%d %H:%M')
            if gp.in_date:
                prefill['expected_in'] = gp.in_date.strftime('%Y-%m-%d %H:%M')
            # Default IN to "now" so guard can just submit
            prefill['actual_in'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M')
            if gp.entry:
                if gp.entry.actual_out_datetime and not gp.entry.actual_in_datetime:
                    prefill['entry_state'] = 'out'
                elif gp.entry.actual_out_datetime and gp.entry.actual_in_datetime:
                    prefill['entry_state'] = 'done'

    if request.method == 'POST':
        action = request.form.get('action', '').strip().lower()  # out | in
        request_id = request.form.get('request_id', '').strip()
        enrollment = request.form.get('enrollment', '').strip()
        actual_out = request.form.get('actual_out', '').strip()
        actual_in = request.form.get('actual_in', '').strip()
        payment_mode = request.form.get('payment_mode', '').strip()
        fine_amount_input = request.form.get('fine_amount', '').strip()
        fine_status_input = request.form.get('fine_status', '').strip()  # Paid/Unpaid/''(auto)

        # Duplicate-submission guard for entry action
        entry_payload = f"{action}|{request_id}|{enrollment}|{actual_out}|{actual_in}|{payment_mode}|{fine_status_input}|{fine_amount_input}"
        if session.get('last_gatepass_entry') == entry_payload:
            flash('This entry was already saved.', 'info')
            return redirect(url_for('security.dashboard'))

        errors = []
        if not enrollment:
            errors.append('Enrollment number is required.')
        if action not in ('out', 'in'):
            errors.append('Invalid action. Please try again.')

        # Accept both "YYYY-MM-DD HH:MM" and HTML datetime-local "YYYY-MM-DDTHH:MM"
        date_pattern = r'^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}$'
        if action == 'out':
            if not actual_out:
                errors.append('Actual OUT DateTime is required.')
            elif not re.match(date_pattern, actual_out):
                errors.append('OUT DateTime must be in YYYY-MM-DD HH:MM format.')
        elif action == 'in':
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

        # Create or update GatepassEntry
        entry = gatepass.entry
        if not entry:
            entry = GatepassEntry(
                request_id=gatepass.request_id,
                guard_id=session['guard_id'],
            )
            db.session.add(entry)

        # Apply the correct action
        if action == 'out':
            if entry.actual_out_datetime:
                flash('OUT time is already recorded for this request.', 'info')
                return redirect(url_for('security.dashboard'))

            actual_out_dt = datetime.strptime(actual_out.replace('T', ' '), '%Y-%m-%d %H:%M')
            entry.actual_out_datetime = actual_out_dt
            entry.guard_id = session['guard_id']
            db.session.commit()

            session['last_gatepass_entry'] = entry_payload
            flash('OUT marked successfully.', 'success')
            return redirect(url_for('security.dashboard'))

        # action == 'in'
        if not entry.actual_out_datetime:
            flash('Cannot mark IN before OUT is recorded for this request.', 'error')
            return render_template('security/gatepass_entry.html', prefill=prefill)

        if entry.actual_in_datetime:
            flash('IN time is already recorded for this request.', 'info')
            return redirect(url_for('security.dashboard'))

        actual_in_dt = datetime.strptime(actual_in.replace('T', ' '), '%Y-%m-%d %H:%M')

        late_days, fine, fine_status = calculate_late_and_fine(gatepass.in_date, actual_in_dt)

        # If guard provided a manual fine amount, override the calculated fine
        if fine_amount_input:
            try:
                manual_fine = float(fine_amount_input)
                if manual_fine < 0:
                    raise ValueError
                fine = manual_fine
            except ValueError:
                flash('Invalid fine amount. Using automatically calculated fine instead.', 'error')

        # Allow manual fine status override (Paid/Unpaid) for late cases
        if fine_status_input in ('Paid', 'Unpaid'):
            fine_status = fine_status_input

        entry.actual_in_datetime = actual_in_dt
        entry.late_days = late_days
        entry.fine_amount = fine
        entry.fine_status = fine_status
        entry.payment_mode = payment_mode
        entry.guard_id = session['guard_id']

        db.session.commit()

        # Remember last successfully saved entry payload
        session['last_gatepass_entry'] = entry_payload

        flash(f'IN marked successfully! Late: {late_days} days | Fine: ₹{fine} | Status: {fine_status}', 'success')
        return redirect(url_for('security.dashboard'))

    return render_template('security/gatepass_entry.html', prefill=prefill)


# ===================== GATEPASS REGISTER =====================
@security_bp.route('/gatepass-register')
def gatepass_register():
    if 'security_mobile' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('security.login'))

    search = request.args.get('search', '').strip()

    # Security should only see Approved requests (those they can verify)
    base_query = GatepassRequest.query.filter_by(status='Approved')
    if search:
        base_query = base_query.filter(
            GatepassRequest.enrollment_no.ilike(f'%{search}%')
        )

    requests_list = base_query.order_by(GatepassRequest.request_id.desc()).all()

    return render_template('security/gatepass_register.html',
                           requests=requests_list, search=search)


# ===================== EXPORT GATEPASS =====================
@security_bp.route('/export-gatepass')
def export_gatepass():
    if 'security_mobile' not in session:
        flash('Please login first.', 'error')
        return redirect(url_for('security.login'))

    status_filter = request.args.get('filter', 'All').strip()
    enrollment_filter = request.args.get('enrollment', '').strip()
    
    query = db.session.query(GatepassEntry).join(GatepassRequest)
    
    if status_filter == 'Out':
        # Students who are currently Out (have not returned)
        query = query.filter(
            GatepassEntry.actual_out_datetime != None,
            GatepassEntry.actual_in_datetime == None
        )
    elif status_filter == 'In':
        # Students who have returned today (or ever if we adjust logic, sticking to ever for report)
        query = query.filter(
            GatepassEntry.actual_in_datetime != None
        )
        
    if enrollment_filter:
        query = query.filter(GatepassRequest.enrollment_no.ilike(f'%{enrollment_filter}%'))
        
    entries = query.order_by(GatepassEntry.entry_id.desc()).all()
    
    import pandas as pd
    from io import BytesIO
    from flask import send_file
    
    data = []
    for entry in entries:
        req = entry.request
        data.append({
            'Entry ID': entry.entry_id,
            'Request ID': req.request_id,
            'Enrollment No': req.enrollment_no,
            'Student Name': req.student.full_name,
            'Place': req.place,
            'Expected Out': req.out_date.strftime('%Y-%m-%d %H:%M') if req.out_date else '',
            'Actual Out': entry.actual_out_datetime.strftime('%Y-%m-%d %H:%M') if entry.actual_out_datetime else '',
            'Expected In': req.in_date.strftime('%Y-%m-%d %H:%M') if req.in_date else '',
            'Actual In': entry.actual_in_datetime.strftime('%Y-%m-%d %H:%M') if entry.actual_in_datetime else 'Still Out',
            'Late Days': entry.late_days,
            'Fine Amount': entry.fine_amount,
            'Fine Status': entry.fine_status,
            'Payment Mode': entry.payment_mode or ''
        })
        
    df = pd.DataFrame(data)
    
    output = BytesIO()
    csv_data = df.to_csv(index=False).encode('utf-8')
    output.write(csv_data)
    output.seek(0)
    
    filename = f"gatepass_log_{status_filter.lower()}_{datetime.now().strftime('%Y%m%d%H%M')}.csv"
    
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )


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
            
            # Security notices go to all students (no branch/year mapping for guards)
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

    notices_raw = Notice.query.order_by(Notice.notice_id.desc()).all()

    notices_list = []
    for n in notices_raw:
        dt_str = n.sent_at.strftime('%Y-%m-%d %H:%M') if n.sent_at else ''

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

    return render_template('security/notices.html', notices=notices_list)


# ===================== LOGOUT =====================
@security_bp.route('/logout')
def logout():
    for key in ['guard_id', 'security_mobile', 'security_name']:
        session.pop(key, None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('home.index'))

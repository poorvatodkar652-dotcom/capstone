from flask import Blueprint, render_template, request, redirect, url_for, session, flash

home_bp = Blueprint('home', __name__)

ADMIN_PASSWORD = 'GRWPT@416312'


@home_bp.route('/')
def index():
    return render_template('home.html')


@home_bp.route('/admin-login', methods=['POST'])
def admin_login():
    password = request.form.get('password', '').strip()
    if password == ADMIN_PASSWORD:
        session['admin'] = True
        flash('Admin login successful!', 'success')
        return redirect(url_for('home.admin_panel'))
    else:
        flash('Invalid admin password!', 'error')
        return redirect(url_for('home.index'))


@home_bp.route('/admin')
def admin_panel():
    if not session.get('admin'):
        flash('Please login as admin first.', 'error')
        return redirect(url_for('home.index'))
    return render_template('admin_panel.html')


@home_bp.route('/admin-logout')
def admin_logout():
    session.pop('admin', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('home.index'))


@home_bp.route('/admin/add-staff', methods=['GET', 'POST'])
def add_staff():
    if not session.get('admin'):
        flash('Please login as admin first.', 'error')
        return redirect(url_for('home.index'))
        
    from models import Staff, db
    from werkzeug.security import generate_password_hash
    import re
    
    BRANCHES = ['Computer Engineering', 'Civil Engineering', 'Electrical Engineering', 'Mechanical Engineering', 'Electronics Engineering']
    YEARS = ['1st Year', '2nd Year', '3rd Year']

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        mobile = request.form.get('mobile', '').strip()
        dob = request.form.get('dob', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        role = request.form.get('role', '').strip()
        branch = request.form.get('branch', '').strip()
        year = request.form.get('year', '').strip()

        errors = []
        if not name: errors.append('Name is required.')
        elif len(name) < 2: errors.append('Name must be at least 2 characters.')
        if not email: errors.append('Email is required.')
        elif not re.match(r'^[^@]+@[^@]+\.[^@]+$', email): errors.append('Invalid email format.')
        if not mobile: errors.append('Mobile number is required.')
        elif not re.match(r'^\d{10}$', mobile): errors.append('Mobile number must be exactly 10 digits.')
        if not dob: errors.append('Date of Birth is required.')
        elif not re.match(r'^\d{4}-\d{2}-\d{2}$', dob): errors.append('DOB must be in YYYY-MM-DD format.')
        if not password: errors.append('Password is required.')
        elif len(password) < 4: errors.append('Password must be at least 4 characters.')
        if password != confirm_password: errors.append('Passwords do not match.')
        if not role: errors.append('Role is required.')
        if not branch: errors.append('Branch is required.')
        if role == 'Warden' and not year: errors.append('Year is required for Warden.')

        if errors:
            for e in errors: flash(e, 'error')
            return render_template('admin/add_staff.html', branches=BRANCHES, years=YEARS)

        try:
            existing = Staff.query.filter_by(mobile_no=mobile).first()
            if existing:
                flash('This mobile number is already registered for a staff member.', 'error')
                return render_template('admin/add_staff.html', branches=BRANCHES, years=YEARS)

            new_staff = Staff(
                full_name=name,
                email=email,
                mobile_no=mobile,
                password_hash=generate_password_hash(password),
                role=role,
                branch=branch,
                year=year if role != 'HOD' else None
            )
            db.session.add(new_staff)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error adding staff: {e}")
            flash('Something went wrong. Please try again.', 'error')
            return render_template('admin/add_staff.html', branches=BRANCHES, years=YEARS)

        flash('Staff member successfully registered!', 'success')
        return redirect(url_for('home.admin_panel'))

    return render_template('admin/add_staff.html', branches=BRANCHES, years=YEARS)


@home_bp.route('/admin/add-security', methods=['GET', 'POST'])
def add_security():
    if not session.get('admin'):
        flash('Please login as admin first.', 'error')
        return redirect(url_for('home.index'))
        
    from models import SecurityGuard, db
    from werkzeug.security import generate_password_hash
    import re
    from datetime import datetime
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        mobile = request.form.get('mobile', '').strip()
        dob = request.form.get('dob', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        gender = request.form.get('gender', '').strip()

        errors = []
        if not name: errors.append('Name is required.')
        elif len(name) < 2: errors.append('Name must be at least 2 characters.')
        if not email: errors.append('Email is required.')
        elif not re.match(r'^[^@]+@[^@]+\.[^@]+$', email): errors.append('Invalid email format.')
        if not mobile: errors.append('Mobile number is required.')
        elif not re.match(r'^\d{10}$', mobile): errors.append('Mobile number must be exactly 10 digits.')
        if not dob: errors.append('Date of Birth is required.')
        elif not re.match(r'^\d{4}-\d{2}-\d{2}$', dob): errors.append('DOB must be in YYYY-MM-DD format.')
        if not password: errors.append('Password is required.')
        elif len(password) < 4: errors.append('Password must be at least 4 characters.')
        if password != confirm_password: errors.append('Passwords do not match.')
        if not gender: errors.append('Gender is required.')

        if errors:
            for e in errors: flash(e, 'error')
            return render_template('admin/add_security.html')

        try:
            existing = SecurityGuard.query.filter_by(mobile_no=mobile).first()
            if existing:
                flash('This mobile number is already registered for a security guard.', 'error')
                return render_template('admin/add_security.html')

            new_guard = SecurityGuard(
                full_name=name,
                email=email,
                mobile_no=mobile,
                date_of_birth=datetime.strptime(dob, '%Y-%m-%d').date(),
                password_hash=generate_password_hash(password),
                gender=gender
            )
            db.session.add(new_guard)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error adding security guard: {e}")
            flash('Something went wrong. Please try again.', 'error')
            return render_template('admin/add_security.html')

        flash('Security guard successfully registered!', 'success')
        return redirect(url_for('home.admin_panel'))

    return render_template('admin/add_security.html')

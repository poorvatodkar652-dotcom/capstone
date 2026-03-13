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

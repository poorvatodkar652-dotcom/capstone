import re
from flask import Blueprint, render_template, request, redirect, url_for, session, flash

from models import db, Student

admission_bp = Blueprint('admission', __name__)

BRANCHES = ["CO", "IT", "ENTC", "EJ", "DD", "CE"]
YEARS = ["FY", "SY", "TY"]


@admission_bp.route('/add-student', methods=['GET', 'POST'])
def add_student():
    if not session.get('admin'):
        flash('Admin access required.', 'error')
        return redirect(url_for('home.index'))

    if request.method == 'POST':
        enrollment = request.form.get('enrollment', '').strip()
        name = request.form.get('name', '').strip()
        hostel = request.form.get('hostel', '').strip()
        room = request.form.get('room', '').strip()
        branch = request.form.get('branch', '').strip()
        year = request.form.get('year', '').strip()
        password = request.form.get('password', '').strip()
        total_fees_str = request.form.get('total_fees', '').strip()
        paid_fees_str = request.form.get('paid_fees', '').strip()

        errors = []
        if not enrollment:
            errors.append('Enrollment number is required.')
        if not name:
            errors.append('Student name is required.')
        elif len(name) < 2:
            errors.append('Student name must be at least 2 characters.')
        if not hostel:
            errors.append('Hostel name is required.')
        if not room:
            errors.append('Room number is required.')
        if not branch:
            errors.append('Branch is required.')
        if not year:
            errors.append('Year is required.')
        if not password:
            errors.append('Password is required.')
        elif len(password) < 4:
            errors.append('Password must be at least 4 characters.')

        # Validate fees
        total_fees = 0.0
        paid_fees = 0.0
        if not total_fees_str:
            errors.append('Total fees is required.')
        else:
            try:
                total_fees = float(total_fees_str)
                if total_fees < 0:
                    errors.append('Total fees cannot be negative.')
            except ValueError:
                errors.append('Total fees must be a numeric value.')

        if not paid_fees_str:
            errors.append('Paid fees is required.')
        else:
            try:
                paid_fees = float(paid_fees_str)
                if paid_fees < 0:
                    errors.append('Paid fees cannot be negative.')
            except ValueError:
                errors.append('Paid fees must be a numeric value.')

        if not errors and paid_fees > total_fees:
            errors.append('Paid fees cannot exceed total fees.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('admission/add_student.html',
                                   branches=BRANCHES, years=YEARS)

        # Check duplicate
        existing = Student.query.get(enrollment)
        if existing:
            flash('A student with this enrollment number already exists.', 'error')
            return render_template('admission/add_student.html',
                                   branches=BRANCHES, years=YEARS)

        remaining = total_fees - paid_fees
        if remaining == 0:
            status = 'Paid'
        elif paid_fees > 0:
            status = 'Partial'
        else:
            status = 'Due'

        new_student = Student(
            enrollment=enrollment,
            student_name=name,
            hostel_name=hostel,
            room_number=room,
            branch=branch,
            year=year,
            password=password,
            total_fees=total_fees,
            paid_fees=paid_fees,
            remaining_fees=remaining,
            fees_status=status
        )
        db.session.add(new_student)
        db.session.commit()

        flash('✅ Student added successfully!', 'success')
        return render_template('admission/add_student.html',
                               branches=BRANCHES, years=YEARS)

    return render_template('admission/add_student.html',
                           branches=BRANCHES, years=YEARS)

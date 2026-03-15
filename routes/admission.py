import re
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash

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
        email = request.form.get('email', '').strip()
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
        if not email:
            errors.append('Student email is required.')
        elif not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            errors.append('Invalid email format for student.')
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

        try:
            # Check duplicate
            existing = Student.query.filter_by(enrollment_no=enrollment).first()
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
                enrollment_no=enrollment,
                full_name=name,
                email=email,
                hostel_name=hostel,
                room_number=room,
                branch=branch,
                year=year,
                password_hash=generate_password_hash(password),
                total_fees=total_fees,
                paid_fees=paid_fees,
                remaining_fees=remaining,
                fee_status=status
            )
            db.session.add(new_student)
            db.session.commit()
        except Exception:
            db.session.rollback()
            flash('Something went wrong. Please try again.', 'error')
            return render_template('admission/add_student.html',
                                   branches=BRANCHES, years=YEARS)

        flash('✅ Student added successfully!', 'success')
        return render_template('admission/add_student.html',
                               branches=BRANCHES, years=YEARS)

    return render_template('admission/add_student.html',
                           branches=BRANCHES, years=YEARS)

# ===================== EXPORT STUDENTS =====================
@admission_bp.route('/export-students')
def export_students():
    if not session.get('admin'):
        flash('Admin access required.', 'error')
        return redirect(url_for('home.admin_login'))

    students = Student.query.order_by(Student.student_id.desc()).all()
    
    import pandas as pd
    from io import BytesIO
    from flask import send_file
    from datetime import datetime
    
    data = []
    for s in students:
        data.append({
            'Student ID': s.student_id,
            'Enrollment No': s.enrollment_no,
            'Name': s.full_name,
            'Email': s.email,
            'Hostel': s.hostel_name,
            'Room': s.room_number,
            'Branch': s.branch,
            'Year': s.year,
            'Total Fees': s.total_fees,
            'Paid Fees': s.paid_fees,
            'Remaining Fees': s.remaining_fees,
            'Fee Status': s.fee_status,
            'Registered On': s.created_at.strftime('%Y-%m-%d %H:%M') if s.created_at else ''
        })
        
    df = pd.DataFrame(data)
    
    output = BytesIO()
    csv_data = df.to_csv(index=False).encode('utf-8')
    output.write(csv_data)
    output.seek(0)
    
    filename = f"all_students_{datetime.now().strftime('%Y%m%d%H%M')}.csv"
    
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )

# ===================== IMPORT STUDENTS =====================
@admission_bp.route('/import-students', methods=['POST'])
def import_students():
    if not session.get('admin'):
        flash('Admin access required.', 'error')
        return redirect(url_for('home.admin_login'))

    if 'excel_file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('admission.add_student'))

    file = request.files['excel_file']
    
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('admission.add_student'))

    if file and file.filename.endswith('.xlsx'):
        try:
            import pandas as pd
            
            # Read the excel file
            df = pd.read_excel(file)
            
            # Expected columns
            required_cols = ['Enrollment No', 'Name', 'Email', 'Hostel', 'Room', 'Branch', 'Year', 'Total Fees', 'Paid Fees']
            
            actual_cols = df.columns.tolist()
            col_map = {}
            for req in required_cols:
                for act in actual_cols:
                    if str(act).strip().lower() == req.lower():
                        col_map[req] = act
                        break
                if req not in col_map:
                    flash(f'Missing required column: {req}', 'error')
                    return redirect(url_for('admission.add_student'))

            success_count = 0
            duplicate_count = 0
            error_count = 0
            
            for index, row in df.iterrows():
                try:
                    enrollment = str(row[col_map['Enrollment No']]).strip()
                    if not enrollment or enrollment == 'nan':
                        continue
                        
                    name = str(row[col_map['Name']]).strip()
                    email = str(row[col_map['Email']]).strip()
                    hostel = str(row[col_map['Hostel']]).strip()
                    room = str(row[col_map['Room']]).strip()
                    branch = str(row[col_map['Branch']]).strip()
                    year = str(row[col_map['Year']]).strip()
                    
                    total_fees = float(row[col_map['Total Fees']]) if not pd.isna(row[col_map['Total Fees']]) else 0.0
                    paid_fees = float(row[col_map['Paid Fees']]) if not pd.isna(row[col_map['Paid Fees']]) else 0.0
                    
                    if not all([enrollment, name, email, hostel, room, branch, year]):
                        error_count += 1
                        continue
                        
                    existing = Student.query.filter_by(enrollment_no=enrollment).first()
                    if existing:
                        duplicate_count += 1
                        continue
                        
                    remaining = max(0.0, total_fees - paid_fees)
                    if remaining == 0:
                        status = 'Paid'
                    elif paid_fees > 0:
                        status = 'Partial'
                    else:
                        status = 'Due'
                        
                    new_student = Student(
                        enrollment_no=enrollment,
                        full_name=name,
                        email=email,
                        hostel_name=hostel,
                        room_number=room,
                        branch=branch,
                        year=year,
                        password_hash=generate_password_hash(enrollment),
                        total_fees=total_fees,
                        paid_fees=paid_fees,
                        remaining_fees=remaining,
                        fee_status=status
                    )
                    db.session.add(new_student)
                    success_count += 1
                    
                except Exception as e:
                    print(f"Error parsing row {index}: {e}")
                    error_count += 1
                    
            db.session.commit()
            flash(f'Import Complete: {success_count} added, {duplicate_count} duplicates skipped, {error_count} errors.', 'success')
            
        except Exception as e:
            flash(f'Failed to process file: {str(e)}', 'error')
    else:
        flash('Invalid file format. Please upload an .xlsx file.', 'error')
        
    return redirect(url_for('admission.add_student'))

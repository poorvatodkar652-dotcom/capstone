import os
from app import create_app
from models import db, Student, Staff, SecurityGuard
from werkzeug.security import generate_password_hash

def migrate_passwords():
    """
    Migrates plain-text passwords in the database to werkzeug scrypt hashes.
    Run this script once after adding password hashing to the application.
    """
    app = create_app()
    with app.app_context():
        count_students, count_staff, count_guards = 0, 0, 0
        
        print("Migrating student passwords...")
        for s in Student.query.all():
            if not s.password.startswith('scrypt:'):
                s.password = generate_password_hash(s.password)
                count_students += 1
                
        print("Migrating staff passwords...")
        for s in Staff.query.all():
            if not s.password.startswith('scrypt:'):
                s.password = generate_password_hash(s.password)
                count_staff += 1
                
        print("Migrating security guard passwords...")
        for g in SecurityGuard.query.all():
            if not g.password.startswith('scrypt:'):
                g.password = generate_password_hash(g.password)
                count_guards += 1
                
        db.session.commit()
        print(f"\nMigration Complete!")
        print(f"Updated passwords for:")
        print(f" - {count_students} students")
        print(f" - {count_staff} staff members")
        print(f" - {count_guards} security guards")

if __name__ == '__main__':
    migrate_passwords()

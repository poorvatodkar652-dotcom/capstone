import os
from datetime import timedelta
from flask import Flask, flash, redirect, url_for, render_template
from dotenv import load_dotenv
from models import db

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'hostel-secret-key-2026')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

    db.init_app(app)

    # Register blueprints
    from routes.home import home_bp
    from routes.student import student_bp
    from routes.staff import staff_bp
    from routes.security import security_bp
    from routes.admission import admission_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(staff_bp, url_prefix='/staff')
    app.register_blueprint(security_bp, url_prefix='/security')
    app.register_blueprint(admission_bp, url_prefix='/admission')

    # Create tables and QR directory
    with app.app_context():
        db.create_all()

    # Custom error handlers — never show raw Flask errors to users
    @app.errorhandler(404)
    def not_found(e):
        flash('Page not found.', 'error')
        return redirect(url_for('home.index'))

    @app.errorhandler(500)
    def server_error(e):
        flash('Something went wrong. Please try again.', 'error')
        return redirect(url_for('home.index'))

    return app


# ASGI wrapper for running with uvicorn
from asgiref.wsgi import WsgiToAsgi
asgi_app = WsgiToAsgi(create_app())


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)

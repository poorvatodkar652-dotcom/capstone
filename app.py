import os
from flask import Flask
from dotenv import load_dotenv
from models import db

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'hostel-secret-key-2026')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
        os.makedirs(os.path.join(app.static_folder, 'qr_codes'), exist_ok=True)

    return app


# ASGI wrapper for running with uvicorn
from asgiref.wsgi import WsgiToAsgi
asgi_app = WsgiToAsgi(create_app())


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)

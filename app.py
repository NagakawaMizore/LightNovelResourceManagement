import os
from flask import Flask
from flask_login import LoginManager
from config import Config
from models import db, User


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    # init extensions
    db.init_app(app)
    login_manager = LoginManager(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "请先登录"
    login_manager.login_message_category = "warning"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # register blueprints
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)

    # ensure upload dir
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # create tables + seed admin
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username="admin").first():
            admin = User(username="admin", role="admin")
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
            print("✓ 默认管理员已创建  username=admin  password=admin123")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)

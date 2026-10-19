import os
import random
from flask import Flask, url_for
from flask_login import LoginManager
from config import Config
from models import db, User

# FR-01: 背景资源池支持的图片扩展名
BACKGROUND_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


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

    # FR-01: 背景资源池与随机注入 —— 每次请求扫描 static/backgrounds/，
    # 随机抽取一张注入模板上下文（bg_image_url），供导航栏/帘幕共用。
    # 目录缺失或为空时降级为 default-cover.svg，不报错。
    @app.context_processor
    def inject_random_background():
        bg_dir = os.path.join(app.static_folder, "backgrounds")
        filename = "css/default-cover.svg"
        try:
            files = [
                f for f in os.listdir(bg_dir)
                if os.path.splitext(f)[1].lower() in BACKGROUND_EXTS
            ]
        except OSError:
            files = []
        if files:
            filename = f"backgrounds/{random.choice(files)}"
        return {"bg_image_url": url_for("static", filename=filename)}

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

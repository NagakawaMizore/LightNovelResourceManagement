from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import User, db

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=True)
            flash("登录成功！", "success")
            next_page = request.args.get("next")
            if next_page and next_page.startswith("/admin"):
                return redirect(next_page) if user.is_admin else redirect(url_for("main.index"))
            return redirect(next_page or url_for("main.index"))

        flash("用户名或密码错误", "danger")

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not username or not password:
            flash("用户名和密码不能为空", "danger")
        elif len(password) < 6:
            flash("密码长度至少为6位", "danger")
        elif password != confirm:
            flash("两次输入的密码不一致", "danger")
        elif User.query.filter_by(username=username).first():
            flash("用户名已被使用", "danger")
        else:
            user = User(username=username, role="user")
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("注册成功！", "success")
            return redirect(url_for("main.index"))

    return render_template("register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("已退出登录", "info")
    return redirect(url_for("main.index"))

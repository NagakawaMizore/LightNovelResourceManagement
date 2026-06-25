import os
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models import Novel, ResourceLink, db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("需要管理员权限", "danger")
            return redirect(url_for("main.index"))
        return f(*args, **kwargs)
    return decorated


def _allowed(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]


def _save_resource_links(novel_id: int, form) -> None:
    providers = form.getlist("provider_name[]")
    urls = form.getlist("download_url[]")
    codes = form.getlist("access_code[]")
    for i, (provider, url) in enumerate(zip(providers, urls)):
        if provider.strip() and url.strip():
            code = codes[i].strip() if i < len(codes) else None
            link = ResourceLink(
                novel_id=novel_id,
                provider_name=provider.strip(),
                download_url=url.strip(),
                access_code=code or None,
            )
            db.session.add(link)


# ── Dashboard ──────────────────────────────────────────────
@admin_bp.route("/")
@login_required
@admin_required
def dashboard():
    total = Novel.query.count()
    recommended = Novel.query.filter_by(is_recommended=True).count()
    links = ResourceLink.query.count()
    novels = Novel.query.order_by(Novel.updated_at.desc()).all()
    return render_template(
        "admin/dashboard.html",
        total=total, recommended=recommended, links=links, novels=novels,
    )


# ── Add Novel ──────────────────────────────────────────────
@admin_bp.route("/novel/add", methods=["GET", "POST"])
@login_required
@admin_required
def add_novel():
    if request.method == "POST":
        novel = Novel(
            title=request.form.get("title", "").strip(),
            author=request.form.get("author", "").strip(),
            series=request.form.get("series", "").strip() or None,
            summary=request.form.get("summary", "").strip(),
            rating=float(request.form.get("rating", 0) or 0),
            is_recommended=bool(request.form.get("is_recommended")),
        )

        # cover
        cover_file = request.files.get("cover_file")
        cover_url = request.form.get("cover_url", "").strip()
        if cover_file and cover_file.filename and _allowed(cover_file.filename):
            fname = secure_filename(cover_file.filename)
            upload_dir = current_app.config["UPLOAD_FOLDER"]
            os.makedirs(upload_dir, exist_ok=True)
            cover_file.save(os.path.join(upload_dir, fname))
            novel.cover_url = f"/static/uploads/{fname}"
        elif cover_url:
            novel.cover_url = cover_url

        db.session.add(novel)
        db.session.flush()
        _save_resource_links(novel.id, request.form)
        db.session.commit()

        flash("小说上架成功！", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("admin/add_novel.html")


# ── Edit Novel ─────────────────────────────────────────────
@admin_bp.route("/novel/<int:novel_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_novel(novel_id):
    novel = Novel.query.get_or_404(novel_id)

    if request.method == "POST":
        novel.title = request.form.get("title", "").strip()
        novel.author = request.form.get("author", "").strip()
        novel.series = request.form.get("series", "").strip() or None
        novel.summary = request.form.get("summary", "").strip()
        novel.rating = float(request.form.get("rating", 0) or 0)
        novel.is_recommended = bool(request.form.get("is_recommended"))

        cover_file = request.files.get("cover_file")
        cover_url = request.form.get("cover_url", "").strip()
        if cover_file and cover_file.filename and _allowed(cover_file.filename):
            fname = secure_filename(cover_file.filename)
            upload_dir = current_app.config["UPLOAD_FOLDER"]
            os.makedirs(upload_dir, exist_ok=True)
            cover_file.save(os.path.join(upload_dir, fname))
            novel.cover_url = f"/static/uploads/{fname}"
        elif cover_url:
            novel.cover_url = cover_url

        # rebuild links
        ResourceLink.query.filter_by(novel_id=novel.id).delete()
        _save_resource_links(novel.id, request.form)
        db.session.commit()

        flash("更新成功！", "success")
        return redirect(url_for("admin.dashboard"))

    links = ResourceLink.query.filter_by(novel_id=novel_id).all()
    return render_template("admin/edit_novel.html", novel=novel, links=links)


# ── Toggle Recommend ──────────────────────────────────────
@admin_bp.route("/novel/<int:novel_id>/toggle_recommend", methods=["POST"])
@login_required
@admin_required
def toggle_recommend(novel_id):
    novel = Novel.query.get_or_404(novel_id)
    novel.is_recommended = not novel.is_recommended
    db.session.commit()
    flash("已推荐" if novel.is_recommended else "已取消推荐", "success")
    return redirect(url_for("admin.dashboard"))


# ── Delete Novel ──────────────────────────────────────────
@admin_bp.route("/novel/<int:novel_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_novel(novel_id):
    novel = Novel.query.get_or_404(novel_id)
    db.session.delete(novel)
    db.session.commit()
    flash("小说已下架", "success")
    return redirect(url_for("admin.dashboard"))

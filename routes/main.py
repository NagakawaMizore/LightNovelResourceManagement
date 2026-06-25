from flask import Blueprint, render_template, request
from models import Novel, ResourceLink, Comment, db

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    recommended = Novel.query.filter_by(is_recommended=True).order_by(Novel.created_at.desc()).all()
    all_novels = Novel.query.order_by(Novel.created_at.desc()).paginate(page=page, per_page=12)
    return render_template("index.html", recommended=recommended, novels=all_novels)


@main_bp.route("/novel/<int:novel_id>")
def novel_detail(novel_id):
    novel = Novel.query.get_or_404(novel_id)
    links = ResourceLink.query.filter_by(novel_id=novel_id).all()
    comments = Comment.query.filter_by(novel_id=novel_id).order_by(Comment.created_at.desc()).all()
    return render_template("detail.html", novel=novel, links=links, comments=comments)


@main_bp.route("/novel/<int:novel_id>/comment", methods=["POST"])
def add_comment(novel_id):
    novel = Novel.query.get_or_404(novel_id)
    nickname = request.form.get("nickname", "").strip()
    content = request.form.get("content", "").strip()

    if nickname and content:
        comment = Comment(novel_id=novel.id, nickname=nickname, content=content)
        db.session.add(comment)
        db.session.commit()

    from flask import redirect, url_for
    return redirect(url_for("main.novel_detail", novel_id=novel_id))


@main_bp.route("/search")
def search():
    keyword = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    novels = None

    if keyword:
        like = f"%{keyword}%"
        novels = (
            Novel.query.filter(
                db.or_(
                    Novel.title.like(like),
                    Novel.author.like(like),
                    Novel.series.like(like),
                )
            )
            .order_by(Novel.created_at.desc())
            .paginate(page=page, per_page=12)
        )

    return render_template("search.html", keyword=keyword, novels=novels)

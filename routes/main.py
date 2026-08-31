from flask import Blueprint, render_template, request
from sqlalchemy import or_, func
from models import Novel, ResourceLink, Comment, Tag, novel_tags, db

main_bp = Blueprint("main", __name__)

# 命中字段 → 中文标签
FIELD_LABELS = {
    "title": "书名",
    "author": "作者",
    "tag": "标签",
    "summary": "简介",
}


def _escape(text: str) -> str:
    """转义 HTML 特殊字符，防止 XSS。"""
    from markupsafe import escape as _e
    return _e(text)


def _highlight(text: str, keyword: str) -> str:
    """把 text 中所有 keyword 用 <mark> 包裹（大小写不敏感），并转义其他 HTML 字符。"""
    if not keyword or not text:
        return _escape(text)
    import re
    # 先整体 escape，再在 escape 后的文本上做正则替换
    escaped = _escape(text)
    pattern = re.compile(re.escape(_escape(keyword)), re.IGNORECASE)
    return pattern.sub(lambda m: f"<mark>{m.group(0)}</mark>", escaped)


def _extract_snippet(summary: str, keyword: str, radius: int = 50) -> str:
    """在 summary 中找到关键词第一次出现的位置，截取前后 radius 字符的上下文。"""
    if not keyword or not summary:
        return ""
    idx = summary.lower().find(keyword.lower())
    if idx == -1:
        return ""
    start = max(0, idx - radius)
    end = min(len(summary), idx + len(keyword) + radius)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(summary) else ""
    raw = summary[start:end]
    return f"{prefix}{_highlight(raw, keyword)}{suffix}"


def _collect_matches(novel: Novel, keyword: str) -> dict:
    """
    分析 keyword 命中了 novel 的哪些字段，返回 {field, label, value, snippet} 列表。
    严禁匹配 comments。
    """
    matches = []
    kw_lower = keyword.lower()

    # 书名
    if kw_lower in novel.title.lower():
        matches.append({
            "field": "title",
            "label": FIELD_LABELS["title"],
            "value": _highlight(novel.title, keyword),
            "snippet": None,
        })

    # 作者
    if kw_lower in novel.author.lower():
        matches.append({
            "field": "author",
            "label": FIELD_LABELS["author"],
            "value": _highlight(novel.author, keyword),
            "snippet": None,
        })

    # 标签
    for tag in novel.tags.all():
        if kw_lower in tag.name.lower():
            matches.append({
                "field": "tag",
                "label": FIELD_LABELS["tag"],
                "value": _highlight(tag.name, keyword),
                "snippet": None,
            })

    # 简介（只取命中点的第一个 snippet）
    if novel.summary and kw_lower in novel.summary.lower():
        matches.append({
            "field": "summary",
            "label": FIELD_LABELS["summary"],
            "value": None,
            "snippet": _extract_snippet(novel.summary, keyword),
        })

    return matches


# ── 首页 ──────────────────────────────────────────────────
@main_bp.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    recommended = Novel.query.filter_by(is_recommended=True).order_by(Novel.created_at.desc()).all()
    all_novels = Novel.query.order_by(Novel.created_at.desc()).paginate(page=page, per_page=12)
    return render_template("index.html", recommended=recommended, novels=all_novels)


# ── 小说详情 ──────────────────────────────────────────────
@main_bp.route("/novel/<int:novel_id>")
def novel_detail(novel_id):
    novel = Novel.query.get_or_404(novel_id)
    links = ResourceLink.query.filter_by(novel_id=novel_id).all()
    comments = Comment.query.filter_by(novel_id=novel_id).order_by(Comment.created_at.desc()).all()
    return render_template("detail.html", novel=novel, links=links, comments=comments)


# ── 提交评论 ──────────────────────────────────────────────
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


# ── 搜索（增强版：标题 / 作者 / 标签 / 简介，排除评论） ─────
@main_bp.route("/search")
def search():
    keyword = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    results = None  # 带命中信息的列表
    pagination = None

    if keyword:
        like = f"%{keyword}%"

        # 子查询：命中标签的 novel_id
        tag_match_ids = (
            db.session.query(novel_tags.c.novel_id)
            .join(Tag, Tag.id == novel_tags.c.tag_id)
            .filter(Tag.name.ilike(like))
            .distinct()
            .subquery()
        )

        # 主查询：title / author / summary 命中 OR 标签命中
        query = Novel.query.filter(
            or_(
                Novel.title.ilike(like),
                Novel.author.ilike(like),
                Novel.series.ilike(like),
                Novel.summary.ilike(like),
                Novel.id.in_(db.session.query(tag_match_ids.c.novel_id)),
            )
        ).order_by(Novel.created_at.desc())

        pagination = query.paginate(page=page, per_page=12)

        # 收集命中信息（需在模板外处理 mark safe）
        results = []
        for novel in pagination.items:
            matches = _collect_matches(novel, keyword)
            results.append({"novel": novel, "matches": matches})

    return render_template(
        "search.html",
        keyword=keyword,
        results=results,
        pagination=pagination,
    )


# ── 按标签筛选 ─────────────────────────────────────────────
@main_bp.route("/tag/<path:tag_name>")
def tag_filter(tag_name):
    page = request.args.get("page", 1, type=int)
    tag = Tag.query.filter(func.lower(Tag.name) == tag_name.lower()).first_or_404()
    novels = (
        Novel.query.filter(Novel.tags.contains(tag))
        .order_by(Novel.created_at.desc())
        .paginate(page=page, per_page=12)
    )
    all_tags = Tag.query.order_by(Tag.name).all()
    return render_template(
        "tag_filter.html",
        tag=tag, novels=novels, all_tags=all_tags,
    )

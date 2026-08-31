from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


# ── 多对多关联表：小说 ↔ 标签 ──────────────────────────────
novel_tags = db.Table(
    "novel_tags",
    db.Column("novel_id", db.Integer, db.ForeignKey("novels.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id"), primary_key=True),
)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), default="user", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class Novel(db.Model):
    __tablename__ = "novels"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    author = db.Column(db.String(100), nullable=False, index=True)
    series = db.Column(db.String(150), default=None, index=True)
    cover_url = db.Column(db.String(512), default=None)
    summary = db.Column(db.Text, default="")
    rating = db.Column(db.Float, default=0.0)
    is_recommended = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    resource_links = db.relationship(
        "ResourceLink", backref="novel", lazy=True, cascade="all, delete-orphan"
    )
    comments = db.relationship(
        "Comment", backref="novel", lazy=True, cascade="all, delete-orphan",
        order_by="Comment.created_at.desc()",
    )
    tags = db.relationship(
        "Tag", secondary=novel_tags, backref="novels", lazy="dynamic"
    )

    @property
    def cover_or_default(self) -> str:
        return self.cover_url or "/static/css/default-cover.svg"


class ResourceLink(db.Model):
    __tablename__ = "resource_links"

    id = db.Column(db.Integer, primary_key=True)
    novel_id = db.Column(db.Integer, db.ForeignKey("novels.id"), nullable=False, index=True)
    provider_name = db.Column(db.String(50), nullable=False)
    download_url = db.Column(db.String(1000), nullable=False)
    access_code = db.Column(db.String(50), default=None)


class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    novel_id = db.Column(db.Integer, db.ForeignKey("novels.id"), nullable=False, index=True)
    nickname = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Tag(db.Model):
    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Tag {self.name}>"

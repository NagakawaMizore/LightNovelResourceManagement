"""Tag 管理 & 增强搜索 单元测试套件

运行：
    python -m pytest tests/test_tags.py -v
    # 或
    python -m unittest tests.test_tags -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from models import db, User, Novel, Tag, novel_tags


# ══════════════════════════════════════════════════════════════════════
# 共享测试装置：单一内存 SQLite + 单 app 实例，避免全局 db 状态污染
# ══════════════════════════════════════════════════════════════════════
_TEST_APP = None


def _get_app():
    global _TEST_APP
    if _TEST_APP is None:
        _TEST_APP = create_app()
        _TEST_APP.config.update({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
        })
        with _TEST_APP.app_context():
            db.create_all()
    return _TEST_APP


def _count_tags(novel):
    """跨不同 lazy 模式安全地取标签数量。"""
    try:
        return novel.tags.count()
    except AttributeError:
        return len(list(novel.tags))


def _tag_names(novel):
    try:
        return [t.name for t in novel.tags.all()]
    except AttributeError:
        return [t.name for t in novel.tags]


class TagModelTests(unittest.TestCase):
    """Tag 模型本身 + Novel ↔ Tag 多对多关联"""

    @classmethod
    def setUpClass(cls):
        cls.app = _get_app()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()

    @classmethod
    def tearDownClass(cls):
        cls.ctx.pop()

    def setUp(self):
        db.session.query(novel_tags).delete()
        Tag.query.delete()
        Novel.query.delete()
        db.session.commit()

    # —— Tag 创建 / 查询 ——
    def test_create_tag(self):
        tag = Tag(name="校园")
        db.session.add(tag)
        db.session.commit()
        self.assertIsNotNone(tag.id)
        self.assertEqual(Tag.query.count(), 1)

    def test_tag_name_unique(self):
        db.session.add(Tag(name="百合"))
        db.session.commit()
        dup = Tag(name="百合")
        db.session.add(dup)
        with self.assertRaises(Exception):
            db.session.commit()
        db.session.rollback()

    # —— 多对多关联 ——
    def test_novel_tags_association(self):
        novel = Novel(title="A", author="X", summary="y")
        db.session.add(novel)
        db.session.flush()

        t1 = Tag(name="校园")
        t2 = Tag(name="日常")
        db.session.add_all([t1, t2])
        db.session.flush()

        novel.tags.append(t1)
        novel.tags.append(t2)
        db.session.commit()

        self.assertEqual(_count_tags(novel), 2)
        self.assertIn(novel, list(t1.novels))
        self.assertIn(novel, list(t2.novels))

    def test_replace_tags(self):
        novel = Novel(title="B", author="X")
        db.session.add(novel)
        db.session.flush()
        novel.tags.append(Tag(name="旧标签"))
        db.session.commit()

        novel.tags = [Tag(name="新标签")]
        db.session.commit()

        self.assertEqual(_count_tags(novel), 1)
        self.assertEqual(_tag_names(novel)[0], "新标签")

    def test_assign_tags_helper_creates_missing(self):
        from routes.admin import _assign_tags
        novel = Novel(title="C", author="X")
        db.session.add(novel)
        db.session.flush()

        _assign_tags(novel, "校园,  日常 , 旧标签")
        db.session.commit()

        self.assertEqual(set(_tag_names(novel)), {"校园", "日常", "旧标签"})

    def test_assign_tags_reuses_existing(self):
        from routes.admin import _assign_tags
        novel = Novel(title="D", author="X")
        db.session.add(novel)
        db.session.flush()
        db.session.add(Tag(name="百合"))
        db.session.commit()

        _assign_tags(novel, "百合, 校园")
        db.session.commit()

        self.assertEqual(Tag.query.count(), 2)
        self.assertEqual(set(_tag_names(novel)), {"百合", "校园"})

    def test_delete_tag_cascades_properly(self):
        """删除 Tag 不应级联删除 Novel（只清除关联）。"""
        novel = Novel(title="E", author="X")
        tag = Tag(name="待删除")
        db.session.add_all([novel, tag])
        db.session.flush()
        novel.tags.append(tag)
        db.session.commit()

        db.session.delete(tag)
        db.session.commit()

        self.assertIsNone(Tag.query.get(tag.id))
        self.assertEqual(Novel.query.count(), 1)
        self.assertEqual(_count_tags(novel), 0)


class PermissionTests(unittest.TestCase):
    """普通用户 / 未登录 访问管理员路由应被拒绝"""

    @classmethod
    def setUpClass(cls):
        cls.app = _get_app()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        cls.client = cls.app.test_client()

        # 准备 admin 和 normal 用户（幂等：已存在则跳过）
        if not User.query.filter_by(username="t_admin").first():
            admin = User(username="t_admin", role="admin")
            admin.set_password("1234")
            db.session.add(admin)
        if not User.query.filter_by(username="t_user").first():
            user = User(username="t_user", role="user")
            user.set_password("1234")
            db.session.add(user)
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        cls.ctx.pop()

    def _login(self, username):
        self.client.post("/login", data={
            "username": username, "password": "1234"
        }, follow_redirects=True)

    def _logout(self):
        self.client.get("/logout")

    def _protected_routes(self):
        return [
            ("GET",  "/admin/tags"),
            ("POST", "/admin/tags/add"),
            ("POST", "/admin/tags/delete/99999"),
        ]

    def test_guest_denied(self):
        for method, url in self._protected_routes():
            resp = self.client.get(url) if method == "GET" else self.client.post(url, data={"name": "x"})
            self.assertNotEqual(resp.status_code, 200,
                                f"guest 不应直接访问 {method} {url}，got {resp.status_code}")

    def test_normal_user_denied(self):
        self._login("t_user")
        for method, url in self._protected_routes():
            resp = self.client.get(url) if method == "GET" else self.client.post(url, data={"name": "x"})
            self.assertNotEqual(resp.status_code, 200,
                                f"普通用户不应访问 {method} {url}")
        self._logout()

    def test_admin_allowed(self):
        self._login("t_admin")
        resp = self.client.get("/admin/tags")
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post("/admin/tags/add", data={"name": "测试标签"})
        self.assertIn(resp.status_code, (200, 302))
        self._logout()


class SearchTests(unittest.TestCase):
    """增强版搜索：范围 / 命中分析 / snippet / 高亮 / 排除评论"""

    @classmethod
    def setUpClass(cls):
        cls.app = _get_app()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        cls.client = cls.app.test_client()

        cls.n1 = Novel(title="桌球少女", author="百合作家", series="体育",
                       summary="放学后她们经常在旧校舍一起打桌球，两人的关系开始微妙地变化。")
        cls.n2 = Novel(title="校园日常", author="日常作者",
                       summary="一本讲述高中生活的校园轻小说，有温馨的日常剧情。")
        cls.n3 = Novel(title="异世界转生", author="奇幻作者",
                       summary="穿越到异世界成为冒险家，开始冒险。")
        db.session.add_all([cls.n1, cls.n2, cls.n3])
        db.session.flush()

        cls.tag_sport = Tag(name="体育")
        cls.tag_school = Tag(name="校园")
        db.session.add_all([cls.tag_sport, cls.tag_school])
        db.session.flush()

        cls.n1.tags.append(cls.tag_sport)
        cls.n2.tags.append(cls.tag_school)
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        cls.ctx.pop()

    def test_title_match(self):
        resp = self.client.get("/search?q=桌球")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("桌球少女", html)
        self.assertIn("<mark>桌球</mark>", html)

    def test_author_match(self):
        resp = self.client.get("/search?q=百合作家")
        html = resp.get_data(as_text=True)
        self.assertIn("<mark>百合作家</mark>", html)

    def test_tag_name_match(self):
        resp = self.client.get("/search?q=体育")
        html = resp.get_data(as_text=True)
        self.assertIn("命中标签", html)
        self.assertIn("桌球少女", html)

    def test_summary_snippet(self):
        resp = self.client.get("/search?q=冒险")
        html = resp.get_data(as_text=True)
        self.assertIn("…", html)
        self.assertIn("<mark>冒险</mark>", html)
        self.assertIn("search-snippet", html)

    def test_comments_excluded_from_search(self):
        """用户评论不参与搜索（不应导致 n3 命中）。"""
        from models import Comment
        db.session.add(Comment(novel_id=self.n3.id, nickname="匿名",
                               content="桌球少女好看！"))
        db.session.commit()

        resp = self.client.get("/search?q=桌球")
        html = resp.get_data(as_text=True)
        # n3（异世界转生）的标题 / 作者 / 简介都没有"桌球"，
        # 就算评论被加了也不应该出现在搜索结果卡片里
        self.assertNotIn("异世界转生", html)

    def test_no_match(self):
        resp = self.client.get("/search?q=不存在的关键词xyz")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("未找到匹配", html)

    def test_empty_keyword(self):
        resp = self.client.get("/search?q=")
        self.assertEqual(resp.status_code, 200)

    def test_tag_filter_ok(self):
        resp = self.client.get(f"/tag/{self.tag_sport.name}")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("桌球少女", html)
        self.assertNotIn("校园日常", html)

    def test_tag_filter_not_found(self):
        resp = self.client.get("/tag/根本不存在的标签")
        self.assertEqual(resp.status_code, 404)


class HighlightHelpersTests(unittest.TestCase):
    """main.py 内部的高亮 / snippet 截取工具函数"""

    @classmethod
    def setUpClass(cls):
        cls.app = _get_app()
        cls.ctx = cls.app.app_context()
        cls.ctx.push()

    @classmethod
    def tearDownClass(cls):
        cls.ctx.pop()

    def test_highlight_basic(self):
        from routes.main import _highlight
        out = _highlight("这是桌球少年的故事", "桌球")
        self.assertIn("<mark>桌球</mark>", out)

    def test_highlight_case_insensitive(self):
        from routes.main import _highlight
        out = _highlight("Snooker 桌球 POOL", "snooker")
        self.assertIn("<mark>Snooker</mark>", out)

    def test_highlight_escape_html(self):
        """原文中的 <script> 不应被当作 HTML 执行。"""
        from routes.main import _highlight
        out = _highlight("hello <script>alert(1)</script> world", "hello")
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)

    def test_snippet_mid(self):
        from routes.main import _extract_snippet
        long_text = "A" * 200 + "桌球" + "B" * 200
        snip = _extract_snippet(long_text, "桌球", radius=20)
        self.assertTrue(snip.startswith("…"))
        self.assertTrue(snip.endswith("…"))
        self.assertIn("<mark>桌球</mark>", snip)

    def test_snippet_at_start(self):
        from routes.main import _extract_snippet
        text = "桌球开场的故事非常精彩，后面还有很多内容" + "C" * 100
        snip = _extract_snippet(text, "桌球", radius=30)
        self.assertFalse(snip.startswith("…"))

    def test_snippet_not_found(self):
        from routes.main import _extract_snippet
        snip = _extract_snippet("完全没有目标词的文本", "不存在")
        self.assertEqual(snip, "")

    def test_collect_matches_no_comments(self):
        """_collect_matches 只扫描 title/author/summary/tags，绝不过 comments。"""
        from routes.main import _collect_matches
        from models import Comment
        novel = Novel(title="T", author="A", summary="S")
        db.session.add(novel)
        db.session.flush()
        db.session.add(Comment(novel_id=novel.id, nickname="x", content="桌球"))
        db.session.commit()

        matches = _collect_matches(novel, "桌球")
        self.assertEqual(len(matches), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

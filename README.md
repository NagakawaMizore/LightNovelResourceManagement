# LightNovel Resource Management (LNMS)

轻小说资源管理系统（Light Novel Resource Management System），一个基于 Python Flask 与 SQLite/SQLAlchemy 构建的轻小说书籍信息与资源管理 Web 应用。

---

## 📖 项目简介

LNMS 旨在为轻小说爱好者及管理者提供一个简洁、直观的书籍检索与管理平台。系统支持多角色权限控制（普通用户与管理员），具备书籍信息展示、检索、分类浏览以及后台管理功能。

---

## ✨ 功能特性

- **📚 书籍信息检索与展示**：
  - 支持多维度搜索（书名、作者等）与小说详情页浏览。
  - 封面图片展示与本地媒体资源管理。
- **🔐 身份认证与权限控制**：
  - 用户注册与登录体系。
  - 管理员后台权限鉴权，防止越权操作。
- **🛠️ 管理员控制面板**：
  - 轻小说条目增删改查（CRUD）。
  - 支持封面图片上传与元数据维护。
- **📱 响应式前端界面**：
  - 基于 Jinja2 模板与自定义样式，布局清晰直观。

---

## 📂 项目结构

```text
LightNovelResourceManagement/
├── app.py                  # 应用入口，初始化 Flask 实例与蓝图注册
├── config.py               # 项目配置文件（数据库连接、SECRET_KEY、上传路径等）
├── models.py               # 数据模型定义（User, LightNovel 等）
├── lnms.db                 # SQLite 数据库文件
├── requirements.txt        # 项目依赖清单
├── routes/                 # 路由及业务逻辑模块（蓝图）
│   ├── __init__.py
│   ├── auth.py             # 认证模块（登录、注册、注销）
│   ├── main.py             # 主站模块（首页、搜索、详情页）
│   └── admin.py            # 管理后台模块（作品管理、上传等）
├── static/                 # 静态资源文件
│   ├── css/                # 样式表文件
│   └── uploads/            # 用户/管理员上传的文件与封面
└── templates/              # Jinja2 视图模板
    ├── base.html           # 基础全局布局模板
    ├── index.html          # 首页模板
    ├── detail.html         # 小说详情页
    ├── search.html         # 搜索结果页
    ├── login.html          # 用户登录页
    ├── register.html       # 用户注册页
    └── admin/              # 后台管理相关模板
        ├── dashboard.html  # 管理面板仪表盘
        ├── add_novel.html  # 添加轻小说条目
        └── edit_novel.html # 编辑轻小说条目

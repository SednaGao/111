# Smart Crawler Cluster Management System (SCCM)

## 本项目使用框架Flask-MVC (fmvc)

基于Flask的MVC框架。

## 开发环境启动项目

- 开发环境安装mongodb

- 修改配置文件 /config/env 中关于数据库连接的项，DATABASE_URI指向本地名为sccm的数据库。

```
mongodb://localhost/sccm
```

- 配置conda环境

```
conda create --name py38-sccm python=3.8
pip install -r requirements.txt
```

- 在开发环境启动项目，默认侦听localhost:5000

```bash
./start_dev_server.sh
```

- 查看已有接口文档，使用浏览器访问:
```
http://localhost:5000/api-doc
```

## fmvc使用说明

### 模块

项目的模块都组织在/app/下，每个模块的路由(routes.py)、API(apis.py)、页面数据控制层（views.py）、应用库(utils.py)都存放在相应的模块下。sccm项目仅需要编写每个模块的apis.py即可。

apis.py中，经常要用到的两个装饰器是@params和@api。

- @params可以方便的为一个普通的flask接口添加数据校验功能，并能配合api的注释，自动生成相应的api文档。
- @api自动为一个普通的flask接口生成规范的json返回格式。

### 数据模型

sccm使用mongodb数据库，数据模型存储在models_mongo.py中。它使用mongoengine作为ORM工具，封装了所有的db操作。
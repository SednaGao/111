from flask import request, url_for, redirect, render_template, current_app as app
from flask_restful import Resource as RestfulResource
from ..models_mongo import Executor
from flask_security import current_user
from .. import api, params, json_validator
from wtforms import *
from urllib import parse
import time, os
from datetime import datetime

class APICreate(RestfulResource):
    @params({
        "title": StringField(
            description="包名",
            validators=[validators.length(max=64), validators.DataRequired()]
        ),
        "description": StringField(
            description="描述",
            validators=[validators.length(max=1024)]
        ),
        "executor_file": StringField(
            description="包执行文件上传（*.pyz）"
        )
    })

    @api
    def post(self):
        """
        创建新包
        :return:
            :success:
                {
                    "executor_id": "600a7053951c1caad7128d9b"
                }
            :failure:
                -1, "创建失败，包名已存在"
                -2, "未上传资源文件包"

        """
        title = request.args.get("title")

        if len(Executor.objects(title=title)) > 0:
            return -1, "创建失败，包名已存在"

        file = request.files['executor_file']
        executor_file = file.read()
        ext = os.path.splitext(file.filename)[1]
        title_ext = title + ext
        # uploaded_file = secure_filename(executor_file.filename)
        # check if clicking upload button without importing files
        if executor_file is None:
            return -2, "未上传资源文件包"

        # 文件包本地保存
        if not os.path.exists(app.config['EXECUTOR_PKG_DIR']):
            os.makedirs(app.config['EXECUTOR_PKG_DIR'])
        f_url = os.path.join(app.config['EXECUTOR_PKG_DIR'], title_ext)
        with open(f_url, 'w') as f:
            f.write(str(executor_file, 'utf-8'))
        file_url = parse.urljoin(app.config['EXECUTOR_PKG_BASE_URL'], f_url).encode('utf-8')

        # executor_file_url = os.path.join(app.instance_path, 'packages', uploaded_file)
        # executor_file.save(executor_file_url)

        executor = Executor(title=title,
                            description=request.args.get("description"),
                            create_time=datetime.now(),
                            url=file_url,
                            status="READY"
        )

        executor.save()

        return {"executor_id": str(executor.id)}

class APIList(RestfulResource):
    @params({
        'p': IntegerField(
            default=1,
            description="页码",
            validators=[validators.number_range(min=1)]
        ),
        'psize': IntegerField(
            default=10,
            description="每页记录数",
            validators=[validators.number_range(min=10)]
        ),
        'search_key': StringField(
            description="包名称",
            validators=[validators.length(max=64)]
        ),
    })

    @api
    def get(self):
        """
        获取包列表
        :return:
            :success:
                [
                    "page": [
                        {
                            "create_time": "2021-01-22 18:14:42",
                            "description": "bb",
                            "id": "600aa5923817e4fb8f8267b0",
                            "status": "READY",
                            "title": "uuu",
                            "url": "http://127.0.0.1:3000/tmp/sccm_epkg/uuu"
                        }
                    ],
                    "total": 1
                ]

        """
        search_key = request.args.get("search_key")
        p = request.args.get('p')
        filter_kwargs = {}
        psize = request.args.get('psize')
        executor_list = Executor.objects(**filter_kwargs)
        if search_key:
            executor_list = executor_list.filter(title__contains=search_key).order_by('-create_time')
            filter_kwargs.update({"title": executor_list})
        return {
            "page": [j.to_dict() for j in executor_list[(p-1)*psize:psize]],
            'total': executor_list.count()
        }



class APIDelete(RestfulResource):
    @params({
        "title": StringField(
            description="包名",
            validators=[validators.length(max=64), validators.DataRequired()]
        )
    })

    @api
    def delete(self):
        """
        删除包
        :return:
            :success:
                0
        """
        title = request.args.get("title")
        exexutor_object = Executor.objects.get(title=title)
        # 文件系统执行包删除
        os.remove(os.path.join(app.config['EXECUTOR_PKG_DIR'], title))
        exexutor_object.update(set__status="DELETED")
        return 0

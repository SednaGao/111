from flask import request, url_for, redirect, render_template, current_app as app
from flask_restful import Resource as RestfulResource
from .. import models_mongo
from flask_security import current_user
from .. import api, params, json_validator
from wtforms import *
from .utils import DbOperation


db_operation = DbOperation()


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
        "search_key": StringField(
            description="搜索关键词",
        )
    })

    @api
    def get(self):
        """
        获取列表信息
        :return:
            :success:
                [
                    {
                        "title": "test",
                        "url_count": 5,
                        "be_task": "task_01"
                    },
                    {
                        "title": "test1",
                        "url_count": 5,
                        "be_task": "task_05"
                    },
                ]
            :failure:
                -1, "XXXX"
        """
        return [
            {
                "title": "test",
                "url_count": 5,
                "be_task": "task_01"
            },
            {
                "title": "test1",
                "url_count": 5,
                "be_task": "task_05"
            },
        ]
        p = request.args.get('p')
        psize = request.args.get('psize')
        db_operation.get_scc_redis()
        if request.args.get("search_key"):
            return db_operation.get_list(request.args.get("search_key"))[(p-1)*psize:psize]
        return db_operation.get_list()[(p-1)*psize:psize]


class APIDelete(RestfulResource):
    @params({
        "title": StringField(
            description="操作项title(名称)",
            validators=[validators.DataRequired()]
        )
    })

    @api
    def delete(self):
        """
        删除
        :return:
            :success:
                0
            :failure:
                -1, "未知错误"
        """
        db_operation.get_scc_redis()
        if db_operation.del_db(request.args.get("title")) == 0:
            return 0

        return -1, "未知错误"

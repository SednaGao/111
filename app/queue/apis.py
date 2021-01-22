from flask import request, url_for, redirect, render_template, current_app as app
from flask_restful import Resource as RestfulResource
from .. import models_mongo
from flask_security import current_user
from .. import api, params, json_validator
from wtforms import *


class APIList(RestfulResource):
    @params({
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


class APIDelete(RestfulResource):
    @params({
        "title": StringField(
            description="操作项title",
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
                -1, "XXXX"
        """
        return 0

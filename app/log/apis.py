from flask import request, url_for, redirect, render_template, current_app as app
from flask_restful import Resource as RestfulResource
from ..models_mongo import Logs
from flask_security import current_user
from .. import api, params, json_validator
from wtforms import *
from .utils import log_operation

import re


class APIList(RestfulResource):
    @params({
        'p': IntegerField(
            default=1,
            description="页码(注：当real_time字段为True时，此选项数字为多少页，即返回数据条数为（p*psize）)",
            validators=[validators.number_range(min=1)]
        ),
        'psize': IntegerField(
            default=10,
            description="每页记录数",
            validators=[validators.number_range(min=10)]
        ),
        'spider_name': StringField(
            description="爬虫名，当real_time为True时为必传字段"
        ),
        'search_key': StringField(
            description="搜索关键词",
        ),
        "start_time": DateTimeField(
            description="起始筛选时间"
        ),
        "end_time": DateTimeField(
            description="起始筛选时间"
        ),
        "level": StringField(
            description="等级",
        ),
        "spider_idx": StringField(
            description="爬虫idx"
        ),
        "real_time": BooleanField(
            default=True,
            description="日志类型，实时日志或数据库日志(注：当此选项为True时，其他筛选字段无须提交)",
        )
    })

    @api
    def get(self):
        """
        获取日志列表
        :return:
            :success:
                [
                    {
                        "message": "XXX",
                        "level": "DEBUG",
                        "add_time": "1609752384.6248367",
                        "crawler_id": "XXX"
                    },
                    {
                        "message": "XXX",
                        "level": "WARNING",
                        "add_time": "1609752384.6248367",
                        "crawler_id": "XXX"
                    }
                ]
            :failure:
                -1, "XXXX"
        """
        # 这里关键词暂未确定匹配项

        return [
            {
                "message": "XXX",
                "level": "DEBUG",
                "add_time": "1609752384.6248367",
                "crawler_id": "XXX"
            },
            {
                "message": "XXX",
                "level": "WARNING",
                "add_time": "1609752384.6248367",
                "crawler_id": "XXX"
            }
        ]

        p = request.args.get('p')
        psize = request.args.get('psize')
        if request.args.get("real_time"):
            # 获取实时日志
            if request.args.get("spider_name"):
                return log_operation.get_stream_logs(spider_name=request.args.get("spider_name"))[-p*10:]
            return -2, '实时日志模式spider_name为必传字段'
        filter_kwargs = {}
        if request.args.get("search_key"):
            regex = re.compile('.*' + request.args.get("search_key") + '.*')
            filter_kwargs.update({"message": regex})
        for key in ['spider_idx', 'level']:
            if request.args.get(key):
                filter_kwargs.update({key: request.args.get(key)})
        if request.args.get("start_time") and request.args.get("end_time"):
            filter_kwargs.update({
                "add_time__gte": request.args.get("start_time"),
                "add_time__lte": request.args.get("end_time"),
            })

        return [j.to_dict() for j in Logs.objects(**filter_kwargs).order_by('-add_time')[(p - 1) * psize:psize]]

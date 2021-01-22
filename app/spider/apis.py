from flask import request, url_for, redirect, render_template, current_app as app
from flask_restful import Resource as RestfulResource
from ..models_mongo import Job
from flask_security import current_user
from .. import api, params, json_validator
from wtforms import *
from .utils import Spider, SpiderCrawler

import re


class APICreate(RestfulResource):
    @params({
        "name": StringField(
            description="爬虫名，必须为数字和字母的组合",
            validators=[validators.length(max=64), validators.regexp(r'^\w+$')]
        ),
        "count": IntegerField(
            description="爬虫数量",
            validators=[validators.number_range(min=1, max=20)]
        ),
        'force': StringField(
            description="是否允许强制减少爬虫进程数，yes允许，no不允许",
            validators=[validators.data_required(), validators.any_of(['yes', 'no'])]
        ),
    })
    @api
    def post(self):
        """
        创建爬虫进程或变更爬虫进程数。如果不带force参数，则不允许减少正在爬取的爬虫进程数。
        :return:
            :success:
                0
            :failure:
                -22, "爬虫已经有{}个进程在运行了。如果要减少爬虫进程数，请先暂停爬取。"
        """
        spider = Spider(request.args.get("name"))
        spider.launch(request.args.get("count"), request.args.get("force") == 'yes')
        return 0


class APIList(RestfulResource):
    @api
    def get(self):
        """
        获取爬虫列表。返回一个字典，字典键名为爬虫名，键值为爬虫下的进程列表。
        :return:
            :success:
                {
                    "single": [
                      {
                        "CURRENT STATE": "Running 6 days ago",
                        "DESIRED STATE": "Running",
                        "ERROR": "",
                        "IMAGE": "192.168.0.47:5000/eric-et/crawler:latest",
                        "NAME": "single_crawler.1",
                        "NODE": "crawler-02",
                        "PORT": "",
                        "Replica ID": "q5gtznjrtatn",
                        "INDEX": "1"
                      }
                    ],
                    "test": [
                      {
                        "CURRENT STATE": "Running 25 minutes ago",
                        "DESIRED STATE": "Running",
                        "ERROR": "",
                        "IMAGE": "192.168.0.47:5000/eric-et/crawler:latest",
                        "NAME": "test_crawler.1",
                        "NODE": "crawler-02",
                        "PORT": "",
                        "Replica ID": "zq8dv80mfnda",
                        "INDEX": "1"
                      },
                      {
                        "CURRENT STATE": "Running 25 minutes ago",
                        "DESIRED STATE": "Running",
                        "ERROR": "",
                        "IMAGE": "192.168.0.47:5000/eric-et/crawler:latest",
                        "NAME": "test_crawler.2",
                        "NODE": "crawler-02",
                        "PORT": "",
                        "Replica ID": "ck30393lj4gu",
                        "INDEX": "2"
                      },
                      {
                        "CURRENT STATE": "Running 27 minutes ago",
                        "DESIRED STATE": "Running",
                        "ERROR": "",
                        "IMAGE": "192.168.0.47:5000/eric-et/crawler:latest",
                        "NAME": "test_crawler.3",
                        "NODE": "crawler-02",
                        "PORT": "",
                        "Replica ID": "y6vhxpermb71",
                        "INDEX": "3"
                      }
                    ]
                  }
            :failure:
                --
        """
        ss = Spider.info()
        ret = []
        for s in ss:
            for c in s['crawlers']:
                c.update({'spider_name': s['spider_name'], 'queue_status': s['status']})
                ret.append(c)
        return ret


class CrawlerIdentity(Form):
    name = StringField(validators=[validators.data_required(), validators.regexp(r'^\w+$')])
    index = IntegerField(validators=[validators.data_required(), validators.number_range(min=1)])


class APIOperate(RestfulResource):
    @params({
        "name": StringField(
            description="爬虫名，必须为数字和字母的组合",
            validators=[validators.length(max=64), validators.regexp(r'^\w+$')]
        ),
        "do": StringField(
            description="操作指令(pause-暂停, resume-恢复)",
            validators=[validators.any_of(["pause", "resume"])]
        )
    })
    @api
    def post(self):
        """
        暂停爬虫队列，爬虫仍然运行但取不到任务；或恢复爬虫队列
        :return:
            :success:
                0
            :failure:
                --
        """
        s = Spider(request.args.get('name'))
        s.pause(request.args.get('do') == 'pause')
        return 0


class APIStop(RestfulResource):
    @params({
        "name": StringField(
            description="爬虫名，必须为数字和字母的组合",
            validators=[validators.length(max=64), validators.regexp(r'^\w+$')]
        ),
    })
    @api
    def post(self):
        """
        停止爬虫进程组。直接调用此方法可能会导致正在运行的任务数据丢失。通常应该先挂起，再等待空闲，再停止。
        :return:
            :success:
                0
            :failure:
                --
        """
        s = Spider(request.args.get('name'))
        s.stop()
        return 0


class APIIdle(RestfulResource):
    @params({
        "name": StringField(
            description="爬虫名，必须为数字和字母的组合",
            validators=[validators.length(max=64), validators.regexp(r'^\w+$')]
        ),
    })
    @api
    def get(self):
        """
        判断爬虫进程组是否空闲（没有任何爬取任务在运行）。空闲有两种情况：1. 爬虫被挂起；2. 爬虫所属任务队列为空。返回列表，按照爬虫进程传入顺序，列出是否空闲。

        :return:
            :success:
                true // or false
            :failure:
                --
        """
        s = Spider(request.args.get('name'))
        return s.is_idle()


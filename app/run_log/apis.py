from flask import request, url_for, redirect, render_template, current_app as app
from flask_restful import Resource as RestfulResource
from mongoengine.queryset.visitor import Q
from ..models_mongo import *
from flask_security import current_user
from .. import api, params
from wtforms import *

import re

from .utils import SpiderRunLog


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
            description="搜索关键词",
        ),
        "start_time": DateTimeField(
            description="起始筛选时间"
        ),
        "end_time": DateTimeField(
            description="起始筛选时间"
        ),
        "status": FieldList(
            StringField(
                validators=[validators.optional(), validators.any_of(
                    ['INIT', 'SENT', 'READY', 'RUNNING', 'PAUSED', 'STOPPED', 'CANCELED', 'DONE'])]
            ),
            description="运行状态的列表，为下列的组合，通过status-0, status-1依次传入："
                        "<br/>INIT, 刚提交"
                        "<br/>SENT, 已提交爬虫端"
                        "<br/>READY, 爬虫已启动。尚未开始运行任务；或任务已经全部完成，即将由scheduler关闭"
                        "<br/>RUNNING, 正在爬取"
                        "<br/>PAUSED, 爬取暂停，爬虫待命，任务队列尚在，可恢复执行"
                        "<br/>STOPPED, 爬取停止，爬虫停止，任务队列尚在，可恢复执行"
                        "<br/>CANCELED, 结束状态：取消，任务队列已删除，不可恢复"
                        "<br/>DONE, 结束状态：爬取任务已经完成，等待标记为SUCCESS"
        ),
        "result": FieldList(
            StringField(
                validators=[validators.optional(), validators.any_of(
                    ['UNKNOWN', 'SUCCESS', 'FAILURE'])]
            ),
            description="运行结果的列表，为下列的组合，通过result-0, result-1依次传入："
                        "<br/>UNKNOWN, 运行中，结果未知"
                        "<br/>SUCCESS, 运行成功"
                        "<br/>FAILURE, 运行失败"
        ),
        'job_id': StringField(
            description="任务id",
            validators=[validators.length(max=32)]
        ),
        'service_id': StringField(
            description="服务id",
            validators=[validators.length(max=32)]
        ),
    })
    @api
    def get(self):
        """
        获取运行记录列表；如果传入任务id或服务id，则返回该任务或服务下的运行记录。
        :return:
            :success:
                {
                    "page": [
                      {
                        "title": "123321",
                        "category": "SERVICE",
                        "end_datetime": "2021-01-19 13:17:13",
                        "error_message": "\u722c\u866b\u670d\u52a1\u63d0\u4ea4\u5931\u8d25: HTTPConnectionPool(host='106.12.9.121', port=5343): Max retries exceeded with url: /feed (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f9a1d402550>: Failed to establish a new connection: [Errno 61] Connection refused'))",
                        "id": "60066b55ab60703b4364b5fb",
                        "invoke_datetime": "2021-01-19 13:16:06",
                        "job": null,
                        "service": {
                          "crawler_count": 1,
                          "create_time": "2021-01-13 16:06:02",
                          "enabled": true,
                          "id": "5ffea9ea9f5864d962ea3f30",
                          "last_done_time": null,
                          "last_start_time": null,
                          "params": [],
                          "spec": {
                            "appid": "~4.5.0",
                            "crawlid": "~4.5.0",
                            "spiderid": "~4.5.0",
                            "url": "~4.5.0"
                          },
                          "title": "123321"
                        },
                        "spec": {
                          "appid": "~4.5.0",
                          "crawlid": "~4.5.0",
                          "spiderid": "~4.5.0",
                          "url": "~4.5.0"
                        },
                        "status": "ERROR",
                        "result": "FAILURE"
                      },
                      {
                        "title": "123321",
                        "category": "SERVICE",
                        "end_datetime": "2021-01-19 12:35:50",
                        "error_message": "\u722c\u866b\u670d\u52a1\u63d0\u4ea4\u5931\u8d25: HTTPConnectionPool(host='106.12.9.121', port=5343): Max retries exceeded with url: /feed (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x7f9b551d14f0>: Failed to establish a new connection: [Errno 61] Connection refused'))",
                        "id": "600661a6071daca9fd488f95",
                        "invoke_datetime": "2021-01-19 12:35:45",
                        "job": null,
                        "service": {
                          "crawler_count": 1,
                          "create_time": "2021-01-13 16:06:02",
                          "enabled": true,
                          "id": "5ffea9ea9f5864d962ea3f30",
                          "last_done_time": null,
                          "last_start_time": null,
                          "params": [],
                          "spec": {
                            "appid": "~4.5.0",
                            "crawlid": "~4.5.0",
                            "spiderid": "~4.5.0",
                            "url": "~4.5.0"
                          },
                          "title": "123321"
                        },
                        "spec": {
                          "appid": "~4.5.0",
                          "crawlid": "~4.5.0",
                          "spiderid": "~4.5.0",
                          "url": "~4.5.0"
                        },
                        "status": "ERROR",
                        "result": "FAILURE"
                      }
                    ],
                    "total": 10
                }
            :failure:
                -1, "XXXX"
        """
        p = request.args.get('p')
        psize = request.args.get('psize')
        filter_kwargs = {}
        if request.args.get("search_key"):
            regex = re.compile('.*' + re.escape(request.args.get("search_key")) + '.*')
            filter_kwargs.update({"title": regex})
        # filter status
        if request.args.get("status"):
            filter_kwargs.update({"status__in": request.args.get("status")})
        if request.args.get("result"):
            filter_kwargs.update({"result__in": request.args.get("result")})
        if request.args.get("start_time") and request.args.get("end_time"):
            filter_kwargs.update({
                "invoke_datetime__gte": request.args.get("start_time"),
                "invoke_datetime__lte": request.args.get("end_time"),
            })
        if request.args.get('job_id'):
            filter_kwargs.update({"job": Job(id=request.args.get('job_id'))})
        if request.args.get('service_id'):
            filter_kwargs.update({"service": Job(id=request.args.get('service_id'))})
        filter_runlog = RunLog.objects(**filter_kwargs).no_dereference().order_by('-invoke_datetime')
        return {
            'page': [j.to_dict() for j in filter_runlog[(p - 1) * psize:p * psize]],
            'total': filter_runlog.count()
        }


class APIResume(RestfulResource):
    @params({
        'id': StringField(
            description="运行记录id",
            validators=[validators.length(max=32), validators.data_required()]
        ),
    })
    @api
    def post(self):
        """
        恢复运行

        :return:
            :success:
                0
            :failure:
                -1, "运行记录id不存在"
                -2, "任务已经是运行状态"
                -3, "被取消、运行结束（完成、成功或失败）的运行记录不能恢复运行"
        """
        rl = RunLog.objects.get(id=request.args.get("id"))
        if not rl.title:
            return -1, "运行记录id不存在"
        if rl.status in ('CANCELED', 'SUCCESS', 'ERROR'):
            return -2, "被取消、运行结束（完成、成功或失败）的运行记录不能再恢复"

        srl = SpiderRunLog(rl)
        state = srl.status_check()
        if state == 'RUNNING':
            return -2, "任务已经是运行状态"

        while True:
            state = srl.status()
            if state in ('CANCELED', 'SUCCESS', 'ERROR', 'DONE'):
                return -3, "被取消、运行结束（完成、成功或失败）的运行记录不能恢复运行"
            if state == 'STOPPED':
                srl.spider.launch(rl.crawler_count)
                continue
            if state == 'PAUSED':
                srl.resume()
                continue
            if state == 'RUNNING':
                break

        if rl.status != "RUNNING":
            rl.update(set__status="RUNNING")

        return 0


class APIPause(RestfulResource):
    @params({
        'id': StringField(
            description="运行记录id",
            validators=[validators.length(max=32), validators.data_required()]
        ),
    })
    @api
    def post(self):
        """
        暂停运行

        :return:
            :success:
                0
            :failure:
                -1, "id和title必须指定其一"
        """
        rl = RunLog.objects.get(id=request.args.get("id"))
        if not rl.title:
            return -1, "运行记录id不存在"
        if rl.status in ('CANCELED', 'SUCCESS', 'ERROR'):
            return -2, "被取消、运行结束（完成、成功或失败）的运行记录不能再被暂停"

        srl = SpiderRunLog(rl)
        state = srl.status_check()
        if state == 'PAUSED':
            return -2, "任务已经是暂停状态"
        if state == 'STOPPED':
            return -3, "爬虫已停止，无需暂停"

        while True:
            state = srl.status()
            if state in ('CANCELED', 'SUCCESS', 'ERROR', 'DONE'):
                return -4, "被取消、运行结束（完成、成功或失败）的运行记录不能暂停运行"
            if state == 'RUNNING':
                srl.pause(do_pause=True)
                continue
            if state == 'PAUSED' or state == 'STOPPED':
                break

        rl.update(set__status=state)

        return 0


class APIStop(RestfulResource):
    @params({
        'id': StringField(
            description="运行记录id",
            validators=[validators.length(max=32), validators.data_required()]
        ),
    })
    @api
    def post(self):
        """
        停止相应的爬虫进程。直接调用此方法有可能会导致正在运行的任务的数据丢失；一般为先暂停任务，再等待任务爬虫组空闲，再停止。

        :return:
            :success:
                0
            :failure:
                -1, "id和title必须指定其一"
        """
        rl = RunLog.objects.get(id=request.args.get("id"))
        if not rl.title:
            return -1, "运行记录id不存在"
        if rl.status in ('CANCELED', 'SUCCESS', 'ERROR'):
            return -2, "被取消、运行结束（完成、成功或失败）的运行记录不能再停止"

        srl = SpiderRunLog(rl)
        state = srl.status_check()
        if state == 'STOPPED':
            return -2, "爬虫已经是停止状态"

        while True:
            state = srl.status()
            if state in ('CANCELED', 'SUCCESS', 'ERROR', 'DONE'):
                return -4, "被取消、运行结束（完成、成功或失败）的运行记录不能再停止"
            if state == 'RUNNING' or state == 'PAUSED':
                srl.stop()
                continue
            if state == 'STOPPED':
                break

        rl.update(set__status=state)

        return 0


class APIStart(RestfulResource):
    @params({
        'id': StringField(
            description="运行记录id",
            validators=[validators.length(max=32), validators.data_required()]
        ),
    })
    @api
    def post(self):
        """
        启动相应的爬虫

        :return:
            :success:
                0
            :failure:
                -1, "id和title必须指定其一"
        """
        rl = RunLog.objects.get(id=request.args.get("id"))
        if not rl.title:
            return -1, "运行记录id不存在"

        srl = SpiderRunLog(rl)
        state = srl.status_check()
        if state == 'STOPPED':
            return -2, "爬虫已经是停止状态"

        srl.spider.launch(rl.crawler_count)
        srl.status_check()
        return 0


class APICancel(RestfulResource):
    @params({
        'id': StringField(
            description="运行记录id",
            validators=[validators.length(max=32), validators.data_required()]
        ),
    })
    @api
    def post(self):
        """
        取消运行。停止爬虫，并删除爬取队列。

        :return:
            :success:
                0
            :failure:
                -1, "id和title必须指定其一"
        """
        rl = RunLog.objects.get(id=request.args.get("id"))
        if not rl.title:
            return -1, "运行记录id不存在"
        if rl.status in ('CANCELED', 'SUCCESS', 'ERROR'):
            return -2, "被取消、运行结束（完成、成功或失败）的运行记录不能再取消"

        srl = SpiderRunLog(rl)
        srl.spider.stop()
        srl.spider.queue_clear()
        rl.update(set__status='CANCELED')
        return 0

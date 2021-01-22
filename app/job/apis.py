from flask import request, url_for, redirect, render_template, current_app
from flask_restful import Resource as RestfulResource
from ..models_mongo import *
from flask_security import current_user
from .. import api, params, json_validator, json_field_validator
from wtforms import *
from flask_mongoengine.wtf import model_form
from hashlib import md5

from datetime import datetime
import json, re
import requests
import time
from pymongo.errors import DuplicateKeyError
from mongoengine.errors import NotUniqueError, DoesNotExist
from jsonschema import validate as json_validate

from .utils import SpiderJob, spec_schema, ServiceParamsForm
from datetime import datetime


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
        'category': StringField(
            description="筛选任务类别，TASK 或 SERVICE 或为空",
            validators=[validators.optional(), validators.any_of(['TASK', 'SERVICE'])]
        ),
        "search_key": StringField(
            description="搜索关键词",
        ),
        "schedule": StringField(
            description="筛选执行计划",
            validators=[validators.optional(), validators.any_of(['at', 'cron', 'unknown'])]
        ),
        "enabled": StringField(
            description="是否启用：yes启用 或 no禁用，不传则为全部",
            validators=[validators.optional(), validators.any_of(['yes', 'no'])]
        ),
    })
    @api
    def get(self):
        """
        获取任务列表

        :return:
            :success:
                {
                  "page":[
                     {
                        "category":"TASK",
                        "content":{
                           "service_inst":null,
                           "spec":{}
                        },
                        "create_time":"2021-01-13 13:03:30",
                        "enabled":true,
                        "id":"5ffe7f22aad296c2c98761a9",
                        "last_done_time":null,
                        "last_start_time":null,
                        "schedule":{
                           "at":{
                              "$date":1640858400000
                           },
                           "cron":null
                        },
                        "crawler_count":1,
                        "title":"test_spec1"
                     },
                     {
                        "category":"TASK",
                        "content":{
                           "service_inst":null,
                           "spec":{}
                        },
                        "create_time":"2021-01-13 10:12:02",
                        "enabled":true,
                        "id":"5ffe56f26e6a0a2efd8316f9",
                        "last_done_time":null,
                        "last_start_time":null,
                        "schedule":{
                           "at":{
                              "$date":1640858400000
                           },
                           "cron":null
                        },
                        "crawler_count":1,
                        "title":"test_spec13"
                     },
                  ],
                  "total":2
               }
        """
        p = request.args.get('p')
        psize = request.args.get('psize')
        filter_kwargs = {}
        if request.args.get('category'):
            filter_kwargs.update({'category': request.args.get('category')})
        if request.args.get("search_key"):
            regex = re.compile('.*' + re.escape(request.args.get("search_key")) + '.*')
            filter_kwargs.update({"title": regex})

        # filter schedule
        if request.args.get("schedule") == 'at':
            filter_kwargs.update({"schedule__at__ne": None})
        elif request.args.get("schedule") == 'cron':
            filter_kwargs.update({"schedule__cron__ne": None})
        elif request.args.get("schedule") == 'unknown':
            filter_kwargs.update({"schedule__at": None})
            filter_kwargs.update({"schedule__cron": None})

        # enabled
        if request.args.get("enabled"):
            filter_kwargs.update({"enabled": request.args.get("enabled") == 'yes'})

        filter_job = Job.objects(**filter_kwargs).order_by('-create_time')
        return {
            'page': [j.to_dict() for j in filter_job[(p-1)*psize:p*psize]],
            'total': filter_job.count()
        }


class APICreate(RestfulResource):
    @params({
        'title': StringField(
            description="任务名称",
            validators=[validators.length(max=64), validators.data_required()]
        ),
        'category': StringField(
            description="任务类别，TASK 或 SERVICE",
            default='TASK',
            validators=[validators.optional(), validators.any_of(['TASK', 'SERVICE'])]
        ),
        'spec': StringField(
            description="任务配置，json串",
            validators=[json_field_validator()]
        ),
        'service_id': StringField(
            description="调用服务id",
            validators=[validators.length(max=32)]
        ),
        'service_params': FieldList(
            FormField(ServiceParamsForm),
            description="调用服务的参数，service_params-0-name和service_params-0-value来传入第一组参数名和值；第二组参数则为service_params-1-name和service_params-1-value，依此类推"
        ),
        'schedule_at': DateTimeField(
            description="任务执行时间"
        ),
        'schedule_cron_second': StringField(
            description="cron秒，可精确到毫秒",
        ),
        'schedule_cron_minute': StringField(
            description="cron分钟",
        ),
        'schedule_cron_hour': StringField(
            description="cron小时",
        ),
        'schedule_cron_day_of_month': StringField(
            description="cron几号",
        ),
        'schedule_cron_month': StringField(
            description="cron月份",
        ),
        'schedule_cron_day_of_week': StringField(
            description="cron星期",
        ),
        'crawler_count': IntegerField(
            description="所需爬虫数",
            default=1,
            validators=[validators.number_range(min=1, max=20)]
        ),
    })
    @api
    def post(self):
        """
        创建任务

        :return:
            :success:
                {
                    "job_id": "5fe756b270d69643f25be490"
                }
            :failure:
                -1, "spec或service_id不可同时为空"
                -2, "任务名不可重复。有相同名称的任务已存在。"
                -3, "任务关联的服务不存在。"
        """
        job = Job()
        job.title = request.args.get('title')
        # not sure why the default value is not taken
        job.category = request.args.get('category') if request.args.get('category') else "TASK"
        job.create_time = datetime.now()
        job.crawler_count = request.args.get('crawler_count')
        # content: spec 或 服务实例 二选一
        spec = None
        job_srv_inst = None
        if request.args.get('service_id'):
            try:
                srv = Service.objects.get(id=request.args.get('service_id'))
            except DoesNotExist:
                return -3, "任务关联的服务不存在。"
            service_params = {elm['name']: elm['value'] for elm in request.args.get('service_params')}
            job_srv_inst = JobContentServiceInstance(
                service=srv,
                params=service_params
            )
        elif request.args.get('spec'):
            spec = json.loads(request.args.get('spec'))
            json_validate(spec, json.loads(spec_schema))
        else:
            return -1, "spec或service_id不可同时为空"

        job.content = JobContent(spec=spec, service_inst=job_srv_inst)
        # schedule
        cron = None
        if request.args.get('schedule_cron_second') and \
                request.args.get('schedule_cron_minute') and \
                request.args.get('schedule_cron_hour') and \
                request.args.get('schedule_cron_day_of_month') and \
                request.args.get('schedule_cron_month') and \
                request.args.get('schedule_cron_day_of_week'):
            cron = JobScheduleCron(
                second=request.args.get('schedule_cron_second'),
                minute=request.args.get('schedule_cron_minute'),
                hour=request.args.get('schedule_cron_hour'),
                day_of_month=request.args.get('schedule_cron_day_of_month'),
                month=request.args.get('schedule_cron_month'),
                day_of_week=request.args.get('schedule_cron_day_of_week'),
            )
        job.schedule = JobSchedule(
            at=request.args.get('schedule_at'),
            cron=cron
        )

        try:
            job.save()
        except (DuplicateKeyError, NotUniqueError):
            return -2, "任务名不可重复。有相同名称的任务已存在。"

        sj = SpiderJob(job)
        sj.schedule()

        return {"job_id": str(job.id)}


class APIUpdate(RestfulResource):
    @params({
        'id': StringField(
            description="任务id",
            validators=[validators.length(max=32)]
        ),
        'title': StringField(
            description="任务名称",
            validators=[validators.length(max=64)]
        ),
        'spec': StringField(
            description="任务配置，json串",
            validators=[json_field_validator()]
        ),
        'service_params': FieldList(
            FormField(ServiceParamsForm),
            description="调用服务的参数，service_params-0-name和service_params-0-value来传入第一组参数名和值；第二组参数则为service_params-1-name和service_params-1-value，依此类推"
        ),
        'schedule_at': DateTimeField(
            description="任务执行时间"
        ),
        'schedule_cron_second': StringField(
            description="cron秒，可精确到毫秒",
        ),
        'schedule_cron_minute': StringField(
            description="cron分钟",
        ),
        'schedule_cron_hour': StringField(
            description="cron小时",
        ),
        'schedule_cron_day_of_month': StringField(
            description="cron几号",
        ),
        'schedule_cron_month': StringField(
            description="cron月份",
        ),
        'schedule_cron_day_of_week': StringField(
            description="cron星期",
        ),
        'crawler_count': IntegerField(
            description="所需爬虫数",
            validators=[validators.optional(), validators.number_range(min=1, max=20)]
        ),
    })
    @api
    def patch(self):
        """
        更新任务内容。仅可以更新任务名称，爬虫数，爬取计划，以及：普通任务可更新配置；服务任务可更新参数，不可变更服务id；任务类型不可更新

        :return:
            :success:
                true
            :failure:
                -1, "任务id不存在"
                -2, "任务名不可重复。有相同名称的任务已存在。"
        """
        try:
            job = Job.objects.get(id=request.args.get('id'))
        except DoesNotExist:
            return -1, "任务id不存在"

        tmp_dict = {}
        if request.args.get("title"):
            tmp_dict.update({"title": request.args.get("title")})
        if job.category == 'TASK' and request.args.get('spec'):
            spec = json.loads(request.args.get('spec'))
            json_validate(spec, json.loads(spec_schema))
            tmp_dict.update({"content__spec": spec})
        elif job.category == 'SERVICE' and request.args.get('service_params'):
            service_params = {elm['name']: elm['value'] for elm in request.args.get('service_params')}
            tmp_dict.update({"content__service_inst": JobContentServiceInstance(
                service=Service(id=job.content.service_inst.service.id),
                params=service_params
            )})
        if request.args.get('schedule_at'):
            tmp_dict.update({"schedule__at": request.args.get('schedule_at')})
            tmp_dict.update({"schedule__cron": None})
        if request.args.get("crawler_count"):
            tmp_dict.update({"crawler_count": request.args.get("crawler_count")})
        try:
            if request.args.get('schedule_cron_second') and \
                    request.args.get('schedule_cron_minute') and \
                    request.args.get('schedule_cron_hour') and \
                    request.args.get('schedule_cron_day_of_month') and \
                    request.args.get('schedule_cron_month') and \
                    request.args.get('schedule_cron_day_of_week'):

                cron = JobScheduleCron(
                    second=request.args.get('schedule_cron_second'),
                    minute=request.args.get('schedule_cron_minute'),
                    hour=request.args.get('schedule_cron_hour'),
                    day_of_month=request.args.get('schedule_cron_day_of_month'),
                    month=request.args.get('schedule_cron_month'),
                    day_of_week=request.args.get('schedule_cron_day_of_week'),
                )
                tmp_dict.update({"schedule__cron": cron})
                tmp_dict.update({"schedule__at": None})

            job.update(**tmp_dict)
        except (DuplicateKeyError, NotUniqueError):
            return -2, "任务名不可重复。有相同名称的任务已存在。"

        # reschedule
        sj = SpiderJob(job)
        sj.schedule()

        return 0


class APIGet(RestfulResource):
    @params({
        'id': StringField(
            description="任务id",
            validators=[validators.length(max=32)]
        ),
        'title': StringField(
            description="任务名称",
            validators=[validators.length(max=64)]
        ),
    })
    @api
    def get(self):
        """
        通过id或title获得任务信息

        :return:
            :success:
                {
                    "category": "TASK",
                    "content": {
                      "service_inst": {
                        "params": {
                          "name": "1"
                        },
                        "service": {
                          "$oid": "5fe75c4ebbdf645a871aa287"
                        }
                      },
                      "spec": null
                    },
                    "create_time": "2020-12-27 10:38:02",
                    "enabled": true,
                    "id": "5fe7f38ab219d1906289628c",
                    "schedule": {
                      "at": {
                        "$date": 1609322400000
                      },
                      "cron": {
                        "day_of_month": "10",
                        "day_of_week": "10",
                        "hour": "10",
                        "minute": "10",
                        "month": "10",
                        "second": "10"
                      }
                    },
                    "crawler_count":1,
                    "title": "test"
                  }
            :failure:
                -1, "任务id不存在"
                -2, "id和title必须指定其一"
        """
        try:
            job_id = request.args.get('id')
            if job_id:
                return Job.objects.get(id=job_id).to_dict()
            title = request.args.get('title')
            if title:
                return Job.objects.get(title=title).to_dict()
        except DoesNotExist:
            return -1, "任务id不存在"
        return -2, "id和title必须指定其一"


class APIEnable(RestfulResource):
    @params({
        "ids": FieldList(
            StringField(),
            description="任务id列表，参数示例ids-0=xxx&ids-1=xxx",
            validators=[validators.DataRequired()]
        ),
        'enable': StringField(
            description="是否启用，yes启用，no禁用",
            validators=[validators.data_required(), validators.any_of(['yes', 'no'])]
        ),
    })
    @api
    def post(self):
        """
        启用或禁用任务。返回状态被成功改变的任务id列表；没有返回的id其禁用启用状态没有变化。注意：被禁用的任务不会按期或按时执行，但是可以手动提交。

        :return:
            :success:
                ["5ffea9ea9f5864d962ea3f30", "5ffea9ea9f5864d962ea3f31"]
            :failure:
                --
        """
        changed_ids = []
        try:
            job = Job.objects(id__in=request.args.get("ids"), enabled=(request.args.get('enable') == 'no'))
            for j in job:
                changed_ids.append(str(j.id))
                sj = SpiderJob(j)
                if request.args.get('enable') == 'no':
                    sj.schedule_cancel()
                else:
                    sj.schedule()
            job.update(set__enabled=(request.args.get('enable') == 'yes'))
        except DoesNotExist:
            pass
        return changed_ids


class APIRun(RestfulResource):
    @params({
        'id': StringField(
            description="任务id",
            validators=[validators.length(max=32), validators.data_required()]
        ),
    })
    @api
    def post(self):
        """
        立即运行任务。

        :return:
            :success:8
                0
            :failure:
                -1, "任务id不存在"
        """
        try:
            job = Job.objects.get(id=request.args.get('id'))
        except DoesNotExist:
            return -1, "任务id不存在"

        sj = SpiderJob(job)
        sj.schedule(right_now=True)
        return 0

from flask import request, url_for, redirect, render_template, current_app as app
from flask_restful import Resource as RestfulResource
from ..models_mongo import *
from flask_security import current_user
from .. import api, params, json_validator, json_field_validator
from wtforms import *

import json, re
from datetime import datetime
from pymongo.errors import DuplicateKeyError
from mongoengine.errors import NotUniqueError, DoesNotExist
from jsonschema import validate as json_validate
from .utils import SpiderService
from ..job.utils import ServiceParamsForm, spec_schema


class ServiceParamsSpecForm(Form):
    name = StringField(validators=[validators.data_required(), validators.length(max=64)])
    default = StringField(validators=[validators.optional()])
    desc = StringField(validators=[validators.optional()])


class APICreate(RestfulResource):
    @params({
        'title': StringField(
            description="服务名称",
            validators=[validators.length(max=64), validators.data_required()]
        ),
        'spec': StringField(
            description="任务配置，json串",
            validators=[json_field_validator(), validators.data_required()]
        ),
        'service_params_spec': FieldList(
            FormField(ServiceParamsSpecForm),
            description="调用服务的参数规格，service_params_spec-0-name、service_params_spec-0-default和service_params_spec-0-desc来传入第一组参数名、默认值和描述；第二组参数则为service_params_spec-1-name、service_params_spec-1-value和service_params_spec-1-desc依此类推",
            validators=[validators.optional()]
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
        创建服务

        :return:
            :success:
                {
                    "service_id"："5fe756b270d69643f25be490"
                }
            :failure:
                -1, "任务名不可重复。有相同名称的任务已存在。"
        """
        srv = Service()
        srv.title = request.args.get('title')
        srv.create_time = datetime.now()
        srv.crawler_count = request.args.get('crawler_count')
        spec = json.loads(request.args.get('spec'))
        json_validate(spec, json.loads(spec_schema))
        srv.spec = spec
        srv.params = [
            ServiceParamsSpec(name=elm['name'], default=elm.get('default', ''), description=elm.get('desc', ''))
            for elm in request.args.get('service_params_spec')]
        try:
            srv.save()
        except (DuplicateKeyError, NotUniqueError):
            return -1, "服务名不可重复。有相同名称的任务已存在。"
        return {"service_id": str(srv.id)}


class APIUpdate(RestfulResource):
    @params({
        'id': StringField(
            description="服务id",
            validators=[validators.data_required(), validators.length(max=32)]
        ),
        'title': StringField(
            description="服务名称",
            validators=[validators.length(max=64)]
        ),
        'spec': StringField(
            description="任务配置，json串",
            validators=[json_field_validator()]
        ),
        'service_params_spec': FieldList(
            FormField(ServiceParamsSpecForm),
            description="调用服务的参数规格，service_params_spec-0-name、service_params_spec-0-default和service_params_spec-0-desc来传入第一组参数名、默认值和描述；第二组参数则为service_params_spec-1-name、service_params_spec-1-value和service_params_spec-1-desc依此类推",
            validators=[validators.optional()]
        ),
        'crawler_count': IntegerField(
            description="所需爬虫数",
            validators=[validators.optional(), validators.number_range(min=1, max=20)]
        ),
    })
    @api
    def patch(self):
        """
        更新服务。除参数id外必须外，其余参数均为选填。

        :return:
            :success:
                0
            :failure:
                -1, "匹配id的服务不存在"
                -2, "任务名不可重复。有相同名称的任务已存在"
        """
        try:
            srv = Service.objects.get(id=request.args.get('id'))
        except DoesNotExist:
            return -1, "匹配id的服务不存在"

        tmp_dict = {}
        if request.args.get("title"):
            tmp_dict.update({"title": request.args.get("title")})
        if request.args.get('spec'):
            spec = json.loads(request.args.get('spec'))
            json_validate(spec, json.loads(spec_schema))
            tmp_dict.update({"spec": spec})
        if request.args.get('crawler_count'):
            tmp_dict.update({"crawler_count": request.args.get('crawler_count')})
        if request.args.get('service_params_spec'):
            tmp_dict.update({"params": [
                ServiceParamsSpec(name=elm['name'], default=elm.get('default', ''), description=elm.get('desc', ''))
                for elm in request.args.get('service_params_spec')]})
        try:
            srv.update(**tmp_dict)
        except (DuplicateKeyError, NotUniqueError):
            return -2, "任务名不可重复。有相同名称的任务已存在。"

        return 0


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
            validators=[validators.length(max=64)]
        ),
        "enabled": StringField(
            description="是否启用：yes启用 或 no禁用，不传则为全部",
            validators=[validators.optional(), validators.any_of(['yes', 'no'])]
        ),
    })
    @api
    def get(self):
        """
        获取服务列表

        :return:
            :success:
                {
                    "page": [
                      {
                        "create_time": "2021-01-13 16:06:02",
                        "id": "5ffea9ea9f5864d962ea3f30",
                        "last_done_time": null,
                        "last_start_time": null,
                        "params": [],
                        "spec": {...},
                        "crawler_count":1,
                        "enabled": true,
                        "title": "123321"
                      },
                      {
                        "create_time": "2021-01-14 16:21:22",
                        "id": "5fffff02a226e6ef30134587",
                        "last_done_time": null,
                        "last_start_time": null,
                        "params": [
                          {
                            "default": "1",
                            "description": "",
                            "name": "test"
                          }
                        ],
                        "spec": {...},
                        "crawler_count":1,
                        "enabled": false,
                        "title": "test srv"
                      }
                    ],
                    "total": 2
                  }
            :failure:
                -1, "id和title必须指定其一"
        """
        p = request.args.get('p')
        psize = request.args.get('psize')
        filter_kwargs = {}
        if request.args.get("enabled"):
            filter_kwargs.update({"enabled": (request.args.get("enabled") == 'yes')})
        if request.args.get("search_key"):
            regex = re.compile('.*' + re.escape(request.args.get("search_key")) + '.*')
            filter_kwargs.update({"title": regex})
        filter_srv = Service.objects(**filter_kwargs)
        return {
            'page': [j.to_dict() for j in filter_srv[(p - 1) * psize:p * psize]],
            'total': filter_srv.count()
        }


class APIEnable(RestfulResource):
    @params({
        "ids": FieldList(
            StringField(),
            description="服务id列表，参数示例ids-0=xxx&ids-1=xxx",
            validators=[validators.DataRequired()]
        ),
        "enable": StringField(
            description="启用与否，yes启用，no禁用",
            validators=[validators.data_required(), validators.any_of(['yes', 'no'])]
        )
    })
    @api
    def post(self):
        """
        启用或禁用服务。返回状态被成功改变的服务id列表；没有返回的id其禁用启用状态没有变化。
        :return:
            :success:
                ["5ffea9ea9f5864d962ea3f30", "5ffea9ea9f5864d962ea3f31"]
            :failure:
                --
        """
        changed_ids = []
        try:
            srvs = Service.objects(id__in=request.args.get("ids"), enabled=(request.args.get('enable') == 'no'))
            changed_ids = [s.to_dict(fields=['id'])['id'] for s in srvs]
            srvs.update(set__enabled=(request.args.get('enable') == 'yes'))
        except DoesNotExist:
            pass
        return changed_ids


class APICall(RestfulResource):
    @params({
        'id': StringField(
            description="服务id",
            validators=[validators.length(max=64)]
        ),
    }, strict=False)
    @api
    def get(self):
        """
        调用服务
        :return:
            :success:
                0
            :failure:
                -1, "匹配id的服务不存在"
                -2, "服务是禁用状态，不能调用"
        """
        try:
            srv = Service.objects.get(id=request.args.get('id'))
        except DoesNotExist:
            return -1, "匹配id的服务不存在"
        if not srv.enabled:
            return -2, "服务是禁用状态，不能调用"

        params = dict(request.args)
        params.pop('id', None)

        ss = SpiderService(srv, params)
        ss.schedule()
        return 0

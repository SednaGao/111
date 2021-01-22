from flask import g, current_app as app
from flask.json import loads, dumps
import re
import redis
import subprocess
from apscheduler.jobstores.base import JobLookupError
import os, sys
from wtforms import StringField, validators, Form
from .. import FMVCUserError
from ..spider.utils import Spider
sys.path.append(os.path.dirname(sys.path[0]))
from sccm.utils.functions import find_by_jpath


class ServiceParamsForm(Form):
    name = StringField(validators=[validators.data_required()])
    value = StringField()


class SpiderJob:

    def __init__(self, job_obj):
        self.job = job_obj
        self.spec = self.get_spec()
        spider_name = find_by_jpath(self.spec, "$.spiderid", True)
        if not spider_name:
            raise FMVCUserError(-11, "配置中没有找到spider名")
        self.spider = Spider(spider_name)

    def get_spec(self):
        if self.job.content.spec:
            return self.job.content.spec
        elif self.job.content.service_inst:
            from ..service.utils import SpiderService
            srv = SpiderService(self.job.content.service_inst.service, self.job.content.service_inst.params)
            return srv.get_spec()
        raise FMVCUserError(-19, '无法获取任务的爬虫配置。这可能是一个非法的任务。')

    def schedule(self, right_now=False):
        from ..run_log.utils import scheduler_send_request
        spec_json = self.get_spec()

        kwargs = {}
        if right_now:
            return scheduler_send_request(job_id=self.job.id, spec=spec_json)
        elif self.job.schedule.at:
            kwargs.update({'trigger': 'date', 'run_date': self.job.schedule.at})
        elif self.job.schedule.cron:
            kwargs.update({
                'trigger': 'cron',
                'month': self.job.schedule.cron.month,
                'day': self.job.schedule.cron.day_of_month,
                'day_of_week': self.job.schedule.cron.day_of_week,
                'hour': self.job.schedule.cron.hour,
                'minute': self.job.schedule.cron.minute,
                'second': self.job.schedule.cron.minute,
            })
        else:
            # 未计划
            return
        app.scheduler.add_job(id=str(self.job.id), replace_existing=True, func=scheduler_send_request, kwargs={
            'job_id': self.job.id,
            'spec': spec_json
        }, **kwargs)

    def schedule_cancel(self):
        try:
            app.scheduler.remove_job(str(self.job.id))
        except JobLookupError:
            # safely ignored
            pass


spec_schema = '''
{
    "type": "object",
    "properties": {
        "appid": {
            "type": "string",
            "default": "sccm"
        },
        "crawlid": {
            "type": "string",
            "default": ""
        },
        "spiderid": {
            "type": "string",
            "default": ""
        },
        "url": {
            "type": "string"
        },
        "priority": {
            "type": "integer",
            "minimum": 1,
            "default": 50
        },
        "maxdepth": {
            "type": "integer",
            "minimum": 0,
            "maximum": 10000000,
            "default": 0
        },
        "allowed_domains": {
            "type": "array",
            "uniqueItems": true,
            "items": {
                "type": "string"
            },
            "default": null
        },
        "allow_regex": {
            "type": "array",
            "uniqueItems": true,
            "items": {
                "type": "string"
            },
            "default": null
        },
        "deny_regex": {
            "type": "array",
            "uniqueItems": true,
            "items": {
                "type": "string"
            },
            "default": null
        },
        "deny_extensions": {
            "type": "array",
            "uniqueItems": true,
            "items": {
                "type": "string"
            },
            "default": null
        },
        "expires": {
            "type": "integer",
            "default": 0
        },
        "useragent": {
            "type": "string",
            "minLength": 3,
            "maxLength": 1000,
            "default": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36"
        },
        "cookie": {
            "type": "string",
            "minLength": 3,
            "maxLength": 1000,
            "default": null
        },
        "attrs": {
            "type": "object",
            "default": null
        }
    },
    "required": [
        "appid",
        "crawlid",
        "url"
    ],
    "additionalProperties": false
}
'''

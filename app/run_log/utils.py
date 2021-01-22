from flask import g, current_app as app
from flask.json import loads, dumps
import re
import redis
import requests
import os, sys, datetime
from wtforms import StringField, validators, Form
from .. import FMVCUserError
from ..spider.utils import Spider
from ..job.utils import SpiderJob
from ..service.utils import SpiderService
from ..models_mongo import *
sys.path.append(os.path.dirname(sys.path[0]))
from sccm.utils.functions import find_by_jpath


def scheduler_send_request(job_id=None, service_id=None, spec={}):
    # init runlog
    rl = RunLog()
    if job_id:
        rl.category = "JOB"
        job = Job.objects.get(id=job_id)
        rl.job = job
        rl.title = job.title
        rl.crawler_count = job.crawler_count
    elif service_id:
        rl.category = "SERVICE"
        srv = Service.objects.get(id=service_id)
        rl.service = srv
        rl.title = srv.title
        rl.crawler_count = srv.crawler_count
    rl.invoke_datetime = datetime.now()
    rl.spec = spec
    rl.status = 'INIT'
    rl.save()

    # send the request to scc
    error = ""
    try:
        response = requests.post("http://{}:{}/feed".format(
            app.config['SCC_SERVICE_HOST'], app.config['SCC_SERVICE_PORT']), json=spec, timeout=3)
        if response.status_code < 200 or response.status_code >= 300:
            error = "爬虫服务异常返回：{}".format(response.text)
        else:
            resp_json = response.json()
            if resp_json.get('status') != "SUCCESS":
                error = "爬虫服务提交失败：{}".format(resp_json.get('error'))
    except Exception as e:
        error = "爬虫服务提交失败: {}".format(e)
    if error:
        rl.update(set__status='SENT', set__error_message=error, set__end_datetime=datetime.now(), set__result='FAILURE')
        return

    # SENT success
    rl.update(set__status='SENT')

    # 为此次爬取启动爬虫
    #rl.spider.launch(rl.crawler_count)
    rl.update(set__status='READY')


def scheduler_stop_spider():
    pass


class SpiderRunLog:

    def __init__(self, run_log_obj):
        self.run_log = run_log_obj
        if run_log_obj.category == 'JOB':
            self.run_spider_obj = SpiderJob(run_log_obj.job)
        elif run_log_obj.category == 'SERVICE':
            self.run_spider_obj = SpiderService(run_log_obj.service)
        spider_name = find_by_jpath(self.get_spec(), "$.spiderid", True)
        if not spider_name:
            raise FMVCUserError(-11, "配置中没有找到spider名")
        self.spider = Spider(spider_name)

    # 执行状态
    # INIT, 刚提交
    # SENT, 已提交爬虫端
    # READY, 爬虫已启动。尚未开始运行任务；或任务已经全部完成，即将由scheduler关闭
    # RUNNING, 正在爬取
    # PAUSED, 爬取暂停，爬虫待命，任务队列尚在，可恢复执行
    # STOPPED, 爬取停止，爬虫停止，任务队列尚在，可恢复执行
    # CANCELED, 结束状态：取消，任务队列已删除，不可恢复
    def status(self):
        if self.run_log.status in ('CANCELED', 'DONE'):
            return self.run_log.status
        return self.spider.status()

    def status_check(self):
        state = self.status()
        if state != self.run_log.status:
            self.run_log.update(set__status=state)

    def is_idle(self):
        return self.spider.is_idle()

    def pause(self, do_pause=True):
        status = 'PAUSED' if do_pause else 'RUNNING'
        self.spider.pause(do_pause)
        self.run_log.update(set__status=status)

    def resume(self):
        self.pause(False)

    def stop(self):
        self.spider.stop()
        self.run_log.update(set__status="STOPPED")

    def cancel(self):
        self.spider.stop()
        self.spider.queue_clear()
        self.run_log.update(set__status="CANCELED")

    def get_spec(self):
        return self.run_spider_obj.get_spec()

    def schedule(self, right_now=False):
        self.run_spider_obj.schedule(right_now=right_now)

# coding: utf8

import requests

from flask import current_app as app
from .utils import SpiderJob


def run_job(job):
    """
    爬虫运行调度任务
    :param job: 当前任务对象
    :return:
        ：success:
            0
    """
    sj = SpiderJob(job)
    state = sj.status_check()
    if state == 'RUNNING':
        raise ValueError("当前任务已在运行,任务id: {}".format(job.id))

    if state == 'PAUSED':
        sj.resume()
    if state == 'STOPPED':
        # no spider process
        sj.start_crawlers(1)
        state_new = sj.status()
        if state_new == 'RUNNING':
            raise ValueError("任务已经是运行状态，需要等待其结束,任务id: {}".format(job.id))

    response = requests.post("http://{}:{}/feed".format(
        app.config['SCC_SERVICE_HOST'], app.config['SCC_SERVICE_PORT']), json=sj.spec)

    if response.status_code < 200 or response.status_code >= 300:
        raise ValueError("爬虫服务异常返回：{}".format(response.text))
    resp_json = response.json()
    if resp_json.get('status') != "SUCCESS":
        raise ValueError("爬虫服务提交失败：{}".format(resp_json.get('error')))

    if job.status != "RUNNING":
        job.update(set__status="RUNNING")

    return 0

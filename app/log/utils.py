# coding: utf8

import subprocess

from flask import current_app as app


class LogOperation:
    def __init__(self):
        self.spider_name = ''

    def get_crawlers_log(self):
        docker_control_cmd = "cd {}; ./shell/docker_control.sh st {} l".format(
            app.config['SCC_ROOT'], self.spider_name)
        return subprocess.check_output(
            docker_control_cmd, stderr=subprocess.STDOUT, timeout=3, shell=True).decode('utf-8')

    def get_stream_logs(self, spider_name=''):
        """
        获取实时日志信息
        :param: spider_name: 当前查看日志任务名称
        :return:
            :success:
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
        """
        self.spider_name = spider_name
        return self.get_crawlers_log().split("\n")


log_operation = LogOperation()

import subprocess
import os
import redis
import time

from flask import g, request, url_for, redirect, render_template, current_app as app
from .. import FMVCUserError


def get_scc_redis():
    if 'scc_redis' not in g:
        g.scc_redis = redis.Redis(
            host=app.config['SCC_REDIS_HOST'],
            port=app.config['SCC_REDIS_PORT'],
            db=app.config['SCC_REDIS_DB'],
            password=app.config['SCC_REDIS_PASSWD'],
        )
    return g.scc_redis


class Spider:

    def __init__(self, name):
        self.name = name

        # check if cmd is there
        #if not os.access('{}/shell/docker_control.sh'.format(app.config['SCC_ROOT']), os.X_OK):
            #raise FMVCUserError(-21, "未找到爬虫控制程序")

    # RUNNING, PAUSED, STOPPED, DONE
    def status(self):
        # check if it's stopped
        if not Spider.crawlers_info(self.name):
            return 'STOPPED'
        paused_key = "scc-queue:paused"
        if get_scc_redis().hget(paused_key, self.name):
            return 'PAUSED'
        for q in self.queues():
            if get_scc_redis().zcard(q):
                return 'RUNNING'
        if self.is_idle():
            return 'DONE'
        return 'RUNNING'

    def is_idle(self):
        crawler_count = len(Spider.crawlers_info(self.name))
        # 仅查看1分钟内的log
        cmd = "docker service logs --tail {} {}_crawler 2>&1 | fgrep '| {{\"message\": \"' | fgrep -v '| {{\"message\": \"pop item\"' | fgrep -v '| {{\"message\": \"Current public ip:' | fgrep -v '| {{\"message\": \"Reporting self id\"' | fgrep -v '| {{\"message\": \"Queue is paused' | egrep -v '| {{\"message\": \"[\\w\\s]+Zookeeper connection'".format(
            crawler_count * 12, self.name)
        working_logs = ""
        try:
            working_logs = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=3, shell=True).decode('utf-8')
        except subprocess.CalledProcessError as e:
            if not e.output and not e.stderr:
                return True
            app.logger.debug(e.stdout)
            app.logger.debug(e.stderr)
        if not working_logs:
            return True
        return False

    def launch(self, count=1, force=False):
        """
        执行爬虫,爬虫数量默认为1
        """
        crawler_count = len(Spider.crawlers_info(self.name))
        if not force and crawler_count >= count and not self.is_idle():
            raise FMVCUserError(-22, "爬虫已经有{}个进程在运行了。如果要减少爬虫进程数，请先暂停爬取。".format(crawler_count))
        docker_control_cmd = "cd {}; ./shell/docker_control.sh st {} d {}".format(
            app.config['SCC_ROOT'], self.name, count)
        try:
            ret = subprocess.check_output(
                docker_control_cmd, stderr=subprocess.STDOUT, timeout=20, shell=True).decode('utf-8')
        except subprocess.CalledProcessError as e:
            app.logger.debug(e.stdout)
            app.logger.debug(e.stderr)
            raise FMVCUserError(-23, "启动爬虫指令运行失败。")
        except subprocess.TimeoutExpired as e:
            raise FMVCUserError(-23, "启动爬虫指令运行失败超时。请刷新列表查看是否成功。")
        if not ret:
            raise FMVCUserError(-24, "SCC_ROOT配置不对，无法找到爬虫控制命令。")

        app.logger.debug(ret)

    def scale(self, count):
        crawler_count = len(Spider.crawlers_info(self.name))
        if crawler_count < count:
            return self.launch(count)
        if crawler_count > count:
            # shrink
            self.pause()
            while not self.is_idle():
                time.sleep(10)
            self.launch(count, True)
            self.pause(False)

    def pause(self, do_pause=True):
        if do_pause:
            key = "scc-queue:paused"
            get_scc_redis().hset(key, self.name, 1)
        else:
            self.resume()

    def resume(self):
        key = "scc-queue:paused"
        get_scc_redis().hdel(key, self.name)

    def stop(self):
        docker_control_cmd = "cd {}; ./shell/docker_control.sh st {} s".format(app.config['SCC_ROOT'], self.name)
        try:
            ret = subprocess.check_output(
                docker_control_cmd, stderr=subprocess.STDOUT, timeout=3, shell=True).decode('utf-8')
        except:
            raise FMVCUserError(-27, "停止爬虫指令运行失败。")
        if not ret:
            raise FMVCUserError(-28, "SCC_ROOT配置不对，无法找到爬虫控制命令。")

    # todo: 流式日志
    def logs(self):
        docker_control_cmd = "cd {}; ./shell/docker_control.sh st {} l".format(app.config['SCC_ROOT'], self.name)
        return subprocess.check_output(
            docker_control_cmd, stderr=subprocess.STDOUT, timeout=3, shell=True).decode('utf-8')

    def queues(self):
        return get_scc_redis().keys('{}:*:queue'.format(self.name))

    def queue_clear(self):
        # do it 3 times
        for q in self.queues():
            get_scc_redis().delete(q)
        time.sleep(1)

        for q in self.queues():
            get_scc_redis().delete(q)
        time.sleep(1)

        for q in self.queues():
            get_scc_redis().delete(q)

    @staticmethod
    def info():
        """
        获取进程执行信息
        :return:
            :success:
                {
                    "爬虫组1":  [
                          {
                              'Replica ID': 'xxx',
                              'NAME': 'xxx',
                              'IMAGE': 'xxx',
                              'NODE': 'xxx',
                              'DESIRED STATE': 'xxx',
                              'CURRENT STATE': 'xxx',
                              'ERROR': 'xxx',
                              'PORT': 0
                          },
                          {
                              'Replica ID': 'xxx',
                              'NAME': 'xxx',
                              'IMAGE': 'xxx',
                              'NODE': 'xxx',
                              'DESIRED STATE': 'xxx',
                              'CURRENT STATE': 'xxx',
                              'ERROR': 'xxx',
                              'PORT': 0
                          },
                      ],
                    "爬虫组2":  [
                          {
                              'Replica ID': 'xxx',
                              'NAME': 'xxx',
                              'IMAGE': 'xxx',
                              'NODE': 'xxx',
                              'DESIRED STATE': 'xxx',
                              'CURRENT STATE': 'xxx',
                              'ERROR': 'xxx',
                              'PORT': 0
                          },
                      ]
                    }
        """
        spider_group_info = []
        docker_control_com_cmd = "cd {}; ./shell/docker_control.sh st".format(app.config['SCC_ROOT'])
        try:
            ret = subprocess.check_output(
                docker_control_com_cmd, stderr=subprocess.STDOUT, timeout=5, shell=True
            ).decode('utf-8')

            ret_com_list = ret.split("\n")
            if len(ret_com_list) == 2:
                return {}
            # 总的信息爬虫组索引
            spider_name_index = ret_com_list[0].index("ID")

            for line_com_str in ret_com_list[1:-1]:
                spider_name = line_com_str[:spider_name_index].strip()
                spider_group_info.append({
                    'spider_name': spider_name,
                    'status': Spider(spider_name).status(),
                    "crawlers": Spider.crawlers_info(spider_name)
                })
        except:
            raise FMVCUserError(-29, "获取爬虫信息指令运行失败。")

        if not ret:
            raise FMVCUserError(-30, "SCC_ROOT配置不对，无法找到爬虫控制命令。")

        return spider_group_info

    @staticmethod
    def crawlers_info(spider_name):
        """
        获取爬虫组总的信息
        :return:
            :success:
                [
                    {
                      'Replica ID': 'xxx',
                      'NAME': 'xxx',
                      'IMAGE': 'xxx',
                      'NODE': 'xxx',
                      'DESIRED STATE': 'xxx',
                      'CURRENT STATE': 'xxx',
                      'ERROR': 'xxx',
                      'PORT': 0
                  },
                  {
                      'Replica ID': 'xxx',
                      'NAME': 'xxx',
                      'IMAGE': 'xxx',
                      'NODE': 'xxx',
                      'DESIRED STATE': 'xxx',
                      'CURRENT STATE': 'xxx',
                      'ERROR': 'xxx',
                      'PORT': 0
                  },
                ]
        """
        spider_key_list = ['Replica ID', 'NAME', 'IMAGE', 'NODE', 'DESIRED STATE', 'CURRENT STATE', 'ERROR', 'PORT']

        docker_control_spider_cmd = "cd {}; ./shell/docker_control.sh st {} | tail -n +2".format(
            app.config['SCC_ROOT'], spider_name)
        crawlers_info = []
        try:
            item_index = [0]
            ret = subprocess.check_output(
                docker_control_spider_cmd, stderr=subprocess.STDOUT, timeout=3, shell=True
            ).decode('utf-8')
            ret_spider_list = ret.split("\n")
            if "Not found" in ret:
                return []
            for spider_key in spider_key_list[1:]:
                item_index.append(ret_spider_list[0].index(spider_key))
            item_index.append(-1)
            for line_str in ret_spider_list[1:-1]:
                crawler_info = {spider_key_list[index]: line_str[item_index[index]:item_index[index + 1]].strip()
                                for index in range(len(spider_key_list))}
                crawler_info['INDEX'] = crawler_info['NAME'][crawler_info['NAME'].rfind('.')+1:]
                crawler_info['STATUS'] = "ERROR"
                if not crawler_info['ERROR']:
                    sc = SpiderCrawler(spider_name, crawler_info['INDEX'])
                    crawler_info['STATUS'] = sc.status()
                crawlers_info.append(crawler_info)
        except:
            raise FMVCUserError(-31, "获取爬虫信息指令运行失败。")

        return crawlers_info


class SpiderCrawler:

    def __init__(self, spider_name, index):
        self.index = index
        self.spider_name = spider_name

        # check if cmd is there
        if not os.access('{}/shell/docker_control.sh'.format(app.config['SCC_ROOT']), os.X_OK):
            raise FMVCUserError(-32, "未找到爬虫管理工具")

    def suspend(self):
        cmd = "cd {}; ./shell/docker_control.sh st {} e spider_status suspend {} {}".format(
            app.config['SCC_ROOT'], self.spider_name, self.spider_name, self.index)
        app.logger.debug(cmd)
        ret = ""
        try:
            ret = subprocess.check_output(
                cmd, stderr=subprocess.STDOUT, timeout=5, shell=True).decode('utf-8')
        except subprocess.CalledProcessError as e:
            raise FMVCUserError(-33, "挂起爬虫指令运行失败：{}: {}".format(ret, e.output))
        except Exception as e:
            raise FMVCUserError(-33, "挂起爬虫指令运行失败：{}: {}".format(ret, e))
        return ret.strip()

    def resume(self):
        cmd = "cd {}; ./shell/docker_control.sh st {} e spider_status resume {} {}".format(
            app.config['SCC_ROOT'], self.spider_name, self.spider_name, self.index)
        app.logger.debug(cmd)
        ret = ""
        try:
            ret = subprocess.check_output(
                cmd, stderr=subprocess.STDOUT, timeout=5, shell=True).decode('utf-8')
        except subprocess.CalledProcessError as e:
            raise FMVCUserError(-34, "停止爬虫指令运行失败：{}: {}".format(ret, e.output))
        except Exception as e:
            raise FMVCUserError(-34, "停止爬虫指令运行失败：{}: {}".format(ret, e))
        return ret.strip()

    def status(self):
        # READY RUNNING SUSPENDED
        key = "scc-spider:{}".format(self.spider_name)
        status_str = get_scc_redis().hget(key, self.index)
        app.logger.debug("{} {} {}".format(self.spider_name, self.index, status_str))
        if status_str.decode('utf-8') == 'IM_SUSPENDED':
            return 'SUSPENDED'
        if status_str:
            return 'RUNNING'
        return 'READY'

    def stop(self):
        pass

    def is_idle(self):
        # 仅查看1分钟内的log
        crawler_count = len(Spider.crawlers_info(self.spider_name))
        cmd = "docker service logs --tail {} {}_crawler 2>&1 | fgrep '{}_crawler.{}' | fgrep '| {{\"message\": \"' | fgrep -v '| {{\"message\": \"pop item\"' | fgrep -v '| {{\"message\": \"Current public ip:' | fgrep -v '| {{\"message\": \"Reporting self id\"'".format(
            crawler_count * 12, self.spider_name, self.spider_name, self.index)
        working_logs = ""
        try:
            working_logs = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=5, shell=True).decode('utf-8')
        except subprocess.CalledProcessError as e:
            if not e.output and not e.stderr:
                return True
            app.logger.debug(e.stdout)
            app.logger.debug(e.stderr)
        if not working_logs:
            return True
        return False

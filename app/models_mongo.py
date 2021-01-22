from datetime import date, datetime

from mongoengine import Document
from mongoengine import CASCADE, PULL, DENY
from mongoengine.errors import DoesNotExist
from mongoengine import StringField, IntField, DateTimeField, DictField, ReferenceField, BooleanField
from mongoengine import LazyReferenceField, ObjectIdField, FloatField, ListField, EmailField, EmbeddedDocumentField
from bson import objectid
from bson.dbref import DBRef
from .db import db
from flask_security import UserMixin, RoleMixin
import time


class FMVCDocument:
    meta = {'abstract': True}

    def to_dict(self, fields=None):
        """
        document to dict 方式

        :param fields: 获取的字段列表, 默认为获取全部

        example:
            from datetime import datetime

            from mongoengine import StringField, DateTimeField, ReferenceField, connect


            class Person(BaseDocument):
                username = StringField()
                create_time = DateTimeField()
                blog = ReferenceField('Blog')


            class Blog(BaseDocument):
                title = StringField()
                content = StringField()

            connect("main", host="localhost", port=27017)

            person = Person()
            person.username = "xiaoming"
            person.create_time = datetime.now()

            blog = Blog()
            blog.title = 'blog title'
            blog.content = 'blog content'
            person.blog = blog

            blog.save()
            person.save()

            data = person.to_dict(fields=[
                 "id:person_id",
                 "username",
                 "create_time",
                 "blog.id:blog_id",
                 "blog.title:blog_title",
                 "blog.content"
            ])
            print(data)
            -----------------------------------------
            {
             'person_id': '5df321b482fb700f766f2f02',
             'username': 'xiaoming',
             'create_time': '2019-12-24 13:11:54',
             'blog': {'blog_id': '5df321b482fb700f766f2f03', 'blog_title': 'blog title', 'content': 'blog content'}
            }

            )
        """

        def _format_(value):
            if isinstance(value, objectid.ObjectId):
                value = str(value)
            elif isinstance(value, datetime):
                value = value.strftime('%Y-%m-%d %H:%M:%S')
            elif isinstance(value, date):
                value = value.strftime('%Y-%m-%d')
            elif isinstance(value, (BaseDocument, EmbeddedDocument)):
                value = value.to_dict()
            elif isinstance(value, DBRef):
                value = {'$oid': str(value.id)}
            return value

        def _set_dotted_value(dotted_key, value, item):

            parts = dotted_key.split(':')[-1].split('.')
            key = parts.pop(0)
            parent = item
            while parts:
                parent = parent.setdefault(key, {})
                key = parts.pop(0)
            parent[key] = value

        def _get_dotted_value(key, document):
            key = key.split(':')[0]
            parts = key.split('.')
            key = parts.pop(0)
            value = _get_field_value(key, document)
            try:
                while parts:
                    key = parts.pop(0)
                    value = _get_field_value(key, value)
            except AttributeError:
                value = None
            return _format_(value)

        def _get_field_value(key, document):
            try:
                if key in getattr(document, '_fields', {}):
                    return document[key]
            except (AttributeError, DoesNotExist):
                pass

        data = {}
        if fields and all(f.startswith("+") for f in fields):
            fields = list(self._data.keys()) + list(map(lambda x: x[1:], fields))
        if fields is None:
            fields = self._data.keys()
        for field_key in fields:
            if isinstance(field_key, str) and not field_key.startswith('_'):
                field_value = _get_dotted_value(field_key, self)
                _set_dotted_value(field_key, field_value, data)

        return data


class BaseDocument(db.Document, FMVCDocument):
    meta = {'abstract': True}


class EmbeddedDocument(db.EmbeddedDocument, FMVCDocument):
    meta = {'abstract': True}


class JobContentServiceInstance(EmbeddedDocument):
    service = ReferenceField('Service')  # 关联的service
    params = DictField(null=True)  # 调用时的参数


class JobContent(EmbeddedDocument):
    spec = DictField(null=True)  # scc的爬虫配置
    service_inst = EmbeddedDocumentField(JobContentServiceInstance, null=True)  # 指向服务的详情


class JobScheduleCron(EmbeddedDocument):
    second = StringField()
    minute = StringField()
    hour = StringField()
    day_of_month = StringField()
    month = StringField()
    day_of_week = StringField()


class JobSchedule(EmbeddedDocument):
    at = DateTimeField(null=True)  # 调用时间
    cron = EmbeddedDocumentField(JobScheduleCron, null=True)  # 调用周期配置


class Job(BaseDocument):
    """
    任务表
    """
    meta = {
        'indexes': [
            {'fields': ['-create_time']}
        ]
    }

    title = StringField(max_length=64, unique=True)  # 任务名
    category = StringField(choices=('TASK', 'SERVICE'), required=True)  # 任务类型：工作型和服务型
    create_time = DateTimeField()  # 创建时间
    last_start_time = DateTimeField(null=True)  # 上次执行开始时间
    last_done_time = DateTimeField(null=True)  # 上次执行结束时间
    content = EmbeddedDocumentField(JobContent)  # 任务配置
    schedule = EmbeddedDocumentField(JobSchedule)  # 任务计划
    crawler_count = IntField(required=True, default=1)
    enabled = BooleanField(required=True, default=True)  # 启用 or 禁用


class ServiceParamsSpec(EmbeddedDocument):
    name = StringField(max_length=64)
    default = StringField()
    description = StringField()


class Service(BaseDocument):
    """
    任务表
    """
    meta = {
        'indexes': [
            {'fields': ['-create_time']}
        ]
    }

    title = StringField(max_length=64, unique=True)  # 服务名
    spec = DictField()  # scc的爬取配置
    create_time = DateTimeField()  # 创建时间
    last_start_time = DateTimeField(null=True)  # 上次调用开始时间
    last_done_time = DateTimeField(null=True)  # 上次调用结束时间
    crawler_count = IntField(required=True, default=1)
    params = ListField(EmbeddedDocumentField(ServiceParamsSpec), null=True)  # 指定账号集
    enabled = BooleanField(required=True, default=True)  # 启用 or 禁用


class RunLog(BaseDocument):
    meta = {
        'indexes': [
            {'fields': ['-invoke_datetime']},
        ]
    }

    title = StringField(max_length=64)
    category = StringField(choices=('JOB', 'SERVICE'), required=True)  # 类型：任务 或 服务
    job = ReferenceField('Job')
    service = ReferenceField('Service')
    spec = DictField()  # scc的爬取配置，如果来自服务，则已经做过参数替换
    crawler_count = IntField(min_value=1, max_value=50)
    invoke_datetime = DateTimeField(default=datetime.now())
    end_datetime = DateTimeField(null=True)
    # 执行状态
    # INIT, 刚提交
    # SENT, 已提交爬虫端
    # READY, 爬虫已启动。尚未开始运行任务；或任务已经全部完成，即将由scheduler关闭
    # RUNNING, 正在爬取
    # PAUSED, 爬取暂停，爬虫待命，任务队列尚在，可恢复执行
    # STOPPED, 爬取停止，爬虫停止，任务队列尚在，可恢复执行
    # CANCELED, 结束状态：取消，任务队列已删除，不可恢复
    # DONE, 结束状态：爬取任务已经完成，等待标记为SUCCESS
    status = StringField(choices=('INIT', 'SENT', 'READY', 'RUNNING', 'PAUSED', 'STOPPED', 'CANCELED'), required=True)
    # 执行结果
    # UNKNOWN, 未知
    # SUCCESS, 结束状态：执行完成，爬虫关闭
    # ERROR, 结束状态：执行错误，爬虫关闭
    result = StringField(choices=('SUCCESS', 'FAILURE', 'UNKNOWN'), default='UNKNOWN')
    error_message = StringField(default='')


class Executor(BaseDocument):
    """
    任务表
    """
    meta = {
        'indexes': [
            {'fields': ['-create_time']}
        ]
    }

    title = StringField(max_length=64, unique=True)  # 包名
    description = StringField(max_length=1024)  # 描述
    create_time = DateTimeField()  # 创建时间
    url = StringField(max_length=1024)  # 下载地址
    status = StringField(choices=('READY', 'DELETED'), default='READY')  # 状态: 就绪，已删除


class Activity(BaseDocument):
    """
    活动表
    """

    name = StringField(max_length=64)  # 活动的名称
    account_source = ReferenceField('AccountSource')  # 所属平台
    activity_type = StringField(choices=('ROUTINE', 'ONCE', 'EVENT'), required=True)  # 活动类型
    create_time = FloatField()  # 创建时间
    start_time = DateTimeField()  # 开始时间
    end_time = DateTimeField()  # 结束时间
    minions_set = ListField(ReferenceField('MinionsSet'))  # 指定账号集
    extra = DictField()  # 活动配置
    config = ListField(DictField())  # 动作组配置
    status = StringField(choices=('ENABLED', 'DISABLED', 'RUNNING', 'FINISHED'), default='ENABLED')  # 状态


class AccountAction(BaseDocument):
    """
    动作链表
    """
    choices = ('ACTION', 'CRAWL', 'WATCH', 'CREATE')
    start_url = StringField(max_length=128, required=True)  # 起始url
    source_id = ObjectIdField()  # 平台id
    account_source = ReferenceField('AccountSource', required=True)  # 所属平台
    action_name = StringField(max_length=64, unique_with='source_id')  # 描述行为的名称
    action_type = StringField(choices=choices)  # 动作链的类型
    action_config = DictField(required=True)  # 页面动作的全json
    crawl_elements = DictField()  # 爬虫的爬取元素
    data_download_settings = DictField()  # 爬虫数据存储位置的配置
    file_download_settings = DictField()  # 爬虫文件下载的配置
    create_time = FloatField(required=True)  # 创建时间
    status = StringField(choices=('ENABLE', 'DISABLE'), default='ENABLE')  # 状态


class AccountActionParts(BaseDocument):
    """
    动作链片段表
    """
    choices = ('crawl_pages', 'wb_events')
    config = StringField(required=True)  # 爬虫配置
    context = StringField(required=True, choices=choices)  # 上级配置节点
    action_name = StringField(max_length=64, required=True, unique_with='source_id', null=False)  # 片段的行为名称
    create_time = FloatField()  # 创建时间timestamp
    source_id = ObjectIdField()  # 平台id


class AccountSource(BaseDocument):
    """
    平台表
    """

    source_name = StringField(max_length=64, required=True)  # 平台名称
    source_type = StringField(choices=('EMAIL', 'APP'), required=True, unique_with='source_name', default='APP')  # 类型
    login_url = StringField(max_length=128, required=True, unique_with='source_name')  # 平台登录页面的url
    action_parts_login = ReferenceField(AccountActionParts)  # account_action_parts用于用户登录该平台
    action_create = ReferenceField('AccountAction')  # account_action，用于创建该平台的账号的动作链id
    smart_option = DictField()  # 用于定义爬虫的smart_option
    create_time = FloatField(time.time())  # 创建时间timestamp
    status = StringField(default='ENABLED', choices=('DISABLED', 'ENABLED'))  # 平台状态


class Account(BaseDocument):
    """
    账号表
    """
    account_source = ReferenceField('AccountSource', required=True, reverse_delete_rule=CASCADE)  # 所属平台
    user_name = StringField(max_length=64, required=True, unique_with='account_source')  # 账号用户名
    password = StringField(max_length=64, required=True)  # 账号密码
    account_info = ReferenceField('AccountInfo')  # 所属账号信息
    reg_email = EmailField()  # 注册账号使用的邮箱
    phone_number = StringField(max_length=16)  # 注册账号使用的手机号
    reg_time = FloatField()  # 注册时间
    health_status = StringField(default="unknown",
                                choices=("unknown", "healthy", "unhealthy", "creating", "failure"))  # 健康状态
    activities = ListField(ReferenceField(Activity, reverse_delete_rule=PULL))  # 账号在哪些即将或正在进行的活动中使用
    login_cookie = StringField()  # 账号登录的cookie
    last_active_time = FloatField()  # 上次活跃时间
    stats30 = IntField(default=0)  # 近30天活跃天数
    stats7 = IntField(default=0)  # 近7天活跃天数
    stats = ListField(IntField())  # 近30天的活动数组
    status = StringField(choices=('ENABLED', 'DISABLED'), default='ENABLED')  # 账号状态, 0启用, 1禁用


class AccountInfo(Document):
    """
    账号信息表
    """

    owner = ReferenceField('Account')  # 所属账号
    nickname = StringField(max_length=64)  # 账号昵称
    brief = StringField(max_length=254)  # 账号简介
    region_id = IntField()  # 地区id
    region_name = StringField(max_length=64)  # 地区名称
    last_ip = StringField(max_length=16)  # 上次登录ip
    extra = DictField()  # 其他任何信息


class MinionsSet(BaseDocument):
    """
    账号集合表
    """

    duration = IntField()  # 持续时间
    curve = StringField(max_length=16)  # 时间函数类型
    count = IntField()  # 账号数量
    times = IntField()  # 全局可以被取次数
    start_time = DateTimeField()  # 第一个账号被取出的时间
    strategy = StringField(choices=('RANDOM', 'PRIORITY'))  # 提取账号的方式
    priority_by = StringField()  # 排序字段


class AccountCreateRequestLog(Document):
    """
    记录由web端传递过来的相关的数据
    """

    # platform = StringField(max_length=32)   # 平台的id
    account_source = LazyReferenceField('AccountSource')  # 所属平台
    number = IntField()  # 一次请求应创建指定个数的account
    status = StringField(choices=('new', 'doing', 'done', 'error'))  # 请求的状态
    date = FloatField()  # 创建请求的时间（时间戳）
    error_msg = StringField()  # 错误请求的详细信息


class AccountLog(BaseDocument):
    """
    记录由web端传递过来的相关的数据
    """

    account = ReferenceField('Account')  # 所属账号
    activity_id = ObjectIdField()  # 活动id
    activity = ReferenceField('Activity')  # 所属活动
    add_time = FloatField(default=time.time())  # 任务添加时间（时间戳）
    callback_time = FloatField()  # 任务回调时间（时间戳）
    status = IntField(choices=(0, 1, 2, 3), default=0)  # 任务完成状态
    crawler_id = StringField(max_length=256)  # 执行任务的crawler id
    actual_config = DictField(default={})


class Logs(BaseDocument):
    meta = {
        'indexes': [
            {'fields': ['-add_time']}
        ]
    }

    choices = ('DEBUG', 'INFO', 'WARNING', 'ERROR')
    message = StringField()
    level = StringField(choices=choices, required=True)  # 活动类型
    add_time = FloatField(default=time.time())
    crawler_id = StringField(max_length=256)  # 执行任务的crawler id


AccountInfo.register_delete_rule(Account, 'account_info', CASCADE)
AccountSource.register_delete_rule(Account, 'account_source', CASCADE)


class Role(db.Document, RoleMixin):
    name = db.StringField(max_length=80, unique=True)
    description = db.StringField(max_length=255)


class FinalUser(db.Document, UserMixin):
    date_created = db.FloatField(default=time.time())
    date_modified = db.DateTimeField()
    social_id = db.StringField(max_length=64, null=True, unique=True)
    email = db.StringField(max_length=64, unique=True)
    mobile = db.StringField(max_length=32, unique=True, null=True)
    password = db.StringField(c=255)
    last_login_at = db.DateTimeField()
    last_login_ip = db.StringField(max_length=45)
    login_count = db.IntField(default=0)
    active = db.BooleanField(default=True)
    balance = db.FloatField(default=0.0)
    roles = db.ReferenceField(Role, DBRef=True)


class RolesUsers(db.Document):
    final_user_id = db.ReferenceField(FinalUser, DBRef=True)
    role_id = db.ReferenceField(Role)


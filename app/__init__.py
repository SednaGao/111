import sys
import os
# correct sys.stdout
import codecs
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
from os import path
from werkzeug.datastructures import MultiDict

sys.path.append((path.dirname(path.dirname(path.abspath(__file__)))) + "/lib")
import sqlite3
import traceback
import time
import json
from functools import wraps

from flask import current_app
from jsonschema import validate as json_validate
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError
from mongoengine.errors import ValidationError as MongoEngineValidationError
from mongoengine import connect
from flask import Flask, render_template, current_app, request, jsonify
from flask_assets import Environment
from flask_wtf import CSRFProtect
from flask_cors import CORS
from flask_security import Security, SQLAlchemyUserDatastore, utils, MongoEngineUserDatastore
from lib.flask_via import Via
from wtforms.form import Form
from wtforms import ValidationError
from apscheduler.schedulers.background import BackgroundScheduler

from sqlalchemy_utils import database_exists, create_database
from sqlalchemy import create_engine
from .db import db
from .assets import create_assets

from .admin import create_security_admin

from config.config import app_config

import inspect
import re

from config.config import DevelopmentConfig
from app.db import EngineType

if DevelopmentConfig.DATABASE_TYPE == EngineType.SQLEngine:
    from .models import FinalUser, Role

    user_datastore = SQLAlchemyUserDatastore(db, FinalUser, Role)
else:
    from .models_mongo import FinalUser, Role
    user_datastore = MongoEngineUserDatastore(db, FinalUser, Role)


def create_app(config_name):
    global user_datastore, current_rest_api

    app = Flask(__name__)

    app.config.from_object(app_config[config_name])
    app.logger.setLevel(app.config['LOG_LEVEL'])

    csrf = CSRFProtect()
    csrf.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    assets = Environment(app)
    create_assets(assets)
    api_version = ""
    if 'API_VERSION' in app.config and app.config['API_VERSION'] and \
            not str(app.config['API_VERSION']).startswith('/'):
        api_version = "/" + str(app.config['API_VERSION'])

    via = Via()
    via.init_app(app, api_url_prefix='/api' + api_version)

    # Code for desmostration the flask upload in several models - - - -

    # from .restaurant import restaurant_photo
    # from .food import food_photo

    # configure_uploads(app, (restaurant_photo, food_photo, user_photo))

    # engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    # if not database_exists(engine.url):
    #     create_database(engine.url)
    from app.user.forms import SecurityRegisterForm
    security = Security(app, user_datastore, register_form=SecurityRegisterForm)
    create_security_admin(app=app, path=os.path.join(os.path.dirname(__file__)))
    with app.app_context():
        db.init_app(app)
        if DevelopmentConfig.DATABASE_TYPE == EngineType.SQLEngine:
            db.create_all()
        user_datastore.find_or_create_role(name='admin', description='Administrator')
        if DevelopmentConfig.DATABASE_TYPE == EngineType.SQLEngine:
            db.session.commit()
        user_datastore.find_or_create_role(name='end-user', description='End user')
        if DevelopmentConfig.DATABASE_TYPE == EngineType.SQLEngine:
            db.session.commit()
    # @app.route('/', methods=['GET'])
    # @app.route('/home', methods=['GET'])
    # def index():
    #     return render_template('index.html')
    #
    # @app.errorhandler(403)
    # def forbidden(error):
    #     return render_template('error/403.html', title='Forbidden'), 403
    #
    # @app.errorhandler(404)
    # def page_not_found(error):
    #     return render_template('error/404.html', title='Page Not Found'), 404
    #
    # @app.errorhandler(500)
    # def internal_server_error(error):
    #     db.session.rollback()
    #     return render_template('error/500.html', title='Server Error'), 500

    with app.app_context():
        if app.config['SCHEDULER_REDIS_HOST']:
            current_app.scheduler = BackgroundScheduler({
                'apscheduler.jobstores.default': {
                    'type': 'redis',
                    'db': 0,
                    'jobs_key': app.config['SCHEDULER_JOBS_KEY'],
                    'run_times_key': "{}-runtime".format(app.config['SCHEDULER_JOBS_KEY']),
                    'host': app.config['SCHEDULER_REDIS_HOST'],
                    'port': app.config['SCHEDULER_REDIS_PORT'],
                    'password': app.config['SCHEDULER_REDIS_PASSWD'],
                },
                'apscheduler.executors.default': {
                    'class': 'apscheduler.executors.pool:ThreadPoolExecutor',
                    'max_workers': '20'
                },
                'apscheduler.executors.processpool': {
                    'type': 'processpool',
                    'max_workers': '5'
                },
                'apscheduler.job_defaults.coalesce': 'true',
                'apscheduler.job_defaults.max_instances': '3',
                'apscheduler.timezone': 'Asia/Shanghai',
            })
            current_app.scheduler.start()

    return app




decorator_registry = {}


def __inspect_get_decorated_function_id(f):
    f_file = str(inspect.getmodule(f))
    f_lines = inspect.getsourcelines(f)
    f_line = f_lines[1]
    for idx, l in enumerate(f_lines[0]):
        if re.search('def\s+\w+\s?\(', l):
            f_line += idx
            break
    return f_file + str(f_line)


def api(f):
    global decorator_registry
    ds = []
    f_id = __inspect_get_decorated_function_id(f)
    if f_id in decorator_registry:
        ds = decorator_registry[f_id]
    ds.append('api')
    decorator_registry[f_id] = ds
    """Wrap the API return data format."""

    @wraps(f)
    def wrapper(*args, **kw):
        instance = args[0]
        if isinstance(instance, object) and \
                not instance.__class__.__name__.startswith("API"):
            current_app.logger.error('flaskmvc convention requires API class name starts with "API"')
            raise Exception('flaskmvc convention requires API class name starts with "API"')
        print('entering api call')
        ts = int(time.time())
        data = None
        code = 0
        error_message = ""
        instance.is_api = True

        if hasattr(instance, 'code') and instance.code:
            code = instance.code
            error_message = instance.error_message
        else:
            try:
                ret = f(*args, **kw)
            except MongoEngineValidationError as ex:
                return {
                    'data': None,
                    'code': -93,
                    'error_message': 'mongodb字段"%s"验证失败: %s' % (ex.field_name, str(ex)),
                    'timestamp': ts
                }
            except JsonSchemaValidationError as ex:
                message = "json schema校验错误："
                code = -97
                if ex.validator == 'required':
                    message += '以下字段不能为空: %s' % ex.validator_value
                    code = -96
                elif ex.validator == 'type':
                    message += '字段"%s"必须为%s类型' % (ex.path[0], ex.validator_value)
                    code = -95
                elif ex.validator == 'enum':
                    message += '字段"%s"必须为以下值: %s' % (ex.path[0], ex.validator_value)
                    code = -94
                return {
                    'data': None,
                    'code': code,
                    'error_message': message,
                    'timestamp': ts
                }
            except FMVCUserError as ex:
                traceback.print_exc()
                return {
                    'data': None,
                    'code': ex.code,
                    'error_message': str(ex),
                    'timestamp': ts
                }
            except Exception as e:
                traceback.print_exc()
                return {
                    'data': None,
                    'code': -92,
                    'error_message': "服务内部错误：{}".format(e),
                    'timestamp': ts
                }
            if isinstance(ret, tuple):
                if len(ret):
                    data = ret[0]
                if len(ret) > 1:
                    code = ret[1]
                if len(ret) > 2:
                    error_message = ret[2]
            else:
                data = ret
        res_data = {
            'data': data,
            'code': code,
            'error_message': error_message,
            'timestamp': ts
        }
        print('data returned')
        return jsonify(res_data)

    return wrapper


def params(fields, strict=True):
    """validate query parameters."""
    if not fields:
        raise Exception('params decorator requires a dict argument with wtforms validation fields')

    def decorator(f):

        global decorator_registry
        f_id = __inspect_get_decorated_function_id(f)
        is_api = False
        if f_id in decorator_registry and 'api' in decorator_registry[f_id]:
            is_api = True
        field_count = 0
        for k, v in fields.items():
            description = v.__dict__.get('kwargs').get('description', "")
            field_type = v.field_class.__name__
            vs = v.__dict__.get('kwargs').get('validators')
            if vs:
                for validator in vs:
                    # todo: get validator info here
                    pass
            # 在 object.__dict__ 的return前加field信息
            func_source_doc_lis = f.__doc__.split("\n")
            for index, line in enumerate(func_source_doc_lis):
                if ":return:" in line:
                    func_source_doc_lis.insert(index, "\n:type {}:{}".format(k, str(field_type)))
                    func_source_doc_lis.insert(index, "\n:param {}:{}".format(k, str(description)))
                    field_count += 1
                    break
            else:
                func_source_doc_lis.append("\n:param {}:{}".format(k, str(description)))
                func_source_doc_lis.append("\n:type {}:{}".format(k, str(field_type)))
            f.__doc__ = '\n'.join(func_source_doc_lis)

        @wraps(f)
        def wrapper(*args, **kwargs):
            print('entering validation')
            _unbound_fields = getattr(Form(), '_unbound_fields')
            if _unbound_fields:
                _unbound_fields.clear()
            for t in fields.items():
                _unbound_fields.append(t)
            setattr(Form(), '_unbound_fields', _unbound_fields)
            args_data = request.args if request.args else {}
            # json_data = request.json if request.json else {}
            post_data = request.form if request.form else {}
            # request_data = dict(args_data, **json_data, **post_data)

            validate_data = MultiDict()
            validate_data.update(args_data)
            validate_data.update(post_data)
            print(validate_data)
            form = Form(formdata=validate_data, meta={'locales': app_config['development'].FORM_META_LOCALES})
            ts = int(time.time())
            flag = form.validate()
            if not flag:
                if is_api:
                    ret_data = {
                        'data': None,
                        'code': -99,
                        'error_message': "API参数验证失败：{}".format(form.errors),
                        'timestamp': ts
                    }
                    return jsonify(ret_data)
                else:
                    return form.errors
            print(form.data)
            if strict:
                request.args = form.data
            else:
                original_args = dict(request.args)
                original_args.update(form.data)
                request.args = original_args
            try:
                return f(*args, **kwargs)
            except Exception as e:
                traceback.print_exc()
                return str(e)

        return wrapper

    return decorator


def json_validator(f):
    """
    validate the json data
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            method = f.__name__
            json_data = request.json or {}
            self = args[0]
            filepath = path.dirname(self.__module__.replace('.', '/'))

            filename = path.join(path.join(filepath, 'schemas'), '{}.{}.json'.format(
                self.__class__.__name__, method))
            if path.isfile(filename):
                with open(filename, 'r') as file:
                    schema = json.load(file)
                json_validate(json_data, schema)
                return f(*args, **kwargs)
            else:
                pass
            raise FileNotFoundError('The "{}" not found'.format(filename))
        except FileNotFoundError as ex:
            return {
                'data': None,
                'code': -98,
                'error_message': str(ex),
                'timestamp': time.time()
            }
        except Exception as ex:
            return {
                'data': None,
                'code': -99,
                'error_message': str(ex),
                'timestamp': time.time()
            }
    return wrapper


# json field validator
class JsonStringValidator(object):
    def __init__(self, message=None):
        if not message:
            message = u'Field must be valid json string.'
        self.message = message

    def __call__(self, form, field):
        if not field.data:
            return
        try:
            json.loads(field.data)
        except:
            raise ValidationError(self.message)


json_field_validator = JsonStringValidator


# customized exception for fmvc
class FMVCUserError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'程序内层错误: {self.message}'

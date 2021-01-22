# coding=utf8
import json
from operator import itemgetter
import traceback
import sys
from flask import Blueprint, Response, Markup
import os
import re
from jinja2 import Environment, FileSystemLoader
from .utils import func_sign, js_string_to_html
import markdown
from . import describer

apidoc_bp = Blueprint('api-doc', __name__, template_folder='', url_prefix='/api-doc')

INSTANCE = None


@apidoc_bp.route('')
def response_index():
    """
    输出html
    :return:
    :rtype:
    """
    if not INSTANCE:
        return "Not initialized properly"
    return INSTANCE.generate_html()


@apidoc_bp.route('/html')
def response_html():
    """
    输出html
    :return:
    :rtype:
    """
    if not INSTANCE:
        return "Not initialized properly"
    return INSTANCE.generate_html()


@apidoc_bp.route('/md')
def response_markdown():
    """
    输出html
    :return:
    :rtype:
    """
    if not INSTANCE:
        return "Not initialized properly"
    return INSTANCE.generate_markdown()


@apidoc_bp.route('/loading.gif')
def loading_gif():
    """
    返回loading.gif
    :return:
    :rtype:
    """
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'loading.gif')
    with open(path, 'rb') as f:
        gif = f.read()
    response = Response(gif, mimetype="image/jpeg")
    return response


class FunctionDocument(object):
    """
    接口类的文档对象
    """

    def __init__(self, doc_string, url, method, endpoint, prefix, forms, args, json_body, schema_filepath):
        self.prefix = prefix
        self.endpoint = endpoint
        self.doc_string = doc_string
        self.url = url
        self.method = method
        self.show_idx = 0
        self.name = ""
        self.description = None
        self.content = ""
        self.form_params = forms
        self.query_params = args
        if json_body:
            self.json_body = json.dumps(json_body().gen_doc(), indent=4, ensure_ascii=False)
        else:
            self.json_body = None
        self.url_params = {}
        self.normal_lines = []
        self.return_lines = []
        self.has_content = False
        self.document_format(doc_string)
        self.uid = ""
        self.json_example = self.get_json_example()
        if os.path.isfile(schema_filepath):
            with open(schema_filepath, 'r') as f:
                self.schema = f.read()
        else:
            self.schema = None

    def __getitem__(self, item):
        return getattr(self, item)

    def anchor(self):
        """
        返回锚点
        :return:
        :rtype:
        """
        return u"<a name=\"api-%s\"></a>" % self.uid

    def link(self):
        return u"<a href=\"#api-%s\">%s</a>" % (self.uid, self.name)

    def document_format(self, doc_str):
        """
        格式化API的doc_string到markdown格式
        :param doc_str:
        :type doc_str:
        :return:
        :rtype:
        """
        command_flag = "#idx:"
        url_param_flag = ":param"
        url_param_type_flag = ":type"
        lines = doc_str.split('\n')
        rt_mode = False
        for line in lines:
            s = line.strip()
            if rt_mode:
                if s.startswith(':rtype'):
                    rt_mode = False
                    continue
                if not s:
                    break
                self.return_lines.append(line)
                continue
            if s.startswith(command_flag):
                # 获取排序索引
                self.show_idx = int(s[5:])
                continue
            if s.startswith(url_param_flag):
                name, value = s[6:].split(':')
                self.url_params[name.strip()] = [name.strip(), None, value.strip()]
                continue
            if s.startswith(url_param_type_flag):
                name, value = s[6:].split(':')
                if name in self.url_params:
                    arr = self.url_params[name.strip()]
                    arr[1] = value.strip()
                    self.url_params[name.strip()] = arr
                continue
            if s.startswith(":return:"):
                # import re
                # re.compile(':return:.*?\n')
                # self.return_lines = re.
                rt_mode = True
                continue
            self.normal_lines.append(s)
        for line in self.normal_lines:
            if line.strip():
                line = line.strip()
                name_and_description = line.split(':', 1)
                self.name = name_and_description[0]
                if len(name_and_description) == 2:
                    self.description = name_and_description[1]
                else:
                    self.description = self.name
                break
        content = "\n".join(self.normal_lines[2:]) if len(self.normal_lines[2:]) else ""
        self.has_content = True if content else False
        self.content = Markup(markdown.markdown(content))

    def return_value(self):
        """
        解析返回值信息
        :return:
        :rtype:
        """
        success_string = re.search(r':success:\n(\s*.*?)\n\s*(:failure:|\n|$)', self.doc_string, re.S)
        if success_string:
            success_string = success_string.group(1)
            n_backspace = re.search(r'(\s+)', success_string)
            if n_backspace:
                n_backspace = n_backspace.group(1)
                success_string = '\n'.join(line.replace(n_backspace, '', 1) for line in success_string.split('\n'))
        filure_dic = {}
        flag_failure = False
        for rt_line in self.return_lines:
            rt_line = rt_line.strip()
            if rt_line == ":failure:":
                flag_failure = True
                continue
            if flag_failure:
                if ',' in rt_line:
                    k, v = rt_line.split(',')
                    filure_dic[k] = v
        filure_dic['-99'] = "validator errors"
        return {
            'success_string': success_string,
            'filure_dic': filure_dic
        }

    def get_json_example(self):
        """
        获取注释中json格式的例子, 如
        :json:
            {
                'a': 'b'
            }

        """
        json_example = re.search(r':json:\n(\s*.*?)(\n\s*\n|\n\s*$)', self.doc_string, re.S)
        if json_example:
            json_example = json_example.group(1)
            n_backspace = re.search(r'(\s+)', json_example)
            if n_backspace:
                n_backspace = n_backspace.group(1)
                json_example = '\n'.join(line.replace(n_backspace, '', 1) for line in json_example.split('\n'))
            return json_example

    def gen_markdown(self):
        """
        生成markdown文件
        :return:
        :rtype:
        """
        lines = [u"### %s" % self.description, u" ", u"#### Overview"]
        for normal_line in self.normal_lines[1:]:
            lines.append(u"> %s" % normal_line)
        lines.append(u"")
        lines.append(u"#### URL")
        lines.append(u"> %s" % self.url)
        lines.append(u"")
        lines.append(u"#### HTTP Method")
        lines.append(u"> %s" % self.method)
        if self.url_params:
            lines.append(u" ")
            lines.append(u"#### URL Parameter")
            lines.append(u" ")
            lines.append(u"| Name | Type | Description |")
            lines.append(u"|:----- |:----| --------- |")
            for k, param in self.url_params.items():
                lines.append(u"|%s|" % u"|".join([p if p else u' ' for p in param]))
        lines.append(u" ")
        if self.query_params:
            lines.append(u" ")
            lines.append(u"#### QueryString Parameter")
            lines.append(u" ")
            lines.append(u"| Name | Require | Type | Description |")
            lines.append(u"|:----- |:---- |:----| --------- |")
            for param in self.query_params:
                lines.append(u"|%s|" % u"|".join(param.get_arr() if param else []))
        if self.form_params:
            lines.append(u" ")
            lines.append(u"#### Form Parameter")
            lines.append(u" ")
            lines.append(u"| Name | Require | Type | Description |")
            lines.append(u"|:----- |:---- |:----| --------- |")
            for param in self.form_params:
                lines.append(u"|%s|" % u"|".join(param.get_arr() if param else []))
        lines.append(u" ")
        lines.append(u"#### Return Value")
        lines.append(u" ")
        for rt_line in self.return_lines:
            lines.append(u"%s" % rt_line)
        lines.append(u" ")
        mark_down = u"\n".join(lines)
        return mark_down


class Bp(object):
    name = ""
    key = ''
    funcs = []

    def sort(self):
        for s_idx, fc in enumerate(self.funcs):
            if fc.show_idx < 1:
                fc.show_idx = s_idx

        self.funcs = sorted(self.funcs, key=itemgetter('prefix', 'show_idx'))

        for idx, f in enumerate(self.funcs):
            f.uid = "%s-%s" % (self.key, idx)


class Generator(object):
    """
    生成器
    """

    def __init__(self, flask_app, filters=None):
        """
        初始化对象, 注入flask的App
        :param flask_app: flask的app对象
        :type flask_app: App
        :param filters: 过滤列表, 只显示部分选定blueprints的文档
        :type filters: [str...]
        """
        self.app = flask_app
        self.filters = filters
        self.functions = []
        self.blueprints = {}
        self.blueprint_ins = []
        self.global_auth = ""
        global INSTANCE
        INSTANCE = self

    def prepare(self):
        """
        生成文档数据
        :return:
        :rtype:
        """
        ft_dict = self.filters if self.filters else []
        apps = ['static']

        for k, v in self.app.view_functions.items():

            app_doc_name = k.split('.')[0] if '.' in k else k

            if app_doc_name in ft_dict:
                apps.append(k)
        api_items = [(k, v) for k, v in self.app.view_functions.items() if k in apps]
        rules_arr1 = [rule for rule in self.app.url_map.iter_rules()]
        rules_arr = [(rule.endpoint, rule) for rule in self.app.url_map.iter_rules()]
        rules = dict(rules_arr)
        for api_name, api_func in api_items:

            if api_name == 'static':
                continue
            if api_name == 'index':
                continue
            prefix, _ = api_name.split('.')

            if self.filters and prefix not in ft_dict:
                continue  # 如果没有加进来就跳过不care

            rule = rules.get(api_name)
            url = rule.rule
            method = [m for m in list(rule.methods) if m != 'OPTIONS' and m != 'HEAD']
            for method1 in method:
                method1 = method1.lower()
                class_dic = api_func.__dict__
                view_class = api_func.__dict__.get('view_class')
                func_ = view_class.__dict__.get(method1)
                doc = func_.__doc__

                if not doc:
                    continue
                f_name = func_sign(func_)
                forms = describer.api_forms[f_name] if f_name in describer.api_forms else []
                args = describer.api_args[f_name] if f_name in describer.api_args else []
                json_body = describer.api_json[f_name] if f_name in describer.api_json else None
                if json_body:
                    assert forms == [], u"如果定义了json_form就能定义forms了"

                if prefix in self.blueprints:
                    bp = self.blueprints[prefix]
                else:
                    bp = Bp()
                    # bp.name = ft_dict[prefix] if self.filters else prefix
                    bp.name = prefix
                    bp.key = prefix
                    bp.funcs = []
                    self.blueprints[prefix] = bp
                schema_filepath = self._get_schema_filepath(func_)
                bp.funcs.append(FunctionDocument(doc, url, method1, rule.endpoint, prefix, forms, args, json_body, schema_filepath))
                bp.sort()
            self.blueprint_ins = [bp for k, bp in self.blueprints.items()]
        self.app.register_blueprint(apidoc_bp)

    def generate_markdown(self):
        """
        生成markdown
        :return:
        :rtype:
        """
        doc_lines = [u"API Document", u"----------------", u" "]
        doc_lines.append(u"<center>")
        doc_lines.append(u"### TOC Index")
        doc_lines.append(u"</center>")
        doc_lines.append(u" ")
        doc_lines.append(u"| id | title |")
        doc_lines.append(u"|:----- |:--------- |")
        for doc_idx, doc in enumerate(self.functions):
            doc_lines.append(u"|%s|" % u"|".join([str(doc_idx), doc.link()]))
        doc_lines.append(u" ")
        doc_lines.append(u"---")
        doc_lines.append(u"  ")
        doc_lines.append(u"  ")
        for bp in self.blueprint_ins:
            doc_lines.append(u"#### %s" % bp.name)
            for doc_idx, doc in enumerate(bp.funcs):
                doc_lines.append(doc.anchor())
                doc_lines.append(doc.gen_markdown())
                doc_lines.append(u" ")
                doc_lines.append(u"---")

        markdown = "\n".join([line for line in doc_lines])
        return markdown

    def generate_html(self):
        """
        生成html
        :return:
        :rtype:
        """
        from flask import request
        self.global_auth = request.args.get('auth', "")
        path = os.path.dirname(os.path.abspath(__file__))
        template_env = Environment(
            autoescape=False,
            loader=FileSystemLoader(path),
            trim_blocks=False)
        return template_env.get_template('gen_template.html').render(gen=self)

    def _get_schema_filepath(self, func):
        """
        根据func获取schema的文件路径
        :param func:
        :return:
        """

        filepath = '/'.join(func.__module__.split('.')[1:-1])
        filepath = os.path.join(os.path.join(self.app.root_path, filepath), 'schemas')
        result = re.search(r'\<function (\w+)\.(\w+)', str(func))
        if result:
            classname = result.group(1)
            method = result.group(2)
            schema_filepath = os.path.join(filepath, '%s.%s.json' % (classname, method))
            return schema_filepath


def main():
    sys.path.append(os.getcwd())
    if len(sys.argv) < 2:
        print("Missing argument: mod_name:<Flask App> for Example manager:app")
        sys.exit(1)
    if len(sys.argv) > 2:
        filter_arr = sys.argv[2].split(',')
    else:
        filter_arr = None
    import_str = sys.argv[1]

    try:
        mod_name, var_name = import_str.split(":")
        mod = __import__(mod_name, globals(), locals(), fromlist=[var_name, ])
        app = getattr(mod, var_name)
        g = Generator(app, filters=filter_arr)
        g.prepare()
        print(g.generate_markdown())
        sys.exit(0)
    except Exception as e:
        traceback.print_exc()
        print("Can not import Flask app from argument", import_str)
        sys.exit(1)

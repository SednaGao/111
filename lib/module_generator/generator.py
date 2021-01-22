import os
import shutil
from string import Template


class MVCTemplate(Template):
    """重载标识符"""
    delimiter = '@$'


class MVCGenerator(object):
    """Generate the mvc modules, based on the given template"""

    def __init__(self, name, folder=None, template_folder=None, is_sql=True):
        self._name = name
        self._c_name = self._get_capitalize(self._name)
        self._folder = folder or os.path.join(os.getcwd(), name)
        if not os.path.exists(self._folder):
            os.makedirs(self._folder)
        self._templates_folder = template_folder or os.path.join(os.path.dirname(__file__), 'module_templates')
        self.is_sql = is_sql

    def generate_mvc(self):
        self.gen_template(
            template='forms',
            classname='%sForm' % self._c_name
        )
        self.gen_template(
            template='views',
            classname='View%s' % self._c_name,
            form_classname='%sForm' % self._c_name
        )
        self.gen_template(
            template='routes',
            view=self._name,
            api='api_%s' % self._name,
            view_classname='View%s' % self._c_name,
            api_classname='API%s' % self._c_name
        )
        self.gen_template(
            template='apis',
            classname='API%s' % self._c_name,
            model_import='from ..models import *' if self.is_sql else 'from .. import models_mongo'
        )
        self.gen_template(
            template='utils'
        )
        self.gen_template(
            template='__init__'
        )

        example_folder = os.path.join(self._folder, 'templates')
        self.gen_template(
            template='example',
            folder=example_folder,
            file_type='html',
            blueprint_name=self._name,
            view_classname='View%s' % self._c_name
        )

        schema_folder = os.path.join(self._folder, 'schemas')
        self.gen_template(
            template='schema',
            folder=schema_folder,
            target_name='API%s' % self._c_name,
            file_type='json',
            api_classname='API%s' % self._c_name
        )

    def gen_template(self, template, folder=None, target_name=None, file_type='py', **substitute_options):
        target_name = target_name or template
        folder = folder or self._folder
        if not os.path.exists(folder):
            os.makedirs(folder)

        template_file = self._find_template(template)
        target_file = os.path.join(folder, '%s.%s' % (target_name, file_type))
        shutil.copyfile(template_file, target_file)
        self._render_template_file(target_file, **substitute_options)
        print("Created module %s using template %s " % (target_file, template_file))

    @staticmethod
    def _render_template_file(path, **kwargs):
        with open(path, 'rb') as fp:
            raw = fp.read().decode('utf8')

        content = MVCTemplate(raw).substitute(**kwargs)

        render_path = path[:-len('.tmpl')] if path.endswith('.tmpl') else path
        with open(render_path, 'wb') as fp:
            fp.write(content.encode('utf8'))

    def _find_template(self, template):
        template_file = os.path.join(self._templates_folder, '%s.tmpl' % template)
        if os.path.exists(template_file):
            return template_file
        print("Unable to find template: %s\n" % template_file)

    @staticmethod
    def _get_lower_case_name(string):
        """
        ClassA => class_a
        """
        lst = []
        for i, char in enumerate(string):
            if char.isupper() and i != 0:
                lst.append('_')
            lst.append(char)

        return ''.join(lst).lower()

    @staticmethod
    def _get_capitalize(string):
        """
        class_a => ClassA
        """
        return ''.join(s.capitalize() for s in string.split('_'))

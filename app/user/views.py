from flask import jsonify, request, url_for, redirect, current_app, render_template, flash, make_response
from flask.views import MethodView
from .forms import *


class ViewExampleHelloWorld(MethodView):
    """
       #idx:3
       an example api view function
       :param resource_id: resource_id
       :type resource_id:int
       :return:
       if success {rs=true}
       if faild   {rs=false, error=错误原因}
       :rtype:
       """

    def get(self):

        who = ""
        if 'who' in request.args:
            who = request.args['who']
        form = ExampleFormSayHi()
        return render_template('example.html', str='hello world', who=who, form=form)


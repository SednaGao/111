from flask import jsonify, request, url_for, redirect, current_app, render_template, flash, make_response
from flask.views import MethodView
from .forms import *


class ViewService(MethodView):

    def get(self):
        who = ""
        if 'who' in request.args:
            who = request.args['who']
        form = ServiceForm()
        return render_template('example.html', str='hello world', who=who, form=form)

from flask import request, url_for, redirect, render_template, current_app as app
from flask_restful import Resource as RestfulResource
# from ..models import *
from ..models_mongo import *
from flask_security import current_user
from .. import api, params
from wtforms import *
import json


class APISign(RestfulResource):
    def post(self):
        pass

from lib.flask_via.routers.default import Pluggable
from lib.flask_via.routers.restful import Resource
from .views import *
from .apis import *


routes = [
    Resource('/create', APICreate, 'APICreate'),
    Resource('/list', APIList, 'APIList'),
    Resource('/operate', APIOperate),
    Resource('/stop', APIStop),
    Resource('/if-idle', APIIdle),
]

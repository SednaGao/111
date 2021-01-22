from lib.flask_via.routers.default import Pluggable
from lib.flask_via.routers.restful import Resource
from .views import *
from .apis import *


routes = [
    Resource('/list', APIList, 'APIList'),
    Resource('/create', APICreate, 'APICreate'),
    Resource('/update', APIUpdate),
    Resource('/get', APIGet),
    Resource('/enable', APIEnable),
    Resource('/run', APIRun),
]

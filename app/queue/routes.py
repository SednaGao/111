from lib.flask_via.routers.default import Pluggable
from lib.flask_via.routers.restful import Resource
from .views import *
from .apis import *


routes = [
    Pluggable('/queue', ViewQueue, 'ViewQueue'),
    Resource('/list', APIList, 'APIList'),
    Resource('/delete', APIDelete, 'APIDelete'),
]

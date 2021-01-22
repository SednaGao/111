from lib.flask_via.routers.default import Pluggable
from lib.flask_via.routers.restful import Resource
from .views import *
from .apis import *


routes = [
    Resource('/list', APIList),
    Resource('/resume', APIResume),
    Resource('/pause', APIPause),
    Resource('/stop', APIStop),
    Resource('/start', APIStart),
    Resource('/cancel', APICancel),
]

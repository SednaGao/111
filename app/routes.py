from lib.flask_via.routers.default import Blueprint

routes = [
    Blueprint('user', 'app.user', template_folder='templates', url_prefix='/user'),
    Blueprint('job', 'app.job', template_folder='templates', url_prefix='/job'),
    Blueprint('service', 'app.service', template_folder='templates', url_prefix='/service'),
    Blueprint('executor', 'app.executor', template_folder='templates', url_prefix='/executor'),
    Blueprint('log', 'app.log', template_folder='templates', url_prefix='/log'),
    Blueprint('spider', 'app.spider', template_folder='templates', url_prefix='/spider'),
    Blueprint('dupdb', 'app.dupdb', template_folder='templates', url_prefix='/dupdb'),
    Blueprint('queue', 'app.queue', template_folder='templates', url_prefix='/queue'),
    Blueprint('run_log', 'app.run_log', template_folder='templates', url_prefix='/run_log'),
]

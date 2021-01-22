from app import create_app
from lib.flask_doc import Generator
from utils.app_methods import get_module_list
import logging


def load_app():
    app = create_app('testing')
    if app.config['LOG_LEVEL'] == logging.DEBUG:
        generator = Generator(app, get_module_list())
        generator.prepare()
    return app


uwsgi_app = load_app()

if __name__ == '__main__':
    app = create_app('testing')
    if app.config['LOG_LEVEL'] == logging.DEBUG:
        generator = Generator(app, get_module_list())
        generator.prepare()
    app.run(host='127.0.0.1', port=5000, debug=True, threaded=True)

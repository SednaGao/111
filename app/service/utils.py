# coding: utf8

from flask import g, current_app as app
import re
from flask.json import loads, dumps


class SpiderService:

    def __init__(self, service, params):
        self.service = service
        self.params = params

    def get_spec(self):
        spec_template = dumps(self.service.spec)
        spec_str = re.sub(r"$(.*?)$", lambda x: self.params.get(x.group(1), ''), spec_template)
        return loads(spec_str)

    def schedule(self, right_now=True):
        spec_json = self.get_spec()
        from ..run_log.utils import scheduler_send_request
        scheduler_send_request(service_id=self.service.id, spec=spec_json)

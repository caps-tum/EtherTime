import json
from datetime import timedelta, datetime


class ModelJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, timedelta) or isinstance(obj, datetime):
            return str(obj)
        return super().default(obj)

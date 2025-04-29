from bson.objectid import ObjectId
from datetime import datetime
from flask.json.provider import JSONProvider
import json

class CustomJSONEncoder(JSONProvider):
    def dumps(self, obj, **kwargs):
        return json.dumps(obj, default=self._default, **kwargs)
    
    def loads(self, s, **kwargs):
        return json.loads(s, **kwargs)
    
    def _default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable") 
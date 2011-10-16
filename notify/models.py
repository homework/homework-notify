## Copyright (C) 2011 Richard Mortier <mort@cantab.net>
##
## This program is free software: you can redistribute it and/or
## modify it under the terms of the GNU Affero General Public License
## as published by the Free Software Foundation, either version 3 of
## the License, or (at your option) any later version.
##
## This program is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## Affero General Public License for more details.
##
## You should have received a copy of the GNU Affero General Public
## License along with this program.  If not, see
## <http://www.gnu.org/licenses/>.

import sys, logging, datetime, time
log = logging.info
err = logging.exception

import secrets

from django.utils import simplejson as json
from google.appengine.ext import db
from google.appengine.ext.db import polymodel

def datetime_as_float(dt):
    '''Convert a datetime.datetime into a microsecond-precision float.'''
    return time.mktime(dt.timetuple())+(dt.microsecond/1e6)

DEFAULT_ROUTER_ID = "0"*40
DEFAULT_SERVICEUSE_ID = "1"*40

class Router(db.Model):
    routerid  = db.StringProperty(required=True)
    name = db.StringProperty(required=False)

    def todict(self):
        return { 'routerid': self.routerid,
                 'name': self.name,
                 }
    
    def put(self):
        n = db.GqlQuery(
            "SELECT * FROM Router WHERE routerid=:r", r=self.routerid).count()
        if n > 0: raise ValueError("collision", self.routerid, n)
        
        super(Router, self).put()        

    @staticmethod
    def ins_default():
        try: Router(routerid=DEFAULT_ROUTER_ID, name="empty-default-router").put()
        except ValueError, ve:
            if (ve[0] == "collision" and ve[1] == DEFAULT_ROUTER_ID): pass
            else: raise

class Service(db.Model):
    endpoint = db.StringProperty(required=True)

    def todict(self):
        return { 'service': self.key().name(),
                 'endpoint': self.endpoint,
                 }
    
    @staticmethod
    def ins_default():
        Service.get_or_insert("twitter", endpoint=secrets.TWITTER_ENDPOINT)
        Service.get_or_insert("email", endpoint=secrets.EMAIL_ENDPOINT)
        Service.get_or_insert("facebook", endpoint=secrets.FACEBOOK_ENDPOINT)
        Service.get_or_insert("phone", endpoint=secrets.PHONE_ENDPOINT)
        Service.get_or_insert("push", endpoint=secrets.PUSH_ENDPOINT)
        Service.get_or_insert("growl", endpoint=secrets.GROWL_ENDPOINT)

class ServiceUse(db.Model):
    suid = db.StringProperty(required=True)
    service = db.ReferenceProperty(Service, collection_name="uses", required=True)
    router = db.ReferenceProperty(Router, collection_name="services", required=True)
    endpoint = db.StringProperty(required=True)

    def todict(self):
        return { 'suid': self.suid,
                 'service': self.service.todict(),
                 'router': self.router.todict(),
                 'endpoint': self.endpoint,
                 }

    def put(self):
        n = db.GqlQuery(
            "SELECT * FROM ServiceUse WHERE suid=:suid", suid=self.suid).count()
        if n > 0: raise ValueError("collision", self.suid, n)
        
        super(ServiceUse, self).put()        

    @staticmethod
    def ins_default():
        try:
            router = Router.all().filter("routerid =", DEFAULT_ROUTER_ID).get()
            service = Service.get_by_key_name("email")
            ServiceUse(
                suid=DEFAULT_SERVICEUSE_ID, endpoint="empty-default-serviceuse",
                service=service, router=router
                ).put()
        except ValueError, ve:
            if (ve[0] == "collision" and ve[1] == DEFAULT_SERVICEUSE_ID): pass
            else: raise
                   
class Log(db.Model):
    svcu = db.ReferenceProperty(ServiceUse, collection_name="log_entries")
    ts   = db.DateTimeProperty(auto_now_add=True)
    msg  = db.TextProperty(required=True)

    def todict(self):
        ts = datetime_as_float(self.ts) if self.ts else None
        return { 'uid': self.svcu.router.routerid,
                 'msg': self.msg,
                 'service': self.svcu.service.key().name(),
                 'ts': ts,
                 }
class NotifyResult(db.Model):
    statusCode = db.IntegerProperty(required=True)
    statusMessage = db.TextProperty(required=True)
    notification = db.StringProperty(required=True)
    router = db.ReferenceProperty(Router, collection_name="statuses", required=True)
    
    def todict(self):
        return {
            'code' : self.statusCode,
            'message' : self.statusMessage,
            }
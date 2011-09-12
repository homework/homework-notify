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

import logging, urllib, datetime, hashlib
log = logging.info

from google.appengine.api import urlfetch
from google.appengine.ext import webapp
from google.appengine.api.labs import taskqueue
from google.appengine.api import users
from django.utils import simplejson as json
from google.appengine.api import mail

import notify.models as models
import secrets
import oauth
                      
class Root(webapp.RequestHandler):
    def get(self):
        routerid = models.DEFAULT_ROUTER_ID
        while routerid == models.DEFAULT_ROUTER_ID:
            n = models.Router.all().count()
            d = datetime.datetime.now().isoformat()
            routerid = hashlib.sha1("%s:%s" % (n, d)).hexdigest()
        self.response.out.write(routerid)

class Log(webapp.RequestHandler):
    def get(self, routerid, pageno=None):
        u = models.Router.all().filter("routerid =", routerid).get()
        if not u:
            self.response.out.write("")
            return            

        les = sorted([ le.todict() for s in u.services for le in s.log_entries ],
                     key=lambda le: le.ts)
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps(les, indent=2))

def json_services_used(r, s):
    s = models.Service.get_by_key_name(s)
    r = models.Router.all().filter("routerid =", r).get()
    if not r: return ""

    return json.dumps(
        [ su.todict() for su in r.services.filter("service =", s) ],
        indent=2)

class Email(webapp.RequestHandler):
    def post(self, routerid):
        if routerid == models.DEFAULT_ROUTER_ID: return
        r = models.Router.all().filter("routerid =", routerid).get()
        if not r: BARF

        s = models.Service.get_by_key_name("email")
        sus = r.services.filter("service =", s).fetch(100)
        if not sus: BARF

        body = self.request.get("body")
        if not body: BARF

        to = self.request.get("to")
        registered_emails = [ su.endpoint for su in sus ]
        if (not to or to not in registered_emails): BARF
                
        log("EMAIL: user:%s to:%s body:\n%s\n--\n" % (
            r.name, to, body))

        message = mail.EmailMessage(sender=s.endpoint,
                                    subject="Homework Router Notification!")
        message.to = to
        message.body = body
        message.send()

    def get(self, routerid):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json_services_used(routerid, "email"))
        
class Facebook(webapp.RequestHandler):
    def post(self, routerid):
        if routerid == models.DEFAULT_ROUTER_ID: return
        r = models.Router.all().filter("routerid =", routerid).get()
        if not r: BARF
        
    def get(self, routerid):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json_services_used(routerid, "facebook"))

class Twitter(webapp.RequestHandler):
    def post(self, routerid):
        if routerid == models.DEFAULT_ROUTER_ID: return
        r = models.Router.all().filter("routerid =", routerid).get()
        if not r: BARF
        
        s = models.Service.get_by_key_name("twitter")
        sus = r.services.filter("service =", s).fetch(100)
        if not sus: BARF

        body = self.request.get("body")
        if not body: BARF

        to = self.request.get("to")
        registered_eps = [ su.endpoint for su in sus ]
        if (not to or to not in registered_eps): BARF

        log("TWITTER: user:%s to:%s body:\n%s\n--\n" % (
            r.name, to, body))

        client = oauth.TwitterClient(
            secrets.TWITTER_CONSUMER_KEY,
            secrets.TWITTER_CONSUMER_SECRET,
            None
            )
        
        resp = client.make_request(
            "http://api.twitter.com/1/direct_messages/new.json",
            token=secrets.TWITTER_ACCESS_TOKEN,
            secret=secrets.TWITTER_ACCESS_TOKEN_SECRET,
            additional_params={ 'text': body, 'screen_name': to,},
            method=urlfetch.POST,
            )

        log("result: %s -- %s -- %s -- %s" % (
            resp, resp.status_code, resp.headers, resp.content))
        
    def get(self, routerid):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json_services_used(routerid, "twitter"))

class Sms(webapp.RequestHandler):
    def post(self, routerid):
        if routerid == models.DEFAULT_ROUTER_ID: return
        r = models.Router.all().filter("routerid =", routerid).get()
        if not r: BARF
        
    def get(self, routerid):
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json_services_used(routerid, "sms"))


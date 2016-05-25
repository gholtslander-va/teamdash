#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os

import webapp2
from github import Github
from google.appengine.ext import ndb
from google.appengine.ext.webapp import template
from google.appengine.api import users

TOKEN = ""
ORG = "vendasta"
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')


class BaseHandler(webapp2.RequestHandler):

    user = None
    logout_url = ""

    def dispatch(self):
        user = users.get_current_user()
        if user:
            user_domain = user.email().split('@')[1]
            self.logout_url = users.create_logout_url('/')
            if user.email().split('@')[1] == 'vendasta.com':
                if self.request.path == '/token':
                    super(BaseHandler, self).dispatch()
                else:
                    self.check_user(user)
            else:
                self.response.write('Must be logged in with a vendasta.com account.  <a href="%s">Sign Out</a>' % self.logout_url)
        else:
            login_url = users.create_login_url(self.request.url)
            self.redirect(login_url)

    def check_user(self, user):
        db_user = self.get_current_user_from_database()
        if db_user:
            print 'user exists'
            print self.request.relative_url('/')
            if db_user.github_token:
                global TOKEN
                TOKEN = db_user.github_token
                super(BaseHandler, self).dispatch()
            else:
                self.redirect('/token')
        else:
            print 'user does not exist in the database'
            db_user = User(user_id=user.user_id())
            db_user.key = ndb.Key('User', user.user_id())
            db_user.put()
            self.redirect('/token')

    @classmethod
    def get_current_user_from_database(cls):
        user = users.get_current_user()
        return User.get_by_id(user.user_id())


class HomeHandler(BaseHandler):
    def get(self):
        g = Github(login_or_token=TOKEN)
        o = g.get_organization(ORG)
        teams = sorted([team.name for team in o.get_teams()])
        template_values = {
            'team_name': 'Home',
            'logout_url': self.logout_url,
            'teams': teams,
        }
        self.response.out.write(template.render(os.path.join(TEMPLATE_DIR, 'home.html'), template_values))

    def post(self):
        team = self.request.get('teamSelect')
        self.redirect('/%s' % team)


class TokenHandler(BaseHandler):
    def get(self):
        template_values = {
            'team_name': 'Access Token',
            'logout_url': self.logout_url,
        }
        self.response.out.write(template.render(os.path.join(TEMPLATE_DIR, 'token.html'), template_values))

    def post(self):
        token = self.request.get('tokenInput')
        if token:
            user = users.get_current_user()
            db_user = User.get_by_id(user.user_id())
            db_user.github_token = token
            db_user.put()
            self.redirect('/')
        else:
            self.redirect('/token')


class DashHandler(BaseHandler):
    def get(self, team_name):
        template_values = {
            'team_name': team_name,
            'logout_url': self.logout_url,
        }
        print self.user
        self.response.out.write(template.render(os.path.join(TEMPLATE_DIR, 'dash.html'), template_values))


class MembersHandler(BaseHandler):
    def get(self, team_name):
        g = Github(login_or_token=TOKEN)
        o = g.get_organization(ORG)
        teams = o.get_teams()
        for team in teams:
            if team.name.lower() == team_name.lower():
                break
            else:
                team = None
        team_name_encoded = team_name.lower().replace(' ', '-')

        members = [{
            'name': member.name,
            'username': member.login,
            'pic': member.avatar_url,
            'url': member.html_url,
            'events': member.get_events(),
        } for member in team.get_members()]
        template_values = {
            'team_name': team.name,
            'team_name_encoded': team_name_encoded,
            'members': members,
        }
        self.response.out.write(template.render(os.path.join(TEMPLATE_DIR, 'partials/members-partial.html'), template_values))


class PRsHandler(BaseHandler):

    page_size = 7
    curr_page = 0

    def get_prs_for_range(self, team_name, start, end):
        g = Github(login_or_token=TOKEN)
        o = g.get_organization(ORG)
        teams = o.get_teams()
        for team in teams:
            if team.name.lower() == team_name.lower():
                break
            else:
                team = None
        team_name_encoded = team_name.lower().replace(' ', '-')
        query_string = "team:%s/%s is:pr" % (ORG, team_name_encoded)
        results = g.search_issues(query_string, sort="updated")[start:end]
        pulls = []
        for pull in results:
            repo = g.get_repo(pull.repository.id)
            pr = repo.get_pull(pull.number)
            pulls.append({
                'title': pull.title,
                'url': pull.html_url,
                'state': 'merged' if pr.is_merged() else pull.state,
                'number': pull.number,
                'user': pull.user,
                'repo': pull.repository.name,
                'comments': pull.comments,
            })
        return pulls

    def get(self, team_name):
        pulls = self.get_prs_for_range(team_name, 0, self.page_size)
        template_values = {
            'org': ORG,
            'pulls': pulls,
            'page': 0,
        }
        self.response.out.write(template.render(os.path.join(TEMPLATE_DIR, 'partials/prs-partial.html'), template_values))

    def get_page(self, team_name, page):
        start = int(page) * int(self.page_size)
        end = int(start) + self.page_size
        print '%s, %s, %s' % (page, start, end)
        pulls = self.get_prs_for_range(team_name, start, end)
        self.curr_page = page
        template_values = {
            'org': ORG,
            'pulls': pulls,
            'page': self.curr_page,
        }
        self.response.out.write(template.render(os.path.join(TEMPLATE_DIR, 'partials/prs-partial.html'), template_values))


class User(ndb.Model):

    user_id = ndb.StringProperty()
    github_token = ndb.StringProperty()

app = webapp2.WSGIApplication([
    webapp2.Route('/', handler=HomeHandler),
    webapp2.Route('/token', handler=TokenHandler),
    webapp2.Route('/<team_name>', handler=DashHandler, name='team_name'),
    webapp2.Route('/<team_name>/members', handler=MembersHandler, name='team_name'),
    webapp2.Route('/<team_name>/prs', handler=PRsHandler, name='team_name'),
    webapp2.Route('/<team_name>/prs/<page>', handler=PRsHandler, name='team_name', handler_method='get_page'),
    webapp2.Route('/*', handler=HomeHandler),
], debug=True)

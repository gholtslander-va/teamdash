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
import json
import os
import urllib2
import webapp2

from github import Github
from webapp2_extras import sessions

from google.appengine.ext.webapp import template, urlparse, urllib

ORG = "vendasta"
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')

SECRETS = json.load(open('secrets.json', 'r'))


class BaseHandler(webapp2.RequestHandler):

    session_store = None

    def dispatch(self):

        self.session_store = sessions.get_store(request=self.request)

        if not self.session().get('token') and not self.__class__.__name__ == 'GithubAuth':
            self.github_login()
        else:
            try:
                super(BaseHandler, self).dispatch()
            finally:
                self.session_store.save_sessions(self.response)

    def session(self):
        return self.session_store.get_session()

    def github_login(self):
        url_string = "https://github.com/login/oauth/authorize?client_id={}&scope=user:email repo read:org".format(SECRETS['github']['client_id'])
        self.redirect(url_string)


class GithubAuth(BaseHandler):

    def get(self):
        code = self.request.get('code')
        payload = urllib.urlencode({'client_id': SECRETS['github']['client_id'],
                   'client_secret': SECRETS['github']['client_secret'],
                   'code': code})
        req = urllib2.Request('https://github.com/login/oauth/access_token', payload)
        response = urllib2.urlopen(req)
        parse_string = urlparse.parse_qs(response.read())
        token = parse_string['access_token'][0]
        self.session()['token'] = token
        self.redirect('/')


class HomeHandler(BaseHandler):
    def get(self):
        g = Github(login_or_token=self.session()['token'])
        o = g.get_organization(ORG)
        teams = sorted([team.name for team in o.get_teams()])
        template_values = {
            'team_name': 'Home',
            'teams': teams,
        }
        self.response.out.write(template.render(os.path.join(TEMPLATE_DIR, 'home.html'), template_values))

    def post(self):
        team = self.request.get('teamSelect')
        self.redirect('/%s' % team)


class DashHandler(BaseHandler):
    def get(self, team_name):
        template_values = {
            'team_name': team_name,
        }
        self.response.out.write(template.render(os.path.join(TEMPLATE_DIR, 'dash.html'), template_values))


class MembersHandler(BaseHandler):
    def get(self, team_name):
        g = Github(login_or_token=self.session()['token'])
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
        g = Github(login_or_token=self.session()['token'])
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

config = {}
config['webapp2_extras.sessions'] = {
    'secret_key': str(SECRETS['sessions']['secret']),
}

app = webapp2.WSGIApplication([
    webapp2.Route('/', handler=HomeHandler),
    webapp2.Route('/githubauth', handler=GithubAuth),
    webapp2.Route('/<team_name>', handler=DashHandler, name='team_name'),
    webapp2.Route('/<team_name>/members', handler=MembersHandler, name='team_name'),
    webapp2.Route('/<team_name>/prs', handler=PRsHandler, name='team_name'),
    webapp2.Route('/<team_name>/prs/<page>', handler=PRsHandler, name='team_name', handler_method='get_page'),
    webapp2.Route('/*', handler=HomeHandler),
], debug=True, config=config)

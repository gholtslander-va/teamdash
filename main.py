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
from google.appengine.ext.webapp import template

TOKEN = "47d418c077b06cd8788bef092a48d67dd9cf0db4"
ORG = "vendasta"
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')


class DashHandler(webapp2.RequestHandler):
    def get(self, team_name):
        template_values = {
            'team_name': team_name,
        }
        self.response.out.write(template.render(os.path.join(TEMPLATE_DIR, 'dash.html'), template_values))


class MembersHandler(webapp2.RequestHandler):
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


class PRsHandler(webapp2.RequestHandler):
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
        query_string = "team:%s/%s is:pr" % (ORG, team_name_encoded)
        results = g.search_issues(query_string, sort="updated")
        pulls = [{
            'title': pull.title,
            'url': pull.html_url,
            'state': pull.state,
            'number': pull.number,
            'user': pull.user,
            'repo': pull.repository.name,
            'comments': pull.comments,
        } for pull in results[:5]]
        template_values = {
                'org': ORG,
                'pulls': pulls,
        }
        self.response.out.write(template.render(os.path.join(TEMPLATE_DIR, 'partials/prs-partial.html'), template_values))

app = webapp2.WSGIApplication([
    webapp2.Route('/<team_name>', handler=DashHandler, name='team_name'),
    webapp2.Route('/<team_name>/members', handler=MembersHandler, name='team_name'),
    webapp2.Route('/<team_name>/prs', handler=PRsHandler, name='team_name'),
], debug=True)

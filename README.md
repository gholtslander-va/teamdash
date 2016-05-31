# TeamDash

![Dashboard Screenshot](img/screen1.png)

TeamDash provides a simple way to check the status of your team(s) at Vendasta.
Currently, it lists the members and recent pull requests of a given GitHub team.

## Features

- Choose any [GitHub team at Vendasta](https://github.com/orgs/vendasta/teams)
- Google Authentication
- Direct links to recent PRs

## Sort of working

- PR pagination is somewhat janky, but works well enough

## Usage

The app is currently hosted at [https://vendasta-team-dashboard.appspot.com](https://vendasta-team-dashboard.appspot.com)

When you go to the page, you will need to sign in with your Vendasta Google account.
After logging in, you will need to authorize your Vendasta Github account.

You will then be taken to a team selection page.  Choose your team from the dropdown
and click submit.

The PR list will refresh every 60 seconds.
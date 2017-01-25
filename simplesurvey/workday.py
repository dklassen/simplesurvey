import requests
import pandas as pd

from requests.auth import HTTPBasicAuth


class Report():
    """ Workday report handles connecting to and downloading json reports from Workday.
    JSON reports are parsed and returned as a dataframe
    """

    def __init__(self, user=None, password=None):
        self.user = user
        self.password = password

    def config(self, user=None, password=None):
        if user:
            self.user = user
        if password:
            self.password = password

    def _basic_auth_header(self):
        return HTTPBasicAuth(self.user, self.password)

    def _workday_request(self, url):
        r = requests.get(url, auth=self._basic_auth_header())
        if r.status_code != 200:
            raise Exception(r.reason)
        return r.json()

    def _parse_request(self, r):
        if "Report_Entry" not in r:
            raise Exception("JSON not in expected format")
        return r['Report_Entry']

    def fetch_report(self, url):
        request = self._workday_request(url)
        json = self._parse_request(request)
        return pd.DataFrame(json)

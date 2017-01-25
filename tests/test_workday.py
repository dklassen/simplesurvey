from simplesurvey import workday
import pandas as pd
from unittest import mock


class MockResponse:

    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data


def test_workday_fetch_report_and_convert_to_dataframe():
    data = {"Report_Entry": [
        {
            "field1": "2013-11-28",
            "field2": "type",
            "field3": "name",
        }
    ]}

    def mocked_requests_get(*args, **kwargs):
        return MockResponse(data, 200)

    with mock.patch('requests.get', side_effect=mocked_requests_get):
        test_report = workday.Report(user="test", password="test2")
        result = test_report.fetch_report("https://wd7-services.myworkday.com/ccx/service/somereport/klassenterprises/dana.klassen/super_important_repot?format=json")
        expected = pd.DataFrame(data['Report_Entry'])

        assert result.equals(expected)

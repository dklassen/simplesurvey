import yaml
import requests
import numpy as np
import pandas as pd

from simplesurvey.stats import Chi2Test
from itertools import product, combinations


class SurveyLoadingException(Exception):
    pass


class DuplicateColumnException(Exception):
    pass


class Column():

    def __init__(self, text, column=None, description=None, calculated=None):
        if column is None:
            self._column = text
        else:
            self._column = column

        self.description = description
        self.text = text

        self._data = None
        self._filters = []
        self._transforms = []
        self.calculated = calculated

    @property
    def column(self):
        return self._column

    @property
    def data(self):
        self.transform()
        self.filter()
        return self._data.copy()

    @property
    def filters(self):
        return self._filters

    def add_transform(self, func):
        """ Append a transform func to the list of transform funcs """
        self._transforms.append(func)
        return self

    def transform(self):
        """ tranform applies a map of the list of stored transforms to the data """
        for func in self._transforms:
            self._data = self._data.map(func)

    def add_filter(self, func):
        """ Append filter func to the list of filter funcs. """
        self._filters.append(func)
        return self

    def filter(self):
        """ Filter applies filters funcs to data."""
        for func in self._filters:
            self._data = self._data.loc[func]

    def is_loaded(self):
        if self._data:
            return True
        return False

    def load(self, series):
        self._data = series


class Question(Column):

    def __init__(self, text, description=None, column=None, scale=None, breakdown_by=False):
        super().__init__(text, column=column, description=description)
        self.scale = scale
        self.breakdown_by = breakdown_by

    def describe(self, percentiles=None, include=None, exclude=None):
        if not self.is_loaded():
            return None
        return self._data.describe(percentiles=percentiles, include=include, exclude=exclude)

    def replace_responses(self):
        if self.scale:
            self._data = self._data.replace(self.scale.scoring())

    def load(self, series):
        super(Question, self).load(series)
        self.replace_responses()


class Dimension(Column):

    def __init__(self, text, column=None, calculated=None, breakdown_by=None):
        super().__init__(text, column=column, calculated=calculated)
        if breakdown_by is None:
            breakdown_by = Chi2Test
        self.breakdown_by = breakdown_by

    def categories(self):
        return self.data.unique()

    def pairwise_categories(self):
        return list(combinations(self.categories(), 2))

    def breakdown_with(self, question):
        return self.breakdown_by().test(self, question)


class Summarizer():

    def __init__(self, data):
        self.data = data
        self.summary_rows = []
        self.summary_cols = []

    def average(self, title="Average", **kwargs):
        return self.summary(np.mean, title, **kwargs)

    def median(self, title="Median", **kwargs):
        return self.summary(np.median, title, **kwargs)

    def summary(self, func, title, axis=0, **kwargs):
        return self.multi_summary([func], [title], axis, **kwargs)

    def multi_summary(self, funcs, titles, axis=0, **kwargs):
        output = [self.data.apply(f, axis=axis, **kwargs).to_frame(t)
                  for f, t in zip(funcs, titles)]

        if axis == 0:
            self.summary_rows += [row.T for row in output]
        elif axis == 1:
            self.summary_cols += output
        else:
            ValueError("Invalid axis can be 1 or 0")

        return self

    def column_summary(self):
        return pd.concat(self.summary_cols, axis=1, ignore_index=False)

    def row_summary(self):
        return pd.concat(self.summary_rows, axis=0, ignore_index=False)

    def apply(self):
        colnames = list(self.data.columns)
        summary_colnames = [series.columns[0] for series in self.summary_cols]
        summary_rownames = [series.index[0] for series in self.summary_rows]

        self.data = pd.concat([self.data] + self.summary_cols,
                              axis=1,
                              ignore_index=False)
        self.data = pd.concat([self.data] + self.summary_rows,
                              axis=0,
                              ignore_index=False)

        self.data = self.data[colnames + summary_colnames]

        for row, col in product(summary_rownames, summary_colnames):
            self.data.loc[row, col] = ''

        return self


class Survey():

    def __init__(self, summarizer=None):
        if summarizer is None:
            summarizer = Summarizer

        self._responses = None
        self._supplementary_data = []
        self.columns = {}
        self.processed = False
        self.summarizer = summarizer

    def summarize(self, cols):
        data = self.slice(cols)
        return self.summarizer(data)

    def crosstab(self, ind, dep, **kwargs):
        independent = self.columns[ind]
        dependent = self.columns[dep]

        data = pd.crosstab(independent.data, dependent.data, **kwargs)
        if dependent.scale:
            data = data[dependent.ratings]

        return data

    def responses(self, path, natural_key=None, header=0):
        if isinstance(path, pd.DataFrame):
            self._responses = path
        else:
            self._load_responses_into_dataframe(path, natural_key=natural_key, header=header)

        return self

    def _load_responses_into_dataframe(self, path, natural_key=None, header=0):
        self._responses = self._load(path, header=header)

        if natural_key is not None:
            self._responses = self._responses.set_index(natural_key)
        return self

    def supplementary_data(self, path, natural_key=None, header=0):
        if natural_key is None:
            raise Exception("Must supply natural key if joining supplmentary data to responses")

        data = self._load(path, header=header)

        if natural_key is not None:
            data = data.set_index(natural_key)

        self._supplementary_data.append(data)
        return self

    @property
    def dimensions(self):
        return [col for _, col in self.columns.items() if isinstance(col, Dimension)]

    @property
    def questions(self):
        return [col for _, col in self.columns.items() if isinstance(col, Question)]

    @property
    def data(self):
        if not self.processed:
            self.process()

        cols = [entry.data for _, entry in self.columns.items()]
        if not cols:
            return None

        return self._concat(cols)

    def add_column(self, column):
        if column.column in self.columns:
            raise DuplicateColumnException("Column with name %s already exists in survey" % column.column)
        self.columns[column.column] = column
        return self

    def add_columns(self, columns):
        for column in columns:
            self.add_column(column)
        return self

    def slice(self, columns):
        if not self.processed:
            self.process()

        columns = [col.data for name, col in self.columns.items() if name in columns]
        return pd.concat(columns, axis=1, ignore_index=False)

    def process(self):
        merged_data = self._responses.copy()

        if all(merged_data.index.values == [0]) and len(self._supplementary_data) > 0:
            raise SurveyLoadingException("Responses are being joined with out specified natural key")

        for data in self._supplementary_data:
            try:
                merged_data = pd.merge(merged_data, data, suffixes=('', ''), left_index=True, right_index=True, how="left")
            except ValueError as e:
                if str(e).startswith("columns overlap"):
                    raise SurveyLoadingException("No overlapping columns in supplementary data")
                raise e

        self._format_data(merged_data)
        self.processed = True

    def _concat(self, cols):
        return pd.concat(cols, axis=1, ignore_index=False)

    def _verify_columns_exist(self, data):
        # TODO:: Fixup since we can only run this before calculated fields and can't check if
        # calculated fields were created
        columns = set([entry.column if entry.is_loaded() else entry.text for _, entry in self.columns.items() if not entry.calculated])
        missing_columns = columns.difference(data.columns)
        if missing_columns:
            raise SurveyLoadingException("Found missing columns not in dataset %s" % missing_columns)

    def _column_mapping(self):
        return {column.text: column.column for _, column in self.columns.items() if column.calculated is None}

    def _rename_columns(self, data):
        return data.rename(columns=self._column_mapping())

    def _load_data(self, data):
        for _, entry in self.columns.items():
            entry.load(data[entry.column])
            data.drop(entry.column, 1)

    def _create_calculated_columns(self, data):
        # TODO:: Find better way of doing this. Perhaps separate list for calculated columns
        data = data.copy()
        for _, entry in self.columns.items():
            if entry.calculated:
                data[entry.column] = data.apply(entry.calculated, axis=1)
        return data

    def _format_data(self, data):
        self._verify_columns_exist(data)
        data = self._rename_columns(data)
        data = self._create_calculated_columns(data)
        self._load_data(data)

    def _read_excel(self, path, header=0):
        return pd.read_excel(path, header=header)

    def _read_csv(self, path, header=0):
        return pd.read_csv(path, header=header)

    def _data_loader(self, path):
        if path.endswith(".xlsx"):
            return self._read_excel
        elif path.endswith(".csv"):
            return self._read_csv
        else:
            raise ValueError("Unable to determine filetype for %s" % path)

    def _load(self, path, header=0):
        loader = self._data_loader(path)
        return loader(path, header=header)

    def _filter_questions_for_breakdown(self):
        return [question for _, question in self.columns.items() if isinstance(question, Question) and question.breakdown]

    def breakdown_by_dimensions(self, threshold):
        """ {"question1": [Result1, Result2]}"""
        breakdown = {}
        for question in self._filter_questions_for_breakdown():
            results = []
            for dimension in self.dimensions():
                results.append(dimension.breakdown_with(question))
            breakdown[question.column] = results
        return breakdown


class TypeFormSurvey(Survey):
    typeform_url = "https://api.typeform.com/v1/form/{}?key={}"

    def __init__(self, summarizer=None):
        super().__init__(summarizer)
        self.form_uuid = None
        self.api_key = None

    @property
    def url(self):
        return self.typeform_url.format(self.form_uuid, self.api_key)

    def config(self, api_key, form_uuid):
        self.api_key = api_key
        self.form_uuid = form_uuid

    def fetch_data(self):
        response = requests.get(self.url)
        if response.status_code != 200:
            raise "Encountered an error while trying to download from TypeForm: {}".format(response.status_code)
        return response

    def fetch(self):
        """ Download data for a form and convert to a data frame"""
        data = self.fetch_data()

        responses = [x for x in data.json()['responses'] if x['completed'] == '1']
        questions = {x['id']: x['question'] for x in data.json()['questions']}

        data = dict((el, []) for el in questions.keys())
        for r in responses:
            r = r['answers']

            for key in data.keys():
                data[key].append(r.get(key, pd.NaT))

        self._responses = pd.DataFrame(data).rename(columns=questions)
        return self

# NOTE:: Lets dry this up so we don't have a bunch of these
# yaml parsers laying around


def typeform_survey_yaml_constructor(loader, node):
    survey = TypeFormSurvey()
    values = loader.construct_mapping(node, deep=True)
    survey.add_columns(values.get("questions", []))
    survey.add_columns(values.get("dimensions", []))
    return survey


def survey_yaml_constructor(loader, node):
    survey = Survey()
    values = loader.construct_mapping(node, deep=True)
    survey.add_columns(values.get("questions", []))
    survey.add_columns(values.get("dimensions", []))
    return survey


def question_yaml_constructor(loader, node):
    values = loader.construct_mapping(node)
    question = Question(values.get("text"),
                        description=values.get("description"),
                        column=values.get("column"),
                        scale=values.get("scale"),
                        breakdown_by=values.get("breakdown_by", False))

    # NOTE:: Note to future self - eval is the devil
    if values.get("filters"):
        for func_st in values.get("filters"):
            question.add_filter(eval(func_st))

    return question


def dimension_yaml_constructor(loader, node):
    values = loader.construct_mapping(node)
    dimension = Dimension(values.get("text"),
                          column=values.get("column"),
                          calculated=values.get("calculated"),
                          breakdown_by=values.get("breakdown_by", False))

    # NOTE:: Note to future self - eval is the devil
    if values.get("filters"):
        for func_st in values.get("filters"):
            dimension.add_filter(eval(func_st))

    return dimension

yaml.add_constructor("!TypeFormSurvey", typeform_survey_yaml_constructor)
yaml.add_constructor("!Survey", survey_yaml_constructor)
yaml.add_constructor("!Question", question_yaml_constructor)
yaml.add_constructor("!Dimension", dimension_yaml_constructor)

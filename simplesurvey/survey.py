import yaml
import numpy as np
import pandas as pd
import scipy.stats as stats

from itertools import product, combinations


class SurveyLoadingException(Exception):
    pass


class DuplicateColumnException(Exception):
    pass


def contingency_table(x, y, **kwargs):
    return pd.crosstab(x, y, **kwargs)


class Chi2Test():

    def _generate_observed(self, independent, dependent):
        cross_tab = contingency_table(independent, dependent)
        row, col = cross_tab.shape
        observed = cross_tab.iloc[0:row, 0:col]
        observed.index = cross_tab.index
        observed.columns = cross_tab.columns
        return observed

    def test(self, independent, dependent):
        observed = self._generate_observed(independent._data, dependent._data)
        result = stats.chi2_contingency(observed=observed)
        return self._build_result(independent.text, dependent.text, result)

    def _build_result(self, independent_label, dependent_label, result):
        return Chi2TestResult(dependent_label, independent_label, *result)


class KruskallWallisTest():

    def test(self, independent, dependent):
        groups = []

        data = pd.merge(
            independent._data,
            dependent._data,
            left_index=True,
            right_index=True)
        for _, group in data.groupby(independent.column):
            groups.append(group)

        result = stats.mstats.kruskalwallis(*groups)
        return self._build_result(independent.text, dependent.text, *result)

    def _build_result(self, independent_label,
                      dependent_label, hstatistic, pvalue):
        return KruskallWallisTestResult(
            dependent_label, independent_label, hstatistic, pvalue)


class Column():

    def __init__(self):
        self._data = None
        self.calculated = None

    @property
    def data(self):
        return self._data.copy()

    def is_loaded(self):
        if self._data:
            return True
        return False

    def load(self, series):
        self._data = series


class Question(Column):

    def __init__(self, text, description=None,
                 column=None, scale=None, breakdown=False):
        super().__init__()

        if column is None:
            self.column = text
        else:
            self.column = column
        self.scale = scale
        self.description = description
        self.text = text
        self.breakdown = breakdown

    def describe(self, percentiles=None, include=None, exclude=None):
        if not self.is_loaded():
            return None
        return self._data.describe(
            percentiles=percentiles, include=include, exclude=exclude)

    def replace_responses(self):
        if self.scale:
            self._data = self._data.replace(self.scale.scoring())

    def load(self, series):
        super(Question, self).load(series)
        self.replace_responses()


class Dimension(Column):

    def __init__(self, text, column=None, calculated=None, breakdown_by=None):
        super().__init__()

        if breakdown_by is None:
            breakdown_by = Chi2Test

        self.filters = []

        if column is None:
            self._column = text
        else:
            self._column = column

        self.calculated = calculated
        self.text = text
        self.breakdown_by = breakdown_by

    @property
    def column(self):
        return self._column

    def add_filter(self, func):
        self.filters.append(func)

    def _filter(self):
        for f in self.filters:
            self.data = self.data.loc[f]

    def categories(self):
        return self.data.unique()

    def pairwise_categories(self):
        return list(combinations(self.categories(), 2))

    def breakdown_with(self, question):
        self._filter()
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
        self.filters = []
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
            self._load_responses_into_dataframe(
                path, natural_key=natural_key, header=header)

        return self

    def _load_responses_into_dataframe(self, path, natural_key=None, header=0):
        self._responses = self._load(path, header=header)

        if natural_key is not None:
            self._responses = self._responses.set_index(natural_key)
        return self

    def supplementary_data(self, path, natural_key=None, header=0):
        if natural_key is None:
            raise Exception(
                "Must supply natural key if joining supplmentary data to responses")

        data = self._load(path, header=header)

        if natural_key is not None:
            data = data.set_index(natural_key)

        self._supplementary_data.append(data)
        return self

    @property
    def dimensions(self):
        return [col for _, col in self.columns.items(
        ) if isinstance(col, Dimension)]

    @property
    def questions(self):
        return [col for _, col in self.columns.items() if isinstance(col, Question)]

    @property
    def data(self):
        if not self.processed:
            self.process()

        cols = [entry.data for _, entry in self.columns.items()]
        if cols:
            return self._concat(cols)

    def add_column(self, column):
        if column.column in self.columns:
            raise DuplicateColumnException(
                "Column with name %s already exists in survey" % column.column)
        self.columns[column.column] = column
        return self

    def add_columns(self, columns):
        if not columns:
            return self

        for column in columns:
            self.add_column(column)
        return self

    def add_filter(self, func):
        self.filters.append(func)
        return self

    def _apply_filters(self, data):
        for f in self.filters:
            data = data.loc[f, :]
        return data

    def slice(self, columns):
        columns = [col.data for name, col in self.columns.items() if name in columns]
        return pd.concat(columns, axis=1, ignore_index=False)

    def process(self):
        merged_data = self._responses.copy()

        if all(merged_data.index.values == [0]) and len(
                self._supplementary_data) > 0:
            raise SurveyLoadingException(
                "Responses are being joined with out specified natural key")

        for data in self._supplementary_data:
            try:
                merged_data = pd.merge(
                    merged_data,
                    data,
                    suffixes=('', ''),
                    left_index=True,
                    right_index=True,
                    how="left")
            except ValueError as e:
                if str(e).startswith("columns overlap"):
                    raise SurveyLoadingException(
                        "No overlapping columns in supplementary data")
                raise e

        self._format_data(merged_data)
        self.processed = True

    def _concat(self, cols):
        return pd.concat(cols, axis=1, ignore_index=False)

    def _verify_columns_exist(self, data):
        # TODO:: Fixup since we can only run this before calculated fields and can't check if
        # calculated fields were created
        columns = set([entry.column if entry.is_loaded(
        ) else entry.text for _, entry in self.columns.items() if not entry.calculated])
        missing_columns = columns.difference(data.columns)
        if missing_columns:
            raise SurveyLoadingException(
                "Found missing columns not in dataset %s" % missing_columns)

    def _column_mapping(self):
        return {column.text: column.column for _, column in self.columns.items() if column.calculated is None}

    def _rename_columns(self, data):
        return data.rename(columns=self._column_mapping())

    def _load_data(self, data):
        for _, entry in self.columns.items():
            entry.load(data[entry.column])
            data.drop(entry.column, 1)

    def _create_calculated_columns(self, data):
        # TODO:: Find better way of doing this. Perhaps separate list for
        # calculated columns
        data = data.copy()
        for _, entry in self.columns.items():
            if entry.calculated:
                data[entry.column] = data.apply(entry.calculated, axis=1)
        return data

    def _format_data(self, data):
        self._verify_columns_exist(data)
        data = self._rename_columns(data)
        data = self._create_calculated_columns(data)
        data = self._apply_filters(data)
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
        return [question for _, question in self.columns.items() if isinstance(
            question, Question) and question.breakdown]

    def breakdown_by_dimensions(self, threshold):
        """ {"question1": [Result1, Result2]}"""
        breakdown = {}
        for question in self._filter_questions_for_breakdown():
            results = []
            for dimension in self.dimensions():
                results.append(dimension.breakdown_with(question))
            breakdown[question.column] = results
        return breakdown


class Chi2TestResult():

    def __init__(self, dependent_label, independent_label,
                 chi2_statistic, pvalue, degrees_of_freedom, expected):
        self.independent_label = independent_label
        self.dependent_label = dependent_label
        self.chi2_statistic = chi2_statistic
        self.pvalue = pvalue
        self.expected = expected
        self.degrees_of_freedom = degrees_of_freedom

    @property
    def test_statistic(self):
        return self.chi2_statistic

    def __str__(self):
        return """Chi2 Test:
Dependent: %s
Independent: %s
Result: pvalue=%s test_statistic=%s """ % (self.dependent_label, self.independent_label, self.pvalue, self.test_statistic)


class KruskallWallisTestResult():

    def __init__(self, dependent_label, independent_label, hstat, pvalue):
        self.dependent_label = dependent_label
        self.independent_label = independent_label
        self.hstatistic = hstat
        self.pvalue = pvalue

    @property
    def test_statistic(self):
        return self.hstatistic

    def __str__(self):
        return """KruskallWallis Test:
Dependent: %s
Independent: %s
Result: pvalue=%s, test_statistic=%s""" % (self.dependent_label, self.independent_label, self.pvalue, self.test_statistic)


def survey_yaml_constructor(loader, node):
    values = loader.construct_mapping(node, deep=True)
    survey = Survey()
    survey.add_columns(values.get("questions"))
    survey.add_columns(values.get("dimensions"))
    return survey


def question_yaml_constructor(loader, node):
    values = loader.construct_mapping(node)
    return Question(values.get("text"),
                    description=values.get("description"),
                    column=values.get("column"),
                    scale=values.get("scale"),
                    breakdown=values.get("breakdown", False))


def dimension_yaml_constructor(loader, node):
    values = loader.construct_mapping(node)
    return Dimension(values.get("text"),
                     column=values.get("column"),
                     calculated=values.get("calculated"),
                     breakdown_by=values.get("breakdown_by", False))

yaml.add_constructor("!Survey", survey_yaml_constructor)
yaml.add_constructor("!Question", question_yaml_constructor)
yaml.add_constructor("!Dimension", dimension_yaml_constructor)

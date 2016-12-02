import logging
import operator
import itertools
import pandas as pd
import scipy.stats as stats


class DuplicateColumnException(Exception):
    pass


class UnknownResponseFormat(Exception):
    pass


class ColumnNotFoundError(Exception):
    pass


def contingency_table(x, y):
    return pd.crosstab(x, y)


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
        return Chi2TestResult(dependent_label, independent_label,  *result)


class KruskallWallisTest():

    def test(self, independent, dependent):
        groups = []

        data = pd.merge(independent._data, dependent._data,  left_index=True, right_index=True)
        for _, group in data.groupby(independent.column):
            groups.append(group)

        result = stats.mstats.kruskalwallis(*groups)
        return self._build_result(independent.text, dependent.text, *result)

    def _build_result(self, independent_label, dependent_label, hstatistic, pvalue):
        return KruskallWallisTestResult(dependent_label, independent_label, hstatistic, pvalue)


class Scale:

    def __init__(self, scale):
        self._scale = scale

    def sorted_scale_columns(self):
        sorted_scale = sorted(self._scale.items(), key=operator.itemgetter(1))
        return [x for x, y in sorted_scale]


class Question():

    def __init__(self, text, column=None, scale=None, breakdown=False):
        if scale is None:
            self.scale = []

        if column is None:
            self.column = text
        else:
            self.column = column

        self.calculated = None
        self.text = text
        self.breakdown = breakdown
        self._data = None

    def load(self, series):
        self._data = series


class Dimension():

    def __init__(self, text, column=None, calculated=None, breakdown_by=None):
        if breakdown_by is None:
            breakdown_by = Chi2Test

        self.filters = []

        if column is None:
            self.column = text
        else:
            self.column = column

        self.calculated = calculated
        self.text = text
        self.breakdown_by = breakdown_by

    def load(self, series):
        self._data = series

    def add_filter(self, func):
        self.filters.append(func)

    def _filter(self):
        for f in self.filters:
            self._data = self._data.loc[f]

    def categories(self):
        return self._data.unique()

    def pairwise_categories(self):
        return list(itertools.combinations(self.categories(), 2))

    def breakdown_with(self, question):
        self._filter()
        return self.breakdown_by().test(self, question)


def _convert_by(by):
    if by is None:
        by = []
    else:
        by = list(by)
    return by

class Survey():

    def __init__(self):
        self.filters = []
        self.entries = {}
        self._data = None

    def add_entry(self, column):
        if column.column in self.entries:
            raise DuplicateColumnException("Column with name %s already exists in survey" % column.column)
        self.entries[column.column] = column

    @property
    def dimensions(self):
        return [col for _, col in self.entries.items() if isinstance(col, Dimension)]

    def sorted_dimensions(self):
        return sorted(self.dimensions, key=lambda dimension: dimension.column)

    @property
    def questions(self):
        return [col for _, col in self.entries.items() if isinstance(col, Question)]

    def add_filter(self, func):
        self.filters.append(func)

    def apply_filters(self):
        for f in self.filters:
            self._data = self._data.loc[f, :]

    def get_column(self, column_name):
        return self.dimensions.get(column_name, None)

    def _column_mapping(self):
        return {column.text: column.column for _, column in self.entries.items() if column.calculated is None}

    def _rename_columns(self):
        self._data.rename(columns=self._column_mapping(), inplace=True)

    def _load_data(self):
        for _, entry, in self.entries.items():
            if not entry.calculated and entry.column not in self._data:
                raise ColumnNotFoundError("The column %s was not found in the list of data columns: %s" % (entry.column, self._data.columns))

            if entry.calculated:
                logging.info(self._data['hire_date'])
                self._data[entry.column] = self._data.apply(entry.calculated, axis=1)

            entry.load(self._data[entry.column])

    def _format_data(self):
        self._rename_columns()
        self._load_data()

    def _read_excel(self, path, header=0):
        return pd.read_excel(path, header=header)

    def _read_csv(self, path, header=0):
        return pd.read_csv(path, header=header)

    def summary(self):
        return """
Number of Rows: {rownum}
Number of Questions: {questions}
Number of Dimensions: {dimensions}
        """.format(rownum=len(self._data),
                   questions=len(self.questions),
                   dimensions=len(self.dimensions))
    
    def process(self, responses, dimensions=None, left_on=None, right_on=None, how="right", response_header=0, dimension_header=0):
        dimensions = _convert_by(dimensions)

        if not self.questions:
            raise Exception("No questions have been added to survey")

        responses = self._load(responses, header=response_header)

        for dim in dimensions:    
            logging.info("loading dimension %s and merging" % dimension)
            dimensions = self._load(dimensions, header=response_header)
            responses = pd.merge(responses, dimensions, left_on=left_on, right_on=right_on, how=how)

        self._data = responses
        self._format_data()

    def _data_loader(self, path):
        if path.endswith(".xlsx"):
            return self._read_excel
        elif path.endswith(".csv"):
            return self._read_csv
        else:
            raise UnknownResponseFormat("Unable to determine filetype for %s" % path)

    def _load(self, path, header=0):
        loader = self._data_loader(path)
        return loader(path, header=header)

    def _filter_questions_for_breakdown(self):
        return [question for _, question in self.entries.items() if isinstance(question, Question) and question.breakdown]

    def breakdown_by_dimensions(self, threshold):
        """ {"question1": [Result1, Result2]}"""
        breakdown = {}
        for question in self._filter_questions_for_breakdown():
            results = []
            for dimension in self.sorted_dimensions():
                results.append(dimension.breakdown_with(question))
            breakdown[question.column] = results
        return breakdown

    def results_csv(self, threshold=0.01):
        logging.info("generating results with significance alpha < %s" % threshold)
        logging.info("Okay that was a lie for the time being")

class Chi2TestResult():

    def __init__(self, dependent_label, independent_label, chi2_statistic, pvalue, degrees_of_freedom, expected):
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

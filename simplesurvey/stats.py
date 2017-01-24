import scipy.stats as stats
import pandas as pd

from simplesurvey import utilities


class Chi2Test():

    def _generate_observed(self, independent, dependent):
        cross_tab = utilities.contingency_table(independent, dependent)
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

        data = pd.merge(independent._data, dependent._data, left_index=True, right_index=True)
        for _, group in data.groupby(independent.column):
            groups.append(group)

        result = stats.mstats.kruskalwallis(*groups)
        return self._build_result(independent.text, dependent.text, *result)

    def _build_result(self, independent_label, dependent_label, hstatistic, pvalue):
        return KruskallWallisTestResult(dependent_label, independent_label, hstatistic, pvalue)


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

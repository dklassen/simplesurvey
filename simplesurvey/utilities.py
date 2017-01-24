import math
import pandas as pd


def contingency_table(x, y, **kwargs):
    return pd.crosstab(x, y, **kwargs)


def to_ordinal(n):
    return "%d%s" % (
        n, "tsnrhtdd"[(math.floor(n / 10) % 10 != 1) * (n % 10 < 4) * n % 10::4])


def percent_of(data, column):
    col_total = data[column].sum()
    return 100 * data[column] / col_total


def percent_between(data, col1, col2):
    pass


def column_group_sizes(data, column):
    return data.groupby(column)\
               .size()\
               .rename("%s_size" % column) \
               .to_frame()\
               .reset_index()

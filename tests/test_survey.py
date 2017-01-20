import pytest
import yaml
import pandas as pd
import numpy as np
import simplesurvey


def test_loading_survey_from_yaml():
    document = """
--- !Survey
scales:
    - !OrdinalScale
      &standard_likert
      labels: ["Strongly Disagree","Disagree","Neutral","Agree","Strongly Agree"]
      ratings: [ 1,2,3,4,5]
questions:
    - !Question
      text: "How many engineers does it take to screw in a lightbulb?"
      description: |
                    "A question for the engineers in the crowd we are
                    asking to see if there is a difference in the
                    number of reported light bulbs depending on what
                    you do for a living"
      column: "engineer_lightbulb_question"
      scale: *standard_likert
"""
    try:
        simplesurvey.LoadSurvey(document)
    except Exception:
        pytest.fail("Unexpected Exception")


def test_document_loading_follows_aliases():
    document = """
- !OrdinalScale
  &standard_likert
  labels: ["Strongly Disagree","Disagree","Neutral","Agree","Strongly Agree"]
  ratings: [ 1,2,3,4,5]
- !Question
  text: "How many engineers does it take to screw in a lightbulb?"
  description: |
                "A question for the engineers in the crowd we are
                asking to see if there is a difference in the
                number of reported light bulbs depending on what
                you do for a living"
  column: "engineer_lightbulb_question"
  scale: *standard_likert
"""

    result = list(yaml.load_all(document))[0]
    assert len(result) == 2

    result_question = result[1]
    assert result_question.scale.ratings == list(
        range(1, 6))  # range is exclusive


def test_set_response_data(tmpdir):
    path = tmpdir.join("data.csv")
    path.write("""col1,col2,col3
data1,data2,data2""")

    survey = simplesurvey.Survey()
    survey.responses(str(path))\
          .add_column(simplesurvey.Question("col1"))\
          .add_column(simplesurvey.Question("col2"))\
          .add_column(simplesurvey.Question("col3"))\
          .process()

    result = survey.data
    assert sorted(result.columns) == sorted(['col1', 'col2', 'col3'])


def test_supplementary_data(tmpdir):
    path = tmpdir.join("data.csv")
    path.write("""col1,col2,col3
1,data2,data2""")

    suppath = tmpdir.join("data2.csv")
    suppath.write("""natural_key,sup2,sup3
1,data2,data2""")

    survey = simplesurvey.Survey()
    survey.responses(str(path), natural_key='col1')\
          .supplementary_data(str(suppath), "natural_key")\
          .add_column(simplesurvey.Question("col2"))\
          .add_column(simplesurvey.Question("col3"))\
          .add_column(simplesurvey.Question("sup2"))\
          .add_column(simplesurvey.Question("sup3"))\
          .process()

    result = survey.data
    assert sorted(list(result.columns)) == sorted(
        ['col2', 'col3', 'sup2', 'sup3'])


def test_supplementary_data_overlapping_throws_exception(tmpdir):
    path = tmpdir.join("data.csv")
    path.write("""col1,col2,col3
1,data2,data2""")

    suppath = tmpdir.join("data2.csv")
    suppath.write("""natural_key,col2,sup3
1,data2,data2""")

    survey = simplesurvey.Survey()
    survey.responses(str(path), 'col1')\
          .supplementary_data(str(suppath), "natural_key")

    with pytest.raises(simplesurvey.SurveyLoadingException):
        survey.process()


def test_responses_with_no_natural_key_raises_when_supplementary_data_added(
        tmpdir):
    survey = simplesurvey.Survey()
    path = tmpdir.join("data.csv")
    path.write("""col1,col2,col3
1,data2,data2""")

    suppath = tmpdir.join("data2.csv")
    suppath.write("""natural_key,col2,sup3
1,data2,data2""")

    survey.responses(str(path))
    survey.supplementary_data(str(suppath), 'natural_key')

    with pytest.raises(simplesurvey.SurveyLoadingException):
        survey.process()


def test_add_question_to_survey():
    test_question = simplesurvey.Question("A test column")
    survey = simplesurvey.Survey()
    survey.add_column(test_question)

    assert len(survey.questions) == 1
    assert survey.questions[0].column == "A test column"


def test_add_dimension_to_survey():
    test_dimension = simplesurvey.Dimension("A test dimension")
    survey = simplesurvey.Survey()
    survey.add_column(test_dimension)

    assert len(survey.dimensions) == 1
    assert survey.dimensions[0].column == "A test dimension"


def test_add_and_load_calculated_dimension_to_survey():
    def times_2(x):
        return x['col1'] * 2

    survey = simplesurvey.Survey()
    data = pd.DataFrame(data={'col1': [1], 'col2': ['2']})
    survey._responses = data

    calculated_dimension = simplesurvey.Dimension(
        'calc_column', calculated=times_2)
    survey.add_column(calculated_dimension)

    assert len(survey.dimensions) == 1
    result = survey.data
    assert "calc_column" in result
    assert len(result) == 1
    assert result['calc_column'][0] == 2


def test_simple_filter_data():
    survey = simplesurvey.Survey()
    question1 = simplesurvey.Question("col1")
    data = pd.DataFrame(data={'col1': [1, 2, 3], 'col2': [2, 3, 4]})

    survey._responses = data
    survey.add_column(question1)\
          .add_filter(lambda x: x.col1 == 1)\
          .process()

    result = survey.data
    expected = pd.DataFrame({'col1': [1]})

    assert result.equals(expected)


def test_data_raises_exception_if_column_doesnt_exist():
    survey = simplesurvey.Survey()
    question1 = simplesurvey.Question("I am a missing column")
    data = pd.DataFrame(data={'col1': ['1'], 'col2': ['2']})
    survey._responses = data

    survey.add_column(question1)
    with pytest.raises(simplesurvey.SurveyLoadingException):
        survey.process()


def test_raise_error_when_columns_with_same_name_are_added():
    test_question_1 = simplesurvey.Question("repeat_column_name")
    test_question_2 = simplesurvey.Question("repeat_column_name")

    survey = simplesurvey.Survey()
    survey.add_column(test_question_1)
    with pytest.raises(simplesurvey.DuplicateColumnException):
        survey.add_column(test_question_2)


def test_ordinal_scale_throws_error_when_labels_and_ratings_dont_match():
    with pytest.raises(Exception):
        labels = ['cat1', 'cat2', 'cat3']
        ratings = [1, 2, 3, 4]
        simplesurvey.OrdinalScale(labels=labels, ratings=ratings)


def test_ordinal_scale_scoring_returns_dict_mapping():
    labels = ['cat1', 'cat2', 'cat3']
    ratings = [2, 3, 1]
    scale = simplesurvey.OrdinalScale(labels=labels, ratings=ratings)

    mapping = scale.scoring()
    assert mapping == {'cat1': 2, 'cat2': 3, 'cat3': 1}


def test_summarizer_row_summary():
    data = pd.DataFrame({'a': [1, 2, 3, 4, 5]})
    summarizer = simplesurvey.Summarizer(data)

    summarizer.summary(np.count_nonzero, "count")
    result = summarizer.row_summary()
    assert result.loc['count'][0] == 5


def test_survey_summary_returns_summarizer_with_loaded_columns():
    data = pd.DataFrame({'a': [1, 2, 3, 4, 5]})
    survey = simplesurvey.Survey()
    survey.responses(data)\
          .add_column(simplesurvey.Question('a'))\
          .process()

    result = survey.summarize(['a'])
    assert isinstance(result, simplesurvey.Summarizer)

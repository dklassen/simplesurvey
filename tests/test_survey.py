import pytest
import simplesurvey.survey as simplesurvey


def test_add_question_to_survey():
    test_question = simplesurvey.Question("A test column")
    survey = simplesurvey.Survey()
    survey.add_entry(test_question)

    assert len(survey.questions) == 1
    assert survey.questions[0].column == "A test column"


def test_add_dimension_to_survey():
    test_dimension = simplesurvey.Dimension("A test dimension")
    survey = simplesurvey.Survey()
    survey.add_entry(test_dimension)

    assert len(survey.dimensions) == 1
    assert survey.dimensions[0].column == "A test dimension"


def test_raise_error_when_columns_with_same_name_are_added():
    test_question_1 = simplesurvey.Question("repeat_column_name")
    test_question_2 = simplesurvey.Question("repeat_column_name")

    survey = simplesurvey.Survey()
    survey.add_entry(test_question_1)
    with pytest.raises(simplesurvey.DuplicateColumnException):
        survey.add_entry(test_question_2)

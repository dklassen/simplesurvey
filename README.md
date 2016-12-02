# Simple Survey

Status:: PRE-ALPHA

This was a project to explore if doing this via Pandas would provide a good solution to
automate survey analysis of some simple surveys that we had to run. Simple Survey is a
Pandas Backed Survey Creation and Analysis framework. While you still
can't get away from understanding the responses beforehand we want to make it easy to 
encode the rational behind why we split questinons the way we did.

Features
--------

- Create questions and specify how and by what questions should be broken down
- Specify filters for easily cleaning up response data
- Extend with additional test methods for correlation and independence testing per question
- Generate CSV of results meeting your threshold alpha/beta


Installation
------------

You can install SimpleSurvey using `pip` with support for Python 3.4 and 3.5.

``` {.sourceCode .sh}
pip install git+git:github.com:dklassen/simplesurvey.git
```

You can also install from source;
```{.sourceCode .sh}
git clone git@github.com:dklassen/simplesurvey.git
cd simplesurvey
pip install -e .
```

Documentation
-------------

Documentation is not available currently

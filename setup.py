from setuptools import setup
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.txt'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='simplesurvey',

    version='0.0.1',

    description='Pandas backed survey analysis tool.',
    long_description=long_description,

    url='https://github.com/dklassen/simplesurvey',

    author='Dana Klassen',
    author_email='dana.klassen@shopify.com',

    license='MIT',

    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering',

        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3.5',
    ],

    keywords='pandas survey analysis',

    packages=["simplesurvey"],

    install_requires=[
        "numpy == 1.11.0",
        "scipy == 0.18.1",
        "numpy == 1.11.0",
        "termcolor==1.1.0",
        "pandas >= 0.19.0"
    ],
)

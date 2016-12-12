#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name="python-elastic-log-handler",
    version='1.0.3',
    description="Logging handler to send logs to your elasticsearch",
    keywords="logging handler bulk",
    author="saurabh",
    author_email="saurabh.1e1@gmail.com",
    url="https://github.com/saurabh1e/python-elastic-log-handler/",
    license="Apache License 2",
    packages=find_packages(),
    install_requires=[
        "requests"
    ],
    include_package_data=True,
    classifiers=[]
)

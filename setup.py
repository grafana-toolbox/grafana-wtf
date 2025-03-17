# -*- coding: utf-8 -*-
import os

from setuptools import find_packages, setup
from versioningit import get_cmdclasses

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, "README.rst")).read()

no_linux_on_arm = (
    "platform_system != 'Linux' or (platform_machine != 'armv7l' and platform_machine != 'aarch64')"
)

requires = [
    # Core
    "six",
    "docopt-ng>=0.6.2,<0.10",
    "importlib-metadata; python_version<'3.8'",
    "munch>=2.5.0,<5",
    "tqdm>=4.60.0,<5",
    "verlib2>=0.3.1,<0.4",
    # Filtering
    f"pandas<2.3; {no_linux_on_arm}",
    f"duckdb<1.3; {no_linux_on_arm}",
    # Grafana
    "grafana-client>=4,<5",
    "jsonpath-rw>=1.4.0,<2",
    # Caching
    "requests-cache>=0.8.0,<2",
    # Output
    "tabulate>=0.8.5,<0.10",
    "colored>=1.4.3,<3",
    "Pygments>=2.15.1,<3",
    "PyYAML>=5,<7",
]

extras = {
    "test": [
        "pytest<9",
        "pytest-cov<7",
        "lovely-pytest-docker>=1,<2",
        "grafanalib==0.7.1",
    ]
}

setup(
    name="grafana-wtf",
    cmdclass=get_cmdclasses(),
    description="Grep through all Grafana entities in the spirit of git-wtf",
    long_description=README,
    license="AGPL 3, EUPL 1.2",
    classifiers=[
        "Programming Language :: Python",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "License :: OSI Approved :: European Union Public Licence 1.2 (EUPL 1.2)",
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Manufacturing",
        "Intended Audience :: Science/Research",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Telecommunications Industry",
        "Operating System :: POSIX",
        "Operating System :: Unix",
        "Operating System :: MacOS",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Communications",
        "Topic :: Database",
        "Topic :: Internet",
        "Topic :: Scientific/Engineering :: Information Analysis",
        "Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator",
        "Topic :: Scientific/Engineering :: Visualization",
        "Topic :: Software Development :: Embedded Systems",
        "Topic :: Software Development :: Libraries",
        "Topic :: System :: Archiving",
        "Topic :: System :: Networking :: Monitoring",
    ],
    author="Andreas Motl",
    author_email="andreas.motl@panodata.org",
    url="https://github.com/grafana-toolbox/grafana-wtf",
    keywords="grafana search index",
    packages=find_packages(),
    include_package_data=True,
    package_data={},
    zip_safe=False,
    test_suite="grafana_wtf.test",
    install_requires=requires,
    extras_require=extras,
    tests_require=extras["test"],
    dependency_links=[],
    entry_points={
        "console_scripts": [
            "grafana-wtf = grafana_wtf.commands:run",
        ],
    },
)

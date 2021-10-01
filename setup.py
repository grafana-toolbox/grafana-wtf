# -*- coding: utf-8 -*-
import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()

requires = [

    # Core
    'six',
    'docopt>=0.6.2,<0.7',
    'munch>=2.5.0,<3',
    'tqdm>=4.37.0,<5',

    # Grafana
    'requests>=2.23.0,<3',
    'grafana-api>=1.0.3,<2',
    'jsonpath-rw>=1.4.0,<2',

    # Caching
    'requests-cache>=0.5.2,<1',

    # Output
    'tabulate>=0.8.5,<0.9',
    'colored>=1.4.0',
    'Pygments>=2.7.4,<3',

]

extras = {'test': [
    "pytest>=5,<7",
    "lovely-pytest-docker>=0.2.1,<3"
]}

setup(name='grafana-wtf',
      version='0.10.0',
      description='Grep through all Grafana entities in the spirit of git-wtf',
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
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
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
      author='Andreas Motl',
      author_email='andreas@hiveeyes.org',
      url='https://github.com/panodata/grafana-wtf',
      keywords='grafana search index',
      packages=find_packages(),
      include_package_data=True,
      package_data={
      },
      zip_safe=False,
      test_suite='grafana_wtf.test',
      install_requires=requires,
      extras_require = extras,
      tests_require=extras['test'],
      dependency_links=[
      ],
      entry_points={
          'console_scripts': [
              'grafana-wtf = grafana_wtf.commands:run',
          ],
      },
)

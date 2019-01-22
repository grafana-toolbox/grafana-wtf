# -*- coding: utf-8 -*-
import os
from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.rst')).read()

requires = [

    # Core
    'six==1.12.0',
    'docopt==0.6.2',
    'munch==2.3.2',

    # Grafana
    'requests==2.21.0',
    'grafana-api==0.5.0',

    # Caching
    'requests-cache==0.4.13',

]

extras = {}

setup(name='grafana-wtf',
      version='0.0.0',
      description='Grep through all Grafana entities',
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
        "Operating System :: POSIX",
        "Operating System :: Unix",
        "Operating System :: MacOS"
        ],
      author='Andreas Motl',
      author_email='andreas@hiveeyes.org',
      url='https://github.com/daq-tools/grafana-wtf',
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

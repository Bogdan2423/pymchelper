from itertools import chain
from pathlib import Path
import setuptools

from pymchelper.version import git_version


def write_version_py():
    """
    Generate a file with a version number obtained from git (i.e. name of last tag + additional info)
    It uses a dedicated function called `git_version` which sits in the `version` module.
    This autogenerated file will be later included in the package (which will be uploaded to pip server).

    """
    cnt = """%(version)s
"""

    GIT_REVISION = git_version()
    with open(Path('pymchelper', 'VERSION'), 'w') as f:
        f.write(cnt % {'version': GIT_REVISION})


# automatically generate VERSION file upon import or execution of this (setup.py) script
write_version_py()

# extract readme text from the markdown file
with open('README.md') as readme_file:
    readme = readme_file.read()

# extras_require will be used in two scenarios:
#  - installation of pymchelper with all feature via pip using `pip install "pymchelper[full]"`
#  - installation of requirements.txt when working with cloned source code: `pip install -r requirements.txt`
EXTRAS_REQUIRE = {
    'image': ['matplotlib'],
    'excel': ['xlwt'],
    'hdf': ['h5py'],
    'dicom': [
        "pydicom>=2.3.1 ; python_version == '3.11'",
        "pydicom ; python_version < '3.11'"
    ],
    'pytrip': [
        'scipy',
        "pytrip98>=3.8.0 ; python_version >= '3.11'",
        "pytrip98>=3.6.1 ; python_version >= '3.10' and python_version < '3.11'",
        "pytrip98 ; python_version >= '3.5' and python_version < '3.10'"
    ]
}

# inspired by https://github.com/pyimgui/pyimgui/blob/master/setup.py
# construct special 'full' extra that adds requirements for all built-in
# backend integrations and additional extra features.
EXTRAS_REQUIRE['full'] = list(set(chain(*EXTRAS_REQUIRE.values())))
EXTRAS_REQUIRE['full'].extend(["hipsterplot", "bashplotlib"])  # these are needed by verbose inspect tool

# here is table with corresponding numpy versions, and supported python and OS versions
# it is based on inspection of https://pypi.org/project/numpy/
# |---------------------------------------------------|
# | numpy version | python versions |    OS support   |
# |---------------------------------------------------|
# |     1.23.3    |    3.8 - 3.11   | linux, mac, win |
# | 1.22 - 1.23.2 |    3.8 - 3.10   | linux, mac, win |
# |      1.21     |    3.7 - 3.10   | linux, mac, win |
# |      1.20     |    3.7 - 3.9    | linux, mac, win |
# |      1.19     |    3.6 - 3.8    | linux, mac, win |
# |      1.18     |    3.5 - 3.8    | linux, mac, win |
# |      1.17     |    3.5 - 3.7    | linux, mac, win |
# |      1.16     | 2.7,  3.5 - 3.7 | linux, mac, win |
# |      1.15     | 2.7,  3.4 - 3.7 | linux, mac, win |
# |      1.14     | 2.7,  3.4 - 3.6 | linux, mac, win |
# |      1.13     | 2.7,  3.4 - 3.6 | linux, mac, win |
# |      1.12     | 2.7,  3.4 - 3.6 | linux, mac, win |
# |      1.11     | 2.7,  3.4 - 3.5 | linux, mac, win |
# |      1.10     | 2.7,  3.3 - 3.5 |      linux      |
# |       1.9     | 2.7,  3.3 - 3.5 |      linux      |
# |---------------------------------------------------|
# see https://www.python.org/dev/peps/pep-0508/ for language specification
install_requires = [
    "numpy>=1.23.3 ; python_version == '3.11'",
    "numpy>=1.21 ; python_version == '3.10'",
    "numpy>=1.20 ; python_version == '3.9'",
    "numpy>=1.18 ; python_version == '3.8'",
]

setuptools.setup(
    name='pymchelper',
    version=git_version(),
    packages=setuptools.find_packages(where='.', exclude=("tests", "tests.*", "examples")),
    url='https://github.com/DataMedSci/pymchelper',
    license='MIT',
    author='pymchelper team',
    author_email='leszek.grzanka@gmail.com',
    description='Python toolkit for SHIELD-HIT12A and FLUKA',
    long_description=readme + '\n',
    long_description_content_type='text/markdown',
    classifiers=[
        # How mature is this project? Common values are
        'Development Status :: 5 - Production/Stable',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Scientific/Engineering :: Physics',

        # OS and env
        'Environment :: Console',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    entry_points={
        'console_scripts': [
            'convertmc=pymchelper.run:main',
            'runmc=pymchelper.utils.runmc:main',
            'mcscripter=pymchelper.utils.mcscripter:main',
            'plan2sobp=pymchelper.utils.radiotherapy.plan:main',
        ],
    },
    package_data={'pymchelper': ['flair/db/*', 'VERSION']},
    install_requires=install_requires,
    extras_require=EXTRAS_REQUIRE,
    python_requires='>=3.8',
)

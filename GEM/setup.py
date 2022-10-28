import os

from setuptools import find_packages, setup

VERSION = 1.0

def parse_requirements(file):
    required_packages = []
    with open(os.path.join(os.path.dirname(__file__), file)) as req_file:
        for line in req_file:
            if "/" not in line:
                required_packages.append(line.strip())
    return required_packages


setup(
    name="gem-example",
    python_requires=">=3.9",
    version=VERSION,
    description="eo-grow example for GEM project, using the GEM framework and services",
    author="Sinergise EO research team",
    author_email="eoresearch@sinergise.com",
    packages=find_packages(),
    include_package_data=True,
    install_requires=parse_requirements("requirements.txt"),
    zip_safe=False,
)

import os

from setuptools import find_packages, setup


def parse_requirements(file):
    required_packages = []
    with open(os.path.join(os.path.dirname(__file__), file)) as req_file:
        for line in req_file:
            if "/" not in line:
                required_packages.append(line.strip())
    return required_packages


def get_version():
    for line in open(os.path.join(os.path.dirname(__file__), "example_package", "__init__.py")):
        if line.find("__version__") >= 0:
            version = line.split("=")[1].strip()
            return version.strip('"').strip("'")


setup(
    name="example-package",
    python_requires=">=3.8",
    version=get_version(),
    description="eo-grow example for GEM project, using the GEM framework and services",
    author="Sinergise EO research team",
    author_email="eoresearch@sinergise.com",
    packages=find_packages(),
    include_package_data=True,
    install_requires=parse_requirements("requirements.txt"),
    zip_safe=False,
)

from setuptools import setup, find_packages

setup(
    name="raspicam",
    version='1.0',
    packages=find_packages(),
    install_requires=[
        'gouge',
        'config_resolver',
    ],
    requires=[
        'gouge',
        'config_resolver',
    ],
    provides=['raspicam'],
    include_package_data=True,
    author="Michel Albert",
    author_email="michel@albert.lu",
    description="Simple Python motion detection thing",
    license="MIT",
    url="https://github.com/exhuma/raspicam",
)

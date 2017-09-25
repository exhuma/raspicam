from setuptools import setup, find_packages

version = open('raspicam/version.txt').read().strip()

setup(
    name="raspicam",
    version=version,
    packages=find_packages(),
    install_requires=[
        'config_resolver',
        'flask',
        'gouge',
        'numpy',
        'pytesseract',
        'blessings',
    ],
    requires=[
        'config_resolver',
        'flask',
        'gouge',
        'numpy',
        'pytesseract',
        'blessings',
    ],
    entry_points={
        'console_scripts': [
            'raspicam=raspicam.main:main'
        ]
    },
    provides=['raspicam'],
    include_package_data=True,
    author="Michel Albert",
    author_email="michel@albert.lu",
    description="Simple Python motion detection thing",
    license="MIT",
    url="https://github.com/exhuma/raspicam",
)

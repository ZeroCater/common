import os

from setuptools import setup


def get_packages(package):
    """
    Return root package and all sub-packages.
    """
    return [dirpath
            for dirpath, dirnames, filenames in os.walk(package)
            if os.path.exists(os.path.join(dirpath, '__init__.py'))]

setup(
    name='zc_common',
    version='0.1.3',
    description="A collection of Python utils",
    long_description='',
    keywords='zerocater python util',
    author='ZeroCater',
    author_email='tech@zerocater.com',
    url='https://github.com/ZeroCater/zc_common',
    download_url='https://github.com/ZeroCater/zc_common/tarball/0.1.3',
    license='MIT',
    packages=get_packages('zc_common'),
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP",
    ]
)

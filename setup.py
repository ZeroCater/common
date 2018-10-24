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
    version='0.4.12',
    description="Shared code for ZeroCater microservices",
    long_description='',
    keywords='zerocater python util',
    author='ZeroCater',
    author_email='tech@zerocater.com',
    url='https://github.com/ZeroCater/zc_common',
    download_url='https://github.com/ZeroCater/zc_common/tarball/0.4.12',
    license='MIT',
    packages=get_packages('zc_common'),
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP",
    ],
    install_requires=[
        'python-dateutil>=2.6.1,<2.6.2',
        'ujson>=1.35,<1.36',
        'PyJWT>=1.6.4',
        'inflection>=0.3.1'
    ]
)

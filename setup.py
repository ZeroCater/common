from setuptools import setup

setup(name='zc_common',
      version='0.0.3',
      description="A collection of Python utils",
      long_description='',
      keywords='zerocater python util',
      author='ZeroCater',
      author_email='tech@zerocater.com',
      url='https://github.com/ZeroCater/zc_common',
      download_url='https://github.com/ZeroCater/zc_common/tarball/0.0.2',
      license='MIT',
      packages=[
          'zc_common',
      ],
      install_requires=[
          'django',
          'djangorestframework>=3.1.0',
          'djangorestframework-jsonapi>=2.0.0b2'
      ],
      classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP",
      ]
  )

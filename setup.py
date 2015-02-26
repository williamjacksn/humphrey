import humphrey

from setuptools import find_packages, setup

setup(
    name='humphrey',
    version=humphrey.__version__,
    description='An IRC client with no dependencies',
    long_description='',
    url='https://github.com/williamjacksn/humphrey',
    author='William Jackson',
    author_email='william@subtlecoolness.com',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.4'
    ],
    keywords='irc',
    packages=find_packages()
)

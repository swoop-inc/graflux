from setuptools import setup, find_packages
import sys

convert_2_to_3 = {}
if sys.version_info >= (3,):
    convert_2_to_3['use_2to3'] = True

setup(
    name='graflux',
    version='0.3.0',
    url='https://github.com/swoop-inc/graflux',
    license='mit',
    author='Mark Bell',
    author_email='mark@swoop.com',
    description='Influxdb storage adaptor for Graphite-API',
    long_description='',
    packages=find_packages('.'),
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    classifiers=(),
    install_requires=['graphite_api', 'influxdb>=2.12.0'],
    extras_require={},
    **convert_2_to_3
)

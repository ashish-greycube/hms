# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open('requirements.txt') as f:
	install_requires = f.read().strip().split('\n')

# get version from __version__ variable in hms/__init__.py
from hms import __version__ as version

setup(
	name='hms',
	version=version,
	description='Manage hotel operations: Booking, Pricing, Inventory, Customer Relations, Financials, Point of Sale',
	author='GreyCube Technologies',
	author_email='admin@greycube.in',
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)

import setuptools
 
with open("README.md", "r") as fh:
    long_description = fh.read()
 
setuptools.setup(
    name='py_apps',  
    version='0.0.1',
    author="siwinter",
#    author_email="andrew@ao.gl",
    description="A virtual rainsensor",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/siwinter/py_apps",
    packages=["py_apps"],
    entry_points = {
        "console_scripts": ['webInfo = py_apps.webInfo:main',
        'rainRadar = py_apps.rainradar:main',
        'myApp = myApp:main',
        'petrolPrice = py_apps.petrolPrice:main'
        'vpnCtrl = py_apps.vpnCtrl:main',
        'serialBridge = py_apps.serial2mqtt:main']
    },
    install_requires=[
	    	'aiohttp',
	    	'aiomqtt',
            'aioserial',
            'aiosignal',
            'attrs',
            'frozenlist',
            'future',
            'idna',
            'iso8601',
            'multidict',
    		'paho-mqtt',
	    	'pyserial',
            'PyYAML',
            'serial',
            'yarl'],

    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent" ]
)

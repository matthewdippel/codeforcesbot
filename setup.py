from setuptools import setup

setup(
        name="cfbot",
        version='0.0.1',
        description="Discord bot for retrieving Codeforces ranks",
        author="mdippel",
        email="mdippel@ccs.neu.edu",
        license='GPL-3.0',
        packages=['cfbot'],
        scripts=['bin/cfbot'],
        zip_safe=False,
        install_requires=['discord.py',
                          'requests',
                          'docopt']
        )

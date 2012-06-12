============
bootstrap.py
============

Self-update bootstrap script for prepare environment for Python project.

Installation
============

Copy ``bootstrap.py`` to your Python project.

Usage
=====

::

    $ python bootstrap.py --help
    Usage: bootstrap.py [options]

    Options:
      -h, --help            show this help message and exit
      -p PRE_REQUIREMENTS, --pre-requirements=PRE_REQUIREMENTS
                            File with list of pre-reqs
      -E VIRTUALENV, --virtualenv=VIRTUALENV
                            Path to virtualenv to use
      -P INTERPRETER, --python=INTERPRETER
                            Path to Python Interpreter to use
      -s, --no-site         Don't use global site-packages on create virtualenv
      -u, --upgrade         Upgrade packages
      -b, --enable-bootstrap-update
                            Enable self-update of bootstrap script
      -U URL, --bootstrap-url=URL
                            URL to use for updating bootstrap script. By default:
                            'https://raw.github.com/jellycrystal/bootstrap/master/
                            bootstrap.py'
      -c PATH, --config=PATH
                            Path to config file to use. By default:
                            'bootstrap.cfg'


How it works
============

* First of all, script check project pre requirements
* Then create virtual environment if necessary
* Then install pip requirements to virtual environment
* And finally pass control to doit

.. warning:: At current time not all available options covered in this README.
   More information coming soon.

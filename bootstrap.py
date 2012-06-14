#!/usr/bin/env python
"""
Bootstrap script preparing environment for Python project
"""

import copy
import optparse
import os
import subprocess
import sys

from ConfigParser import Error as ConfigParserError, SafeConfigParser
from distutils.util import strtobool

try:
    from urllib2 import Request, urlopen, HTTPError, URLError
except ImportError:
    from urllib.request import Request, urlopen, \
                                HTTPError, URLError


BOOTSTRAP_MOD = 'bootstrap'
BOOTSTRAP_ETAG = '._' + BOOTSTRAP_MOD + '.etag'
BOOTSTRAP_PY = BOOTSTRAP_MOD + '.py'
BOOTSTRAP_URL = \
    'https://raw.github.com/jellycrystal/bootstrap/master/bootstrap.py'
DEFAULT_PRE_REQS = ['virtualenv']


def _err(msg):
    sys.stderr.write("Error: %s\n" % (msg,))
    sys.exit(1)


def _warn(msg):
    sys.stderr.write("Warn: %s\n" % (msg,))


def get_pre_reqs(pre_req_txt):
    """Getting the list of pre-required executables"""
    try:
        pre_reqs = open(pre_req_txt).readlines()
    except IOError:
        _warn("Couldn't find pre-reqs file: %s, use default pre-reqs" % pre_req_txt)
        # There are no pre-reqs yet.
        pre_reqs = DEFAULT_PRE_REQS
    for pre_req in pre_reqs:
        pre_req = pre_req.strip()
        # Skip empty lines and comments
        if not pre_req or pre_req.startswith('#'):
            continue
        yield pre_req


def check_pre_req(pre_req):
    """Check pre-requirements"""
    if subprocess.call(['which', pre_req],
                       stderr=subprocess.PIPE, stdout=subprocess.PIPE) == 1:
        _err("Couldn't find '%s' in PATH" % pre_req)


def provide_virtualenv(ve_target, no_site=True, interpreter=None, config=None):
    """Provide virtualenv"""
    config = config or {}
    config.update({'distribute': True})

    if no_site:
        config.update({'no_site': True})

    if interpreter:
        config.update({'python': interpreter})

    args = config_to_args(config)
    if not os.path.exists(ve_target):
        subprocess.call(['virtualenv'] + args + [ve_target])


def install_pip_requirements(ve_target, upgrade=False, config=None):
    """Install required Python packages into virtualenv"""
    # Initial vars
    base_config = config or {}
    pip_path = os.path.join(ve_target, 'bin', 'pip')
    prefix = 'py'
    req_name = 'requirements'
    version = sys.version_info

    # Update prefix and version if PyPy used
    if hasattr(sys, "pypy_version_info"):
        prefix = "pypy"
        version = sys.pypy_version_info
    elif isinstance(version, tuple):
        major, minor, micro, _, _ = version
    else:
        major = version.major
        minor = version.minor
        micro = version.micro

    # Supported requirements filenames
    extensions = [
        "generic",
        "txt",
        "{0}_{1}".format(prefix, major),
        "{0}_{1}{2}".format(prefix, major, minor),
        "{0}_{1}{2}{3}".format(prefix, major, minor, micro)
    ]

    # Cycle all supported requirements filenames and if file exists install
    # those requirements to virtual environment
    for ext in extensions:
        filename = "{0}.{1}".format(req_name, ext)

        if os.path.exists(filename):
            sys.stderr.write("Installing {0}...".format(filename))

            config = base_config.copy()
            config.update({'requirement': filename})

            if upgrade:
                config.update({'upgrade': True})

            args = config_to_args(config)
            call_args = [pip_path, 'install'] + args

            try:
                if subprocess.call(call_args):
                    _err("Failed to install requirements")
            except OSError:
                _err("Something went wrong during installation "\
                     "requirements: {0}".format(call_args))


def pass_control_to_doit(ve_target, config=None):
    """Pass further control to doit"""
    try:
        import dodo
    except ImportError:
        return

    if hasattr(dodo, 'task_bootstrap'):
        doit = os.path.join(ve_target, 'bin', 'doit')
        subprocess.call([doit, 'bootstrap'])


def do(func, *args, **kwargs):
    """Announce func.__doc__ and run func with provided arguments"""
    doc = getattr(func, '__doc__')
    if doc is None:
        doc = func.__name__
    func_args = ', '.join(str(a) for a in args)
    func_kwargs = ', '.join("%s=%s" % (k, str(kwargs.get(k)))
                            for k in kwargs.keys())
    msg = "%s... %s %s\n" % (doc, func_args, func_kwargs)
    sys.stderr.write(msg)
    return func(*args, **kwargs)


def bootstrap(pre_req_txt, ve_target, no_site=True,
        upgrade=False, interpreter=None, config=None):
    ve_target = os.path.normpath(os.path.abspath(ve_target))
    os.environ['BOOTSTRAP_VIRTUALENV_TARGET'] = ve_target
    for pre_req in do(get_pre_reqs, pre_req_txt):
        do(check_pre_req, pre_req)
    do(provide_virtualenv, ve_target, no_site=no_site, interpreter=interpreter,
       config=config['virtualenv'])
    do(install_pip_requirements, ve_target, upgrade=upgrade,
       config=config['pip'])
    do(pass_control_to_doit, ve_target, config=config['doit'])


def update(**kwargs):
    """
    Self-update bootstrapping script.
    """
    # Idea taken from
    # http://tarekziade.wordpress.com/2011/02/10/a-simple-self-upgrade-build-pattern/
    if not kwargs.pop('enable_bootstrap_update', False):
        kwargs.pop('bootstrap_url')
        return bootstrap(**kwargs)

    bootstrap_url = kwargs.pop('bootstrap_url', BOOTSTRAP_URL)
    headers = {}
    etag = current_etag = None

    # Getting the file age
    if os.path.exists(BOOTSTRAP_ETAG):
        with open(BOOTSTRAP_ETAG) as fh:
            current_etag = fh.read().strip()
            headers['If-None-Match'] = current_etag

    request = Request(bootstrap_url, headers=headers)

    # Checking the last version on server
    try:
        sys.stderr.write("Fetching bootstrap's updates from %s..." %
                         bootstrap_url)
        url = urlopen(request, timeout=5)
        etag = url.headers.get('ETag')
    except HTTPError as e:
        if e.getcode() not in (304, 412):
            raise
        # We're up to date -- 412 precondition failed
        etag = current_etag
        sys.stderr.write("Done. Up to date.\n")
    except URLError:
        # Timeout error
        etag = None
        sys.stderr.write("Fail. Connection error.\n")

    if etag is not None and current_etag != etag:
        sys.stderr.write("Done. New version available.\n")
        # We should update our version
        content = url.read()
        with open(BOOTSTRAP_PY, 'w') as fh:
            fh.write(content)
        with open(BOOTSTRAP_ETAG, 'w') as fh:
            fh.write(etag)
        sys.stderr.write("Bootstrap is updated to %s version.\n" % etag)

    mod = __import__(BOOTSTRAP_MOD)
    mod.bootstrap(**kwargs)


def config_to_args(config):
    """
    Convert config dict to arguments list.
    """
    result = []

    for key, value in config.iteritems():
        print value

        if value is False:
            continue

        key = key.replace('_', '-')

        if value is not True:
            result.append('--{0}={1}'.format(key, str(value)))
        else:
            result.append('--{0}'.format(key))

    return result


def init_parser():
    """
    Initialize ``OptionParser`` instance to read command line arguments.
    """
    parser = optparse.OptionParser()

    parser.add_option("-p", "--pre-requirements", dest="pre_requirements",
                      default="pre-reqs.txt", action="store", type="string",
                      help="File with list of pre-reqs")
    parser.add_option("-E", "--virtualenv", dest="virtualenv",
                      default='ve', action="store", type="string",
                      help="Path to virtualenv to use")
    parser.add_option("-P", "--python", dest="interpreter",
                      default=None, action="store", type="string",
                      help="Path to Python Interpreter to use")
    parser.add_option("-s", "--no-site", dest="no_site",
                      default=False, action="store_true",
                      help="Don't use global site-packages on create " \
                           "virtualenv")
    parser.add_option("-u", "--upgrade", dest="upgrade",
                      default=False, action="store_true",
                      help="Upgrade packages")
    parser.add_option("-b", "--enable-bootstrap-update",
                      dest="enable_bootstrap_update", default=False,
                      action="store_true",
                      help="Disable self-update of bootstrap script")
    parser.add_option("-U", "--bootstrap-url", dest="bootstrap_url",
                      default=BOOTSTRAP_URL, metavar="URL",
                      help="URL to use for updating bootstrap script. By " \
                           "default: '%s'" % BOOTSTRAP_URL)
    parser.add_option("-c", "--config", dest="config", default="bootstrap.cfg",
                      metavar="PATH",
                      help="Path to config file to use. By default: " \
                           "'bootstrap.cfg'")

    return parser


def override_bootstrap_options(options, config):
    """
    Override default options from command line with values from config file.
    """
    for key, value in config.iteritems():
        if hasattr(options, key):
            setattr(options, key, value)
    return options


def read_config(filename):
    """
    Read config from ``filename``. It's possible to use ``~`` and environment
    variables in filename. They will be processed with ``expanduser`` and
    ``expandvar`` methods of ``os.path`` library.

    The main purpose of config file is to give user ability to fully configure
    ``virtualenv``, ``pip``, ``doit`` and ``bootstrap`` itself. By default,
    script searches ``bootstrap.cfg`` in current working directory. Such behavior
    can be changed passing ``-c PATH`` option to ``bootstrap.py`` sys args.

    The ``bootstrap.cfg`` file should use format supported by standard
    Python's ``ConfigParser`` library. More information is available at:
    `http://docs.python.org/library/configparser.html`_.

    Example of config file::

        [bootstrap]
        enable_bootstrap_update = True
        no_site = True
        pre_requirements = pre-requirements.txt
        upgrade = False

        [virtualenv]
        distribute = True
        never_download = True

        [pip]
        download_cache = /var/cache/pip
        use_mirrors = True

    .. note:: If config option name contains underscore it will be replaced
       with a dash, e.g. ``enable_bootstrap_update`` becomes
       ``enable-bootstrap-update``.

    .. note:: True/False and integer values are auto detected. All other
       values are returned as strings.

    If no config file is found, default options will be used.

    Function returns ``dict`` instance as a result, where sections are
    keys and section values are dicts, like::

        {
            'bootstrap': {
                'enable_bootstrap_update': True,
                'no_site': True,
                'pre_requirements': 'pre-requirements.txt',
                'upgrade': False
            },
            'virtualenv': {
                'distribute': True,
                'never_download': True
            },
            'pip': {
                'download_cache': '/var/cache/pip',
                'use_mirrors': True
            }
        }

    """
    filename = os.path.expanduser(os.path.expandvars(filename))

    sections = ('bootstrap', 'doit', 'pip', 'virtualenv')
    default = dict([(section, {}) for section in sections])

    if not os.path.isfile(filename):
        return copy.deepcopy(default)

    config = SafeConfigParser()

    try:
        config.read(filename)
    except ConfigParserError:
        _warn('Cannot parse %r as valid config file.' % filename)
        return copy.deepcopy(default)

    data = copy.deepcopy(default)

    for section in sections:
        try:
            items = config.items(section)
        except ConfigParserError:
            continue

        data[section] = {}

        for key, value in items:
            try:
                value = bool(strtobool(value))
            except ValueError:
                if value.isdigit():
                    value = int(value)

            data[section][key] = value

    return data


def main(args):
    parser = init_parser()
    options, args = parser.parse_args(args)

    config = read_config(options.config)
    options = override_bootstrap_options(options, config['bootstrap'])

    update(
        enable_bootstrap_update=options.enable_bootstrap_update,
        bootstrap_url=options.bootstrap_url,
        pre_req_txt=options.pre_requirements,
        ve_target=options.virtualenv,
        no_site=options.no_site,
        interpreter=options.interpreter,
        upgrade=options.upgrade,
        config=config
    )


if __name__ == '__main__':
    main(sys.argv)

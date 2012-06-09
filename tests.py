#!/usr/bin/env python

import os
import shutil
import sys
import unittest

from bootstrap import config_to_args, init_parser, main, \
    override_bootstrap_options, read_config


VERSION = sys.version_info
TEST_ARGS = {
    'bootstrap': (
        ('--disable-bootstrap-update', None), ('--no-site', None),
        ('--pre-requirements', 'pre-requirements.txt')
    ),
    'virtualenv': (
        ('--distribute', None), ('--never-download', None),
        ('--verbosity', '2')
    ),
    'pip': (
        ('--download-cache', '/var/cache/pip'), ('--use-mirrors', None),
        ('--verbosity', '3')
    ),
    'doit': (),
}
TEST_CONFIG = {
    'bootstrap': {
        'disable_bootstrap_update': True,
        'no_site': True,
        'pre_requirements': 'pre-requirements.txt',
        'upgrade': False
    },
    'virtualenv': {
        'distribute': True,
        'never_download': True,
        'verbosity': 2
    },
    'pip': {
        'download_cache': '/var/cache/pip',
        'use_mirrors': True,
        'verbosity': 3
    },
    'doit': {},
}
TEST_EMPTY_CONFIG = dict([(key, {}) for key, _ in TEST_CONFIG.items()])
TEST_TEXT_CONFIG = """[bootstrap]
disable_bootstrap_update = True
no_site = True
pre_requirements = pre-requirements.txt
upgrade = False

[virtualenv]
distribute = True
never_download = True
verbosity = 2

[pip]
download_cache = /var/cache/pip
use_mirrors = True
verbosity = 3
"""


class TestCase(unittest.TestCase):

    def create_file(self, filename, content):
        handler = open(self.rel(filename), 'w+')
        handler.write(content)
        handler.close()

    def rel(self, *parts):
        return os.path.join(os.path.dirname(__file__), *parts)

    def safe_remove(self, mixed, verbose=True):
        mixed = self.rel(mixed)
        func = shutil.rmtree if os.path.isdir(mixed) else os.unlink

        try:
            func(mixed)
        except (IOError, OSError), e:
            if verbose:
                print('Cannot remove %r cause of %s' % (mixed, e))


class TestBootstrap(TestCase):

    def setUp(self):
        self.create_file('pre-requirements.txt', 'python\n')
        self.create_file('requirements.txt', 'unittest2==0.5.1\n')

    def tearDown(self):
        self.safe_remove('pre-requirements.txt')
        self.safe_remove('requirements.txt')
        self.safe_remove('ve')
        self.safe_remove(
            'requirements.py_%d%d' % (VERSION.major, VERSION.minor), False
        )

    def test_main(self):
        activate = self.rel('ve', 'bin', 'activate')
        bin = self.rel('ve', 'bin')
        env = self.rel('ve')
        unittest2 = self.rel(
            've', 'lib', 'python%d.%d' % (VERSION.major, VERSION.minor),
            'site-packages', 'unittest2'
        )

        self.assertFalse(os.path.isdir(self.rel('ve')))

        main(['-b', '-p', 'pre-requirements.txt'])

        self.assertTrue(os.path.isdir(env), env)
        self.assertTrue(os.path.isdir(bin), bin)
        self.assertTrue(os.path.isfile(activate), activate)
        self.assertTrue(os.path.isdir(unittest2), unittest2)

    def test_main_python(self):
        activate = self.rel('ve', 'bin', 'activate')
        bin = self.rel('ve', 'bin')
        env = self.rel('ve')
        minimock = self.rel(
            've', 'lib', 'python%d.%d' % (VERSION.major, VERSION.minor),
            'site-packages', 'MiniMock.py'
        )
        unittest2 = self.rel(
            've', 'lib', 'python%d.%d' % (VERSION.major, VERSION.minor),
            'site-packages', 'unittest2'
        )

        self.assertFalse(os.path.isdir(env), env)
        self.create_file(
            'requirements.py_%d%d' % (VERSION.major, VERSION.minor),
            'MiniMock==1.2.7\n'
        )

        main(['-b', '-p', 'pre-requirements.txt'])

        self.assertTrue(os.path.isdir(env), env)
        self.assertTrue(os.path.isdir(bin), bin)
        self.assertTrue(os.path.isfile(activate), activate)
        self.assertTrue(os.path.isfile(minimock), minimock)
        self.assertTrue(os.path.isdir(unittest2), unittest2)


class TestConfig(TestCase):

    def setUp(self):
        self.create_file('bootstrap.cfg', TEST_TEXT_CONFIG)

    def tearDown(self):
        self.safe_remove('bootstrap.cfg')

    def test_config_to_args(self):
        for key, data in TEST_CONFIG.iteritems():
            args = config_to_args(data)
            check = TEST_ARGS[key]

            self.assertTrue(isinstance(args, list), type(args))

            for key, value in check:
                index = args.index(key)

                if value is not None:
                    self.assertEqual(value, args[index + 1])

    def test_init_parser(self):
        data = (
            ('-h', '--help', None),
            ('-p', '--pre-requirements', 'pre_requirements'),
            ('-E', '--virtualenv', 'virtualenv'),
            ('-P', '--python', 'interpreter'),
            ('-s', '--no-site', 'no_site'),
            ('-u', '--upgrade', 'upgrade'),
            ('-b', '--disable-bootstrap-update', 'disable_bootstrap_update'),
            ('-c', '--config', 'config')
        )
        parser = init_parser()

        for i, option in enumerate(parser.option_list):
            short_opt, long_opt, dest = data[i]

            self.assertEqual(option._short_opts[0], short_opt)
            self.assertEqual(option._long_opts[0], long_opt)
            self.assertEqual(option.dest, dest)

    def test_override_bootstrap_options(self):
        parser = init_parser()
        options, args = parser.parse_args(['-u', '-p', 'pre-reqs.txt'])

        config = read_config('bootstrap.cfg')
        options = override_bootstrap_options(options, config['bootstrap'])

        self.assertEqual(options.pre_requirements, 'pre-requirements.txt')
        self.assertFalse(options.upgrade)

    def test_read_config(self):
        config = read_config('bootstrap.cfg')
        self.assertEqual(config, TEST_CONFIG)

        os.environ['PREFIX'] = '.'
        config = read_config('$PREFIX/bootstrap.cfg')
        self.assertEqual(config, TEST_CONFIG)

    def test_read_config_wrong_filename(self):
        config = read_config('does_not_exist.cfg')
        self.assertEqual(config, TEST_EMPTY_CONFIG)


if __name__ == '__main__':
    unittest.main()

import operator
import unittest

from mockio import mockio

from nginxparser import NginxParser, load,  dumps


first = operator.itemgetter(0)


class TestNginxParser(unittest.TestCase):
    files = {
        "/etc/nginx/sites-enabled/foo.conf": '''
        user www-data;
        server {
            listen   80;
            server_name foo.com;
            root /home/ubuntu/sites/foo/;

            location /status {
                check_status;
                types {
                    image/jpeg jpg;
                }
            }

            location ~ case_sensitive\.php$ {
                hoge hoge;
            }
            location ~* case_insensitive\.php$ {}
            location = exact_match\.php$ {}
            location ^~ ignore_regex\.php$ {}

        }''',
        "/etc/nginx/sites-enabled/if_condation.conf": '''
        server {
            if ( $request_method !~ ^(GET|POST|HEAD)$ ) {
               return 403;
            }
        }'''
    }

    def test_assignments(self):
        parsed = NginxParser.assignment.parseString('root /test;').asList()
        self.assertEqual(parsed, ['root', '/test'])
        parsed = NginxParser.assignment.parseString('root /test;'
                                                    'foo bar;').asList()
        self.assertEqual(parsed, ['root', '/test'], ['foo', 'bar'])

    def test_blocks(self):
        parsed = NginxParser.assignment.parseString('foo {}').asList()
        self.assertEqual(parsed, ['foo', []])
        parsed = NginxParser.location_block.parseString('location /foo{}').asList()
        self.assertEqual(parsed, ['location', '/foo', []])
        parsed = NginxParser.assignment.parseString('foo { bar foo; }').asList()
        self.assertEqual(parsed, ['foo', [['bar', 'foo']]])

    def test_nested_blocks(self):
        parsed = NginxParser.assignment.parseString('foo { bar {} }').asList()
        self.assertEqual(parsed, ['foo', [['bar', []]]])

    def test_single_quoted_strings(self):
        parsed = NginxParser.script.parseString('''
            include foo.conf;
            header_filter_by_lua '
                return true
            ';
        ''').asList()
        self.assertEqual(parsed, [['include', 'foo.conf'], ['header_filter_by_lua', '\n                return true\n            ']])

    def test_quoted_strings(self):
        parsed = NginxParser.script.parseString('''
    log_by_lua_file log.lua;
    header_filter_by_lua '
        ngx.re.match(ngx.var.host, [=[^[a-zA-Z0-9]{32,255}$]=])
    ';
        ''').asList()
        self.assertEqual(parsed, [['log_by_lua_file', 'log.lua'],
            ['header_filter_by_lua', '\n        ngx.re.match(ngx.var.host, [=[^[a-zA-Z0-9]{32,255}$]=])\n    ']])

    def test_if_block(self):
        parsed = NginxParser.script.parseString('''
	    if ($request_method = 'OPTIONS') {
		return 204;
	    }
        ''').asList()
        self.assertEqual(parsed, [['if', '($request_method = \'OPTIONS\') ',
            [['return', '204']]]])


    def test_dump_as_string(self):
        dumped = dumps([
            ['user', 'www-data'],
            ['server', [
                ['listen', '80'],
                ['server_name', 'foo.com'],
                ['root', '/home/ubuntu/sites/foo/'],
                ['location', '/status', [
                    ['check_status'],
                    ['types', [
                        ['image/jpeg', 'jpg']
                    ]],
                ]]
            ]]])

        self.assertEqual(dumped,
                         'user www-data;\n' +
                         'server {\n' +
                         '    listen 80;\n' +
                         '    server_name foo.com;\n' +
                         '    root /home/ubuntu/sites/foo/;\n' +
                         '    location /status {\n' +
                         '        check_status;\n' +
                         '        types {\n' +
                         '            image/jpeg jpg;\n' +
                         '        }\n' +
                         '    }\n' +
                         '}')

    @mockio(files)
    def test_parse_from_file(self):
        parsed = load(open("/etc/nginx/sites-enabled/foo.conf"))
        self.assertEqual(
            parsed, [
                ['user', 'www-data'],
                ['server', [
                    ['listen', '80'],
                    ['server_name', 'foo.com'],
                    ['root', '/home/ubuntu/sites/foo/'],
                    ['location', '/status ', [
                        ['check_status'],
                        ['types', [['image/jpeg', 'jpg']]],
                    ]],
                    ['location', '~', 'case_sensitive\.php$ ', [
                        ['hoge', 'hoge']]],
                    ['location', '~*', 'case_insensitive\.php$ ', []],
                    ['location', '=', 'exact_match\.php$ ', []],
                    ['location', '^~', 'ignore_regex\.php$ ', []],
                ]]
            ])

    @mockio(files)
    def test_parse_if_condation(self):
        parsed = load(open("/etc/nginx/sites-enabled/if_condation.conf"))
        self.assertEqual(
            parsed, [
                ['server', [
                    ['if', '( $request_method !~ ^(GET|POST|HEAD)$ ) ', [
                        ['return', '403']
                    ]]
                ]]
            ]
        )


if __name__ == '__main__':
    unittest.main()

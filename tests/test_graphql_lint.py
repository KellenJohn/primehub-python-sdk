import ast
import os
import re
import textwrap
from unittest import TestCase

from tests.graphql_formatter import is_formatter_available, format_graphql


class GraphQLQueryFormatChecker(ast.NodeTransformer):

    def __init__(self, testutil: TestCase, filename: str):
        self.testutil = testutil
        self.filename = filename

    def visit_Assign(self, node):

        try:
            n = node.targets[0]
            if not hasattr(n, 'id'):
                return node

            if n.id == 'query':
                first_line_indent = 0
                for line in node.value.s.split('\n'):
                    if line.strip() == '':
                        continue
                    m = re.search(r'^(\s+).*', line)
                    if m:
                        first_line_indent = len(m.group(1))
                        break
                gql = strip_blank_line(node.value.s)
                if has_checkpoint(f'{self.filename}:{n.lineno}', gql):
                    # skip by checkpoint
                    return node

                formatted = textwrap.indent(format_graphql(gql), ' ' * first_line_indent)
                formatted = strip_blank_line(formatted)
                if gql != formatted:
                    print(f'check {self.filename}:{n.lineno}')
                    print(f'please replace the content by this:\n\n>>>>\n{formatted}\n<<<<\n')
                else:
                    save_checkpoint(f'{self.filename}:{n.lineno}', gql)
                self.testutil.assertEqual(gql, formatted)
        except BaseException as e:
            if isinstance(e, AssertionError):
                raise e
            print(type(e), e)

        return node


def strip_blank_line(formatted):
    return '\n'.join([x for x in formatted.split('\n') if x.strip() != ''])


def save_checkpoint(file_loc, content):
    filepath = os.path.join('/tmp', f'._gql_check_{checksum(file_loc)}.{checksum(content)}')
    with open(filepath, 'w') as fh:
        fh.write('')


def has_checkpoint(file_loc, content):
    filepath = os.path.join('/tmp', f'._gql_check_{checksum(file_loc)}.{checksum(content)}')
    return os.path.exists(filepath)


def checksum(content: str):
    import hashlib
    m = hashlib.md5(content.encode())
    return m.hexdigest()


def source_contents():
    project_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '../primehub'))
    for root, dirs, files in os.walk(project_dir):
        for f in files:
            if f.endswith('.py'):
                p = os.path.join(root, f)
                with open(p, 'r') as fh:
                    content = fh.read()
                    yield p, content
        break


class GraphQLLint(TestCase):

    def test_graphql_lint(self):
        if not is_formatter_available():
            print("GRAPHQL FORMATTER NOT AVAILABLE. (please install prettier first)")
            print("SKIP GRAPHQL LINT")
            return

        print("\n---- start to lint graphql ----")
        for filename, c in source_contents():
            node = ast.parse(c)
            GraphQLQueryFormatChecker(self, filename).visit(node)

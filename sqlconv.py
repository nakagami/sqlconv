#!/usr/bin/env python
##############################################################################
# MIT License
#
# Copyright (c) 2024 Hajime Nakagami
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
##############################################################################

import sys
import argparse

from typing import Optional, Sequence, Iterable, TextIO
import sqlparse
from sqlparse.tokens import Comment, Keyword, DDL, DML, Token, Name, Punctuation, String
from sqlparse.sql import Statement
from sqlparse.exceptions import SQLParseError

TokenList = list[Token]

VERSION = (0, 1, 0)
__version__ = '%s.%s.%s' % VERSION


def statement_to_tokens(statement) -> TokenList:
    # skip whitespace and comment
    return [
        t for t in statement.flatten()
        if not (t.is_whitespace or t.ttype in Comment)
    ]


def find_token(tokens: TokenList, match_args: Iterable) -> bool:
    for token in tokens:
        if token.match(*match_args):
            return True
    return False


def match_consume(tokens: TokenList, start: int, match_args: Iterable) -> int:
    if tokens[start].match(*match_args):
        return start + 1
    return start


def unmatch_consume(tokens: TokenList, start: int, match_args: Iterable) -> int:
    if not tokens[start].match(*match_args):
        return start + 1
    return start


def forward_until(tokens: TokenList, start: int, match_args: Iterable) -> int:
    i = start
    while i < len(tokens):
        if tokens[i].match(*match_args):
            return i + 1
    return start


def match_prefix_tokens(tokens: TokenList, start: int, match_args_list: list[Iterable]) -> bool:
    for i, match_args in enumerate(match_args_list):
        if not tokens[i].match(*match_args):
            return False
    return True


def get_inside_parentheses(tokens: TokenList, start: int) -> Optional[tuple[list[TokenList], int]]:
    assert tokens[start].match(Punctuation, "(")
    token_list = []
    count = 1
    i = start
    for j in range(i+1, len(tokens)):
        if tokens[j].match(Punctuation, "("):
            count += 1
            continue
        if tokens[j].match(Punctuation, ")"):
            count -= 1
            if count == 0:
                token_list.append(tokens[i+1:j])
                i = j + 1
                break
        if tokens[j].match(Punctuation, ","):
            token_list.append(tokens[i+1:j])
            i = j
    if count == 0:
        return token_list, i
    raise SQLParseError(f"Parentheses do not match:{tokens}")


class Constraint:
    name: str
    tokens: TokenList


class PrimaryKeyConstraint(Constraint):
    pass


class UniqueConstraint(Constraint):
    pass


class CheckConstraint(Constraint):
    pass


class ForeignKeyConstraint(Constraint):
    column_name: str
    ref_table: str
    ref_column: str


class ColumnDef:
    name: str
    column_type: str
    sub_type: TokenList
    unique: bool
    nullable: bool
    default: TokenList


class TableDef:
    input_type: Optional[str]
    name: TokenList
    columns: list[ColumnDef]
    constraints: list[Constraint]

    def parse_constraint(self, tokens: TokenList, start: int) -> Optional[Constraint]:
        print("parse_constraint()")
        print(tokens[start:])
        return None, start
        # TODO:
        raise NotImplementedError()

    def parse_column(self, tokens: TokenList, start: int) -> tuple[ColumnDef, int]:
        raise NotImplementedError()

    def parse_column_or_constraint(self, tokens: TokenList, start: int) -> tuple[ColumnDef | PrimaryKeyConstraint | UniqueConstraint | ForeignKeyConstraint, int]:
        # TODO:
        print("parse_column_or_constraint()")
        print(tokens[start:])
        raise NotImplementedError()

    def __init__(self, tokens, input_type):
        self.input_type = input_type
        if not match_prefix_tokens(tokens, 0, [(DDL, "CREATE"), (Keyword, "TABLE")]):
            raise SQLParseError(f"Syntax error:{tokens}")
        i = 2
        name = []
        while tokens[i].ttype in (String.Symbol, Name) or tokens[i].match(Punctuation, "."):
            name.append(tokens[i])
            i += 1
        if not tokens[i].match(Punctuation, "("):
            raise SQLParseError(f"Syntax error:{tokens}")
        i += 1

        while not tokens[i].match(Punctuation, ")"):
            column_or_constraint, i = self.parse_column_or_constraint(tokens, i)


class InsertStmt:
    name: TokenList
    columns: list[TokenList]
    values: list[TokenList]

    def __init__(self, tokens, input_type):
        if not match_prefix_tokens(tokens, 0, [(DML, "INSERT"), (Keyword, "INTO")]):
            raise SQLParseError(f"Syntax error:{tokens}")
        i = 2
        name = []
        while tokens[i].ttype in (String.Symbol, Name) or tokens[i].match(Punctuation, "."):
            name.append(tokens[i])
            i += 1

        if tokens[i].match(Punctuation, "("):
            names, i = get_inside_parentheses(tokens, i)
        else:
            names = []
        assert tokens[i].match(Keyword, "VALUES")
        values, _ = get_inside_parentheses(tokens, i+1)

        self.name = name
        self.names = names
        self.values = values


class SQLWriter:
    def __init__(self, input_type: Optional[str]):
        self.input_type = input_type
        self.output_fileobj = sys.stdout
        self.warning_fileobj = sys.stderr

    def is_quoted(self, s: str) -> bool:
        if s[0] == '`' and s[-1] == '`':
            return True
        if s[0] == '[' and s[-1] == ']':
            return True
        if s[0] == '"' and s[-1] == '"':
            return True
        return False

    def mangle_name(self, name: str) -> str:
        raise NotImplementedError()

    def write_create_table(self, table_def: TableDef):
        raise NotImplementedError()

    def write_insert_stmt(self, insert_stmt: InsertStmt, table_defs: list[TableDef]):
        name = self.mangle_name(str(insert_stmt.name[-1]))
        values = [str(value[-1]) for value in insert_stmt.values]

        if insert_stmt.names:
            names = [self.mangle_name(str(names[-1])) for names in insert_stmt.names]
            print(f"INSERT INTO {name} ({','.join(names)}) VALUES ({','.join(values)});", file=self.output_fileobj)
        else:
            print(f"INSERT INTO {name} VALUES ({','.join(values)});", file=self.output_fileobj)


class MySQLWriter(SQLWriter):
    def mangle_name(self, name: str) -> str:
        if self.is_quoted(name):
            return f'`{name[1:-1]}`'
        return name


class PostgreSQLWriter(SQLWriter):
    def mangle_name(self, name: str) -> str:
        if self.is_quoted(name):
            return f'"{name[1:-1]}"'
        return name


class SQLite3Writer(SQLWriter):
    def mangle_name(self, name: str) -> str:
        if self.is_quoted(name):
            return f'[{name[1:-1]}]'
        return name


def convert(src: TextIO | str, sql_writer: SQLWriter, input_type:  Optional[str]):
    table_defs = []

    for stmt in sqlparse.parse(src):
        # skip whitespace and comment
        tokens = [
            t for t in stmt.flatten()
            if not (t.is_whitespace or t.ttype in Comment)
        ]
        if len(tokens) == 0:
            continue

        if tokens[0].match(DDL, "CREATE") and find_token(tokens, (Keyword, "TABLE")):
            table_def = TableDef(tokens, input_type)
            table_defs.append(table_def)

        elif tokens[0].match(DML, "INSERT"):
            insert_stmt = InsertStmt(tokens, input_type)
            sql_writer.write_insert_stmt(insert_stmt, table_defs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=str, choices=['mysql', 'postgresql', 'sqlite3', 'oracle', 'mssql'])
    parser.add_argument('--output', type=str, choices=['mysql', 'postgresql', 'sqlite3'], default='sqlite3')
    args = parser.parse_args()

    stream: TextIO | str
    if args.input == 'mssql':
        stream = ""
        for s in sys.stdin.readlines():
            if s == "GO\n":
                stream += ";\n"
            elif s[:6] == "INSERT":
                stream += s + ";\n"
            else:
                stream += s
    else:
        stream = sys.stdin
    sql_writer = {
        'mysql': MySQLWriter,
        'postgresql': PostgreSQLWriter,
        'sqlite3': SQLite3Writer,
    }[args.output](args.input)

    convert(stream, sql_writer, args.input)

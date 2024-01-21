import unittest
import sqlconv
from sqlconv import TableDef, InsertStmt
import sqlparse
from sqlparse.tokens import Comment, Keyword, DDL, DML, Token, Name, Punctuation, String, Number


class TestSchema(unittest.TestCase):
    def assertEqualTokens(self, tokens, tuples):
        self.assertEqual([(t.ttype, str(t)) for t in tokens], tuples)

    def assertEqualTokensList(self, tokens_list, tuples_list):
        self.assertEqual(len(tokens_list), len(tuples_list))
        for i in range(len(tokens_list)):
            self.assertEqualTokens(tokens_list[i], tuples_list[i])

    def test_parse_create_table(self):
        src = """
            CREATE TABLE child (
                id INT,
                parent_id INT,
                name VARCHAR(20),
                amount INT NULL DEFAULT 1 (+1) UNIQE,
                weight DECIMAL(10, 2),
                PRIMARY KEY (id),
                UNIQUE KEY (parent_id),
                FOREIGN KEY (parent_id)
                    REFERENCES parent(id)
                    ON DELETE CASCADE
            ) ENGINE=INNODB;
        """
        tokens = sqlconv.statement_to_tokens(sqlparse.parse(src)[0])
        self.assertTrue(sqlconv.match_prefix_tokens(tokens, 0, [(DDL, "CREATE"), (Keyword, "TABLE")]))
        table_def = TableDef(tokens, None)

        src = """
            CREATE TABLE child (
                id INT NOT NULL,
                parent_id INT,
                name VARCHAR(20) DEFAULT 'abc',
                amount INT NULL DEFAULT 1 +1,
                weight DECIMAL(10, 2),
                CONSTRAINT `pk_name` PRIMARY KEY (id),
                CONSTRAINT `uk_aount` UNIQUE KEY (amount),
                CONSTRAINT `fk_name` FOREIGN KEY (parent_id)
                    REFERENCES parent(id)
                    ON DELETE CASCADE
            ) ENGINE=INNODB;
        """
        tokens = sqlconv.statement_to_tokens(sqlparse.parse(src)[0])
        self.assertTrue(sqlconv.match_prefix_tokens(tokens, 0, [(DDL, "CREATE"), (Keyword, "TABLE")]))
        table_def = TableDef(tokens, None)

    def test_parse_insert(self):

        src = "INSERT INTO `Foo`.[Bar] (a, bb, ccc, dddd) VALUES ('abc', N'abc', 2, 3.0);"
        expected_names = [
            [(Name, "a")],
            [(Name, "bb")],
            [(Name, "ccc")],
            [(Name, "dddd")],
        ]
        expected_values = [
            [(String.Single, "'abc'")],
            [(Name, "N"), (String.Single, "'abc'")],
            [(Number.Integer, "2")],
            [(Number.Float, "3.0")],
        ]
        tokens = sqlconv.statement_to_tokens(sqlparse.parse(src)[0])
        self.assertTrue(sqlconv.match_prefix_tokens(tokens, 0, [(DML, "INSERT"), (Keyword, "INTO")]))

        names, next_i = sqlconv.get_inside_parentheses(tokens, 5)
        self.assertEqualTokensList(names, expected_names)
        self.assertEqual(next_i, 14)

        values, next_i = sqlconv.get_inside_parentheses(tokens, 15)
        self.assertEqualTokensList(values, expected_values)
        self.assertEqual(next_i, 25)

        insert_stmt = InsertStmt(tokens, None)
        self.assertEqualTokensList(insert_stmt.names, expected_names)
        self.assertEqualTokensList(insert_stmt.values, expected_values)

        src = "INSERT INTO foo VALUES ('abc', 2, 3.0);"
        expected_names = []
        expected_values = [
            [(String.Single, "'abc'")],
            [(Number.Integer, "2")],
            [(Number.Float, "3.0")],
        ]
        tokens = sqlconv.statement_to_tokens(sqlparse.parse(src)[0])
        self.assertTrue(sqlconv.match_prefix_tokens(tokens, 0, [(DML, "INSERT"), (Keyword, "INTO")]))

        values, next_i = sqlconv.get_inside_parentheses(tokens, 4)
        self.assertEqualTokensList(values, expected_values)
        self.assertEqual(next_i, 11)

        insert_stmt = InsertStmt(tokens, None)
        self.assertEqualTokensList(insert_stmt.names, expected_names)
        self.assertEqualTokensList(insert_stmt.values, expected_values)

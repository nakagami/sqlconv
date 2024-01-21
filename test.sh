#!/bin/sh
echo 'mysql'
cat chinook-database/ChinookDatabase/DataSources/Chinook_MySql_AutoIncrementPKs.sql | ./sqlconv.py
echo 'postgresql'
iconv -f iso-8859-1 -t utf8 chinook-database/ChinookDatabase/DataSources/Chinook_PostgreSql.sql | ./sqlconv.py
echo 'oracle'
cat chinook-database/ChinookDatabase/DataSources/Chinook_Oracle.sql | ./sqlconv.py
echo 'SQLServer'
cat chinook-database/ChinookDatabase/DataSources/Chinook_SqlServerCompact.sqlce | ./sqlconv.py
echo 'Db2'
iconv -f iso-8859-1 -t utf8 chinook-database/ChinookDatabase/DataSources/Chinook_Db2.sql | ./sqlconv.py
echo 'SQLite'
cat chinook-database/ChinookDatabase/DataSources/Chinook_Sqlite_AutoIncrementPKs.sql | ./sqlconv.py

#!/usr/bin/env python
#coding:utf-8

'''
Quelle: GGR Verkehrsmodell\extractiontools
'''

import psycopg2
from psycopg2.extras import NamedTupleConnection, DictCursor
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from collections import OrderedDict

from types import MethodType
import os

import logging
logger = logging.getLogger()


class Login(object):
    """
    Login-Object with the Database credentials
    """
    def __init__(self,
                 host='localhost',
                 port=5432,
                 user='postgres',
                 password='',
                 db='',
                 ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.db = db

    def __repr__(self):
        """
        """
        msg = 'host={h}, port={p}, user={U}, password={pw}, db={db}'
        return msg.format(h=self.host, p=self.port, U=self.user,
                          pw=self.password, db=self.db)


class Connection(object):
    """
    Connection object
    """
    def __init__(self, login=None):
        if login is None:
            login = Login()
        self.login = login

    def __enter__(self):
        login = self.login
        conn = psycopg2.connect(host=login.host,
                              user=login.user,
                              password=login.password,
                              port=login.port,
                              database=login.db,
                              connection_factory=NamedTupleConnection,
                              sslmode='prefer')
        self.conn = conn
        self.conn.get_dict_cursor = self.get_dict_cursor
        self.conn.get_column_dict = self.get_column_dict
        self.set_copy_command_format()
        self.set_vacuum_analyze_command()
        return conn

    def __exit__(self, t, value, traceback):
        self.conn.close()

    def set_copy_command_format(self):
        """
        sets the csv-format
        """
        data_format = 'CSV'
        quote = '"'
        delimiter = ','
        strWith = '''WITH (
        FORMAT {data_format},
        DELIMITER '{delimiter}',
        QUOTE '"',
        HEADER);
        '''.format(data_format=data_format, quote=quote,
                                      delimiter=delimiter)
        self.conn.copy_sql = '''COPY "{tn}" TO STDOUT ''' + strWith

    def set_vacuum_analyze_command(self):
        """
        run vacuum analze on a table with the according transaction isolation
        """
        def vacuum_analyze(self, table):
            old_isolation_level = self.isolation_level
            self.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = self.cursor()
            cursor.execute('VACUUM ANALYZE {table};'.format(table=table))
            self.set_isolation_level(old_isolation_level)

        self.conn.vacuum_analyze = MethodType(vacuum_analyze,
                                              self.conn,
                                              self.conn.__class__)

    def get_dict_cursor(self):
        return self.conn.cursor(cursor_factory=DictCursor)

    def get_columns(self, tablename):
        """
        Return a tuple of columns of a table

        Parameters
        ----------
        tablename : str
            the tablename or schema.tablename to query

        Returns
        -------
            tuple of Column objects
        """
        cur = self.get_dict_cursor()
        sql = 'SELECT * FROM {} LIMIT 0;'.format(tablename)
        cur.execute(sql)
        descr = cur.description
        return descr

    def get_column_dict(self, tablename, schema=None):
        """
        Return a tuple of column names of a table

        Parameters
        ----------
        tablename : str
            the tablename or schema.tablename to query

        schema : str, optional
            the schemaname

        Returns
        -------
        cols : Ordered Dict of the columns
        """
        if schema is not None:
            table = '{s}.{t}'.format(s=schema, t=tablename)
        else:
            table = tablename
        descr = self.get_columns(table)
        return OrderedDict(((d.name, d) for d in descr))


class DBConnection(object):
    def __init__(self, login):
        self.login = login

    def fetch(self, sql):
        with Connection(login=self.login) as conn:
            self.conn = conn
            cursor = self.conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
        return rows

    def copy_expert(self, sql, fileobject):
        with Connection(login=self.login) as conn:
            self.conn = conn
            cursor = self.conn.cursor()
            cursor.copy_expert(sql, fileobject)

    def execute(self, sql):
        with Connection(login=self.login) as conn:
            self.conn = conn
            cursor = self.conn.cursor()
            try:
                cursor.execute(sql)
            except psycopg2.ProgrammingError as e:
                raise psycopg2.ProgrammingError(e.message)
            conn.commit()

# -*- coding: utf-8 -*-
BASE_SCENARIO_ID = 1

from datetime import datetime

def get_values(table, columns, db_conn, schema='public', where=''):
    sql = """
    SELECT {columns}
    FROM {schema}.{table}
    """
    if where:
        sql += ' WHERE ' + where
    values = db_conn.fetch(sql.format(
        columns=u','.join(['"{}"'.format(c) for c in columns]),
        table=table, schema=schema))
    return values

def update_erreichbarkeiten(tag, db_conn, szenario_id, where=''):
    table = 'matview_err_' + tag
    ein_schema='einrichtungen'
    err_schema='erreichbarkeiten'
    view_sql =  u"""
    CREATE OR REPLACE VIEW {err_schema}.view_err_{tag} AS
    SELECT
    g.grid_id, l.geom, min(r.travel_time) / 60 AS minuten
    
    FROM
    {ein_schema}.{tag}_szenario AS b,
    {ein_schema}.{tag}2grid AS bg,
    {err_schema}.grid_points AS g,
    {err_schema}.reisezeiten r,
    laea.grid_poly_100 l
    WHERE
    b.szenario_id = {sid}
    AND b."AngebotsID" = bg."AngebotsID"
    AND bg.grid_id = r.destination_id
    AND g.grid_id = r.origin_id
    {where}
    AND l.cellcode = g.cellcode
    GROUP BY g.grid_id, l.geom;
    """
    
    refresh_sql = """
    REFRESH MATERIALIZED VIEW {err_schema}.matview_err_{tag};"""
    if where:
        where = ' AND ' + where

    db_conn.execute(view_sql.format(ein_schema=ein_schema,
                                    err_schema=err_schema,
                                    sid=szenario_id, 
                                    tag=tag, 
                                    where=where))

    db_conn.execute(refresh_sql.format(err_schema=err_schema, tag=tag))

def update_gemeinde_erreichbarkeiten(tag, db_conn):
    table = 'matview_err_' + tag
    gem_table = 'erreichbarkeiten_gemeinden_' + tag
    err_schema='erreichbarkeiten'
    view_sql =  u"""
    CREATE OR REPLACE VIEW {err_schema}.{gem_table} AS
    WITH a AS (
    SELECT
    r.grid_id,
    g."AGS" AS ags,
    r.einwohner_ AS einwohner,
    e.minuten
    
    FROM
    {err_schema}.grid_points_shk r,
    verwaltungsgrenzen.gemeinden_20161231 g,
    {err_schema}.{table} e
    WHERE st_intersects(r.geom, geom_31468)
    AND r.grid_id = e.grid_id)
    
    SELECT
    a.ags,
    g.geom,
    sum(a.einwohner::double precision / ew_gem_szenario.ew_gemeinde * minuten::double precision) AS minuten_mittelwert
    FROM
    (SELECT
    a.ags,
    sum(a.einwohner) AS ew_gemeinde
    FROM a GROUP BY a.ags) AS ew_gem_szenario,
    a,
    verwaltungsgrenzen.gemeinden_20161231 g
    WHERE ew_gem_szenario.ags = a.ags
    AND a.ags = g."AGS"
    GROUP BY a.ags, g.geom;
    
    GRANT SELECT,DELETE,UPDATE,INSERT,TRUNCATE ON {err_schema}.{gem_table} TO saale_holzland;
    """
    print(view_sql.format(err_schema=err_schema,
                          tag=tag, table=table, 
                          gem_table=gem_table))
    
    db_conn.execute(view_sql.format(err_schema=err_schema,
                                    tag=tag, table=table, 
                                    gem_table=gem_table))
    
def create_scenario(name, user, db_conn):
    
    table = 'szenarien'
    schema = 'einrichtungen'
    sql_scen = u"""
    INSERT INTO {schema}.{table} (name, benutzer, datum)
    VALUES ('{name}','{user}', '{ts}')
    RETURNING id
    """
    scenario_id = db_conn.execute(
        sql_scen.format(schema=schema, table=table,
                        name=name, user=user, ts=datetime.now()))
    sql_duplicate = u"""
    SELECT 'INSERT INTO {schema}.{table} (szenario_id, ' || 
    array_to_string(ARRAY(SELECT '"' || c.column_name || '"'
            FROM information_schema.columns As c
                WHERE table_name = '{table}'
               AND table_schema = '{schema}'
               AND  c.column_name NOT IN('szenario_id', 'id')
        ), ',')
    
     || ') SELECT {s_id} AS szenario_id, '
     || array_to_string(ARRAY(SELECT 'o' || '."' || c.column_name || '"'
            FROM information_schema.columns As c
                WHERE table_name = '{table}' 
               AND table_schema = '{schema}'
               AND  c.column_name NOT IN('szenario_id', 'id')
        ), ',') || ' FROM {schema}.{table} As o WHERE "szenario_id" = {base_id}' As sqlstmt;
    """
    sql2 = """SELECT '"' || c.column_name || '"'
            FROM information_schema.columns As c
                WHERE table_name = '{table}'
               AND table_schema = '{schema}'
               AND  c.column_name NOT IN('szenario_id', 'id')"""
    tables = ['bildung_szenario', 'gesundheit_szenario', 'nahversorgung_szenario']
    for table in tables:
        #b = db_conn.execute(sql2.format(schema=schema, table=table))
        #print(b)
        reply = db_conn.execute(sql_duplicate.format(
            schema=schema, table=table,
            s_id=scenario_id, 
            base_id=BASE_SCENARIO_ID))
        full_sql = '''
        SET session_replication_role = replica;
        {};
        SET session_replication_role = DEFAULT;
        '''.format(reply)
        db_conn.execute(full_sql)

def remove_scenario(scenario_id, db_conn):
    table = 'szenarien'
    schema = 'einrichtungen'
    # should not happen, but as a precaution to prevent deleting the base scenario
    if scenario_id == BASE_SCENARIO_ID:
        return
    sql = """
    DELETE FROM {schema}.{table} WHERE id={s_id}
    """
    db_conn.execute(sql.format(schema=schema, table=table, s_id=scenario_id))


class Scenario(object):
    def __init__(self, id, name, user, date, editable):
        self.id = id
        self.name = name
        self.user = user
        self.date = date
        self.editable = editable

def get_scenarios(db_conn):
    table = 'szenarien'
    schema = 'einrichtungen'
    columns = ['id', 'name', 'benutzer', 'datum', 'editierbar']
    rows = get_values(table, columns, db_conn, schema=schema)
    scenarios = []
    for id, name, user, date, editable in rows:
        scenario = Scenario(id, name, user, date, editable)
        scenarios.append(scenario)
    return scenarios
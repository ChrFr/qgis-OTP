# -*- coding: utf-8 -*-

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

def update_erreichbarkeiten(tag, db_conn, where=''):
    table = 'matview_err_' + tag
    ein_schema='einrichtungen'
    err_schema='erreichbarkeiten'
    view_sql =  """
    CREATE OR REPLACE VIEW {err_schema}.view_err_{tag} AS
    SELECT
    g.grid_id, l.geom, min(r.travel_time) / 60 AS minuten
    
    FROM
    {ein_schema}.{tag}_gesamt AS b,
    {ein_schema}.{tag}2grid AS bg,
    {err_schema}.grid_points AS g,
    {err_schema}.reisezeiten r,
    laea.grid_poly_100 l
    WHERE
    b."AngebotsID" = bg."AngebotsID"
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
                                    tag=tag, 
                                    where=where))

    db_conn.execute(refresh_sql.format(err_schema=err_schema, tag=tag))

def update_gemeinde_erreichbarkeiten(tag, db_conn):
    table = 'matview_err_' + tag
    gem_table = 'erreichbarkeiten_gemeinden_' + tag
    err_schema='erreichbarkeiten'
    view_sql =  """
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
    sum(a.einwohner::double precision / ew_gem_gesamt.ew_gemeinde * minuten::double precision) AS minuten_mittelwert
    FROM
    (SELECT
    a.ags,
    sum(a.einwohner) AS ew_gemeinde
    FROM a GROUP BY a.ags) AS ew_gem_gesamt,
    a,
    verwaltungsgrenzen.gemeinden_20161231 g
    WHERE ew_gem_gesamt.ags = a.ags
    AND a.ags = g."AGS"
    GROUP BY a.ags, g.geom;
    
    GRANT SELECT,DELETE,UPDATE,INSERT,TRUNCATE ON {err_schema}.{gem_table} TO saale_holzland;
    """

    db_conn.execute(view_sql.format(err_schema=err_schema,
                                    tag=tag, table=table, 
                                    gem_table=gem_table))
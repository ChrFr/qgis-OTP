# -*- coding: utf-8 -*-

def get_values(table, column, db_conn, schema='public', where=''):
    sql = """
    SELECT "{column}"
    FROM {schema}.{table}
    """
    if where:
        sql += ' WHERE ' + where
    values = db_conn.fetch(sql.format(
        column=column, table=table, schema=schema))
    return values

def update_erreichbarkeiten(table, db_conn, where=''):
    ein_schema='einrichtungen'
    err_schema='erreichbarkeiten'
    view_sql =  """
    CREATE OR REPLACE VIEW {err_schema}.view_err_bildung AS
    SELECT
    g.grid_id, l.geom, min(r.travel_time) / 60 AS minuten
    
    FROM
    {ein_schema}.bildung_gesamt AS b,
    {ein_schema}.bildung2grid AS bg,
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
    REFRESH MATERIALIZED VIEW {err_schema}.matview_err_bildung;"""
    if where:
        where = ' AND ' + where
    print(view_sql.format(ein_schema=ein_schema,
                          err_schema=err_schema,
                          where=where))
    db_conn.execute(view_sql.format(ein_schema=ein_schema,
                                    err_schema=err_schema,
                                    where=where))

    print(refresh_sql.format(err_schema=err_schema))    
    db_conn.execute(refresh_sql.format(err_schema=err_schema))
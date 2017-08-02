# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SHKPluginDialog
                                 A QGIS plugin
 Plugin zur Berechnung von Erreichbarkeiten im Saale-Holzland-Kreis

                             -------------------
        begin                : 2017-07-20
        git sha              : $Format:%H$
        copyright            : (C) 2017 by GGR
        email                : franke@ggr-planung.de
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from PyQt4 import QtGui, uic, QtCore

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'shk_plugin_dialog_base.ui'))

from config import Config
from connection import DBConnection, Login
from qgis.core import QgsDataSourceURI, QgsVectorLayer, QgsMapLayerRegistry
import numpy as np

config = Config()

SCHEMA = 'einrichtungen'


class Filter(object):
    def __init__(self, displayname, options):
        self.displayname = displayname
        self.options = options
        self.active = self.options[0]


class SHKPluginDialog(QtGui.QMainWindow, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(SHKPluginDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.load_config()
        self.save_button.clicked.connect(self.save_config)
        self.connect_button.clicked.connect(self.connect)
        self.layers = {'Bildungseinrichtungen': ('bildung_gesamt', self.schools_tree),
                       'Medizinische Versorgung': ('gesundheit_gesamt', self.medicine_tree),
                       'Nahversorgung': ('nahversorgung_gesamt', self.supply_tree)}
        self.filters = dict([(v, []) for v in self.layers.keys()])
    
    def load_config(self):
        db_config = config.db_config
        self.user_edit.setText(str(db_config['username']))
        self.pass_edit.setText(str(db_config['password']))
        self.db_edit.setText(str(db_config['db_name']))
        self.host_edit.setText(str(db_config['host']))
        self.port_edit.setText(str(db_config['port']))
        self.srid_edit.setText(str(db_config['srid']))
        
    def save_config(self):
        db_config = config.db_config
        db_config['username'] = str(self.user_edit.text())
        db_config['password'] = str(self.pass_edit.text())
        db_config['db_name'] = str(self.db_edit.text())
        db_config['host'] = str(self.host_edit.text())
        db_config['port'] = str(self.port_edit.text())
        db_config['srid'] = str(self.srid_edit.text())

        config.write()

    def connect(self):
        
        db_config = config.db_config
        self.login = Login(host=db_config['host'], port=db_config['port'],
                           user=db_config['username'],
                           password=db_config['password'],
                           db=db_config['db_name'])
        self.db_conn = DBConnection(self.login)
        self.refresh()
        
    def add_db_layer(self, name, schema, tablename): 
        uri = QgsDataSourceURI()
        uri.setConnection(self.login.host,
                          self.login.port,
                          self.login.db,
                          self.login.user,
                          self.login.password)
        uri.setDataSource(schema, tablename, 'geom')
        layer = QgsVectorLayer(uri.uri(), name, "postgres")
        ex = QgsMapLayerRegistry.instance().mapLayersByName(name)
        if len(ex) > 0:
            for e in ex:
                QgsMapLayerRegistry.instance().removeMapLayer(e.id())
        QgsMapLayerRegistry.instance().addMapLayer(layer, True)
    
    def refresh(self):
        for layername, (table, tree) in self.layers.iteritems():
            self.add_db_layer(layername, SCHEMA, table)
        self.init_filters()
            
    def init_filters(self):
        table_sql = """
        SELECT spalte
        FROM meta.filter_einrichtungen
        WHERE tabelle = '{table}'
        """
        column_sql = """
        SELECT "{column}"
        FROM {schema}.{table}
        """
        for layername, (tablename, tree) in self.layers.iteritems():
            tree.clear()
            res = self.db_conn.fetch(table_sql.format(table=tablename))
            filters = []
            for r in res:
                column = r[0]
                values = self.db_conn.fetch(column_sql.format(
                    column=column, table=tablename, schema=SCHEMA))
                values = [v[0].strip() if v[0] else '' for v in values]
                options = np.unique(values)
                filters.append(Filter(column, options))
                
                col_item = QtGui.QTreeWidgetItem(tree, [column])
                col_item.setCheckState(0, QtCore.Qt.Unchecked)
                col_item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
                for option in options:
                    opt_item = QtGui.QTreeWidgetItem(col_item, [option])
                    opt_item.setCheckState(0, QtCore.Qt.Unchecked)
                    opt_item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            tree.resizeColumnToContents(0)
            self.filters[layername] = filters
            
    def render_structure(self):
        idx = self.year_combo.currentIndex()
        # nothing selected (e.g. when triggered on clearance)
        if idx < 0:
            return
        self.structure_tree.clear()
        year = str(self.year_combo.currentText())
        structure = self.db_conn.get_structure_available(year)
        for cat, cols in structure.iteritems():
            cat_item = QtGui.QTreeWidgetItem(self.structure_tree, [cat])
            cat_item.setCheckState(0,QtCore.Qt.Unchecked)
            cat_item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            for col in cols:
                col_item = QtGui.QTreeWidgetItem(cat_item, [col['name']])
                col_item.setText(1, _fromUtf8(col['description']))
                col_item.setCheckState(0,QtCore.Qt.Unchecked)
                col_item.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
        self.structure_tree.resizeColumnToContents(0)    
        
if __name__ == '__main__':
    print ('hallo')
        
        
    
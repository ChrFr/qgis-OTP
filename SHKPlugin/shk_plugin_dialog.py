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
try:
    from qgis.core import QgsDataSourceURI, QgsVectorLayer, QgsMapLayerRegistry
except: pass
from PyQt4 import QtGui, uic, QtCore
import numpy as np
from xml.etree import ElementTree as ET
from collections import defaultdict

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'shk_plugin_dialog_base.ui'))

from config import Config
from connection import DBConnection, Login

config = Config()

SCHEMA = 'einrichtungen'


#class Filter(object):
    #def __init__(self, column, values):
        #self.column = column
        #self.filter_values = dict([(k, False) for k in values])
    
    #def activate(self, filter_value, active=True):
        #self.filter_values[filter_value] = active
    
    #@property
    #def is_active(self):
        #return np.any(self.filter_values.values())
    
    #@property
    #def active_values(self):
        #idx = np.array(self.filter_values.values()) == True
        #return np.array(self.filter_values.keys())[idx]
    
    #@property
    #def where(self):
        #return "WHERE {} IN ({})".format(
            #",".join(''.format(a) for a in self.active_filters))
            
class Filter():
    def __init__(self, field, values):
        self.field = field
        self.values = values
    
    @property
    def where(self):
        return '"{}" IN ({})'.format(self.field, 
            ','.join("'{}'".format(v) for v in self.values))


class LabeledSlider(QtGui.QWidget):
    def __init__(self, min, max):
        super(LabeledSlider, self).__init__()
        self.min_label = QtGui.QLabel(str(min))
        self.max_label = QtGui.QLabel(str(max))
        self.slider = QtGui.QSlider(QtCore.Qt.Horizontal)
        layout = QtGui.QHBoxLayout()
        layout.addWidget(self.min_label)
        layout.addWidget(self.slider)
        layout.addWidget(self.max_label)
        self.setLayout(layout)


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
        
        self.layers = {
            'Bildungseinrichtungen': ('bildung_gesamt', self.schools_tree),
            'Medizinische Versorgung': ('gesundheit_gesamt', self.medicine_tree),
            'Nahversorgung':  ('nahversorgung_gesamt', self.supply_tree)
        }
        
        self.filters = dict([(v, []) for v in self.layers.keys()])
        
        for (table, tree) in self.layers.itervalues():
            tree.itemClicked.connect(filter_clicked)
        
        self.filter_button.clicked.connect(self.apply_filters)
    
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
        fn = os.path.join(os.path.split(__file__)[0], "filter.xml")
        root = ET.parse(fn).getroot()
        table_filters = dict([(c.attrib['name'], c.getchildren())
                              for c in root.getchildren()])
        for layername, (tablename, tree) in self.layers.iteritems():
            tree.clear()
            filter_nodes = table_filters[tablename]
            item = QtGui.QTreeWidgetItem(tree, ['Spalten'])
            item.setExpanded(True)
            for child in filter_nodes:
                self.add_filter_node(item, child, tablename, tree)
            tree.resizeColumnToContents(0)
            
    def add_filter_node(self, parent_item, node, tablename, tree, where=''):
        column_sql = """
        SELECT "{column}"
        FROM {schema}.{table}
        """
        alias = node.attrib['alias'] if node.attrib.has_key('alias') else None
        display_name = alias or node.attrib['name']
        item = None
        if node.tag == 'column':
            item = QtGui.QTreeWidgetItem(parent_item, [display_name])
            item.setCheckState(0, QtCore.Qt.Unchecked)
            item.setFlags(QtCore.Qt.ItemIsUserCheckable |
                          QtCore.Qt.ItemIsEnabled)
            column = node.attrib['name'].encode('utf-8')
            if where:
                column_sql += ' WHERE ' + where
            values = self.db_conn.fetch(column_sql.format(
                column=column, table=tablename, schema=SCHEMA))
            #stripped = []
            #for value, in values:
                #if type(value) == str:
                    #value = value.strip()
                #elif value is None:
                    #continue
                #stripped.append(value)

            if node.attrib.has_key('input') and node.attrib['input'] == 'range':
                values = [v for v, in values if v is not None]
                v_min = np.min(values)
                v_max = np.max(values)
                slider = LabeledSlider(v_min, v_max)
                tree.setItemWidget(item, 1, slider)
            else:
                values = ['' if v is None else v for v, in values]
                options = np.sort(np.unique(values))
                for o in options:
                    option = QtGui.QTreeWidgetItem(item, [o])
                    option.setCheckState(0, QtCore.Qt.Unchecked)
                    option.setFlags(QtCore.Qt.ItemIsUserCheckable |
                                    QtCore.Qt.ItemIsEnabled)
                
                item.column = column
            where = ''
            
        elif node.tag == 'value':
            value = node.attrib['name']
            # search parent for entry; if exists, add children to found one
            found = None
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                if child.text(0) == value:
                    found = child
                    break
            item = found
            if hasattr(parent_item, 'column'):
                where = """"{c}" = '{v}'""".format(c=parent_item.column,
                                                   v=value)
            
        if item:
            for child in node.getchildren():
                self.add_filter_node(item, child, tablename, tree, where)
    
    #def filter_layers(self):
        #for layer, filters in self.filters.iteritems():
            #for filter in filters:
                #print(filter.filter_values)
                #if filter.is_active:
                    #print filter.active_values
    
    def apply_filters(self):
        for layer_name, (table, tree) in self.layers.iteritems():
            root = tree.topLevelItem(0)
            queries = []
            for i in range(root.childCount()):
                child = root.child(i)
                # root 'Spalten' has columns as children, no need to process them
                # if not checked
                if child.checkState(0) != QtCore.Qt.Unchecked:
                    subquery = build_queries(child)
                    if subquery:
                        queries.append(subquery)
            subset = ' AND '.join(queries)
            layer = QgsMapLayerRegistry.instance().mapLayersByName(layer_name)[0]
            layer.setSubsetString(subset)
    
def build_queries(tree_item):
    queries = ''
    # column
    child_count = tree_item.childCount()
    if hasattr(tree_item, 'column'):
        column = tree_item.column
        values = []
        subqueries = []
        for i in range(tree_item.childCount()):
            child = tree_item.child(i)
            if child.checkState(0) != QtCore.Qt.Unchecked:
                value = child.text(0)
                if child.childCount() > 0:
                    subquery = build_queries(child)
                    subquery = u'''("{c}" = '{v}' AND ({s}))'''.format(
                        c=column, v=value, s=subquery)
                    subqueries.append(subquery)
                else:
                    values.append(value)
        query = ''
        if len(values) > 0:
            query = u'"{c}" IN ({v})'.format(
                c=column,  v=u','.join(u"'{}'".format(v) for v in values))
            queries += u' ' + query
        if len(subqueries) > 0:
            if query:
                queries += u' OR '
            queries += u'({})'.format(u' OR '.join(subqueries))
    # value
    else:
        if child_count > 0:
            subqueries = []
            for i in range(tree_item.childCount()):
                child = tree_item.child(i)
                if (child.childCount() > 0 and
                    child.checkState(0) != QtCore.Qt.Unchecked):
                    subqueries.append(build_queries(child))
            queries += u' AND '.join(subqueries)
            
    return queries

def filter_clicked(item):
    
    # check or uncheck all direct children
    if item.checkState(0) != QtCore.Qt.PartiallyChecked:
        state = item.checkState(0)
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, state)

    parent = item.parent()
    while (parent and parent.text(0) != 'Spalten'):
        parent_filter = parent.filter if hasattr(parent, 'filter') else None
        # check/uncheck/partial check of parent of given item, depending on number of checked children
        child_count = parent.childCount()
        checked_count = 0
        for i in range(child_count):
            child = parent.child(i)
            is_checked = False
            if (child.checkState(0) != QtCore.Qt.Unchecked):
                checked_count += 1
                is_checked = True
        if checked_count == 0:
            parent.setCheckState(0, QtCore.Qt.Unchecked)
        elif checked_count == child_count:
            parent.setCheckState(0, QtCore.Qt.Checked)
        else:
            parent.setCheckState(0, QtCore.Qt.PartiallyChecked)
            
        parent = parent.parent()
        
if __name__ == '__main__':
    print
    
        
        
    
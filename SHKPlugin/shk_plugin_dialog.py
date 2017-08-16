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
from osgeo import gdal
from qgis.core import (QgsDataSourceURI, QgsVectorLayer, 
                       QgsMapLayerRegistry, QgsRasterLayer)
import numpy as np
from xml.etree import ElementTree as ET
from collections import defaultdict

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'shk_plugin_dialog_base.ui'))

from config import Config
from connection import DBConnection, Login
from queries import get_values, update_erreichbarkeiten
from ui_elements import LabeledSlider, SimpleSymbology, GraduatedSymbology

config = Config()

SCHEMA = 'einrichtungen'

OSM_XML = os.path.join(os.path.split(__file__)[0], 'osm_background.xml')


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
        self.login = None

        color_ranges =  [
            (0, 5, 'unter 5 Minuten', QtGui.QColor(37, 52, 148)), 
            (10, 15, '10 bis 15 Minuten', QtGui.QColor(42, 111, 176)), 
            (15, 20, '15 bis 20 Minuten', QtGui.QColor(56, 160, 191)), 
            (20, 25, '20 bis 25 Minuten', QtGui.QColor(103, 196, 189)), 
            (25, 30, '25 bis 30 Minuten', QtGui.QColor(179, 225, 184)), 
            (30, 100000000, 'mehr als 30 Minuten', QtGui.QColor(208, 255, 204)), 
        ]
        
        self.err_ranges = {
            'Bildungseinrichtungen': color_ranges,
            'Medizinische Versorgung': color_ranges,
            'Nahversorgung': color_ranges
        }
        
        self.err_tags = {
            'Bildungseinrichtungen': 'bildung',
            'Medizinische Versorgung': 'gesundheit',
            'Nahversorgung': 'nahversorgung'
        }
        
        self.symbology = {
            'Bildungseinrichtungen': SimpleSymbology('yellow'),
            'Medizinische Versorgung': SimpleSymbology('red'),
            'Nahversorgung': SimpleSymbology('#F781F3')
        }
        
        
        self.layers = {
            'Bildungseinrichtungen': ('bildung_gesamt', self.schools_tree),
            'Medizinische Versorgung': ('gesundheit_gesamt', self.medicine_tree),
            'Nahversorgung':  ('nahversorgung_gesamt', self.supply_tree)
        }
        
        self.filters = dict([(v, '') for v in self.layers.keys()])
        
        for (table, tree) in self.layers.itervalues():
            tree.itemClicked.connect(filter_clicked)
        
        self.filter_button.clicked.connect(self.apply_filters)
        self.calculate_button.clicked.connect(self.calculate)
    
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
        
    def add_db_layer(self, name, schema, tablename, geom,
                     symbology=None, uri=None, key=None):
        """type: str, optional vector or polygon"""
        if not uri:
            uri = QgsDataSourceURI()
            uri.setConnection(self.login.host,
                              self.login.port,
                              self.login.db,
                              self.login.user,
                              self.login.password)
            uri.setDataSource(schema, tablename, geom, aKeyColumn=key)
            uri = uri.uri(False)
        layer = QgsVectorLayer(uri, name, "postgres")
        print(uri)
        print(layer.isValid())
        ex = QgsMapLayerRegistry.instance().mapLayersByName(name)
        if len(ex) > 0:
            for e in ex:
                QgsMapLayerRegistry.instance().removeMapLayer(e.id())
        if symbology:
            symbology.apply(layer)
        QgsMapLayerRegistry.instance().addMapLayer(layer, True)
        
    def add_background_map(self):
        ex = QgsMapLayerRegistry.instance().mapLayersByName('OpenStreetMap')
        if len(ex) > 0:
            for e in ex:
                QgsMapLayerRegistry.instance().removeMapLayer(e.id())
        QgsMapLayerRegistry.instance().removeMapLayer('OpenStreetMap')
        layer = QgsRasterLayer(OSM_XML, 'OpenStreetMap')
        QgsMapLayerRegistry.instance().addMapLayer(layer, True)
    
    def refresh(self):
        self.add_background_map()
        for layername, (table, tree) in self.layers.iteritems():
            symbology = self.symbology[layername]
            self.add_db_layer(layername, SCHEMA, table, 'geom_gk', symbology)
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
        alias = node.attrib['alias'] if node.attrib.has_key('alias') else None
        display_name = alias or node.attrib['name']
        item = None
        if node.tag == 'column':
            item = QtGui.QTreeWidgetItem(parent_item, [display_name])
            item.setCheckState(0, QtCore.Qt.Unchecked)
            item.setFlags(QtCore.Qt.ItemIsUserCheckable |
                          QtCore.Qt.ItemIsEnabled)
            column = node.attrib['name'].encode('utf-8')
            values = get_values(tablename, column, self.db_conn,
                                schema=SCHEMA, where=where)
            
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
    
    def apply_filters(self):
        if not self.login:
            return
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
            print(subset)
            layer = QgsMapLayerRegistry.instance().mapLayersByName(layer_name)[0]
            layer.setSubsetString(subset)
            self.filters[layer_name] = subset
    
    def calculate(self):
        if not self.login:
            return
        tab = self.get_selected_tab()
        ranges = self.err_ranges[tab]
        where = self.filters[tab]
        tag = self.err_tags[tab]
        symbology = GraduatedSymbology('minuten', ranges, no_pen=True)
        update_erreichbarkeiten(tag, self.db_conn, where=where)
        name = 'Erreichbarkeiten ' + tab
        self.add_db_layer(name, 'erreichbarkeiten',
                          'matview_err_' + tag, 'geom', key='grid_id',
                          symbology=symbology)
    
    def get_selected_tab(self):
        idx = self.selection_tabs.currentIndex()
        tab_name = self.selection_tabs.tabText(idx)
        return tab_name
        
    
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
    
        
        
    
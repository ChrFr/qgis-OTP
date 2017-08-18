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
                       QgsMapLayerRegistry, QgsRasterLayer,
                       QgsProject)
from qgis.utils import iface
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

        self.err_color_ranges =  [
            (0, 5, 'unter 5 Minuten', QtGui.QColor(37, 52, 148)), 
            (10, 15, '10 bis 15 Minuten', QtGui.QColor(42, 111, 176)), 
            (15, 20, '15 bis 20 Minuten', QtGui.QColor(56, 160, 191)), 
            (20, 25, '20 bis 25 Minuten', QtGui.QColor(103, 196, 189)), 
            (25, 30, '25 bis 30 Minuten', QtGui.QColor(179, 225, 184)), 
            (30, 100000000, 'mehr als 30 Minuten', QtGui.QColor(208, 255, 204)), 
        ]
        
        self.err_tags = {
            'Bildungseinrichtungen': 'bildung',
            'Medizinische Versorgung': 'gesundheit',
            'Nahversorgung': 'nahversorgung'
        }
        
        self.colors = {
            'Bildungseinrichtungen': 'yellow',
            'Medizinische Versorgung': 'red',
            'Nahversorgung': '#F781F3'
        }
        
        self.categories = {
            'Bildungseinrichtungen': ('bildung_gesamt', self.schools_tree),
            'Medizinische Versorgung': ('gesundheit_gesamt', self.medicine_tree),
            'Nahversorgung':  ('nahversorgung_gesamt', self.supply_tree)
        }

        for (table, tree) in self.categories.itervalues():
            tree.headerItem().setHidden(True)
            tree.header().setResizeMode(QtGui.QHeaderView.ResizeToContents)
            tree.setHeaderLabels(['', ''])
            tree.itemClicked.connect(filter_clicked)
        
        for button in ['filter_button', 'filter_button_2', 'filter_button_3']:
            getattr(self, button).clicked.connect(self.apply_filters)
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
                     symbology=None, uri=None, key=None, zoom=True, group=None):
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
        remove_layer(name, group)
        QgsMapLayerRegistry.instance().addMapLayer(layer, group is None)
        if group:
            group.addLayer(layer)
        if symbology:
            symbology.apply(layer)
        if zoom:
            canvas = iface.mapCanvas()
            extent = layer.extent()
            canvas.setExtent(extent)
        
    def add_background_map(self, group=None):
        layer_name = 'OpenStreetMap'
        for child in group.children():
            pass
        layer = QgsRasterLayer(OSM_XML, layer_name)
        remove_layer(layer_name, group)
        QgsMapLayerRegistry.instance().addMapLayer(layer, group is None)
        if group:
            group.addLayer(layer)

    def get_group(self, groupname, parent_group=None):
        if not parent_group:
            parent_group = QgsProject.instance().layerTreeRoot()
        group = parent_group.findGroup(groupname)
        if not group:
            group = parent_group.addGroup(groupname)
        return group

    def refresh(self):
        # just for the right initial order
        self.get_group('Filter')
        self.get_group('Erreichbarkeiten Auto')
        
        for category, (table, tree) in self.categories.iteritems():
            symbology = SimpleSymbology(self.colors[category])
            self.add_db_layer(category, SCHEMA, table, 'geom_gk', symbology,
                              group=self.get_group('Einrichtungen'))
        
        self.add_background_map(group=self.get_group('Hintergrundkarte'))
        self.init_filters()
            
    def init_filters(self):
        fn = os.path.join(os.path.split(__file__)[0], "filter.xml")
        root = ET.parse(fn).getroot()
        table_filters = dict([(c.attrib['name'], c.getchildren())
                              for c in root.getchildren()])
        for layername, (tablename, tree) in self.categories.iteritems():
            tree.clear()
            filter_nodes = table_filters[tablename]
            item = QtGui.QTreeWidgetItem(tree, ['Spalten'])
            item.setExpanded(True)
            for child in filter_nodes:
                self.add_filter_node(item, child, tablename, tree)
            #tree.resizeColumnToContents(0)
            
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
        category = self.get_selected_tab()
        table, tree = self.categories[category]
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
        orig_layer = QgsMapLayerRegistry.instance().mapLayersByName(category)[0]
        name, ok = QtGui.QInputDialog.getText(self, 'Filter',
                                              'Name des zu erstellenden Layers',
                                              text=category)
        if not ok:
            return
        parent_group = self.get_group('Filter')
        subgroup = self.get_group(category, parent_group)
        remove_layer(name, subgroup)
        
        print(subset)
        layer = QgsVectorLayer(orig_layer.source(), name, "postgres")
        QgsMapLayerRegistry.instance().addMapLayer(layer, False)
        subgroup.addLayer(layer)
        layer.setSubsetString(subset)
        symbology = SimpleSymbology(self.colors[category], shape='diamond')
        symbology.apply(layer)
    
    def calculate(self):
        if not self.login:
            return
        items = []
        filter_group = self.get_group('Filter')
        for category in self.categories.iterkeys():
            subgroup = self.get_group(category, filter_group)
            subitems = [(category, c.layer().name())
                        for c in subgroup.children()]
            items += subitems
        if not items:
            QtGui.QMessageBox.information(
                'Fehler', 'Es sind keine gefilterten Layer vorhanden.')
            return
        
        item_texts = ['{} - {}'.format(l, c) for l, c in items]
        sel, ok = QtGui.QInputDialog.getItem(self, 'Erreichbarkeiten',
                                              u'Gefilterten Layer auswählen',
                                              item_texts, 0, False)
        if not ok:
            return
        
        category, layer_name = items[item_texts.index(sel)]
        tag = self.err_tags[category]
        
        # find the layer and get it's query
        subgroup = self.get_group(category, filter_group)
        for child in subgroup.children():
            if child.layer().name() == layer_name:
                query = child.layer().subsetString()
                break
        
        results_group = self.get_group('Erreichbarkeiten Auto')
        subgroup = self.get_group(category, results_group)
        symbology = GraduatedSymbology('minuten', self.err_color_ranges,
                                       no_pen=True)
        update_erreichbarkeiten(tag, self.db_conn, where=query)
        self.add_db_layer(layer_name, 'erreichbarkeiten',
                          'matview_err_' + tag, 'geom', key='grid_id',
                          symbology=symbology, group=subgroup, zoom=False)
    
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
                    sq = build_queries(child)
                    sq = ' AND ({})'.format(sq) if sq else ''
                    subquery = u'''("{c}" = '{v}' {s})'''.format(
                        c=column, v=value, s=sq)
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
                    sq = build_queries(child)
                    if sq:
                        subqueries.append(sq)
            queries += u' AND '.join(subqueries)
            
    return queries

def filter_clicked(item):
    
    # check or uncheck all direct children
    if item.checkState(0) != QtCore.Qt.PartiallyChecked:
        state = item.checkState(0)
        if hasattr(item, 'column'):
            for i in range(item.childCount()):
                child = item.child(i)
                child.setCheckState(0, state)

    parent = item.parent()
    while (parent and parent.text(0) != 'Spalten'):
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

def remove_layer(name, group=None):

    if not group:
        ex = QgsMapLayerRegistry.instance().mapLayersByName(name)
        if len(ex) > 0:
            for e in ex:
                QgsMapLayerRegistry.instance().removeMapLayer(e.id())
    else:
        for child in group.children():
            l = child.layer()
            if l and l.name() == name:
                QgsMapLayerRegistry.instance().removeMapLayer(l.id())
        
if __name__ == '__main__':
    print
    
        
        
    
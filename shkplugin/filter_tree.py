from PyQt4 import QtGui, QtCore
from queries import get_values
from xml.etree import ElementTree as ET
import numpy as np
from ui_elements import LabeledRangeSlider

def set_checkable(item):
    item.setCheckState(0, QtCore.Qt.Unchecked)
    item.setFlags(QtCore.Qt.ItemIsUserCheckable |
                  QtCore.Qt.ItemIsEnabled)


class FilterTree(object):

    def __init__(self, category, tablename, db_conn, parent_node):
        parent_node.headerItem().setHidden(True)
        parent_node.header().setResizeMode(QtGui.QHeaderView.ResizeToContents)
        parent_node.setHeaderLabels(['', ''])
        parent_node.itemClicked.connect(self.filter_clicked)
        self.parent_node = parent_node
        self.tablename = tablename
        self.db_conn = db_conn
    
    def from_xml(self, xml_file, region_node=None):
        xml_root = ET.parse(xml_file).getroot()
        self.parent_node.clear()
        table_filters = dict([(c.attrib['name'], c.getchildren())
                              for c in xml_root.getchildren()])
        if not region_node:
            region_node = self.region_node(self.db_conn)
            
        filter_nodes = table_filters[self.tablename]
        item = QtGui.QTreeWidgetItem(self.parent_node, ['Spalten'])
        item.setExpanded(True)
        item.addChild(region_node.clone())
        for child in filter_nodes:
            self.add_filter_node(item, child, self.tablename, self.parent_node)
        #fn = os.path.join(config.cache_folder, PICKLE_EX.format(
            #category=category))
        
    @staticmethod
    def region_node(db_conn):
        root = QtGui.QTreeWidgetItem(['Landkreis'])
        set_checkable(root)
        columns = ['GEN', 'vwg_name', 'kreis_name']
        rows = get_values('gemeinden_20161231', columns,
                          db_conn, schema='verwaltungsgrenzen',
                          where="in_region=TRUE")
        krs_items = {}
        vwg_items = {}
        for gem_name, vwg_name, kreis_name in rows:
            if vwg_name not in vwg_items:
                if kreis_name not in krs_items:
                    krs_item = QtGui.QTreeWidgetItem(root, [kreis_name])
                    krs_items[kreis_name] = krs_item
                    set_checkable(krs_item)
                else:
                    krs_item = krs_items[kreis_name]
                vwg_item = QtGui.QTreeWidgetItem(krs_item, [vwg_name])
                vwg_items[vwg_name] = vwg_item
                set_checkable(vwg_item)
            else:
                vwg_item = vwg_items[vwg_name]
            gem_item = QtGui.QTreeWidgetItem(vwg_item, [gem_name])
            set_checkable(gem_item)
        return root
            
    def add_filter_node(self, parent_item, node, tablename, tree, where=''):
        alias = node.attrib['alias'] if node.attrib.has_key('alias') else None
        display_name = alias or node.attrib['name']
        item = None
        if node.tag == 'column':
            item = QtGui.QTreeWidgetItem(parent_item, [display_name])
            set_checkable(item)
            column = node.attrib['name'].encode('utf-8')
            values = get_values(tablename, [column], self.db_conn,
                                schema='einrichtungen', where=where)

            if node.attrib.has_key('input'):
            
                if node.attrib['input'] == 'range':
                    values = [v for v, in values if v is not None]
                    v_min = np.min(values) if values else 0
                    v_max = np.max(values) if values else 0
                    slider = LabeledRangeSlider(v_min, v_max)
                    tree.setItemWidget(item, 1, slider)
                item.input_type = node.attrib['input']
            else:
                values = ['' if v is None else v for v, in values]
                options = np.sort(np.unique(values))
                for o in options:
                    option = QtGui.QTreeWidgetItem(item, [o])
                    set_checkable(option)
                
            item.column = column
            where = ''
            
        elif node.tag == 'value' and node.attrib['name'] != '*':
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
        
        elif node.tag == 'value' and node.attrib['name'] != '*':
            name = node.attrib['name']
            # search parent for entry; if exists, add children to found one
            found = None
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                if child.text(0) == name:
                    found = child
                    break
            item = found
            if hasattr(parent_item, 'column'):
                where = u""""{c}" = '{v}'""".format(c=parent_item.column,
                                                   v=name)
        # SPECIAL CASE: Joker, do the same for all child nodes
        elif node.tag == 'value' and node.attrib['name'] == '*':
            for i in range(parent_item.childCount()):
                item = parent_item.child(i)
                if hasattr(parent_item, 'column'):
                    where = u""""{c}" = '{v}'""".format(c=parent_item.column,
                                                       v=item.text(0))
                for child in list(node):
                    self.add_filter_node(item, child, tablename, tree, where)
            return

        # recursively build nodes from children
        if item:
            for child in list(node):
                self.add_filter_node(item, child, tablename, tree, where)

    def to_sql_query(self):
        root = self.parent_node.topLevelItem(0)
        queries = []
        for i in range(root.childCount()):
            child = root.child(i)
            # root 'Spalten' has columns as children, no need to process them
            # if not checked
            if child.checkState(0) != QtCore.Qt.Unchecked:
                subquery = self._build_queries(child)
                if subquery:
                    queries.append(subquery)
        query = u' AND '.join(queries)
        return query
    
    def _build_queries(self, tree_item): 
        tree = self.parent_node
        queries = ''
        child_count = tree_item.childCount()
        
        ### COLUMN ###
        if hasattr(tree_item, 'column'):
            column = tree_item.column
            if hasattr(tree_item, 'input_type'):
                widget = tree.itemWidget(tree_item, 1)
                if tree_item.input_type == 'range':
                    query = u'"{c}" BETWEEN {min} AND {max}'.format(
                        c=column, min=widget.min, max=widget.max)
                    ## columns with special input types will not have any children
                    return query
                
            ## normal columns may have subqueries (if value matches definition in xml)
            #else:
            values = []
            subqueries = []
            for i in range(tree_item.childCount()):
                child = tree_item.child(i)
                if child.checkState(0) != QtCore.Qt.Unchecked:
                    value = child.text(0)
                    if child.childCount() > 0:
                        sq = self._build_queries(child)
                        sq = u' AND ({})'.format(sq) if sq else ''
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
                
        ### VALUE ###
        else:
            if child_count > 0:
                subqueries = []
                for i in range(tree_item.childCount()):
                    child = tree_item.child(i)
                    if (child.checkState(0) != QtCore.Qt.Unchecked):
                        sq = self._build_queries(child)
                        if sq:
                            subqueries.append(sq)
                queries += u' AND '.join(subqueries)
                
        return queries    

    def filter_clicked(self, item):
        
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

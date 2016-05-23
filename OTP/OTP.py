# -*- coding: utf-8 -*-
"""
/***************************************************************************
 OTP
                                 A QGIS plugin
 OTP Erreichbarkeitsanalyse
                              -------------------
        begin                : 2016-04-08
        git sha              : $Format:%H$
        copyright            : (C) 2016 by GGR
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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QProcess, QDateTime
from PyQt4.QtGui import QAction, QIcon, QListWidgetItem, QCheckBox, QMessageBox
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from OTP_dialog import OTPDialog
import os
from config import OTP_JAR, GRAPH_PATH, AVAILABLE_MODES, DATETIME_FORMAT, DEFAULT_MODES, AGGREGATION_MODES
from dialogs import ExecCommandDialog, set_file
from qgis._core import QgsVectorLayer, QgsVectorJoinInfo
from qgis.core import QgsVectorFileWriter
from time import strftime
import locale
import tempfile
import shutil
import time

# result-modes
ORIGIN_DESTINATION = 0
AGGREGATION = 1

# how many results are written while running batch script
PRINT_EVERY_N_LINES = 5

class OTP:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        loc = QSettings().value('locale/userLocale')[0:2]
        #locale.setlocale(locale.LC_ALL, 'de_DE')
        #loc = locale.getlocale()
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'OTP_{}.qm'.format(loc))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = OTPDialog()   
        
        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&OTP')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'OTP')
        self.toolbar.setObjectName(u'OTP')        
        
        # PREFILL UI ELEMENTS AND CONNECT SLOTS TO SIGNALS
        
        self.dlg.orig_dest_browse_button.clicked.connect(
            lambda: set_file(self.dlg, 
                             self.dlg.orig_dest_file_edit,
                             filters=['CSV-Dateien (*.csv)'],
                             directory=self.dlg.router_combo.currentText()+'-Quelle-Ziel.csv', # '-'+strftime('%d-%m-%Y-%H:%M')+'.csv', 
                             save=True)
        )            

        self.dlg.aggregation_browse_button.clicked.connect(
            lambda: set_file(self.dlg, 
                             self.dlg.aggregation_file_edit,
                             filters=['CSV-Dateien (*.csv)'],
                             directory=self.dlg.router_combo.currentText()+'-Aggregation.csv', # '-'+strftime('%d-%m-%Y-%H:%M')+'.csv', 
                             save=True)
        )           
        
        # set active tab (aggregation or accumulation depending on arrival checkbox)
        self.arrival_check()
        self.dlg.arrival_checkbox.clicked.connect(self.arrival_check)
        
        self.dlg.start_orig_dest_button.clicked.connect(lambda: self.run_otp(ORIGIN_DESTINATION))
        self.dlg.start_aggregation_button.clicked.connect(lambda: self.run_otp(AGGREGATION))     
         
        self.dlg.close_button.clicked.connect(self.dlg.close)
        
        # store layers to check, if they changed on rerun (combo boxes will be refilled then)                      
        self.layer_list = []      
        self.layers = self.iface.legendInterface().layers()
        self.fill_layer_combos()     
        
        # refresh layer ids on selection of different layer
        self.dlg.origins_combo.currentIndexChanged.connect(
            lambda: self.fill_id_combo(self.dlg.origins_combo, self.dlg.origins_id_combo))   
        self.dlg.destinations_combo.currentIndexChanged.connect(
            lambda: self.fill_id_combo(self.dlg.destinations_combo, self.dlg.destinations_id_combo))  
        # reset aggregation and accumulation field combo, if layer changed
        self.dlg.destinations_combo.currentIndexChanged.connect(
            lambda: self.fill_id_combo(self.dlg.destinations_combo, self.dlg.aggregation_field_combo))       
        self.fill_id_combo(self.dlg.destinations_combo, self.dlg.aggregation_field_combo) 
        self.dlg.destinations_combo.currentIndexChanged.connect(
            lambda: self.fill_id_combo(self.dlg.destinations_combo, self.dlg.accumulation_field_combo))       
        self.fill_id_combo(self.dlg.destinations_combo, self.dlg.accumulation_field_combo) 
        
        # checkboxes for selecting the traverse modes            
        for mode in AVAILABLE_MODES:
            item = QListWidgetItem(self.dlg.mode_list_view)
            checkbox = QCheckBox(mode)
            if mode in DEFAULT_MODES:
                checkbox.setChecked(True)
            self.dlg.mode_list_view.setItemWidget(item, checkbox) 
           
        # combobox with modes for aggregation
        self.dlg.aggregation_mode_combo.addItems(AGGREGATION_MODES)
        self.set_agg_value_select()
        self.dlg.aggregation_mode_combo.currentIndexChanged.connect(self.set_agg_value_select)   
        
        # calendar
        self.set_date()
        self.dlg.calendar_edit.clicked.connect(self.set_date)       

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('OTP', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/OTP/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'OTP Erreichbarkeiten'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&OTP'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar        
        
    def set_date(self):
        date = self.dlg.calendar_edit.selectedDate()
        self.dlg.current_date_label.setText(date.toString())
        
    def arrival_check(self):        
        is_arrival = self.dlg.arrival_checkbox.checkState()         
        self.dlg.calculation_tabs.removeTab(self.dlg.calculation_tabs.indexOf(self.dlg.accumulation_tab))    
        self.dlg.calculation_tabs.removeTab(self.dlg.calculation_tabs.indexOf(self.dlg.aggregation_tab))
        
        if is_arrival:
            self.dlg.calculation_tabs.addTab(self.dlg.accumulation_tab, "Akkumulation")
        else:
            self.dlg.calculation_tabs.addTab(self.dlg.aggregation_tab, "Aggregation")
        
    def fill_layer_combos(self):
        '''
        fill the combo boxes for selection of origin/destination layers with all available vector-layers
        '''
        self.layer_list = []
        active_layer = self.iface.activeLayer()
        self.dlg.origins_combo.clear()   
        self.dlg.destinations_combo.clear()            
        i = 0
        idx = 0
        for layer in self.layers:            
            if isinstance(layer, QgsVectorLayer):
                if layer == active_layer:
                    idx = i
                self.layer_list.append(layer)
                self.dlg.origins_combo.addItem(layer.name())   
                self.dlg.destinations_combo.addItem(layer.name())     
                i += 1        
                
        # select active layer in comboboxes                    
        self.dlg.origins_combo.setCurrentIndex(idx)          
        self.dlg.destinations_combo.setCurrentIndex(idx)   
        
        # fill ids although there is already a signal/slot connection (in __init__) to do this,
        # but if index doesn't change (idx == 0), signal doesn't fire (so it maybe is done twice, but this is not performance-relevant)
        self.fill_id_combo(self.dlg.origins_combo, self.dlg.origins_id_combo)
        self.fill_id_combo(self.dlg.destinations_combo, self.dlg.destinations_id_combo)
        
    def fill_id_combo(self, layer_combo, id_combo):  
        '''
        fill a combo box (id_combo) with all fields of the currently selected layer in the given layer_combo
        '''
        id_combo.clear()
        if len(self.layer_list) == 0 or (layer_combo.currentIndex() >= len(self.layer_list)):
            return
        layer = self.layer_list[layer_combo.currentIndex()]
        fields = layer.pendingFields()
        field_names = [field.name() for field in fields]
        id_combo.addItems(field_names)      
        
    def set_agg_value_select(self):
        selected = self.dlg.aggregation_mode_combo.currentText()
        # only this one needs a value as an argument at the moment
        if selected == 'THRESHOLD_CUMMULATIVE_AGGREGATOR' or selected == 'DECAY_AGGREGATOR':
            self.dlg.aggregation_value_edit.setVisible(True)
            self.dlg.aggregation_value_label.setVisible(True)
        else:
            self.dlg.aggregation_value_edit.setVisible(False)
            self.dlg.aggregation_value_label.setVisible(False)   
        if selected == 'THRESHOLD_CUMMULATIVE_AGGREGATOR':
            self.dlg.aggregation_value_label.setText('Schwellwert')
        if selected == 'DECAY_AGGREGATOR':
            self.dlg.aggregation_value_label.setText('lambda')
        
    def run_otp(self, result_mode):                   
        working_dir = os.path.dirname(__file__)       
        
        # LAYERS
        origin_layer = self.layer_list[self.dlg.origins_combo.currentIndex()]
        destination_layer = self.layer_list[self.dlg.destinations_combo.currentIndex()]    
        
        if origin_layer==destination_layer:
            msg_box = QMessageBox()
            reply = msg_box.question(self.dlg,
                                     'Hinweis',
                                     'Die Layer mit Origins und Destinations sind identisch.\n'+
                                     'Soll die Berechnung trotzdem gestartet werden?',
                                     QMessageBox.Ok, QMessageBox.Cancel)
            if reply == QMessageBox.Cancel:
                return                
        
        tmp_dir = tempfile.mkdtemp()
        orig_tmp_filename = os.path.join(tmp_dir, 'origins.csv')  
        dest_tmp_filename = os.path.join(tmp_dir, 'destinations.csv')    
        
        QgsVectorFileWriter.writeAsVectorFormat(origin_layer, orig_tmp_filename, "utf-8", None, "CSV", layerOptions="GEOMETRY=AS_WKT")
        QgsVectorFileWriter.writeAsVectorFormat(destination_layer, dest_tmp_filename, "utf-8", None, "CSV", layerOptions="GEOMETRY=AS_WKT")
        
        # MODES                
        selected_modes = []
        for index in xrange(self.dlg.mode_list_view.count()):
            checkbox = self.dlg.mode_list_view.itemWidget(self.dlg.mode_list_view.item(index))
            if checkbox.checkState():
                selected_modes.append(str(checkbox.text()))  
                
        router = self.dlg.router_combo.currentText()
        oid = self.dlg.origins_id_combo.currentText()
        did = self.dlg.destinations_id_combo.currentText()
        
        # TRAVEL TIME
        d = self.dlg.calendar_edit.selectedDate()
        t = self.dlg.time_edit.time()
        dt = QDateTime(d)
        dt.setTime(t)                
        dt_string = dt.toPyDateTime().strftime(DATETIME_FORMAT)
        
        # MAX TIME
        max_time = self.dlg.max_time_edit.value() * 60        
        
        # ARRIVAL
        is_arrival = self.dlg.arrival_checkbox.checkState()
        
        # JOIN
        do_join = self.dlg.orig_dest_join_check.checkState() if ORIGIN_DESTINATION else self.dlg.aggregation_join_check.checkState()
        
        # OUT FILE
        if result_mode == ORIGIN_DESTINATION and self.dlg.orig_dest_csv_check.checkState():
            target_file = self.dlg.orig_dest_file_edit.text()
            
        elif result_mode == AGGREGATION and self.dlg.aggregation_csv_check.checkState():
            target_file = self.dlg.aggregation_file_edit.text()
        
        # if saving is not explicitly wanted, file is written to temporary folder, so it will be removed later
        else:
            target_file = os.path.join(tmp_dir, 'results.csv')                
            
        target_path = os.path.dirname(target_file)        
            
        if not os.path.exists(target_path):
            msg_box = QMessageBox(QMessageBox.Warning, "Fehler", u'Sie haben keinen gültigen Dateipfad angegeben.')
            msg_box.exec_()
            return
        elif not os.access(target_path, os.W_OK):
            msg_box = QMessageBox(QMessageBox.Warning, "Fehler", u'Sie benötigen Schreibrechte im Dateipfad {}!'.format(target_path))
            msg_box.exec_()
            return    
        
        # basic cmd looks same for all evaluations
        cmd = '''jython -Dpython.path="{jar}" {wd}/otp_batch.py 
 --router {router} --origins "{origins}" --destinations "{destinations}" 
 --oid {oid} --did {did} --target "{target}" --datetime {datetime} 
 --maxtime {max_time} --modes {modes} --nlines {nlines}'''
        
        cmd = cmd.format(
            jar=OTP_JAR, 
            wd=working_dir, 
            router=router, 
            origins=orig_tmp_filename, 
            destinations=dest_tmp_filename, 
            oid=oid,
            did=did,
            datetime=dt_string,
            target=target_file,
            max_time=max_time,
            modes=' '.join(selected_modes),
            nlines=PRINT_EVERY_N_LINES
        )    
                    
        if is_arrival:
            cmd += ' --arrival'
            n_points = destination_layer.featureCount()       
        else:
            n_points = origin_layer.featureCount()     
            
        if result_mode == AGGREGATION:    
            agg_cmd = ' --aggregate "{field}" --aggregation_mode {mode}'
            agg_cmd = agg_cmd.format(
                field=self.dlg.aggregation_field_combo.currentText(),
                mode=self.dlg.aggregation_mode_combo.currentText())
            if self.dlg.aggregation_value_edit.isVisible():
                value = self.dlg.aggregation_value_edit.value()
                agg_cmd += ' --value {value}'.format(value=value)
            cmd += agg_cmd             
                
        diag = ExecCommandDialog(cmd, parent=self.dlg.parent(), auto_start=True, progress_indicator='Processing:', total_ticks=n_points/PRINT_EVERY_N_LINES)
        diag.exec_()
        
        if do_join:
            result_layer = self.iface.addVectorLayer(target_file, 'results', 'delimitedtext')
            join = QgsVectorJoinInfo()
            join.joinLayerId = result_layer.id()
            join.joinFieldName = 'origin_id'  
            join.targetFieldName = oid      
            origin_layer.addJoin(join)
            # TODO permanent join and remove result layer (origin_layer save as shape?)    
            # csv layer is only link to file, if temporary is removed you won't see anything later
            
        #shutil.rmtree(tmp_dir)                        

    def run(self):
        '''
        called every time, the plugin is (re)started (so don't connect slots to signals here, otherwise they may be connected multiple times)
        '''
        
        # reload layer combos, if layers changed on rerun
        layers = self.iface.legendInterface().layers()     
        if layers != self.layers:
            self.layers = layers
            self.fill_layer_combos()
        
        # reload routers on every run (they might be changed outside)
        # but try to keep old router selected
        prev_router = self.dlg.router_combo.currentText()       
        self.dlg.router_combo.clear()
        idx = 0
        # subdirectories in graph-dir are treated as routers by OTP
        for i, subdir in enumerate(os.listdir(GRAPH_PATH)):
            self.dlg.router_combo.addItem(subdir) 
            if prev_router == subdir:
                idx = i                
        self.dlg.router_combo.setCurrentIndex(idx)        
        
        # show the dialog
        self.dlg.show()                
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
from PyQt4.QtCore import (QSettings, QTranslator, qVersion, 
                          QCoreApplication, QProcess, QDateTime,
                          QVariant)
from PyQt4.QtGui import (QAction, QIcon, QListWidgetItem, 
                         QCheckBox, QMessageBox, QLabel,
                         QDoubleSpinBox, QFileDialog)

# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from OTP_dialog import OTPDialog
import os
from config import (OTP_JAR, GRAPH_PATH, AVAILABLE_TRAVERSE_MODES, 
                    DATETIME_FORMAT, AGGREGATION_MODES, ACCUMULATION_MODES, 
                    MODE_PARAMS, DEFAULT_FILE, CALC_REACHABILITY_MODE, Config)
from dialogs import ExecCommandDialog, set_file
from qgis._core import (QgsVectorLayer, QgsVectorJoinInfo, 
                        QgsCoordinateReferenceSystem, QgsField)
from qgis.core import QgsVectorFileWriter, QgsMapLayerRegistry
import locale
import tempfile
import shutil
import getpass
from datetime import datetime
from PyQt4.QtCore import QLocale

config = Config()
config.read()

# result-modes
ORIGIN_DESTINATION = 0
AGGREGATION = 1
ACCUMULATION = 2
REACHABILITY = 3

# how many results are written while running batch script
PRINT_EVERY_N_LINES = 5

XML_FILTER = u'XML-Dateien (*.xml)'
CSV_FILTER = u'CSV-Dateien (*.csv)'

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
        QLocale.setDefault(QLocale('de'))
        loc = QSettings().value('locale/userLocale')[0:2]
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
        
        ### PREFILL UI ELEMENTS AND CONNECT SLOTS TO SIGNALS ###
        
        # connect browse file buttons with 'smart'(?) naming of target files (that's the main reason why there are 4 seperate ones)
        self.dlg.orig_dest_browse_button.clicked.connect(
            lambda: set_file(self.dlg, 
                             self.dlg.orig_dest_file_edit,
                             filters=[CSV_FILTER],
                             directory='{}-{}-{}.csv'.format(
                                 self.dlg.router_combo.currentText(),
                                 self.dlg.origins_combo.currentText(),
                                 self.dlg.destinations_combo.currentText()
                                  # '-'+strftime('%d-%m-%Y-%H:%M')
                                  ),
                             save=True)
        )            

        self.dlg.aggregation_browse_button.clicked.connect(
            lambda: set_file(self.dlg, 
                             self.dlg.aggregation_file_edit,
                             filters=[CSV_FILTER],
                             directory='{}-{}-aggregiert.csv'.format(
                                 self.dlg.router_combo.currentText(),
                                 self.dlg.origins_combo.currentText()
                                  ),
                             save=True)
        )  
        
        self.dlg.accumulation_browse_button.clicked.connect(
            lambda: set_file(self.dlg, 
                             self.dlg.aggregation_file_edit,
                             filters=[CSV_FILTER],
                             directory='{}-{}-akkumuliert.csv'.format(
                                 self.dlg.router_combo.currentText(),
                                 self.dlg.origins_combo.currentText()
                                  ),
                             save=True)
        )  
        
        self.dlg.reachability_browse_button.clicked.connect(
            lambda: set_file(self.dlg, 
                             self.dlg.reachability_file_edit,
                             filters=[CSV_FILTER],
                             directory='{}-{}-{}-Erreichbarkeit.csv'.format(
                                 self.dlg.router_combo.currentText(),
                                 self.dlg.origins_combo.currentText(),
                                 self.dlg.destinations_combo.currentText()
                                  ),
                             save=True)
        )  
                
        # set active tab (aggregation or accumulation depending on arrival checkbox)
        self.dlg.arrival_checkbox.clicked.connect(self.toggle_arrival)
        
        self.dlg.start_orig_dest_button.clicked.connect(lambda: self.call_otp(ORIGIN_DESTINATION))
        self.dlg.start_aggregation_button.clicked.connect(lambda: self.call_otp(AGGREGATION))     
        self.dlg.start_reachability_button.clicked.connect(lambda: self.call_otp(REACHABILITY))     
         
        self.dlg.close_button.clicked.connect(self.close) #ToDo: save on close
        
        # available layers are stored in here                      
        self.layer_list = []    
        self.layers = None
        
        layers = self.iface.legendInterface().layers()    
        self.fill_layer_combos(layers)        
        
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
        for mode in AVAILABLE_TRAVERSE_MODES:
            item = QListWidgetItem(self.dlg.mode_list_view)
            checkbox = QCheckBox(mode)
            checkbox.setTristate(False)
            self.dlg.mode_list_view.setItemWidget(item, checkbox) 
           
        # combobox with modes
        self.dlg.aggregation_mode_combo.addItems(AGGREGATION_MODES)
        self.set_mode_params(AGGREGATION)
        self.dlg.aggregation_mode_combo.currentIndexChanged.connect(
            lambda: self.set_mode_params(AGGREGATION))   
        
        self.dlg.accumulation_mode_combo.addItems(ACCUMULATION_MODES)
        self.set_mode_params(ACCUMULATION)
        self.dlg.aggregation_mode_combo.currentIndexChanged.connect(
            lambda: self.set_mode_params(ACCUMULATION))       
        
        # router
        self.fill_router_combo()
        
        # calendar
        self.dlg.calendar_edit.clicked.connect(self.set_date)
        
        # time_step
        self.dlg.time_batch_checkbox.clicked.connect(self.toggle_time_batch)
              
        # settings
        self.dlg.config_default_button.clicked.connect(self.reset_config_to_default)
        self.dlg.config_reset_button.clicked.connect(self.apply_config)
        self.dlg.config_read_button.clicked.connect(self.read_config)
        self.dlg.config_save_button.clicked.connect(self.save_config_as)
        # apply settings to UI (the layers are unknown at QGIS startup, so don't expect them to be already selected)
        self.apply_config()
        
        # call checkbox toggle callbacks (settings loaded, but checkboxes not 'clicked' while loading)        
        self.toggle_time_batch()
        self.toggle_arrival()        

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
        
    def reset_config_to_default(self):
        '''
        reset Config.settings to default
        '''
        config.reset()
        self.apply_config()
        
    def apply_config(self):
        '''
        change state of UI (checkboxes, comboboxes) according to the Config.settings
        '''
        # ORIGIN
        origin_config = config.settings['origin'] 
        layer_idx = self.dlg.origins_combo.findText(origin_config['layer'])
        # layer found
        if layer_idx >= 0:  
            self.dlg.origins_combo.setCurrentIndex(layer_idx)    
            # if id is not found (returns -1) take first one (0)
            id_idx = max(self.dlg.origins_id_combo.findText(origin_config['id_field']), 0)           
            self.dlg.origins_id_combo.setCurrentIndex(id_idx)        
        # layer not found -> take first one
        else:
            self.dlg.origins_combo.setCurrentIndex(0)  
            
        # DESTINATION
        dest_config = config.settings['destination'] 
        layer_idx = self.dlg.destinations_combo.findText(dest_config['layer'])
        # layer found
        if layer_idx >= 0:  
            self.dlg.destinations_combo.setCurrentIndex(layer_idx)    
            # if id is not found (returns -1) take first one (0)
            id_idx = max(self.dlg.destinations_id_combo.findText(dest_config['id_field']), 0)           
            self.dlg.destinations_id_combo.setCurrentIndex(id_idx)        
        # layer not found -> take first one
        else:
            self.dlg.destinations_combo.setCurrentIndex(0)        
        
        # ROUTER
        router_config = config.settings['router_config']
        # if router is not found (returns -1) take first one (0)
        idx = max(self.dlg.router_combo.findText(router_config['router']), 0)
        self.dlg.router_combo.setCurrentIndex(idx)    
        
        self.dlg.max_time_edit.setValue(int(router_config['maxTimeMin']))
        self.dlg.max_walk_dist_edit.setValue(int(router_config['maxWalkDistance']))
        self.dlg.walk_speed_edit.setValue(float(router_config['walkSpeed']))
        self.dlg.bike_speed_edit.setValue(float(router_config['bikeSpeed']))
        self.dlg.clamp_edit.setValue(int(router_config['clampInitialWaitSec']))    
        banned = router_config['banned_routes']
        if isinstance(banned, list):
            banned = ','.join(banned)
        self.dlg.banned_routes_edit.setText(banned)            
                    
        # TRAVERSE MODES    
        modes = router_config['traverse_modes']
        for index in xrange(self.dlg.mode_list_view.count()):
            checkbox = self.dlg.mode_list_view.itemWidget(self.dlg.mode_list_view.item(index))
            if str(checkbox.text()) in modes :
                checkbox.setChecked(True) 
            else:
                checkbox.setChecked(False)                 
                
        # TIMES
        times = config.settings['time']
        if times['datetime']:
            dt = datetime.strptime(times['datetime'], DATETIME_FORMAT)
        else:
            dt = datetime.now()
        self.dlg.time_edit.setDateTime(dt)
        self.dlg.calendar_edit.setSelectedDate(dt.date())
        time_batch = times['time_batch']
        if time_batch['datetime_end']:
            dt = datetime.strptime(time_batch['datetime_end'], DATETIME_FORMAT)
        self.dlg.to_time_edit.setDateTime(dt)
        active = time_batch['active'] == 'True' or time_batch['active'] == True
        self.dlg.time_batch_checkbox.setChecked(active)
        if time_batch['time_step']:
            self.dlg.time_step_edit.setValue(int(time_batch['time_step']))
            
        arrive_by = times['arrive_by'] == 'True' or times['arrive_by'] == True
        self.dlg.arrival_checkbox.setChecked(arrive_by)
            
    def update_config(self):     
        '''
        update Config.settings according to the current state of the UI (checkboxes etc.)
        post processing not included! only written to config before calling otp (in call_otp()),
        because not relevant for UI (meaning it is set to default on startup)
        '''
                
        # LAYERS
        origin_config = config.settings['origin'] 
        origin_config['layer'] = self.dlg.origins_combo.currentText()
        origin_config['id_field'] = self.dlg.origins_id_combo.currentText()
        dest_config = config.settings['destination'] 
        dest_config['layer'] = self.dlg.destinations_combo.currentText()
        dest_config['id_field'] = self.dlg.destinations_id_combo.currentText()        
                
        # ROUTER
        router_config = config.settings['router_config']
        router_config['router'] = self.dlg.router_combo.currentText()
        router_config['maxTimeMin'] = self.dlg.max_time_edit.value()
        router_config['maxWalkDistance'] = self.dlg.max_walk_dist_edit.value()      
        router_config['walkSpeed'] = self.dlg.walk_speed_edit.value()      
        router_config['bikeSpeed'] = self.dlg.bike_speed_edit.value()   
        router_config['clampInitialWaitSec'] = self.dlg.clamp_edit.value() 
        router_config['banned_routes'] = self.dlg.banned_routes_edit.text().split(',')        
                
        # TRAVERSE MODES    
        selected_modes = []
        for index in xrange(self.dlg.mode_list_view.count()):
            checkbox = self.dlg.mode_list_view.itemWidget(self.dlg.mode_list_view.item(index))
            if checkbox.checkState():
                selected_modes.append(str(checkbox.text()))   
        router_config['traverse_modes'] = selected_modes
        
        # TIMES
        times = config.settings['time']
        dt = self.dlg.time_edit.dateTime()
        times['datetime'] = dt.toPyDateTime().strftime(DATETIME_FORMAT)
        time_batch = times['time_batch']
        active = self.dlg.time_batch_checkbox.isChecked()
        time_batch['active'] = active
        end = step = ''
        if active:            
            dt = self.dlg.to_time_edit.dateTime()
            end = dt.toPyDateTime().strftime(DATETIME_FORMAT)
            step = self.dlg.time_step_edit.value()            
        time_batch['datetime_end'] = end
        time_batch['time_step'] = step 
        
        is_arrival = self.dlg.arrival_checkbox.isChecked()
        times['arrive_by'] = is_arrival        
        
    def save_config_as(self):        
        filename = str(
            QFileDialog.getSaveFileName(
                self.dlg, u'Konfigurationsdatei wählen',
                directory=DEFAULT_FILE,
                filter=XML_FILTER)
            )
        if filename:         
            self.update_config()
            config.write(filename)    
            
    def read_config(self):
        '''
        save config in selectable file
        '''
        filename = str(
            QFileDialog.getOpenFileName(
                self.dlg, u'Konfigurationsdatei wählen',
                filter=XML_FILTER)
            )
        if filename:
            config.read(filename)
            self.apply_config()
    
    def close(self):
        '''
        save config and close UI
        '''
        self.update_config()
        config.write()  
        self.dlg.close()
        
    def set_date(self):
        date = self.dlg.calendar_edit.selectedDate()
        # ToDo: if focus of user was on to_time, only change value in this one
        # but way below won't work, because focus changes, when calendar is clicked
        #if self.dlg.to_time_edit.hasFocus():
            #self.dlg.to_time_edit.setDate(date)
        #else:
            #self.dlg.time_edit.setDate(date)
        self.dlg.to_time_edit.setDate(date)
        self.dlg.time_edit.setDate(date)
        
    def toggle_arrival(self):
        '''
        enable/disable tabs, depending on arrival is checked or not
        '''
        is_arrival = self.dlg.arrival_checkbox.checkState()
        acc_idx = self.dlg.calculation_tabs.indexOf(self.dlg.accumulation_tab)
        agg_idx = self.dlg.calculation_tabs.indexOf(self.dlg.aggregation_tab)
        reach_idx = self.dlg.calculation_tabs.indexOf(self.dlg.reachability_tab)
        acc_enabled = agg_enabled = reach_enabled = False
        
        if is_arrival:
            acc_enabled = True
        else:
            agg_enabled = reach_enabled = True
            
        self.dlg.calculation_tabs.setTabEnabled(acc_idx, acc_enabled)  
        self.dlg.calculation_tabs.setTabEnabled(agg_idx, agg_enabled) 
        self.dlg.calculation_tabs.setTabEnabled(reach_idx, reach_enabled) 
            
            
    def toggle_time_batch(self):
        active = self.dlg.time_batch_checkbox.isChecked()
        self.dlg.time_step_widget.setVisible(active)
        self.dlg.to_time_widget.setVisible(active)            
            
    def fill_router_combo(self):
        # try to keep old router selected
        prev_router = self.dlg.router_combo.currentText()       
        self.dlg.router_combo.clear()
        idx = 0
        # subdirectories in graph-dir are treated as routers by OTP
        for i, subdir in enumerate(os.listdir(GRAPH_PATH)):
            self.dlg.router_combo.addItem(subdir) 
            if prev_router == subdir:
                idx = i                
        self.dlg.router_combo.setCurrentIndex(idx)    
        
    def fill_layer_combos(self, layers):
        '''
        fill the combo boxes for selection of origin/destination layers with all available vector-layers
        keep selections of previously selected layers, if possible
        '''
        old_origin_layer = None 
        old_destination_layer = None
        if len(self.layer_list) > 0:    
            old_origin_layer = self.layer_list[self.dlg.origins_combo.currentIndex()]
            old_destination_layer = self.layer_list[self.dlg.destinations_combo.currentIndex()]              
        
        self.layer_list = []
        self.dlg.origins_combo.clear()   
        self.dlg.destinations_combo.clear()   
        old_origin_idx = 0
        old_destination_idx = 0
        i = 0 # counter for QgsVectorLayers
        for layer in layers:
            if isinstance(layer, QgsVectorLayer):
                if layer == old_origin_layer:
                    old_origin_idx = i
                if layer == old_destination_idx:
                    old_destination_idx = i
                self.layer_list.append(layer)
                self.dlg.origins_combo.addItem(layer.name())   
                self.dlg.destinations_combo.addItem(layer.name())  
                i += 1
                           
        # select active layer in comboboxes                    
        self.dlg.origins_combo.setCurrentIndex(old_origin_idx)          
        self.dlg.destinations_combo.setCurrentIndex(old_destination_idx)   
        
        # fill ids although there is already a signal/slot connection (in __init__) to do this,
        # but if index doesn't change (idx == 0), signal doesn't fire (so it maybe is done twice, but this is not performance-relevant)
        self.fill_id_combo(self.dlg.origins_combo, self.dlg.origins_id_combo)
        self.fill_id_combo(self.dlg.destinations_combo, self.dlg.destinations_id_combo)
        
        self.layers = layers     
        
    def fill_id_combo(self, layer_combo, id_combo):  
        '''
        fill a combo box (id_combo) with all fields of the currently selected layer in the given layer_combo
        tries to keep same field as selected before
        WARNING: does not keep same field selected if layers are changed and rerun
        '''        
        old_id_field = id_combo.currentText()
        id_combo.clear()
        if len(self.layer_list) == 0 or (layer_combo.currentIndex() >= len(self.layer_list)):
            return
        layer = self.layer_list[layer_combo.currentIndex()]
        fields = layer.pendingFields()
        old_idx = 0
        for i, field in enumerate(fields):
            if field.name() == old_id_field:
                old_idx = i
            id_combo.addItem(field.name())
        id_combo.setCurrentIndex(old_idx)
        
    def set_mode_params(self, result_mode):
        if result_mode == AGGREGATION:
            selected = self.dlg.aggregation_mode_combo.currentText()
            edit_layout = self.dlg.aggregation_value_edit
        else:
            selected = self.dlg.accumulation_mode_combo.currentText()
            edit_layout = self.dlg.accumulation_value_edit     
        
        # clear layout
        for i in reversed(range(edit_layout.count())):
            widget = edit_layout.itemAt(i).widget()
            edit_layout.removeWidget(widget)
            widget.setParent(None)
            
        # only this one needs a value as an argument at the moment
        if selected in MODE_PARAMS.keys():
            for param in MODE_PARAMS[selected]:
                label = QLabel(param["label"])
                edit = QDoubleSpinBox()
                step = param["step"] if param.has_key("step") else 1
                edit.setSingleStep(step)
                if param.has_key("max"):
                    edit.setMaximum(param["max"])
                if param.has_key("min"):
                    edit.setMinimum(param["min"])
                if param.has_key("default"):
                    edit.setValue(param["default"])
                if param.has_key("decimals"):
                    edit.setDecimals(param["decimals"])
                edit_layout.addRow(label, edit)
                
    def get_mode_params(self, result_mode):
        params = []
        if result_mode == AGGREGATION:
            edit_layout = self.dlg.aggregation_value_edit
        else:
            edit_layout = self.dlg.accumulation_value_edit     
        for i in range(edit_layout.count()):
            widget = edit_layout.itemAt(i).widget()
            if isinstance(widget, QDoubleSpinBox):
                params.append(str(widget.value()))
        return params
        
    def call_otp(self, result_mode):   
        now_string = datetime.now().strftime(DATETIME_FORMAT)
                
        # update settings
        self.update_config()
        
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
            
            
        # update postprocessing settings
        postproc = config.settings['post_processing']
        bestof = ''
        if self.dlg.bestof_check.isChecked():
            bestof = self.dlg.bestof_edit.value()
        postproc['best_of'] = bestof               
    
        agg_acc = postproc['aggregation_accumulation']
        agg_acc['active'] = False
    
        if result_mode == AGGREGATION or result_mode == ACCUMULATION:            
            agg_acc['active'] = True            
            if result_mode == AGGREGATION:
                field = self.dlg.aggregation_field_combo.currentText()
                mode = self.dlg.aggregation_mode_combo.currentText()  
            else:                
                field = self.dlg.accumulation_field_combo.currentText()
                mode = self.dlg.accumulation_mode_combo.currentText()  
            agg_acc['mode'] = mode
            agg_acc['processed_field'] = field
    
            agg_acc['params'] = self.get_mode_params(result_mode)
    
        # calc. number of reachabe destinations is an aggregation with only 1s in field to aggregate
        if result_mode == REACHABILITY:          
            agg_acc['active'] = True   
            # duplicate destination layer
            destination_layer = self.iface.addVectorLayer(destination_layer.source(), 
                                                          destination_layer.name(), 
                                                          destination_layer.providerType())
            # add virtual field with 1s as values
            reach_field_name = 'erreichbare_Ziele'
            agg_acc['mode'] = CALC_REACHABILITY_MODE       
            # field already exists -> try to take unique name
            if destination_layer.fieldNameIndex(reach_field_name) > -1:
                reach_field_name += '_' + now_string
            reach_field = QgsField(reach_field_name, QVariant.Int)
            destination_layer.addExpressionField('1', reach_field)
            agg_acc['processed_field'] = reach_field_name   
            # take the set max travel time as the threshold (in seconds)
            threshold = int(config.settings['router_config']['maxTimeMin']) * 60
            agg_acc['params'] = [str(threshold)]
    
        working_dir = os.path.dirname(__file__)               

        # write config to temporary directory with additional meta infos
        tmp_dir = tempfile.mkdtemp()
        config_xml = os.path.join(tmp_dir, 'config.xml')
        meta = {
            'date_of_calculation': now_string,
            'user': getpass.getuser()
        }
        config.write(config_xml, hide_inactive=True, meta=meta)
        
        # convert layers to csv and write them to temporary directory 
        orig_tmp_filename = os.path.join(tmp_dir, 'origins.csv')  
        dest_tmp_filename = os.path.join(tmp_dir, 'destinations.csv')
        
        wgs84 = QgsCoordinateReferenceSystem(4326)
        QgsVectorFileWriter.writeAsVectorFormat(origin_layer, 
                                                orig_tmp_filename, 
                                                "utf-8", 
                                                wgs84, 
                                                "CSV", 
                                                layerOptions=["GEOMETRY=AS_YX", "GEOMETRY_NAME=pnt"])
        QgsVectorFileWriter.writeAsVectorFormat(destination_layer, 
                                                dest_tmp_filename, 
                                                "utf-8", 
                                                wgs84, 
                                                "CSV", 
                                                layerOptions=["GEOMETRY=AS_YX", "GEOMETRY_NAME=geom"])
        print 'wrote origins and destinations to temporary folder "{}"'.format(tmp_dir)
        
        do_copy = False
        # OUT FILE
        if result_mode == ORIGIN_DESTINATION and self.dlg.orig_dest_csv_check.checkState():
            target_file = self.dlg.orig_dest_file_edit.text()
            do_copy = True
            
        elif result_mode == AGGREGATION and self.dlg.aggregation_csv_check.checkState():
            target_file = self.dlg.aggregation_file_edit.text()
            do_copy = True
            
        elif result_mode == REACHABILITY and self.dlg.reachability_csv_check.checkState():
            target_file = self.dlg.reachability_file_edit.text()
            do_copy = True
        
        # if saving is not explicitly wanted, file is written to temporary folder, so it will be removed later
        else:
            target_file = os.path.join(tmp_dir, 'results.csv')             
        
        if do_copy:            
            # copy config to file with similar name as results file
            dst_config = os.path.splitext(target_file)[0] + '-config.xml'
            shutil.copy(config_xml, dst_config)            
                    
        
        target_path = os.path.dirname(target_file)        
            
        if not os.path.exists(target_path):
            msg_box = QMessageBox(QMessageBox.Warning, "Fehler", u'Sie haben keinen gültigen Dateipfad angegeben.')
            msg_box.exec_()
            return
        elif not os.access(target_path, os.W_OK):
            msg_box = QMessageBox(QMessageBox.Warning, "Fehler", u'Sie benötigen Schreibrechte im Dateipfad {}!'.format(target_path))
            msg_box.exec_()
            return    
        
        # basic cmd is same for all evaluations
        cmd = '''jython -Dpython.path="{jar}" {wd}/otp_batch.py 
        --config "{config_xml}" 
        --origins "{origins}" --destinations "{destinations}" 
        --target "{target}" --nlines {nlines}'''
        
        cmd = cmd.format(
            jar=OTP_JAR, 
            wd=working_dir, 
            config_xml = config_xml,
            origins=orig_tmp_filename, 
            destinations=dest_tmp_filename, 
            target=target_file,
            nlines=PRINT_EVERY_N_LINES
        )    
        
        times = config.settings['time']
        arrive_by = times['arrive_by']       
        if arrive_by == True or arrive_by == 'True':
            n_points = destination_layer.featureCount()       
        else:
            n_points = origin_layer.featureCount()     
            
        # how often will the stdout-indicator written before reaching 100%
        ticks = n_points/PRINT_EVERY_N_LINES
        time_batch = times['time_batch']
        batch_active = time_batch['active']
        if batch_active == 'True' or batch_active == True:
            dt_begin = datetime.strptime(times['datetime'], DATETIME_FORMAT)
            dt_end = datetime.strptime(time_batch['datetime_end'], DATETIME_FORMAT)
            n_iterations = (dt_end - dt_begin).total_seconds() / (int(time_batch['time_step']) * 60)
            ticks *= n_iterations + 1
            print (dt_end - dt_begin).total_seconds() / 60
            print n_iterations
            print ticks
                
        diag = ExecCommandDialog(cmd, parent=self.dlg.parent(), 
                                 auto_start=True, 
                                 progress_indicator='Processing:', 
                                 total_ticks=ticks)
        diag.exec_()
        
        ### cleanup and QGIS operations after OTP is done ###
        
        # remove temporary duplicated layer
        if result_mode == REACHABILITY: 
            QgsMapLayerRegistry.instance().removeMapLayer(destination_layer.id())
            
                
        # JOIN
        do_join = False
        if result_mode == AGGREGATION:
            do_join = self.dlg.aggregation_join_check.isChecked()
        elif result_mode == ACCUMULATION:
            do_join = self.dlg.accumulation_join_check.isChecked()    
        elif result_mode == REACHABILITY:
            do_join = self.dlg.reachability_join_check.isChecked()        
            
        if do_join or (result_mode == ORIGIN_DESTINATION and self.dlg.orig_dest_add_check.isChecked()):
            layer_name = 'results-{}-{}'.format(self.dlg.router_combo.currentText(),
                                                   self.dlg.origins_combo.currentText())
            if result_mode == AGGREGATION:
                layer_name += '-aggregiert'
            layer_name += '-' + now_string
            result_layer = self.iface.addVectorLayer(target_file, 
                                                     layer_name, 
                                                     'delimitedtext')
        else:
            # tmp files are no longer needed, if not added to qgis
            shutil.rmtree(tmp_dir) 
            
        if do_join:
            join = QgsVectorJoinInfo()
            join.joinLayerId = result_layer.id()
            join.joinFieldName = 'origin_id'  
            join.targetFieldName = config.settings['origin']['id_field']      
            origin_layer.addJoin(join)
            # TODO permanent join and remove result layer (origin_layer save as shape?)    
            # csv layer is only link to file, if temporary is removed you won't see anything later
            
    def run(self):
        '''
        called every time, the plugin is (re)started (so don't connect slots to signals here, otherwise they may be connected multiple times)
        '''
        
        # reload layer combos, if layers changed on rerun
        layers = self.iface.legendInterface().layers()     
        if layers != self.layers:
            self.fill_layer_combos(layers)
        
        # reload routers on every run (they might be changed outside)
        self.fill_router_combo()    
        
        # show the dialog
        self.dlg.show()                
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
from config import OTP_JAR, GRAPH_PATH, AVAILABLE_MODES, DATETIME_FORMAT
from dialogs import ExecCommandDialog, set_file
from qgis._core import QgsVectorLayer
from qgis.core import QgsVectorFileWriter
from time import strftime
import locale
import tempfile
import shutil
import time

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
        
        self.dlg.target_browse_button.clicked.connect(
            lambda: set_file(self.dlg, 
                             self.dlg.target_file_edit,
                             filters=['CSV-Dateien (*.csv)'],
                             directory=self.dlg.router_combo.currentText()+'-'+strftime('%d-%m-%Y-%H:%M')+'.csv', 
                             save=True)
        )              
                
        self.layer_list = []        
        self.dlg.origins_combo.currentIndexChanged.connect(
            lambda: self.fill_id_combo(self.dlg.origins_combo, self.dlg.origins_id_combo))   
        self.dlg.destinations_combo.currentIndexChanged.connect(
            lambda: self.fill_id_combo(self.dlg.destinations_combo, self.dlg.destinations_id_combo))                 
                    
        for mode in AVAILABLE_MODES:
            item = QListWidgetItem(self.dlg.mode_list_view)
            checkbox = QCheckBox(mode)
            self.dlg.mode_list_view.setItemWidget(item, checkbox)        

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&OTP')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'OTP')
        self.toolbar.setObjectName(u'OTP')

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
        
    def fill_id_combo(self, layer_combo, id_combo):  
        id_combo.clear()
        layer = self.layer_list[layer_combo.currentIndex()]
        fields = layer.pendingFields()
        field_names = [field.name() for field in fields]
        id_combo.addItems(field_names)

    def run(self):
        layers = self.iface.legendInterface().layers()
        
        self.set_date()
        self.dlg.calendar_edit.clicked.connect(self.set_date)          
        
        self.layer_list = []
        active_layer = self.iface.activeLayer()
        self.dlg.origins_combo.clear()   
        self.dlg.destinations_combo.clear()            
        i = 0
        idx = 0
        for layer in layers:            
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
        
        self.dlg.router_combo.clear()
        # subdirectories in graph-dir are treated as routers by OTP
        for subdir in os.listdir(GRAPH_PATH):
            self.dlg.router_combo.addItem(subdir) 
        
        working_dir = os.path.dirname(__file__)        
        
        # show the dialog
        self.dlg.show()        
        
        while True:
            # Run the dialog event loop
            ok = self.dlg.exec_()        
                    
            # if OK was pressed
            if ok:                            
                target_file = self.dlg.target_file_edit.text()
                target_path = os.path.dirname(target_file)          
                
                if not os.path.exists(target_path):
                    msg_box = QMessageBox(QMessageBox.Warning, "Fehler", u'Sie haben keinen gültigen Dateipfad angegeben.')
                    msg_box.exec_()
                    continue
                elif not os.access(target_path, os.W_OK):
                    msg_box = QMessageBox(QMessageBox.Warning, "Fehler", u'Sie haben keine Zugriffsberechtigung auf den Dateipfad.')
                    msg_box.exec_()
                    continue
                
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
                        continue                
                
                tmp_dir = tempfile.mkdtemp()
                orig_tmp_filename = os.path.join(tmp_dir, 'origins.csv')  
                dest_tmp_filename = os.path.join(tmp_dir, 'destinations.csv')    
                
                QgsVectorFileWriter.writeAsVectorFormat(origin_layer, orig_tmp_filename, "utf-8", None, "CSV", layerOptions="GEOMETRY=AS_WKT")
                QgsVectorFileWriter.writeAsVectorFormat(destination_layer, dest_tmp_filename, "utf-8", None, "CSV", layerOptions="GEOMETRY=AS_WKT")
                
                selected_modes = []
                for index in xrange(self.dlg.mode_list_view.count()):
                    checkbox = self.dlg.mode_list_view.itemWidget(self.dlg.mode_list_view.item(index))
                    if checkbox.checkState():
                        selected_modes.append(str(checkbox.text()))  
                        
                router = self.dlg.router_combo.currentText()
                oid = self.dlg.origins_id_combo.currentText()
                did = self.dlg.destinations_id_combo.currentText()
                
                d = self.dlg.calendar_edit.selectedDate()
                t = self.dlg.time_edit.time()
                dt = QDateTime(d)
                dt.setTime(t)                
                dt_string = dt.toPyDateTime().strftime(DATETIME_FORMAT)
                
                max_time = self.dlg.max_time_edit.value() * 60
                
                cmd = 'jython -Dpython.path="{jar}" {wd}/otp_batch.py --router {router} --origins "{origins}" --destinations "{destinations}" --oid {oid} --did {did} --target "{target}" --datetime {datetime} --maxtime {max_time}'.format(
                    jar=OTP_JAR, 
                    wd=working_dir, 
                    router=router, 
                    origins=orig_tmp_filename, 
                    destinations=dest_tmp_filename, 
                    oid=oid,
                    did=did,
                    datetime=dt_string,
                    target=target_file,
                    max_time=max_time
                )            
                diag = ExecCommandDialog(cmd, parent=self.dlg.parent(), auto_start=True)
                diag.exec_()
                
                shutil.rmtree(tmp_dir)
                break
                
            else:
                break
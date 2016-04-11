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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, QProcess
from PyQt4.QtGui import QAction, QIcon, QListWidgetItem, QCheckBox
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from OTP_dialog import OTPDialog
import os
from config import OTP_JAR, GRAPH_PATH, AVAILABLE_MODES
from dialogs import ExecCommandDialog
from qgis._core import QgsVectorLayer
from qgis.core import QgsVectorFileWriter
import tempfile
import shutil


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
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'OTP_{}.qm'.format(locale))

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


    def run(self):
        layers = self.iface.legendInterface().layers()
        
        layer_list = []
        active_layer = self.iface.activeLayer()
        i = 0
        idx = 0
        for layer in layers:            
            if isinstance(layer, QgsVectorLayer):
                if layer == active_layer:
                    idx = i
                layer_list.append(layer)
                self.dlg.origins_combo.addItem(layer.name())   
                self.dlg.destinations_combo.addItem(layer.name())     
                i += 1        
                
        # select active layer in comboboxes                    
        self.dlg.origins_combo.setCurrentIndex(idx)          
        self.dlg.destinations_combo.setCurrentIndex(idx)   
        
        # subdirectories in graph-dir are treated as routers by OTP
        for subdir in os.listdir(GRAPH_PATH):
            self.dlg.router_combo.addItem(subdir) 
            
        for mode in AVAILABLE_MODES:
            item = QListWidgetItem(self.dlg.mode_list_view)
            checkbox = QCheckBox(mode)
            self.dlg.mode_list_view.setItemWidget(item, checkbox)
        
        working_dir = os.path.dirname(__file__)        
        
        # show the dialog
        self.dlg.show()
        
        # Run the dialog event loop
        result = self.dlg.exec_()        
                
        # if OK was pressed
        if result:            
            
            origin_layer = layer_list[self.dlg.origins_combo.currentIndex()]
            destination_layer = layer_list[self.dlg.destinations_combo.currentIndex()]            
            
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
            
            cmd = 'jython -Dpython.path="{jar}" {wd}/otp_batch.py --router {router} --origins "{origins}" --destinations "{destinations}"'.format(
                jar=OTP_JAR, wd=working_dir, router='portland', origins=orig_tmp_filename, destinations=dest_tmp_filename)            
            diag = ExecCommandDialog(cmd, parent=self.dlg.parent(), auto_start=True)
            diag.exec_()
            
            shutil.rmtree(tmp_dir)
# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SmoothLayer
                                 A QGIS plugin
 Smoothes a raster layer
                              -------------------
        begin                : 2016-03-09
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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from smooth_layer_dialog import SmoothLayerDialog
from qgis._core import QgsRasterLayer
from qgis.core import QgsRasterPipe, QgsRasterFileWriter
import os.path
import tempfile
import subprocess

MIN_KERNEL_SIZE = 1
MAX_KERNEL_SIZE = 8
DEFAULT_KERNEL_SIZE = 4

MIN_KERNEL_BETA = -3
MAX_KERNEL_BETA = -0.001
DEFAULT_KERNEL_BETA= -2
FACTOR_KERNEL_BETA = 1000. # sliders work with int, for double ranges you have to convert to int with a factor

class SmoothLayer:
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
            'SmoothLayer_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = SmoothLayerDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&SmoothLayer')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'SmoothLayer')
        self.toolbar.setObjectName(u'SmoothLayer')

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
        return QCoreApplication.translate('SmoothLayer', message)


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
            self.iface.addPluginToRasterMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/SmoothLayer/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Smooth Raster Layer'),
            callback=self.run,
            parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginRasterMenu(
                self.tr(u'&SmoothLayer'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar


    def run(self):
        """Run method that performs all the real work"""
        
        # fill combobox with all raster-layers currently opened in qgis
        layers = self.iface.legendInterface().layers()
        layer_list = []
        active_layer = self.iface.activeLayer()
        i = 0
        idx = 0
        for layer in layers:            
            if isinstance(layer, QgsRasterLayer):
                if layer == active_layer:
                    idx = i
                layer_list.append(layer)
                self.dlg.layer_combo.addItem(layer.name())     
                i += 1
                
        # select active layer in combobox                    
        self.dlg.layer_combo.setCurrentIndex(idx)     
        
        # set the the sliders
        self.dlg.kernel_size_slider.setRange(MIN_KERNEL_SIZE, MAX_KERNEL_SIZE)
        self.dlg.kernel_size_slider.setValue(DEFAULT_KERNEL_SIZE)
        self.dlg.kernel_size_label.setNum(DEFAULT_KERNEL_SIZE)
        self.dlg.kernel_size_min_label.setText(str(MIN_KERNEL_SIZE))
        self.dlg.kernel_size_max_label.setText(str(MAX_KERNEL_SIZE))
        self.dlg.kernel_size_slider.valueChanged.connect(self.dlg.kernel_size_label.setNum)
        
        self.dlg.kernel_beta_slider.setRange(MIN_KERNEL_BETA * FACTOR_KERNEL_BETA, 
                                             MAX_KERNEL_BETA * FACTOR_KERNEL_BETA)  
        self.dlg.kernel_beta_slider.setValue(DEFAULT_KERNEL_BETA * FACTOR_KERNEL_BETA)
        self.dlg.kernel_beta_label.setText(str(DEFAULT_KERNEL_BETA))
        self.dlg.kernel_beta_slider.setTickInterval(100)
        self.dlg.kernel_beta_min_label.setText(str(MIN_KERNEL_BETA))
        self.dlg.kernel_beta_max_label.setText(str(MAX_KERNEL_BETA))
        
        self.dlg.kernel_beta_slider.valueChanged.connect(
            lambda: self.dlg.kernel_beta_label.setText(
                str(self.dlg.kernel_beta_slider.value() / FACTOR_KERNEL_BETA)))
        
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            idx = self.dlg.layer_combo.currentIndex()
            selected_layer = layer_list[idx]
            kernel_size = self.dlg.kernel_size_slider.value()
            kernel_beta = (self.dlg.kernel_beta_slider.value() / FACTOR_KERNEL_BETA)
            
            #tmp_dir = tempfile.mkdtemp()
            tmp_dir = '/home/cfr/Desktop/tmp/'
            tmp_filename = os.path.join(tmp_dir, '{}.tif'.format(selected_layer.name()))     
            
            self.raster_to_file(selected_layer, tmp_filename)
            
            self.call_smooth_process(tmp_filename, tmp_dir, kernel_size, kernel_beta)
            
            #smoothed_layer = self.iface.addRasterLayer(tmp_filename, selected_layer.name() + '_smoothed')   
            # transfer the style from the original layer to the smoothed layer
            #renderer = selected_layer.renderer().clone()
            #smoothed_layer.setRenderer(renderer)
            
            #shutil.rmtree(tmp_dir)
        
        # remove the items (they are always added again, when run() is called from QGis-UI)
        self.dlg.layer_combo.clear()
        
    def raster_to_file(self, layer, filename):
        '''
        write the contents of the raster-layer to a file (tif)
        '''
        extent = layer.extent()
        width, height = layer.width(), layer.height()
        
        # this kind of generating a pipe doesn't set the nodatavalue -> commented out, use provided pipe instead
        #pipe = QgsRasterPipe()
        #renderer = layer.renderer()
        #provider = layer.dataProvider()
        #pipe.set(provider.clone())
        #pipe.set(renderer.clone())
        
        pipe = layer.pipe()
        
        file_writer = QgsRasterFileWriter(filename)
        
        file_writer.writeRaster(pipe,
                                width,
                                height,
                                extent,
                                layer.crs())           
        
    def call_smooth_process(self, filename, working_folder, kernel_size, kernel_beta):
        commands = '''
        activate elan        
        python -m dichte_berlin.smooth --infile {in_file} --subfolder {out_folder} --kernelsize {kernel_size} --kernel_beta {kernel_beta}
        '''
        
        process = subprocess.Popen('/bin/bash', stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        out, err = process.communicate(commands.format(in_file=filename, 
                                                       out_folder = working_folder,
                                                       kernel_size=kernel_size, 
                                                       kernel_beta=kernel_beta))
        print commands.format(in_file=filename, 
                              out_folder = working_folder,
                              kernel_size=kernel_size, 
                              kernel_beta=kernel_beta)
        print out
        print err
        print process.returncode
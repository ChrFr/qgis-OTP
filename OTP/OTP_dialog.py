# -*- coding: utf-8 -*-
"""
/***************************************************************************
 OTPDialog
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

import os

from qgis.PyQt import QtGui, QtWidgets, uic

MAIN_FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui', 'OTP_main_window.ui'))


class OTPMainWindow(QtWidgets.QMainWindow, FORM_CLASS):
    def __init__(self, on_close=None, parent=None):
        """Constructor."""
        super().__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.on_close = on_close

    def closeEvent(self, evnt):
        if self.on_close:
            self.on_close()
        super().closeEvent(evnt)

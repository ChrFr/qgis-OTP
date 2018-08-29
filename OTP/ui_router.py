# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'router.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_RouterDialog(object):
    def setupUi(self, RouterDialog):
        RouterDialog.setObjectName("RouterDialog")
        RouterDialog.setWindowModality(QtCore.Qt.ApplicationModal)
        RouterDialog.resize(517, 331)
        RouterDialog.setMinimumSize(QtCore.QSize(410, 210))
        RouterDialog.setMaximumSize(QtCore.QSize(10000, 10000))
        RouterDialog.setModal(False)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(RouterDialog)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(spacerItem)
        self.textEdit = QtWidgets.QTextEdit(RouterDialog)
        self.textEdit.setEnabled(True)
        self.textEdit.setReadOnly(True)
        self.textEdit.setObjectName("textEdit")
        self.verticalLayout_2.addWidget(self.textEdit)
        self.label = QtWidgets.QLabel(RouterDialog)
        self.label.setObjectName("label")
        self.verticalLayout_2.addWidget(self.label)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.source_edit = QtWidgets.QLineEdit(RouterDialog)
        self.source_edit.setEnabled(True)
        self.source_edit.setReadOnly(True)
        self.source_edit.setObjectName("source_edit")
        self.horizontalLayout_2.addWidget(self.source_edit)
        self.source_browse_button = QtWidgets.QPushButton(RouterDialog)
        self.source_browse_button.setEnabled(True)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.source_browse_button.sizePolicy().hasHeightForWidth())
        self.source_browse_button.setSizePolicy(sizePolicy)
        self.source_browse_button.setMinimumSize(QtCore.QSize(30, 0))
        self.source_browse_button.setMaximumSize(QtCore.QSize(30, 16777215))
        self.source_browse_button.setObjectName("source_browse_button")
        self.horizontalLayout_2.addWidget(self.source_browse_button)
        self.verticalLayout_2.addLayout(self.horizontalLayout_2)
        spacerItem1 = QtWidgets.QSpacerItem(20, 5, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.verticalLayout_2.addItem(spacerItem1)
        self.label_2 = QtWidgets.QLabel(RouterDialog)
        self.label_2.setObjectName("label_2")
        self.verticalLayout_2.addWidget(self.label_2)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.router_name_edit = QtWidgets.QLineEdit(RouterDialog)
        self.router_name_edit.setEnabled(True)
        self.router_name_edit.setObjectName("router_name_edit")
        self.horizontalLayout_3.addWidget(self.router_name_edit)
        self.create_button = QtWidgets.QPushButton(RouterDialog)
        self.create_button.setObjectName("create_button")
        self.horizontalLayout_3.addWidget(self.create_button)
        self.verticalLayout_2.addLayout(self.horizontalLayout_3)
        spacerItem2 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(spacerItem2)
        spacerItem3 = QtWidgets.QSpacerItem(20, 5, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        self.verticalLayout_2.addItem(spacerItem3)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem4 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem4)
        self.close_button = QtWidgets.QPushButton(RouterDialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.close_button.sizePolicy().hasHeightForWidth())
        self.close_button.setSizePolicy(sizePolicy)
        self.close_button.setMinimumSize(QtCore.QSize(87, 23))
        self.close_button.setMaximumSize(QtCore.QSize(87, 23))
        self.close_button.setObjectName("close_button")
        self.horizontalLayout.addWidget(self.close_button)
        self.verticalLayout_2.addLayout(self.horizontalLayout)

        self.retranslateUi(RouterDialog)
        QtCore.QMetaObject.connectSlotsByName(RouterDialog)

    def retranslateUi(self, RouterDialog):
        _translate = QtCore.QCoreApplication.translate
        RouterDialog.setWindowTitle(_translate("RouterDialog", "Router erstellen"))
        self.textEdit.setHtml(_translate("RouterDialog", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'MS Shell Dlg 2\'; font-size:8.25pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Hinweis: Geben Sie einen Pfad zu einem Ordner mit den Eingangsdaten an. Dieser sollte folgende Daten für den Betrachtungsraum enthalten</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">- das OSM Straßennetz als PBF-Datei <span style=\" font-style:italic;\">(*.pbf)</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">- Fahrplandaten als GTFS Feed als Zip-Datei<span style=\" font-style:italic;\"> (*.zip, optional, für verschiedene Modi benötigt)</span></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">- Höhendaten als GeoTIFF <span style=\" font-style:italic;\">(*.tiff, optional)</span></p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Der erstellte Graph wird in ein Verzeichnis mit dem angegebenen Routernamen in das in den Systemeinstellungen eingestellte Routerverzeichnis kopiert.</p></body></html>"))
        self.label.setText(_translate("RouterDialog", "Verzeichnis mit den Eingangsdaten"))
        self.source_browse_button.setText(_translate("RouterDialog", "..."))
        self.label_2.setText(_translate("RouterDialog", "Name des zu erstellenden Routers (beginnend mit Buchstaben, keine Freizeichen oder Sonderzeichen)"))
        self.create_button.setText(_translate("RouterDialog", "Router erstellen"))
        self.close_button.setText(_translate("RouterDialog", "Schließen"))


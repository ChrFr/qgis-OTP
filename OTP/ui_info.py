# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'info.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_InfoDialog(object):
    def setupUi(self, InfoDialog):
        InfoDialog.setObjectName("InfoDialog")
        InfoDialog.resize(469, 184)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(InfoDialog.sizePolicy().hasHeightForWidth())
        InfoDialog.setSizePolicy(sizePolicy)
        self.verticalLayout = QtWidgets.QVBoxLayout(InfoDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label_2 = QtWidgets.QLabel(InfoDialog)
        self.label_2.setText("")
        self.label_2.setPixmap(QtGui.QPixmap(":/plugins/OTP/icon.png"))
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_2.addWidget(self.label_2)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(spacerItem)
        self.version_label = QtWidgets.QLabel(InfoDialog)
        self.version_label.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.version_label.setObjectName("version_label")
        self.verticalLayout_2.addWidget(self.version_label)
        self.label_3 = QtWidgets.QLabel(InfoDialog)
        self.label_3.setTextFormat(QtCore.Qt.RichText)
        self.label_3.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_3.setOpenExternalLinks(True)
        self.label_3.setObjectName("label_3")
        self.verticalLayout_2.addWidget(self.label_3)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(spacerItem1)
        self.label = QtWidgets.QLabel(InfoDialog)
        self.label.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label.setObjectName("label")
        self.verticalLayout_2.addWidget(self.label)
        self.label_38 = QtWidgets.QLabel(InfoDialog)
        self.label_38.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.label_38.setTextFormat(QtCore.Qt.RichText)
        self.label_38.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_38.setOpenExternalLinks(True)
        self.label_38.setObjectName("label_38")
        self.verticalLayout_2.addWidget(self.label_38)
        spacerItem2 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(spacerItem2)
        self.horizontalLayout_2.addLayout(self.verticalLayout_2)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        spacerItem3 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem3)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem4 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem4)
        self.close_button = QtWidgets.QPushButton(InfoDialog)
        self.close_button.setObjectName("close_button")
        self.horizontalLayout.addWidget(self.close_button)
        spacerItem5 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem5)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(InfoDialog)
        QtCore.QMetaObject.connectSlotsByName(InfoDialog)

    def retranslateUi(self, InfoDialog):
        _translate = QtCore.QCoreApplication.translate
        InfoDialog.setWindowTitle(_translate("InfoDialog", "Über"))
        self.version_label.setText(_translate("InfoDialog", "Version"))
        self.label_3.setText(_translate("InfoDialog", "<html><head/><body><p>Plugin für Routenberechnungen mit dem <a href=\"http://www.opentripplanner.org/\"><span style=\" text-decoration: underline; color:#0000ff;\">OpenTripPlanner</span></a></p></body></html>"))
        self.label.setText(_translate("InfoDialog", "entwickelt von "))
        self.label_38.setText(_translate("InfoDialog", "<html><head/><body><p><a href=\"http://www.ggr-planung.de\"><span style=\" text-decoration: underline; color:#0000ff;\">GGR Stadtentwicklung und Mobilität Planung Beratung Forschung GbR</span></a></p></body></html>"))
        self.close_button.setText(_translate("InfoDialog", "OK"))

#import resources

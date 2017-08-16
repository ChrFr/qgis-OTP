# -*- coding: utf-8 -*-
from PyQt4 import QtGui, QtCore
from qgis.core import (QgsCategorizedSymbolRendererV2,
                       QgsSingleSymbolRendererV2, QgsMarkerSymbolV2)


class Symbology(object):
    def __init__(self):
        pass
    
    def apply(self, layer):
        layer.setRendererV2(self.renderer)


class SimpleSymbology(Symbology):
    def __init__(self, color, shape='circle'):
        super(SimpleSymbology, self).__init__()
        self.color = color
        self.shape = shape
        symbol = QgsMarkerSymbolV2.createSimple({'name': self.shape,
                                                 'color': color})
        self.renderer = QgsSingleSymbolRendererV2(symbol)


class CategorizedSymbology(Symbology):
    def __init__(self):
        super(CategorizedSymbology, self).__init__()
        self.renderer = QgsCategorizedSymbolRendererV2()


class LabeledSlider(QtGui.QWidget):
    def __init__(self, min, max):
        super(LabeledSlider, self).__init__()
        self.min_label = QtGui.QLabel(str(min))
        self.max_label = QtGui.QLabel(str(max))
        self.slider = QtGui.QSlider(QtCore.Qt.Horizontal)
        layout = QtGui.QHBoxLayout()
        layout.addWidget(self.min_label)
        layout.addWidget(self.slider)
        layout.addWidget(self.max_label)
        self.setLayout(layout)

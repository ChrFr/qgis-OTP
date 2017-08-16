# -*- coding: utf-8 -*-
from PyQt4 import QtGui, QtCore
from qgis.core import (QgsGraduatedSymbolRendererV2, QgsStyleV2, 
                       QgsSingleSymbolRendererV2, QgsMarkerSymbolV2,
                       QgsRendererRangeV2, QgsSymbolV2)


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
        
    def apply(self, layer):
        symbol = QgsMarkerSymbolV2.createSimple({'name': self.shape,
                                                 'color': self.color})
        self.renderer = QgsSingleSymbolRendererV2(symbol)
        super(SimpleSymbology, self).apply(layer)


class GraduatedSymbology(Symbology):
    """
    field: str
        the field of the underlying table to classify
    """
    def __init__(self, field, ranges, no_pen=False):
        super(GraduatedSymbology, self).__init__()
        self.field = field
        self.ranges = ranges
        self.no_pen = no_pen
        
    def apply(self, layer):
        ranges = []
        for lower, upper, label, color in self.ranges:
            symbol = QgsSymbolV2.defaultSymbol(layer.geometryType())
            symbol.setColor(color)
            if self.no_pen:
                symbol.setOutputUnit(1)
            ranges.append(QgsRendererRangeV2(lower, upper, symbol, label))
        self.renderer = QgsGraduatedSymbolRendererV2(self.field, ranges)
        #self.renderer.setClassAttribute(self.field)
        #self.renderer.setSourceColorRamp(self.color_ramp)
        #self.renderer.setInvertedColorRamp(self.inverted)
        #self.renderer.updateColorRamp(inverted=self.inverted)
        super(GraduatedSymbology, self).apply(layer)



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

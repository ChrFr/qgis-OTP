# -*- coding: utf-8 -*-
from PyQt4 import QtGui, QtCore, Qt
from qgis.core import (QgsGraduatedSymbolRendererV2, QgsStyleV2, 
                       QgsSingleSymbolRendererV2, QgsMarkerSymbolV2,
                       QgsRendererRangeV2, QgsSymbolV2)

CSV_FILTER = u'Comma-seperated values (*.csv)'
KML_FILTER = u'Keyhole Markup Language (*.kml)'
PDF_FILTER = u'PDF (*.pdf)'

def browse_file(file_preset, title, file_filter, save=True, parent=None):
    
    if save:
        browse_func = QtGui.QFileDialog.getSaveFileName
    else:
        browse_func = QtGui.QFileDialog.getOpenFileName
        
    filename = str(
        browse_func(
            parent=parent, 
            caption=title,
            directory=file_preset,
            filter=file_filter
        )
    )   
    return filename


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



class LabeledRangeSlider(QtGui.QWidget):
    def __init__(self, min, max):
        super(LabeledRangeSlider, self).__init__()
        self.min_label = QtGui.QLabel(str(min))
        self.max_label = QtGui.QLabel(str(max))
        self.slider = RangeSlider(Qt.Qt.Horizontal)
        self.slider.setMinimum(min)
        self.slider.setMaximum(max)
        self.slider.setLow(min)
        self.slider.setHigh(max)
        self.slider.setTickPosition(QtGui.QSlider.TicksAbove)
        self.slider.setTickInterval(10)
        layout = QtGui.QHBoxLayout()
        layout.addWidget(self.min_label)
        layout.addWidget(self.slider)
        layout.addWidget(self.max_label)
        self.setLayout(layout)
        
        self.slider.sliderMoved.connect(self.update)
    
    @property
    def min(self):
        return self.slider.low()
    
    @property
    def max(self):
        return self.slider.high()
    
    def update(self):
        self.min_label.setText(str(self.min))
        self.max_label.setText(str(self.max))


class RangeSlider(QtGui.QSlider):
    """ taken from https://www.mail-archive.com/pyqt@riverbankcomputing.com/msg22889.html
    """
    def __init__(self, *args):
        super(RangeSlider, self).__init__(*args)
        #self.setOrientation(QtCore.Qt.Horizontal)
        self._low = self.minimum()
        self._high = self.maximum()
        
        self.pressed_control = QtGui.QStyle.SC_None
        self.hover_control = QtGui.QStyle.SC_None
        self.click_offset = 0
        
        # 0 for the low, 1 for the high, -1 for both
        self.active_slider = 0

    def low(self):
        return self._low

    def setLow(self, low):
        self._low = low
        self.update()

    def high(self):
        return self._high

    def setHigh(self, high):
        self._high = high
        self.update()
        
    def paintEvent(self, event):
        # based on http://qt.gitorious.org/qt/qt/blobs/master/src/gui/widgets/qslider.cpp

        painter = QtGui.QPainter(self)
        style = QtGui.QApplication.style() 
        
        for i, value in enumerate([self._low, self._high]):
            opt = QtGui.QStyleOptionSlider()
            self.initStyleOption(opt)

            # Only draw the groove for the first slider so it doesn't get drawn
            # on top of the existing ones every time
            if i == 0:
                opt.subControls = QtGui.QStyle.SC_SliderHandle#QtGui.QStyle.SC_SliderGroove | QtGui.QStyle.SC_SliderHandle
            else:
                opt.subControls = QtGui.QStyle.SC_SliderHandle

            if self.tickPosition() != self.NoTicks:
                opt.subControls |= QtGui.QStyle.SC_SliderTickmarks

            if self.pressed_control:
                opt.activeSubControls = self.pressed_control
                opt.state |= QtGui.QStyle.State_Sunken
            else:
                opt.activeSubControls = self.hover_control

            opt.sliderPosition = value
            opt.sliderValue = value                                  
            style.drawComplexControl(QtGui.QStyle.CC_Slider, opt, painter, self)
            
        
    def mousePressEvent(self, event):
        event.accept()
        
        style = QtGui.QApplication.style()
        button = event.button()
        
        # In a normal slider control, when the user clicks on a point in the 
        # slider's total range, but not on the slider part of the control the
        # control would jump the slider value to where the user clicked.
        # For this control, clicks which are not direct hits will slide both
        # slider parts
                
        if button:
            opt = QtGui.QStyleOptionSlider()
            self.initStyleOption(opt)

            self.active_slider = -1
            
            for i, value in enumerate([self._low, self._high]):
                opt.sliderPosition = value                
                hit = style.hitTestComplexControl(style.CC_Slider, opt, event.pos(), self)
                if hit == style.SC_SliderHandle:
                    self.active_slider = i
                    self.pressed_control = hit
                    
                    self.triggerAction(self.SliderMove)
                    self.setRepeatAction(self.SliderNoAction)
                    self.setSliderDown(True)
                    break

            if self.active_slider < 0:
                self.pressed_control = QtGui.QStyle.SC_SliderHandle
                self.click_offset = self.__pixelPosToRangeValue(self.__pick(event.pos()))
                self.triggerAction(self.SliderMove)
                self.setRepeatAction(self.SliderNoAction)
        else:
            event.ignore()
                                
    def mouseMoveEvent(self, event):
        if self.pressed_control != QtGui.QStyle.SC_SliderHandle:
            event.ignore()
            return
        
        event.accept()
        new_pos = self.__pixelPosToRangeValue(self.__pick(event.pos()))
        opt = QtGui.QStyleOptionSlider()
        self.initStyleOption(opt)
        
        if self.active_slider < 0:
            offset = new_pos - self.click_offset
            self._high += offset
            self._low += offset
            if self._low < self.minimum():
                diff = self.minimum() - self._low
                self._low += diff
                self._high += diff
            if self._high > self.maximum():
                diff = self.maximum() - self._high
                self._low += diff
                self._high += diff            
        elif self.active_slider == 0:
            if new_pos >= self._high:
                new_pos = self._high - 1
            self._low = new_pos
        else:
            if new_pos <= self._low:
                new_pos = self._low + 1
            self._high = new_pos

        self.click_offset = new_pos

        self.update()

        self.emit(QtCore.SIGNAL('sliderMoved(int)'), new_pos)
            
    def __pick(self, pt):
        if self.orientation() == QtCore.Qt.Horizontal:
            return pt.x()
        else:
            return pt.y()
           
           
    def __pixelPosToRangeValue(self, pos):
        opt = QtGui.QStyleOptionSlider()
        self.initStyleOption(opt)
        style = QtGui.QApplication.style()
        
        gr = style.subControlRect(style.CC_Slider, opt, style.SC_SliderGroove, self)
        sr = style.subControlRect(style.CC_Slider, opt, style.SC_SliderHandle, self)
        
        if self.orientation() == QtCore.Qt.Horizontal:
            slider_length = sr.width()
            slider_min = gr.x()
            slider_max = gr.right() - slider_length + 1
        else:
            slider_length = sr.height()
            slider_min = gr.y()
            slider_max = gr.bottom() - slider_length + 1
            
        return style.sliderValueFromPosition(self.minimum(), self.maximum(),
                                             pos-slider_min, slider_max-slider_min,
                                             opt.upsideDown)


class WaitDialog(QtGui.QDialog):
    
    def __init__(self, function, title='...', label='Bitte warten...',
                 parent=None):
        super(WaitDialog, self).__init__(parent)
        self.setWindowTitle(title)
        vbox_layout = QtGui.QVBoxLayout(self)
        label = QtGui.QLabel(label)
        label.setAlignment(QtCore.Qt.AlignCenter)
        vbox_layout.addWidget(label)
        self.setModal(True)
        self.setMinimumSize(200, 20)


class WaitThread(QtCore.QThread):
    finished = QtCore.pyqtSignal()
    def __init__ (self, function, parent_thread):
        super(WaitThread, self).__init__(parent_thread)
        self.function = function
        self.result = None
    def run(self):
        self.result = self.function()
        self.finished.emit()


class WaitDialogThreaded(WaitDialog):
    finished = QtCore.pyqtSignal()
    
    def __init__(self, function, label='Bitte warten...',
                 parent=None, parent_thread=None):
        super(WaitDialog2, self).__init__(parent)
        self.setMinimumSize(200, 75)
        self.thread = WaitThread(function, parent_thread or parent)
        self.thread.finished.connect(self._close)
        self.done = False
        self.show()
        self.thread.start()
        
    def _close(self):
        self.done = True
        self.finished.emit()
        self.close()
        
    @property    
    def result(self):
        return self.thread.result
        
    # disable closing of wait window
    def closeEvent(self, evnt):
        if self.done:
            super(WaitDialog, self).closeEvent(evnt)
        else:
            evnt.ignore() 
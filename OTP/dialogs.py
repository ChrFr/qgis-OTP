# -*- coding: utf-8 -*-
from ui_progress import Ui_ProgressDialog
from PyQt4 import QtCore, QtGui
import copy, os, re, sys, datetime

# WARNING: doesn't work in QGIS, because it doesn't support the QString module anymore (autocast to str)
try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s
    
DEFAULT_STYLE = """
QProgressBar{
    border: 2px solid grey;
    border-radius: 5px;
    text-align: center
}

QProgressBar::chunk {
    background-color: lightblue;
    width: 10px;
    margin: 1px;
}
"""

FINISHED_STYLE = """
QProgressBar{
    border: 2px solid grey;
    border-radius: 5px;
    text-align: center
}

QProgressBar::chunk {
    background-color: green;
    width: 10px;
    margin: 1px;
}
"""

ABORTED_STYLE = """
QProgressBar{
    border: 2px solid red;
    border-radius: 5px;
    text-align: center
}

QProgressBar::chunk {
    background-color: red;
    width: 10px;
    margin: 1px;
}
"""

                    
class ProgressDialog(QtGui.QDialog, Ui_ProgressDialog):
    """
    Dialog showing progress in textfield and bar after starting a certain task with run()
    """
    def __init__(self, parent=None, auto_close=False):
        super(ProgressDialog, self).__init__(parent=parent)
        self.parent = parent
        self.setupUi(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.progress_bar.setStyleSheet(DEFAULT_STYLE)
        self.progress_bar.setValue(0)
        self.cancelButton.clicked.connect(self.close)
        self.startButton.clicked.connect(self.run)
        self.auto_close = auto_close

    def running(self):
        self.startButton.setEnabled(False)
        self.cancelButton.setText('Stoppen')
        self.cancelButton.clicked.disconnect(self.close)

    def stopped(self):
        self.startButton.setEnabled(True)
        self.cancelButton.setText('Beenden')
        self.cancelButton.clicked.connect(self.close)
        if self.auto_close:
            self.close()

    def show_status(self, text, progress=None):
        if hasattr(text, 'toLocal8Bit'):
            text = str(text.toLocal8Bit())
        else:
            text = _fromUtf8(text)
        self.log_edit.insertHtml(text + '<br>')
        self.log_edit.moveCursor(QtGui.QTextCursor.End)
        if progress:
            if isinstance(progress, QtCore.QVariant):
                progress = progress.toInt()[0]
            self.progress_bar.setValue(progress)

    # task needs to be overridden
    def run(self):        
        pass


class ExecOTPDialog(ProgressDialog):
    """
    ProgressDialog extented by an executable external process
    
    Parameters
    ----------
    n_iterations: number of iterations (like multiple time windows)
    n_points: number of points to calculate in one iteration
    points_per_tick: how many points are calculated before showing progress
    """
    def __init__(self, command, parent=None, auto_close=False, auto_start=False, n_iterations=1, n_points=0, points_per_tick=50):
        super(ExecOTPDialog, self).__init__(parent=parent, auto_close=auto_close)

        # QProcess object for external app
        self.process = QtCore.QProcess(self)
        self.auto_close = auto_close
        self.command = command
        self.start_time = 0
        
        self.success = False

        # aux. variable to determine if process was killed, because exit code of killed process can't be distinguished from normal exit in linux
        self.killed = False
        
        self.ticks = 0.
        self.iterations = 0

        # Just to prevent accidentally running multiple times
        # Disable the button when process starts, and enable it when it finishes
        self.process.started.connect(self.running)
        self.process.finished.connect(self.finished)
        
        # how often will the stdout-indicator written before reaching 100%
        n_ticks = n_points / points_per_tick    
        print n_ticks
        n_ticks *= n_iterations
        print n_ticks
        print n_iterations
        tick_indicator = 'Processing:'
        iteration_finished_indicator = 'A total of'
        
        # leave some space for post processing
        max_progress = 98.
        
        def show_progress():
            out = str(self.process.readAllStandardOutput())
            err = str(self.process.readAllStandardError())
            if len(out):                 
                self.show_status(out)
                if out.startswith(tick_indicator) and n_ticks:
                    self.ticks += 1
                    self.progress_bar.setValue(min(max_progress, int(self.ticks * max_progress / n_ticks)))      
                elif out.startswith(iteration_finished_indicator):
                    self.iterations += 1                      
                    self.progress_bar.setValue(self.iterations * max_progress / n_iterations)  
                        
                '''  this approach shows progress more accurately, but may cause extreme lags -> deactivated (alternative: thread this)
                if out.startswith(progress_indicator):
                    # sometimes the stdout comes in too fast, you have to split it (don't split other than progress messages, warnings tend to be very long with multiple breaks, bad performance)
                    for out_split in out.split("\n"):    
                        if (len(out_split) == 0):
                            continue
                        self.show_status(out_split)                        
                        if(total_ticks and out_split.startswith(progress_indicator)):
                            self.ticks += 100. / total_ticks
                            self.progress_bar.setValue(min(100, int(self.ticks)))       
                else:                  
                    self.show_status(out)                                        
                '''
            if len(err): self.show_status(err)
            
        self.process.readyReadStandardOutput.connect(show_progress)
        self.process.readyReadStandardError.connect(show_progress) 
        
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        
        if auto_start:
            self.startButton.clicked.emit(True)

    def running(self):
        self.cancelButton.clicked.connect(self.kill)
        super(ExecOTPDialog, self).running()

    def stopped(self):
        self.cancelButton.clicked.disconnect(self.kill)
        super(ExecOTPDialog, self).stopped()

    def finished(self):
        self.timer.stop()
        if self.process.exitCode() == QtCore.QProcess.NormalExit and not self.killed:
            self.progress_bar.setValue(100)
            self.progress_bar.setStyleSheet(FINISHED_STYLE)
            self.success = True
        else:
            self.progress_bar.setStyleSheet(ABORTED_STYLE)
            self.success = False
        self.stopped()

    def kill(self):
        self.timer.stop()
        self.killed = True
        self.process.kill()
        self.log_edit.insertHtml('<b> Vorgang abgebrochen </b> <br>')
        self.log_edit.moveCursor(QtGui.QTextCursor.End)
        self.success = False
        
    def run(self):       
        self.killed = False
        self.ticks = 0
        self.progress_bar.setStyleSheet(DEFAULT_STYLE)        
        self.progress_bar.setValue(0)
        self.show_status('<br>Starte Script: <i>' + self.command + '</i><br>')
        self.process.start(self.command)
        self.start_time = datetime.datetime.now()
        self.timer.start(1000)
        
    def update_timer(self):
        delta = datetime.datetime.now() - self.start_time
        h, remainder = divmod(delta.seconds, 3600)
        m, s = divmod(remainder, 60)
        timer_text = '{:02d}:{:02d}:{:02d}'.format(h, m, s)
        self.elapsed_time_label.setText(timer_text)
        

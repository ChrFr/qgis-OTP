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

ALL_FILES_FILTER = 'Alle Dateien (*.*)'

def browse_file(parent, directory=None, filters=[ALL_FILES_FILTER], selected_filter_idx=0, save=False):
    filter = _fromUtf8(';;'.join(filters))
    # disabled because autocast of QString to str in QGIS, but selected filter of QFileDialogs expect QString   
    #selected_filter = _fromUtf8(filters[selected_filter_idx]
    selected_filter=None
    if save:
        filename = str(
            QtGui.QFileDialog.getSaveFileName(
                parent=parent, 
                caption=u'Datei speichern',
                directory=directory,
                filter=filter
            ))
    else:        
        filename = str(
            QtGui.QFileDialog.getOpenFileName(
                parent=parent, 
                caption=u'Datei öffnen',
                directory=directory,
                filter=filter,
                selectedFilter=selected_filter
            ))        
    return filename 
    
def set_file(parent, line_edit, directory=None, filters=[ALL_FILES_FILTER], selected_filter_idx=0, do_split=False, save=False):
    '''
    open a file browser to put a path to a file into the given line edit
    '''    
    # set directory to directory of current entry if not given
    if not directory:
        try:
            directory = os.path.split(str(line_edit.text()))[0]
        except:
            directory = ''

    filename = browse_file(parent, directory=directory, filters=filters,
                          selected_filter_idx=selected_filter_idx, save=save)

    if do_split:
        filename = os.path.split(filename)[0]

    # filename is '' if canceled
    if len(filename) > 0:
        line_edit.setText(filename)

def set_directory(parent, line_edit):
    dirname = str(
            QtGui.QFileDialog.getExistingDirectory(
                parent, u'Zielverzeichnis wählen'))
    # dirname is '' if canceled
    if len(dirname) > 0:
        line_edit.setText(dirname)
                    
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


class ExecCommandDialog(ProgressDialog):
    """
    ProgressDialog extented by an executable external process
    
    Parameters
    ----------
    progress_indicator: string indicating that process progressed (read from stdout, it has to start with this string to indicate progress)
    total_ticks: times the progress_indicator appears in stdout until you reach 100 percent
    """
    def __init__(self, command, parent=None, auto_close=False, auto_start=False, progress_indicator='', total_ticks=0):
        super(ExecCommandDialog, self).__init__(parent=parent, auto_close=auto_close)

        # QProcess object for external app
        self.process = QtCore.QProcess(self)
        self.auto_close = auto_close
        self.command = command
        self.start_time = 0

        # aux. variable to determine if process was killed, because exit code of killed process can't be distinguished from normal exit in linux
        self.killed = False
        
        self.ticks = 0.

        # Just to prevent accidentally running multiple times
        # Disable the button when process starts, and enable it when it finishes
        self.process.started.connect(self.running)
        self.process.finished.connect(self.finished)
        
        def show_progress():
            out = str(self.process.readAllStandardOutput())
            err = str(self.process.readAllStandardError())
            if len(out):                 
                self.show_status(out)
                if total_ticks and out.startswith(progress_indicator):
                    self.ticks += 100. / total_ticks
                    self.progress_bar.setValue(min(100, int(self.ticks)))            
                
            if len(err): self.show_status(err)
            
        self.process.readyReadStandardOutput.connect(show_progress)
        self.process.readyReadStandardError.connect(show_progress) 
        
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        
        if auto_start:
            self.startButton.clicked.emit(True)

    def running(self):
        self.cancelButton.clicked.connect(self.kill)
        super(ExecCommandDialog, self).running()

    def stopped(self):
        self.cancelButton.clicked.disconnect(self.kill)
        super(ExecCommandDialog, self).stopped()

    def finished(self):
        self.timer.stop()
        if self.process.exitCode() == QtCore.QProcess.NormalExit and not self.killed:
            self.progress_bar.setValue(100)
            self.progress_bar.setStyleSheet(FINISHED_STYLE)
        else:
            self.progress_bar.setStyleSheet(ABORTED_STYLE)
        self.stopped()

    def kill(self):
        self.timer.stop()
        self.killed = True
        self.process.kill()
        self.log_edit.insertHtml('<b> Vorgang abgebrochen </b> <br>')
        self.log_edit.moveCursor(QtGui.QTextCursor.End)
        
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
        

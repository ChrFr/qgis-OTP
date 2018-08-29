# -*- coding: utf-8 -*-
from builtins import str
from .ui_progress import Ui_ProgressDialog
from .ui_router import Ui_RouterDialog
from qgis.PyQt import QtCore, QtGui, QtWidgets
import copy, os, re, sys, datetime
from shutil import move

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


class ProgressDialog(QtWidgets.QDialog, Ui_ProgressDialog):
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

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_timer)


    def running(self):
        self.startButton.setEnabled(False)
        self.cancelButton.setText('Stoppen')
        self.cancelButton.clicked.disconnect(self.close)

    def stopped(self):
        self.timer.stop()
        self.startButton.setEnabled(True)
        self.cancelButton.setText('Beenden')
        self.cancelButton.clicked.connect(self.close)
        if self.auto_close:
            self.close()

    def show_status(self, text, progress=None):
        #if hasattr(text, 'toLocal8Bit'):
            #text = str(text.toLocal8Bit())
        #else:
            #text = _fromUtf8(text)
        self.log_edit.insertHtml(text + '<br>')
        self.log_edit.moveCursor(QtGui.QTextCursor.End)
        if progress:
            if isinstance(progress, QtCore.QVariant):
                progress = progress.toInt()[0]
            self.progress_bar.setValue(progress)

    # task needs to be overridden
    def run(self):
        self.start_time = datetime.datetime.now()
        self.timer.start(1000)

    def update_timer(self):
        delta = datetime.datetime.now() - self.start_time
        h, remainder = divmod(delta.seconds, 3600)
        m, s = divmod(remainder, 60)
        timer_text = '{:02d}:{:02d}:{:02d}'.format(h, m, s)
        self.elapsed_time_label.setText(timer_text)


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
        n_ticks = float(n_points) / points_per_tick
        n_ticks *= n_iterations
        tick_indicator = 'Processing:'
        iteration_finished_indicator = 'A total of'

        # leave some space for post processing
        max_progress = 98.

        def show_progress():
            out = self.process.readAllStandardOutput()
            out = str(out.data(), encoding='utf-8')
            err = self.process.readAllStandardError()
            err = str(err.data(), encoding='utf-8')
            if len(out):
                self.show_status(out)
                if tick_indicator in out and n_ticks:
                    self.ticks += max_progress / n_ticks
                    self.progress_bar.setValue(min(max_progress, int(self.ticks)))
                elif iteration_finished_indicator in out:
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
        def error(sth):
            self.kill()
        self.process.errorOccurred.connect(error)
        if auto_start:
            self.startButton.clicked.emit(True)

    def running(self):
        self.cancelButton.clicked.connect(self.kill)
        super(ExecOTPDialog, self).running()

    def stopped(self):
        self.cancelButton.clicked.disconnect(self.kill)
        super(ExecOTPDialog, self).stopped()

    def finished(self):
        self.startButton.setText('Neustart')
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


class ExecCreateRouterDialog(ProgressDialog):
    def __init__(self, source_folder, target_folder,
                 java_executable, otp_jar,
                 parent=None):
        super(ExecCreateRouterDialog, self).__init__(parent=parent)
        self.target_folder = target_folder
        self.source_folder = source_folder
        self.command = '''
        "{javacmd}" -jar "{otp_jar}"
        --build "{folder}"
        '''.format(javacmd=java_executable,
                   otp_jar=otp_jar,
                   folder=source_folder)
        self.process = QtCore.QProcess(self)
        self.process.started.connect(self.running)
        self.process.finished.connect(self.finished)
        def show_progress():
            out = self.process.readAllStandardOutput()
            out = str(out.data(), encoding='utf-8')
            err = self.process.readAllStandardError()
            err = str(err.data(), encoding='utf-8')
            if len(out):
                self.show_status(out)
            if len(err): self.show_status(err)

        self.process.readyReadStandardOutput.connect(show_progress)
        self.process.readyReadStandardError.connect(show_progress)

    def run(self):
        self.killed = False
        self.progress_bar.setStyleSheet(DEFAULT_STYLE)
        self.progress_bar.setValue(0)
        self.process.start(self.command)

    def running(self):
        self.cancelButton.clicked.connect(self.kill)
        super(ExecCreateRouterDialog, self).running()

    def stopped(self):
        self.cancelButton.clicked.disconnect(self.kill)
        super(ExecCreateRouterDialog, self).stopped()

    def finished(self):
        self.startButton.setText('Neustart')
        self.timer.stop()
        if self.process.exitCode() == QtCore.QProcess.NormalExit and not self.killed:
            self.show_status("graph created...")
            self.progress_bar.setValue(100)
            self.progress_bar.setStyleSheet(FINISHED_STYLE)
            graph_file = os.path.join(self.source_folder, "Graph.obj")
            dst_file = os.path.join(self.target_folder, "Graph.obj")
            if not os.path.exists(self.target_folder):
                self.show_status("creating target folder in router directory...")
                os.makedirs(self.target_folder)
            if graph_file != dst_file:
                if os.path.exists(dst_file):
                    self.show_status("overwriting old graph...")
                    os.remove(dst_file)
                self.show_status("moving graph to target location...")
                move(graph_file, dst_file)
            self.show_status("done")
        else:
            self.progress_bar.setStyleSheet(ABORTED_STYLE)
        self.stopped()

    def kill(self):
        self.timer.stop()
        self.killed = True
        self.process.kill()
        self.log_edit.insertHtml('<b> Vorgang abgebrochen </b> <br>')
        self.log_edit.moveCursor(QtGui.QTextCursor.End)


class RouterDialog(QtWidgets.QDialog, Ui_RouterDialog):
    def __init__(self, graph_path, java_executable, otp_jar, parent=None):
        super(RouterDialog, self).__init__(parent=parent)
        self.graph_path = graph_path
        self.java_executable = java_executable
        self.otp_jar = otp_jar
        self.setupUi(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.close_button.clicked.connect(self.close)
        self.source_browse_button.clicked.connect(self.browse_source_path)

        # name has to start with letter, no spaces or special characters
        regex = QtCore.QRegExp("[A-Za-z][A-Za-z0-9_]*")
        validator = QtGui.QRegExpValidator(regex, self)
        self.router_name_edit.setValidator(validator)

        self.create_button.clicked.connect(self.run)

    def browse_source_path(self):
        path = str(
            QtWidgets.QFileDialog.getExistingDirectory(
                self,
                u'Verzeichnis mit Eingangsdaten wählen',
                self.source_edit.text()
            )
        )
        if not path:
            return
        self.source_edit.setText(path)

    def run(self):
        name = self.router_name_edit.text()
        path = self.source_edit.text()
        if not name:
            return
        target_folder = os.path.join(self.graph_path, name)
        diag = ExecCreateRouterDialog(path, target_folder,
                                      self.java_executable, self.otp_jar,
                                      parent=self)
        diag.exec_()


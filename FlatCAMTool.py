############################################################
# FlatCAM: 2D Post-processing for Manufacturing            #
# http://flatcam.org                                       #
# Author: Juan Pablo Caram (c)                             #
# Date: 2/5/2014                                           #
# MIT Licence                                              #
############################################################

from PyQt5 import QtGui, QtWidgets


class FlatCAMTool(QtWidgets.QWidget):

    toolName = "FlatCAM Generic Tool"

    def __init__(self, app, parent=None):
        """

        :param app: The application this tool will run in.
        :type app: App
        :param parent: Qt Parent
        :return: FlatCAMTool
        """
        QtWidgets.QWidget.__init__(self, parent)

        # self.setSizePolicy(QtGui.QSizePolicy.Maximum, QtGui.QSizePolicy.Maximum)

        self.layout = QtGui.QVBoxLayout()
        self.setLayout(self.layout)

        self.app = app

        self.menuAction = None

    def install(self):
        self.menuAction = self.app.ui.menutool.addAction(self.toolName)
        self.menuAction.triggered.connect(self.run)

    def run(self):
        # Remove anything else in the GUI
        self.app.ui.tool_scroll_area.takeWidget()

        # Put ourself in the GUI
        self.app.ui.tool_scroll_area.setWidget(self)

        # Switch notebook to tool page
        self.app.ui.notebook.setCurrentWidget(self.app.ui.tool_tab)

        self.show()

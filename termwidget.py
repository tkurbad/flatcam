"""
Terminal emulator widget.
Shows intput and output text. Allows to enter commands. Supports history.
"""

import cgi
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QColor, QKeySequence, QPalette, \
                        QTextCursor
from PyQt5.QtWidgets import QLineEdit, QSizePolicy, QTextEdit, \
                            QVBoxLayout, QWidget


class _ExpandableTextEdit(QTextEdit):
    """
    Class implements edit line, which expands themselves automatically
    """

    historyNext = pyqtSignal()
    historyPrev = pyqtSignal()

    def __init__(self, termwidget, *args):
        QTextEdit.__init__(self, *args)
        self.setStyleSheet("font: 9pt \"Courier\";")
        self._fittedHeight = 1
        self.textChanged.connect(self._fit_to_document)
        self._fit_to_document()
        self._termWidget = termwidget

    def sizeHint(self):
        """
        QWidget sizeHint impelemtation
        """
        hint = QTextEdit.sizeHint(self)
        hint.setHeight(self._fittedHeight)
        return hint

    def _fit_to_document(self):
        """
        Update widget height to fit all text
        """
        documentsize = self.document().size().toSize()
        self._fittedHeight = documentsize.height() + (self.height() - self.viewport().height())
        self.setMaximumHeight(self._fittedHeight)
        self.updateGeometry()

    def keyPressEvent(self, event):
        """
        Catch keyboard events. Process Enter, Up, Down
        """
        if event.matches(QKeySequence.InsertParagraphSeparator):
            text = self.toPlainText()
            if self._termWidget.is_command_complete(text):
                self._termWidget.exec_current_command()
                return
        elif event.matches(QKeySequence.MoveToNextLine):
            text = self.toPlainText()
            cursor_pos = self.textCursor().position()
            textBeforeEnd = text[cursor_pos:]
            # if len(textBeforeEnd.splitlines()) <= 1:
            if len(textBeforeEnd.split('\n')) <= 1:
                self.historyNext.emit()
                return
        elif event.matches(QKeySequence.MoveToPreviousLine):
            text = self.toPlainText()
            cursor_pos = self.textCursor().position()
            text_before_start = text[:cursor_pos]
            # lineCount = len(textBeforeStart.splitlines())
            line_count = len(text_before_start.split('\n'))
            if len(text_before_start) > 0 and \
                    (text_before_start[-1] == '\n' or text_before_start[-1] == '\r'):
                line_count += 1
            if line_count <= 1:
                self.historyPrev.emit()
                return
        elif event.matches(QKeySequence.MoveToNextPage) or \
                event.matches(QKeySequence.MoveToPreviousPage):
            return self._termWidget.browser().keyPressEvent(event)

        QTextEdit.keyPressEvent(self, event)

    def insertFromMimeData(self, mime_data):
        # Paste only plain text.
        self.insertPlainText(mime_data.text())

class TermWidget(QWidget):
    """
    Widget wich represents terminal. It only displays text and allows to enter text.
    All highlevel logic should be implemented by client classes

    User pressed Enter. Client class should decide, if command must be executed or user may continue edit it
    """

    def __init__(self, *args):
        QWidget.__init__(self, *args)

        self._browser = QTextEdit(self)
        self._browser.setStyleSheet("font: 9pt \"Courier\";")
        self._browser.setReadOnly(True)
        self._browser.document().setDefaultStyleSheet(
            self._browser.document().defaultStyleSheet() +
            "span {white-space:pre;}")

        self._edit = _ExpandableTextEdit(self, self)
        self._edit.historyNext.connect(self._on_history_next)
        self._edit.historyPrev.connect(self._on_history_prev)
        self.setFocusProxy(self._edit)

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._browser)
        layout.addWidget(self._edit)

        self._history = ['']  # current empty line
        self._historyIndex = 0

        self._edit.setFocus()

    def open_proccessing(self, detail=None):
        """
        Open processing and disable using shell commands  again until all commands are finished

        :param detail: text detail about what is currently called from TCL to python
        :return: None
        """

        self._edit.setTextColor(Qt.white)
        self._edit.setTextBackgroundColor(Qt.darkGreen)
        if detail is None:
            self._edit.setPlainText("...proccessing...")
        else:
            self._edit.setPlainText("...proccessing... [%s]" % detail)

        self._edit.setDisabled(True)

    def close_proccessing(self):
        """
        Close processing and enable using shell commands  again
        :return:
        """

        self._edit.setTextColor(Qt.black)
        self._edit.setTextBackgroundColor(Qt.white)
        self._edit.setPlainText('')
        self._edit.setDisabled(False)

    def _append_to_browser(self, style, text):
        """
        Convert text to HTML for inserting it to browser
        """
        assert style in ('in', 'out', 'err')

        text = cgi.escape(text)
        text = text.replace('\n', '<br/>')

        if style == 'in':
            text = '<span style="font-weight: bold;">%s</span>' % text
        elif style == 'err':
            text = '<span style="font-weight: bold; color: red;">%s</span>' % text
        else:
            text = '<span>%s</span>' % text  # without span <br/> is ignored!!!

        scrollbar = self._browser.verticalScrollBar()
        old_value = scrollbar.value()
        scrollattheend = old_value == scrollbar.maximum()

        self._browser.moveCursor(QTextCursor.End)
        self._browser.insertHtml(text)

        """TODO When user enters second line to the input, and input is resized, scrollbar changes its positon
        and stops moving. As quick fix of this problem, now we always scroll down when add new text.
        To fix it correctly, srcoll to the bottom, if before intput has been resized,
        scrollbar was in the bottom, and remove next lien
        """
        scrollattheend = True

        if scrollattheend:
            scrollbar.setValue(scrollbar.maximum())
        else:
            scrollbar.setValue(old_value)

    def exec_current_command(self):
        """
        Save current command in the history. Append it to the log. Clear edit line
        Reimplement in the child classes to actually execute command
        """
        text = str(self._edit.toPlainText())
        self._append_to_browser('in', '> ' + text + '\n')

        if len(self._history) < 2 or\
           self._history[-2] != text:  # don't insert duplicating items
            if text[-1] == '\n':
                self._history.insert(-1, text[:-1])
            else:
                self._history.insert(-1, text)

        self._historyIndex = len(self._history) - 1

        self._history[-1] = ''
        self._edit.clear()

        if not text[-1] == '\n':
            text += '\n'

        self.child_exec_command(text)

    def child_exec_command(self, text):
        """
        Reimplement in the child classes
        """
        pass

    def add_line_break_to_input(self):
        self._edit.textCursor().insertText('\n')

    def append_output(self, text):
        """Appent text to output widget
        """
        self._append_to_browser('out', text)

    def append_error(self, text):
        """Appent error text to output widget. Text is drawn with red background
        """
        self._append_to_browser('err', text)

    def is_command_complete(self, text):
        """
        Executed by _ExpandableTextEdit. Reimplement this function in the child classes.
        """
        return True

    def browser(self):
        return self._browser

    def _on_history_next(self):
        """
        Down pressed, show next item from the history
        """
        if (self._historyIndex + 1) < len(self._history):
            self._historyIndex += 1
            self._edit.setPlainText(self._history[self._historyIndex])
            self._edit.moveCursor(QTextCursor.End)

    def _on_history_prev(self):
        """
        Up pressed, show previous item from the history
        """
        if self._historyIndex > 0:
            if self._historyIndex == (len(self._history) - 1):
                self._history[-1] = self._edit.toPlainText()
            self._historyIndex -= 1
            self._edit.setPlainText(self._history[self._historyIndex])
            self._edit.moveCursor(QTextCursor.End)

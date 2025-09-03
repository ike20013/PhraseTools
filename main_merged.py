#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KeyPhrase Manager Pro - Modern SEO Tool
Автор: Assistant
Python 3.11+ / macOS
"""

import sys
import re
import copy
import json
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, deque
import pandas as pd
from transliterate import translit

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTabWidget, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView, QMenu,
    QMessageBox, QListWidget, QGroupBox, QLineEdit,
    QComboBox, QProgressBar, QStatusBar, QTextEdit,
    QAbstractItemView, QTreeWidget, QTreeWidgetItem,
    QCheckBox, QSpinBox, QGraphicsDropShadowEffect,
    QListWidgetItem, QInputDialog, QDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QMimeData
from PyQt6.QtGui import (
    QAction, QFont, QPalette, QColor, QBrush, QLinearGradient,
    QKeySequence, QShortcut, QTextCharFormat, QTextCursor, QPainter,
    QDrag
)


@dataclass
class Phrase:
    """Модель данных для фразы"""
    text: str
    frequency: int = 0
    source_file: str = ""

    def __hash__(self):
        return hash(self.text.lower())

    def __eq__(self, other):
        if isinstance(other, Phrase):
            return self.text.lower() == other.text.lower()
        return False


class Folder:
    """Модель папки для хранения фраз"""

    def __init__(self, name: str):
        self.name = name
        self.phrases: List[Tuple[str, int]] = []

    def add_phrase(self, phrase: str, frequency: int):
        """Добавление фразы в папку"""
        if (phrase, frequency) not in self.phrases:
            self.phrases.append((phrase, frequency))

    def remove_phrase(self, phrase: str):
        """Удаление фразы из папки"""
        self.phrases = [(p, f) for p, f in self.phrases if p != phrase]

    def clear(self):
        """Очистка папки"""
        self.phrases.clear()


class HistoryManager:
    """Менеджер истории для undo/redo"""

    def __init__(self, max_history=50):
        self.history = deque(maxlen=max_history)
        self.current_index = -1
        self.initial_state = None

    def set_initial_state(self, state: List[Tuple[str, int]]):
        """Установка начального состояния"""
        self.initial_state = copy.deepcopy(state)
        self.history.clear()
        self.history.append(copy.deepcopy(state))
        self.current_index = 0

    def add_state(self, state: List[Tuple[str, int]]):
        """Добавление нового состояния"""
        while len(self.history) > self.current_index + 1:
            self.history.pop()

        self.history.append(copy.deepcopy(state))
        self.current_index = len(self.history) - 1

    def undo(self) -> Optional[List[Tuple[str, int]]]:
        """Отмена последнего действия"""
        if self.current_index > 0:
            self.current_index -= 1
            return copy.deepcopy(self.history[self.current_index])
        return None

    def redo(self) -> Optional[List[Tuple[str, int]]]:
        """Повтор отмененного действия"""
        if self.current_index < len(self.history) - 1:
            self.current_index += 1
            return copy.deepcopy(self.history[self.current_index])
        return None

    def can_undo(self) -> bool:
        """Можно ли отменить"""
        return self.current_index > 0

    def can_redo(self) -> bool:
        """Можно ли повторить"""
        return self.current_index < len(self.history) - 1


class PhraseProcessor:
    """Бизнес-логика обработки фраз"""

    @staticmethod
    def remove_duplicates(phrases: List[Tuple[str, int]]) -> List[Tuple[str, int]]:
        """Удаление точных дубликатов с сохранением порядка"""
        seen = set()
        result = []
        for phrase, freq in phrases:
            phrase_lower = phrase.lower().strip()
            if phrase_lower not in seen:
                seen.add(phrase_lower)
                result.append((phrase.strip(), freq))
        return result

    @staticmethod
    def sort_phrases_alphabetically(phrases: List[Tuple[str, int]], reverse: bool = False) -> List[Tuple[str, int]]:
        """Сортировка фраз по алфавиту"""
        return sorted(phrases, key=lambda x: x[0].lower(), reverse=reverse)

    @staticmethod
    def sort_phrases_by_frequency(phrases: List[Tuple[str, int]], reverse: bool = True) -> List[Tuple[str, int]]:
        """Сортировка фраз по частотности"""
        return sorted(phrases, key=lambda x: x[1], reverse=reverse)

    @staticmethod
    def transliterate_phrases(phrases: List[Tuple[str, int]], reverse: bool = False) -> List[Tuple[str, int]]:
        """Транслитерация фраз (двусторонняя)"""
        result = []
        for phrase, freq in phrases:
            try:
                if reverse:
                    if not re.search('[а-яА-Я]', phrase):
                        result.append((translit(phrase, 'ru', reversed=False), freq))
                    else:
                        result.append((phrase, freq))
                else:
                    if re.search('[а-яА-Я]', phrase):
                        result.append((translit(phrase, 'ru', reversed=True), freq))
                    else:
                        result.append((phrase, freq))
            except:
                result.append((phrase, freq))
        return result

    @staticmethod
    def filter_by_stop_words(phrases: List[Tuple[str, int]], stop_words: Set[str]) -> List[Tuple[str, int]]:
        """Фильтрация по стоп-словам"""
        if not stop_words:
            return phrases

        result = []
        for phrase, freq in phrases:
            phrase_words = set(phrase.lower().split())
            if not phrase_words.intersection(stop_words):
                result.append((phrase, freq))
        return result

    @staticmethod
    def remove_special_chars(phrases: List[Tuple[str, int]]) -> List[Tuple[str, int]]:
        """Удаление спецсимволов и лишних пробелов"""
        result = []
        for phrase, freq in phrases:
            cleaned = re.sub(r'[^\w\s]', ' ', phrase)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            if cleaned:
                result.append((cleaned, freq))
        return result

    @staticmethod
    def convert_case(phrases: List[Tuple[str, int]], to_upper: bool) -> List[Tuple[str, int]]:
        """Преобразование регистра"""
        result = []
        for phrase, freq in phrases:
            if to_upper:
                result.append((phrase.upper(), freq))
            else:
                result.append((phrase.lower(), freq))
        return result

    @staticmethod
    def remove_long_phrases(phrases: List[Tuple[str, int]], max_words: int = 7) -> List[Tuple[str, int]]:
        """Удаление фраз длиннее указанного количества слов"""
        result = []
        for phrase, freq in phrases:
            if len(phrase.split()) <= max_words:
                result.append((phrase, freq))
        return result

    @staticmethod
    def group_phrases(phrases: List[Tuple[str, int]]) -> Dict[str, List[Tuple[str, int]]]:
        """Группировка фраз по общим словам"""
        groups = defaultdict(list)

        for phrase, freq in phrases:
            words = phrase.lower().split()
            word_freq = defaultdict(int)
            for word in words:
                if len(word) > 3:
                    word_freq[word] += 1

            if word_freq:
                main_word = max(word_freq.keys(), key=len)
                groups[main_word].append((phrase, freq))
            else:
                groups['другое'].append((phrase, freq))

        return dict(groups)


class ModernButton(QPushButton):
    """Современная кнопка в стиле macOS"""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setup_style()

    def setup_style(self):
        self.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #007aff;
                border: 1px solid #c7c7cc;
                padding: 6px 12px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #f2f2f7;
            }
            QPushButton:pressed {
                background-color: #e5e5ea;
            }
        """)


class SearchWidget(QWidget):
    """Современный виджет поиска в стиле macOS"""

    search_changed = pyqtSignal(str, bool)

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)

        # Контейнер для поиска
        search_container = QWidget()
        search_container.setStyleSheet("""
            QWidget {
                background: #ffffff;
                border-radius: 8px;
                border: 1px solid #c7c7cc;
            }
        """)
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(8, 4, 8, 4)
        search_layout.setSpacing(8)

        # Поле поиска
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по фразам...")
        self.search_input.textChanged.connect(self.on_search_changed)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #000000;
                font-size: 13px;
            }
            QLineEdit::placeholder {
                color: #8e8e93;
            }
        """)
        search_layout.addWidget(self.search_input)

        # Чекбокс "Только совпадения"
        self.only_matches = QCheckBox("Только совпадения")
        self.only_matches.setStyleSheet("""
            QCheckBox {
                color: #000000;
                font-size: 12px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid #c7c7cc;
                background: #ffffff;
            }
            QCheckBox::indicator:checked {
                background: #007aff;
                border: 1px solid #007aff;
            }
        """)
        self.only_matches.toggled.connect(self.on_filter_changed)
        search_layout.addWidget(self.only_matches)

        search_container.setLayout(search_layout)
        layout.addWidget(search_container)

        # Кнопки навигации
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setFixedSize(30, 24)
        self.prev_btn.setEnabled(False)
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background: #ffffff;
                border: 1px solid #c7c7cc;
                border-radius: 6px;
                color: #007aff;
                font-size: 12px;
            }
            QPushButton:hover:enabled {
                background: #f2f2f7;
            }
            QPushButton:disabled {
                color: #c7c7cc;
            }
        """)
        layout.addWidget(self.prev_btn)

        self.next_btn = QPushButton("▶")
        self.next_btn.setFixedSize(30, 24)
        self.next_btn.setEnabled(False)
        self.next_btn.setStyleSheet(self.prev_btn.styleSheet())
        layout.addWidget(self.next_btn)

        # Счетчик результатов
        self.result_label = QLabel("")
        self.result_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #8e8e93;
                padding: 0 8px;
            }
        """)
        layout.addWidget(self.result_label)

        layout.addStretch()
        self.setLayout(layout)
        self.setMaximumHeight(40)

    def on_search_changed(self):
        text = self.search_input.text()
        self.search_changed.emit(text, self.only_matches.isChecked())

        has_text = bool(text)
        self.prev_btn.setEnabled(has_text)
        self.next_btn.setEnabled(has_text)

    def on_filter_changed(self):
        self.on_search_changed()

    def update_results(self, current: int, total: int):
        if total > 0:
            self.result_label.setText(f"{current}/{total}")
            self.result_label.show()
        else:
            self.result_label.hide()


class FrequencyTableWidgetItem(QTableWidgetItem):
    """Кастомный элемент таблицы для правильной сортировки частотности"""

    def __init__(self, value: int):
        super().__init__(str(value))
        self.value = value

    def __lt__(self, other):
        if isinstance(other, FrequencyTableWidgetItem):
            return self.value < other.value
        return super().__lt__(other)


class CheckboxTableWidgetItem(QTableWidgetItem):
    """Кастомный элемент для правильной сортировки чекбоксов"""

    def __lt__(self, other):
        if isinstance(other, CheckboxTableWidgetItem):
            return self.checkState() < other.checkState()
        return super().__lt__(other)


class MainPhraseTable(QTableWidget):
    """Современная таблица с фразами в стиле macOS"""

    phrases_to_folder = pyqtSignal(list)  # Сигнал для добавления в папку

    def __init__(self, parent=None):
        super().__init__(parent)
        self.processor = PhraseProcessor()
        self.history = HistoryManager()
        self.stop_words = set()
        self.original_data = []
        self.current_data = []
        self.search_text = ""
        self.search_only_matches = False
        self.search_results = []
        self.current_search_index = 0
        self.folders = {}  # Словарь папок
        self.setup_ui()

    def setup_ui(self):
        """Настройка дизайна таблицы в стиле macOS"""
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["", "Фраза", "Частотность"])

        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(0, 40)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(2, 130)

        self.setSortingEnabled(True)

        self.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                color: #000000;
                gridline-color: #e5e5ea;
                border: 1px solid #c7c7cc;
                border-radius: 8px;
                font-family: -apple-system, BlinkMacSystemFont;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 6px;
                border-bottom: 1px solid #f2f2f7;
            }
            QTableWidget::item:selected {
                background-color: #e5e5ea;
                color: #000000;
            }
            QTableWidget::item:hover {
                background-color: #f2f2f7;
            }
            QHeaderView::section {
                background-color: #f2f2f7;
                color: #000000;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #c7c7cc;
                font-weight: 600;
            }
            QScrollBar:vertical {
                background: #f2f2f7;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #c7c7cc;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #a0a0a5;
            }
        """)

        self.setAlternatingRowColors(True)
        self.setAlternatingRowColors(False)  # Отключаем для macOS стиля
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.verticalHeader().setVisible(False)

    def contextMenuEvent(self, event):
        """Создание контекстного меню в стиле macOS"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #c7c7cc;
                border-radius: 8px;
                padding: 5px;
                font-family: -apple-system, BlinkMacSystemFont;
                font-size: 13px;
            }
            QMenu::item {
                padding: 6px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #e5e5ea;
            }
            QMenu::separator {
                height: 1px;
                background: #e5e5ea;
                margin: 5px 0;
            }
        """)

        current_row = self.currentRow()

        if current_row >= 0:
            delete_current = menu.addAction("Удалить эту фразу")
            delete_current.triggered.connect(lambda: self.delete_phrase(current_row))
            menu.addSeparator()

        if self.folders:
            folder_menu = menu.addMenu("Добавить в папку")
            for folder_name in self.folders.keys():
                action = folder_menu.addAction(folder_name)
                action.triggered.connect(lambda checked, fn=folder_name: self.add_selected_to_folder(fn))
            menu.addSeparator()

        select_all = menu.addAction("Выделить все")
        select_all.triggered.connect(self.select_all)

        deselect_all = menu.addAction("Снять выделение")
        deselect_all.triggered.connect(self.deselect_all)

        menu.addSeparator()

        copy_action = menu.addAction("Копировать выбранные")
        copy_action.triggered.connect(self.copy_selected)

        delete_selected = menu.addAction("Удалить выбранные")
        delete_selected.triggered.connect(self.delete_selected)

        menu.addSeparator()

        remove_duplicates = menu.addAction("Удалить дубликаты")
        remove_duplicates.triggered.connect(self.remove_duplicates)

        remove_special = menu.addAction("Удалить спецсимволы")
        remove_special.triggered.connect(self.remove_special_chars)

        remove_long = menu.addAction("Удалить фразы > 7 слов")
        remove_long.triggered.connect(self.remove_long_phrases)

        menu.addSeparator()

        sort_az = menu.addAction("Сортировка А-Я")
        sort_az.triggered.connect(lambda: self.sort_alphabetically(False))

        sort_za = menu.addAction("Сортировка Я-А")
        sort_za.triggered.connect(lambda: self.sort_alphabetically(True))

        sort_freq_high = menu.addAction("По частотности ↓")
        sort_freq_high.triggered.connect(lambda: self.sort_by_frequency(True))

        sort_freq_low = menu.addAction("По частотности ↑")
        sort_freq_low.triggered.connect(lambda: self.sort_by_frequency(False))

        menu.addSeparator()

        to_upper = menu.addAction("В ВЕРХНИЙ РЕГИСТР")
        to_upper.triggered.connect(lambda: self.convert_case(True))

        to_lower = menu.addAction("в нижний регистр")
        to_lower.triggered.connect(lambda: self.convert_case(False))

        menu.addSeparator()

        transliterate = menu.addAction("Транслитерация RU→EN")
        transliterate.triggered.connect(lambda: self.transliterate(False))

        transliterate_back = menu.addAction("Транслитерация EN→RU")
        transliterate_back.triggered.connect(lambda: self.transliterate(True))

        menu.exec(event.globalPos())

    def set_folders(self, folders: Dict[str, Folder]):
        self.folders = folders

    def add_selected_to_folder(self, folder_name: str):
        selected_phrases = []
        for row in range(self.rowCount()):
            checkbox_item = self.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                phrase = self.item(row, 1).text()
                freq_item = self.item(row, 2)
                freq = 0
                if isinstance(freq_item, FrequencyTableWidgetItem):
                    freq = freq_item.value
                elif freq_item:
                    freq = int(freq_item.text()) if freq_item.text().isdigit() else 0
                selected_phrases.append((phrase, freq))
                checkbox_item.setCheckState(Qt.CheckState.Unchecked)

        if selected_phrases:
            self.phrases_to_folder.emit([(folder_name, phrase, freq) for phrase, freq in selected_phrases])

    def delete_phrase(self, visual_row: int):
        self.save_state()
        phrase_item = self.item(visual_row, 1)
        if phrase_item:
            phrase_to_delete = phrase_item.text()
            self.current_data = [
                (p, f) for p, f in self.current_data
                if p != phrase_to_delete
            ]
            self.update_table(self.current_data, save_history=False)

    def select_all(self):
        for row in range(self.rowCount()):
            checkbox_item = self.item(row, 0)
            if checkbox_item:
                checkbox_item.setCheckState(Qt.CheckState.Checked)

    def deselect_all(self):
        for row in range(self.rowCount()):
            checkbox_item = self.item(row, 0)
            if checkbox_item:
                checkbox_item.setCheckState(Qt.CheckState.Unchecked)

    def delete_selected(self):
        self.save_state()
        phrases_to_delete = set()
        for row in range(self.rowCount()):
            checkbox_item = self.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                phrase_item = self.item(row, 1)
                if phrase_item:
                    phrases_to_delete.add(phrase_item.text())

        self.current_data = [
            (p, f) for p, f in self.current_data
            if p not in phrases_to_delete
        ]

        self.update_table(self.current_data, save_history=False)

    def save_state(self):
        self.history.add_state(self.current_data)

    def undo(self):
        state = self.history.undo()
        if state:
            self.current_data = state
            self.update_table(self.current_data, save_history=False)

    def redo(self):
        state = self.history.redo()
        if state:
            self.current_data = state
            self.update_table(self.current_data, save_history=False)

    def load_phrases(self, phrases: List[Phrase]):
        self.original_data = [(p.text, p.frequency) for p in phrases]
        self.current_data = self.original_data.copy()
        self.history.set_initial_state(self.current_data)
        self.update_table(self.current_data, save_history=False)

    def update_table(self, data: List[Tuple[str, int]], save_history: bool = True):
        if save_history:
            self.save_state()

        self.current_data = data

        filtered_data = data
        if self.stop_words:
            filtered_data = self.processor.filter_by_stop_words(data, self.stop_words)

        display_data = filtered_data
        if self.search_text and self.search_only_matches:
            display_data = [
                (phrase, freq) for phrase, freq in filtered_data
                if self.search_text.lower() in phrase.lower()
            ]

        self.setSortingEnabled(False)
        self.setRowCount(len(display_data))

        self.search_results = []

        for i, (phrase, freq) in enumerate(display_data):
            checkbox = CheckboxTableWidgetItem()
            checkbox.setCheckState(Qt.CheckState.Unchecked)
            self.setItem(i, 0, checkbox)

            phrase_item = QTableWidgetItem(phrase)

            if self.search_text and self.search_text.lower() in phrase.lower():
                phrase_item.setBackground(QBrush(QColor(229, 243, 255)))
                self.search_results.append(i)
            else:
                color = self.get_frequency_color(freq)
                phrase_item.setBackground(QBrush(color))

            self.setItem(i, 1, phrase_item)

            freq_item = FrequencyTableWidgetItem(freq)
            freq_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            if freq >= 100000:
                freq_item.setForeground(QBrush(QColor(255, 59, 48)))
            elif freq >= 10000:
                freq_item.setForeground(QBrush(QColor(255, 149, 0)))
            elif freq >= 1000:
                freq_item.setForeground(QBrush(QColor(255, 204, 0)))
            elif freq >= 100:
                freq_item.setForeground(QBrush(QColor(52, 199, 36)))
            else:
                freq_item.setForeground(QBrush(QColor(142, 142, 147)))

            self.setItem(i, 2, freq_item)

        self.setSortingEnabled(True)

    def get_frequency_color(self, freq: int) -> QColor:
        if freq >= 100000:
            return QColor(255, 235, 235)
        elif freq >= 10000:
            return QColor(255, 243, 235)
        elif freq >= 1000:
            return QColor(255, 250, 235)
        elif freq >= 100:
            return QColor(243, 255, 243)
        else:
            return QColor(255, 255, 255)

    def set_stop_words(self, stop_words: Set[str]):
        self.stop_words = stop_words
        self.update_table(self.current_data, save_history=False)

    def set_search(self, text: str, only_matches: bool):
        self.search_text = text
        self.search_only_matches = only_matches
        self.current_search_index = 0
        self.update_table(self.current_data, save_history=False)

        if self.search_results and not only_matches:
            self.scrollToItem(self.item(self.search_results[0], 1))
            self.selectRow(self.search_results[0])

    def next_search_result(self):
        if self.search_results:
            self.current_search_index = (self.current_search_index + 1) % len(self.search_results)
            row = self.search_results[self.current_search_index]
            self.scrollToItem(self.item(row, 1))
            self.selectRow(row)
            return self.current_search_index + 1, len(self.search_results)
        return 0, 0

    def prev_search_result(self):
        if self.search_results:
            self.current_search_index = (self.current_search_index - 1) % len(self.search_results)
            row = self.search_results[self.current_search_index]
            self.scrollToItem(self.item(row, 1))
            self.selectRow(row)
            return self.current_search_index + 1, len(self.search_results)
        return 0, 0

    def get_current_data(self) -> List[Tuple[str, int]]:
        return self.current_data.copy()

    def copy_selected(self):
        selected = []
        for row in range(self.rowCount()):
            checkbox_item = self.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.CheckState.Checked:
                phrase = self.item(row, 1).text()
                selected.append(phrase)

        if selected:
            clipboard = QApplication.clipboard()
            clipboard.setText('\n'.join(selected))

    def remove_duplicates(self):
        self.save_state()
        data = self.processor.remove_duplicates(self.current_data)
        self.current_data = data
        self.update_table(data, save_history=False)

    def remove_special_chars(self):
        self.save_state()
        data = self.processor.remove_special_chars(self.current_data)
        self.current_data = data
        self.update_table(data, save_history=False)

    def remove_long_phrases(self):
        self.save_state()
        data = self.processor.remove_long_phrases(self.current_data, 7)
        self.current_data = data
        self.update_table(data, save_history=False)

    def convert_case(self, to_upper: bool):
        self.save_state()
        data = self.processor.convert_case(self.current_data, to_upper)
        self.current_data = data
        self.update_table(data, save_history=False)

    def sort_alphabetically(self, reverse: bool):
        self.save_state()
        data = self.processor.sort_phrases_alphabetically(self.current_data, reverse)
        self.current_data = data
        self.update_table(data, save_history=False)

    def sort_by_frequency(self, reverse: bool):
        self.save_state()
        data = self.processor.sort_phrases_by_frequency(self.current_data, reverse)
        self.current_data = data
        self.update_table(data, save_history=False)

    def transliterate(self, reverse: bool = False):
        self.save_state()
        data = self.processor.transliterate_phrases(self.current_data, reverse)
        self.current_data = data
        self.update_table(data, save_history=False)


class FileLoader(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, file_paths: List[str]):
        super().__init__()
        self.file_paths = file_paths

    def run(self):
        all_phrases = []

        for i, file_path in enumerate(self.file_paths):
            try:
                path = Path(file_path)

                if path.suffix.lower() in ['.xls', '.xlsx']:
                    df = pd.read_excel(file_path)
                    if len(df.columns) >= 2:
                        for _, row in df.iterrows():
                            phrase = str(row.iloc[0]).strip()
                            freq = int(row.iloc[1]) if pd.notna(row.iloc[1]) else 0
                            all_phrases.append(Phrase(phrase, freq, path.name))
                    else:
                        phrases = df.iloc[:, 0].astype(str).str.strip().tolist()
                        all_phrases.extend([Phrase(p, 0, path.name) for p in phrases])

                elif path.suffix.lower() == '.txt':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        for line in lines:
                            parts = line.strip().split('\t')
                            phrase = parts[0]
                            freq = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
                            all_phrases.append(Phrase(phrase, freq, path.name))

                self.progress.emit(int((i + 1) / len(self.file_paths) * 100))

            except Exception as e:
                self.error.emit(f"Ошибка при загрузке {path.name}: {str(e)}")

        self.finished.emit(all_phrases)


class StopWordsWidget(QWidget):
    """Виджет стоп-слов в стиле macOS"""

    stop_words_changed = pyqtSignal(set)

    def __init__(self):
        super().__init__()
        self.stop_words = set()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header = QLabel("Стоп-слова")
        header.setFont(QFont("-apple-system", 15, QFont.Weight.Bold))
        header.setStyleSheet("color: #000000;")
        layout.addWidget(header)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Введите стоп-слово...")
        self.input_field.returnPressed.connect(self.add_stop_word)
        self.input_field.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                border: 1px solid #c7c7cc;
                border-radius: 6px;
                background-color: #ffffff;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #007aff;
            }
        """)
        layout.addWidget(self.input_field)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #ffffff;
                border: 1px solid #c7c7cc;
                border-radius: 6px;
                padding: 5px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 4px;
            }
            QListWidget::item:selected {
                background-color: #e5e5ea;
            }
        """)
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.remove_btn = ModernButton("Удалить")
        self.remove_btn.clicked.connect(self.remove_stop_word)
        btn_layout.addWidget(self.remove_btn)

        self.clear_btn = ModernButton("Очистить")
        self.clear_btn.clicked.connect(self.clear_stop_words)
        btn_layout.addWidget(self.clear_btn)

        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def add_stop_word(self):
        word = self.input_field.text().strip().lower()
        if word and word not in self.stop_words:
            self.stop_words.add(word)
            self.list_widget.addItem(word)
            self.input_field.clear()
            self.stop_words_changed.emit(self.stop_words)

    def remove_stop_word(self):
        current_item = self.list_widget.currentItem()
        if current_item:
            word = current_item.text()
            self.stop_words.discard(word)
            self.list_widget.takeItem(self.list_widget.row(current_item))
            self.stop_words_changed.emit(self.stop_words)

    def clear_stop_words(self):
        self.stop_words.clear()
        self.list_widget.clear()
        self.stop_words_changed.emit(self.stop_words)


class GroupingWidget(QWidget):
    """Виджет группировки в стиле macOS"""

    def __init__(self):
        super().__init__()
        self.groups = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()

        header = QLabel("Группировка")
        header.setFont(QFont("-apple-system", 15, QFont.Weight.Bold))
        header.setStyleSheet("color: #000000;")
        header_layout.addWidget(header)

        header_layout.addStretch()

        self.export_btn = ModernButton("Экспорт")
        self.export_btn.clicked.connect(self.export_groups)
        header_layout.addWidget(self.export_btn)

        layout.addLayout(header_layout)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Группа / Фраза", "Частотность"])
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #ffffff;
                border: 1px solid #c7c7cc;
                border-radius: 6px;
                padding: 5px;
                font-size: 13px;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #e5e5ea;
            }
            QHeaderView::section {
                background-color: #f2f2f7;
                color: #000000;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #c7c7cc;
                font-weight: 600;
            }
        """)
        layout.addWidget(self.tree)

        self.setLayout(layout)

    def update_groups(self, phrases: List[Tuple[str, int]]):
        processor = PhraseProcessor()
        self.groups = processor.group_phrases(phrases)

        self.tree.clear()

        for group_name, group_phrases in self.groups.items():
            group_item = QTreeWidgetItem(self.tree)
            group_item.setText(0, f"{group_name} ({len(group_phrases)})")
            group_item.setExpanded(True)

            for phrase, freq in group_phrases:
                phrase_item = QTreeWidgetItem(group_item)
                phrase_item.setText(0, phrase)
                phrase_item.setText(1, str(freq))

                if freq >= 100000:
                    phrase_item.setForeground(1, QBrush(QColor(255, 59, 48)))
                elif freq >= 10000:
                    phrase_item.setForeground(1, QBrush(QColor(255, 149, 0)))
                elif freq >= 1000:
                    phrase_item.setForeground(1, QBrush(QColor(255, 204, 0)))
                elif freq >= 100:
                    phrase_item.setForeground(1, QBrush(QColor(52, 199, 36)))

    def export_groups(self):
        if not self.groups:
            QMessageBox.warning(None, "Предупреждение", "Нет данных для экспорта")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            None,
            "Сохранить группы",
            "groups.xlsx",
            "Excel files (*.xlsx)"
        )

        if file_path:
            try:
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    for group_name, group_phrases in self.groups.items():
                        df = pd.DataFrame(group_phrases, columns=['Фраза', 'Частотность'])
                        sheet_name = group_name[:31] if len(group_name) > 31 else group_name
                        df.to_excel(writer, sheet_name=sheet_name, index=False)

                QMessageBox.information(None, "Успех", f"Группы экспортированы")
            except Exception as e:
                QMessageBox.critical(None, "Ошибка", f"Не удалось экспортировать: {str(e)}")


class FoldersWidget(QWidget):
    """Виджет для управления папками в стиле macOS"""

    def __init__(self):
        super().__init__()
        self.folders = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()

        header = QLabel("Папки")
        header.setFont(QFont("-apple-system", 15, QFont.Weight.Bold))
        header.setStyleSheet("color: #000000;")
        header_layout.addWidget(header)

        header_layout.addStretch()

        self.new_folder_btn = ModernButton("Новая папка")
        self.new_folder_btn.clicked.connect(self.create_folder)
        header_layout.addWidget(self.new_folder_btn)

        self.export_btn = ModernButton("Экспорт")
        self.export_btn.clicked.connect(self.export_folders)
        header_layout.addWidget(self.export_btn)

        layout.addLayout(header_layout)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Папка / Фраза", "Частотность"])
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #ffffff;
                border: 1px solid #c7c7cc;
                border-radius: 6px;
                padding: 5px;
                font-size: 13px;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #e5e5ea;
            }
            QHeaderView::section {
                background-color: #f2f2f7;
                color: #000000;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #c7c7cc;
                font-weight: 600;
            }
        """)

        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)

        self.tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.tree.setDefaultDropAction(Qt.DropAction.MoveAction)

        layout.addWidget(self.tree)

        self.setLayout(layout)

    def create_folder(self):
        name, ok = QInputDialog.getText(self, "Новая папка", "Введите название папки:")
        if ok and name:
            if name not in self.folders:
                self.folders[name] = Folder(name)
                self.update_tree()
            else:
                QMessageBox.warning(self, "Ошибка", "Папка с таким именем уже существует")

    def delete_folder(self, folder_name: str):
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить папку '{folder_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            del self.folders[folder_name]
            self.update_tree()

    def show_context_menu(self, position):
        item = self.tree.itemAt(position)
        if not item:
            return

        parent = item.parent()
        if parent is None:
            folder_name = item.text(0).split(" (")[0]
            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #c7c7cc;
                    border-radius: 8px;
                    padding: 5px;
                    font-size: 13px;
                }
                QMenu::item {
                    padding: 6px 20px;
                    border-radius: 4px;
                }
                QMenu::item:selected {
                    background-color: #e5e5ea;
                }
            """)

            delete_action = menu.addAction("Удалить папку")
            delete_action.triggered.connect(lambda: self.delete_folder(folder_name))

            clear_action = menu.addAction("Очистить папку")
            clear_action.triggered.connect(lambda: self.clear_folder(folder_name))

            menu.exec(self.tree.mapToGlobal(position))
        else:
            folder_name = parent.text(0).split(" (")[0]
            phrase = item.text(0)

            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #c7c7cc;
                    border-radius: 8px;
                    padding: 5px;
                    font-size: 13px;
                }
                QMenu::item {
                    padding: 6px 20px;
                    border-radius: 4px;
                }
                QMenu::item:selected {
                    background-color: #e5e5ea;
                }
            """)

            remove_action = menu.addAction("Удалить из папки")
            remove_action.triggered.connect(lambda: self.remove_from_folder(folder_name, phrase))

            menu.exec(self.tree.mapToGlobal(position))

    def clear_folder(self, folder_name: str):
        if folder_name in self.folders:
            self.folders[folder_name].clear()
            self.update_tree()

    def remove_from_folder(self, folder_name: str, phrase: str):
        if folder_name in self.folders:
            self.folders[folder_name].remove_phrase(phrase)
            self.update_tree()

    def add_phrases_to_folder(self, data: List[Tuple[str, str, int]]):
        for folder_name, phrase, freq in data:
            if folder_name in self.folders:
                self.folders[folder_name].add_phrase(phrase, freq)
        self.update_tree()

    def update_tree(self):
        self.tree.clear()

        for folder_name, folder in self.folders.items():
            folder_item = QTreeWidgetItem(self.tree)
            folder_item.setText(0, f"{folder_name} ({len(folder.phrases)})")
            folder_item.setExpanded(True)

            for phrase, freq in folder.phrases:
                phrase_item = QTreeWidgetItem(folder_item)
                phrase_item.setText(0, phrase)
                phrase_item.setText(1, str(freq))

                if freq >= 100000:
                    phrase_item.setForeground(1, QBrush(QColor(255, 59, 48)))
                elif freq >= 10000:
                    phrase_item.setForeground(1, QBrush(QColor(255, 149, 0)))
                elif freq >= 1000:
                    phrase_item.setForeground(1, QBrush(QColor(255, 204, 0)))
                elif freq >= 100:
                    phrase_item.setForeground(1, QBrush(QColor(52, 199, 36)))

    def export_folders(self):
        if not self.folders:
            QMessageBox.warning(self, "Предупреждение", "Нет папок для экспорта")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить папки",
            "folders.xlsx",
            "Excel files (*.xlsx)"
        )

        if file_path:
            try:
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    for folder_name, folder in self.folders.items():
                        if folder.phrases:
                            df = pd.DataFrame(folder.phrases, columns=['Фраза', 'Частотность'])
                            sheet_name = folder_name[:31] if len(folder_name) > 31 else folder_name
                            df.to_excel(writer, sheet_name=sheet_name, index=False)

                QMessageBox.information(self, "Успех", "Папки экспортированы")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать: {str(e)}")

    def get_folders(self) -> Dict[str, Folder]:
        return self.folders


class MainWindow(QMainWindow):
    """Главное окно приложения в стиле macOS"""

    def __init__(self):
        super().__init__()
        self.phrases_data = []
        self.setup_ui()
        self.setup_shortcuts()
        self.setup_style()

    def setup_ui(self):
        self.setWindowTitle("KeyPhrase Manager Pro - Modern SEO Tool")
        self.setGeometry(100, 100, 1400, 900)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        central_widget.setLayout(main_layout)

        toolbar_widget = QWidget()
        toolbar_widget.setStyleSheet("""
            QWidget {
                background-color: #f2f2f7;
                border-bottom: 1px solid #c7c7cc;
            }
        """)
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(10, 5, 10, 5)
        toolbar_layout.setSpacing(8)

        self.load_btn = ModernButton("Загрузить")
        self.load_btn.clicked.connect(self.load_files)
        toolbar_layout.addWidget(self.load_btn)

        self.save_btn = ModernButton("Сохранить")
        self.save_btn.clicked.connect(self.save_file)
        toolbar_layout.addWidget(self.save_btn)

        self.add_btn = ModernButton("Добавить")
        self.add_btn.clicked.connect(self.add_phrase)
        toolbar_layout.addWidget(self.add_btn)

        toolbar_layout.addStretch()

        counter_widget = QWidget()
        counter_widget.setStyleSheet("""
            QWidget {
                background: transparent;
                padding: 0 10px;
            }
        """)
        counter_layout = QHBoxLayout()
        counter_layout.setContentsMargins(0, 0, 0, 0)
        counter_layout.setSpacing(5)

        self.phrase_count_label = QLabel("Фраз: 0")
        self.phrase_count_label.setFont(QFont("-apple-system", 12))
        self.phrase_count_label.setStyleSheet("color: #000000;")
        counter_layout.addWidget(self.phrase_count_label)

        self.filtered_count_label = QLabel("")
        self.filtered_count_label.setFont(QFont("-apple-system", 12))
        self.filtered_count_label.setStyleSheet("color: #8e8e93;")
        counter_layout.addWidget(self.filtered_count_label)

        counter_widget.setLayout(counter_layout)
        toolbar_layout.addWidget(counter_widget)

        toolbar_widget.setLayout(toolbar_layout)
        toolbar_widget.setMaximumHeight(40)
        main_layout.addWidget(toolbar_widget)

        self.search_widget = SearchWidget()
        self.search_widget.search_changed.connect(self.on_search_changed)
        self.search_widget.prev_btn.clicked.connect(self.prev_search)
        self.search_widget.next_btn.clicked.connect(self.next_search)
        main_layout.addWidget(self.search_widget)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #c7c7cc;
            }
        """)

        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)

        editor_label = QLabel("Фразы")
        editor_label.setFont(QFont("-apple-system", 13, QFont.Weight.Bold))
        editor_label.setStyleSheet("color: #000000;")
        left_layout.addWidget(editor_label)

        self.main_table = MainPhraseTable()
        self.main_table.phrases_to_folder.connect(self.on_phrases_to_folder)
        left_layout.addWidget(self.main_table)

        left_panel.setLayout(left_layout)
        splitter.addWidget(left_panel)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #c7c7cc;
                background-color: #ffffff;
                border-radius: 8px;
            }
            QTabBar::tab {
                background-color: #f2f2f7;
                color: #000000;
                padding: 6px 12px;
                margin-right: 1px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                border-bottom: 1px solid #ffffff;
            }
        """)

        self.stop_words_widget = StopWordsWidget()
        self.stop_words_widget.stop_words_changed.connect(self.on_stop_words_changed)
        self.tabs.addTab(self.stop_words_widget, "Стоп-слова")

        self.grouping_widget = GroupingWidget()
        self.tabs.addTab(self.grouping_widget, "Группировка")

        self.folders_widget = FoldersWidget()
        self.tabs.addTab(self.folders_widget, "Папки")

        splitter.addWidget(self.tabs)

        splitter.setSizes([980, 420])

        main_layout.addWidget(splitter)

        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #f2f2f7;
                color: #8e8e93;
                border-top: 1px solid #c7c7cc;
                font-size: 12px;
            }
        """)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов к работе")

    def setup_shortcuts(self):
        undo_shortcut = QShortcut(QKeySequence("Cmd+Z"), self)
        undo_shortcut.activated.connect(self.main_table.undo)

        redo_shortcut = QShortcut(QKeySequence("Cmd+Shift+Z"), self)
        redo_shortcut.activated.connect(self.main_table.redo)

        search_shortcut = QShortcut(QKeySequence("Cmd+F"), self)
        search_shortcut.activated.connect(lambda: self.search_widget.search_input.setFocus())

    def setup_style(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f2f2f7;
            }
        """)

    def add_phrase(self):
        """Добавление новой фразы"""
        phrase, ok = QInputDialog.getText(self, "Добавить фразу", "Введите фразу:")
        if ok and phrase:
            self.main_table.save_state()
            self.main_table.current_data.append((phrase.strip(), 0))
            self.main_table.update_table(self.main_table.current_data, save_history=False)
            self.update_phrase_count()
            current_data = self.main_table.get_current_data()
            self.grouping_widget.update_groups(current_data)

    def on_phrases_to_folder(self, data: List[Tuple[str, str, int]]):
        self.folders_widget.add_phrases_to_folder(data)
        self.main_table.set_folders(self.folders_widget.get_folders())

    def load_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите файлы",
            "",
            "Supported files (*.txt *.xls *.xlsx);;Text files (*.txt);;Excel files (*.xls *.xlsx)"
        )

        if file_paths:
            self.loader = FileLoader(file_paths)
            self.loader.finished.connect(self.on_files_loaded)
            self.loader.error.connect(self.on_load_error)
            self.loader.start()
            self.status_bar.showMessage("Загрузка...")

    def on_files_loaded(self, phrases: List[Phrase]):
        self.phrases_data.extend(phrases)

        self.main_table.load_phrases(self.phrases_data)
        self.update_phrase_count()

        data = [(p.text, p.frequency) for p in self.phrases_data]
        self.grouping_widget.update_groups(data)

        self.main_table.set_folders(self.folders_widget.get_folders())

        self.status_bar.showMessage(f"Загружено {len(phrases)} фраз")

    def on_load_error(self, error: str):
        QMessageBox.warning(self, "Ошибка", error)
        self.status_bar.showMessage("Ошибка загрузки")

    def on_stop_words_changed(self, stop_words: Set[str]):
        self.main_table.set_stop_words(stop_words)
        self.update_phrase_count()

        current_data = self.main_table.get_current_data()
        self.grouping_widget.update_groups(current_data)

    def on_search_changed(self, text: str, only_matches: bool):
        self.main_table.set_search(text, only_matches)

        if text:
            total = len(self.main_table.search_results)
            if total > 0:
                self.search_widget.update_results(1, total)
            else:
                self.search_widget.update_results(0, 0)

    def next_search(self):
        current, total = self.main_table.next_search_result()
        self.search_widget.update_results(current, total)

    def prev_search(self):
        current, total = self.main_table.prev_search_result()
        self.search_widget.update_results(current, total)

    def update_phrase_count(self):
        total = len(self.main_table.current_data)
        self.phrase_count_label.setText(f"Фраз: {total}")

        if self.stop_words_widget.stop_words:
            filtered = self.main_table.rowCount()
            self.filtered_count_label.setText(f"(после фильтра: {filtered})")
        else:
            self.filtered_count_label.setText("")

    def save_file(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить файл",
            "",
            "Text files (*.txt);;Excel files (*.xlsx)"
        )

        if file_path:
            try:
                data = self.main_table.get_current_data()

                if file_path.endswith('.txt'):
                    with open(file_path, 'w', encoding='utf-8') as f:
                        for phrase, freq in data:
                            f.write(f"{phrase}\t{freq}\n")
                elif file_path.endswith('.xlsx'):
                    df = pd.DataFrame(data, columns=['Фраза', 'Частотность'])
                    df.to_excel(file_path, index=False)

                self.status_bar.showMessage(f"Сохранено: {Path(file_path).name}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {str(e)}")


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(242, 242, 247))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
    app.setPalette(palette)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
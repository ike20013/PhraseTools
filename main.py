#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KeyPhrase Manager - Современный аналог KeyCollector/KeyAssort
Автор: Assistant
Python 3.11+ / macOS
"""

import sys
import re
import copy
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
    QCheckBox, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import (
    QAction, QFont, QPalette, QColor, QBrush,
    QKeySequence, QShortcut, QTextCharFormat, QTextCursor
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
        # Удаляем все состояния после текущего индекса
        while len(self.history) > self.current_index + 1:
            self.history.pop()

        # Добавляем новое состояние
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
                    # С английского на русский (обратная транслитерация)
                    if not re.search('[а-яА-Я]', phrase):
                        result.append((translit(phrase, 'ru', reversed=False), freq))
                    else:
                        result.append((phrase, freq))
                else:
                    # С русского на английский
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
            # Удаляем спецсимволы, оставляем только буквы, цифры и пробелы
            cleaned = re.sub(r'[^\w\s]', ' ', phrase)
            # Удаляем множественные пробелы
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            if cleaned:  # Пропускаем пустые строки
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
            # Находим самое значимое слово для группировки
            word_freq = defaultdict(int)
            for word in words:
                if len(word) > 3:  # Игнорируем короткие слова
                    word_freq[word] += 1

            if word_freq:
                # Группируем по самому длинному значимому слову
                main_word = max(word_freq.keys(), key=len)
                groups[main_word].append((phrase, freq))
            else:
                groups['другое'].append((phrase, freq))

        return dict(groups)


class SearchWidget(QWidget):
    """Виджет поиска по фразам"""

    search_changed = pyqtSignal(str, bool)  # текст поиска, только совпадения

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)

        # Поле поиска
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Поиск по фразам...")
        self.search_input.textChanged.connect(self.on_search_changed)
        self.search_input.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border: 2px solid #e0e0e0;
                border-radius: 20px;
                background-color: #ffffff;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #007aff;
            }
        """)
        layout.addWidget(self.search_input)

        # Чекбокс "Только совпадения"
        self.only_matches = QCheckBox("Только совпадения")
        self.only_matches.setStyleSheet("QCheckBox { font-size: 13px; }")
        self.only_matches.toggled.connect(self.on_filter_changed)
        layout.addWidget(self.only_matches)

        # Кнопки навигации
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setFixedSize(35, 35)
        self.prev_btn.setEnabled(False)
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
                border-radius: 17px;
                font-size: 16px;
            }
            QPushButton:hover:enabled {
                background-color: #007aff;
                color: white;
            }
            QPushButton:disabled {
                background-color: #f8f8f8;
                color: #c0c0c0;
            }
        """)
        layout.addWidget(self.prev_btn)

        self.next_btn = QPushButton("▶")
        self.next_btn.setFixedSize(35, 35)
        self.next_btn.setEnabled(False)
        self.next_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #d0d0d0;
                border-radius: 17px;
                font-size: 16px;
            }
            QPushButton:hover:enabled {
                background-color: #007aff;
                color: white;
            }
            QPushButton:disabled {
                background-color: #f8f8f8;
                color: #c0c0c0;
            }
        """)
        layout.addWidget(self.next_btn)

        # Счетчик результатов
        self.result_label = QLabel("")
        self.result_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: 500;
                color: #007aff;
                padding: 5px 10px;
                background-color: #e6f2ff;
                border-radius: 10px;
            }
        """)
        layout.addWidget(self.result_label)

        layout.addStretch()
        self.setLayout(layout)

    def on_search_changed(self):
        """Изменение текста поиска"""
        text = self.search_input.text()
        self.search_changed.emit(text, self.only_matches.isChecked())

        # Включаем/выключаем кнопки навигации
        has_text = bool(text)
        self.prev_btn.setEnabled(has_text)
        self.next_btn.setEnabled(has_text)

    def on_filter_changed(self):
        """Изменение фильтра"""
        self.on_search_changed()

    def update_results(self, current: int, total: int):
        """Обновление счетчика результатов"""
        if total > 0:
            self.result_label.setText(f"Найдено: {current}/{total}")
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


class MainPhraseTable(QTableWidget):
    """Основная таблица с фразами и частотностью"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.processor = PhraseProcessor()
        self.history = HistoryManager()
        self.stop_words = set()
        self.original_data = []  # Храним оригинальные данные
        self.current_data = []  # Текущие данные в таблице
        self.search_text = ""
        self.search_only_matches = False
        self.search_results = []
        self.current_search_index = 0
        self.setup_ui()

    def setup_ui(self):
        """Настройка внешнего вида таблицы"""
        # Настройка колонок
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["✓", "Фраза", "Частотность"])

        # Настройка ширины колонок
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(0, 30)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        # Частотность автоматически подстраивается под содержимое
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        # Включаем сортировку
        self.setSortingEnabled(True)

        # Стиль таблицы
        self.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                color: #000000;
                gridline-color: #d0d0d0;
                border: 1px solid #d0d0d0;
                font-family: "SF Pro Display", -apple-system, sans-serif;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 4px;
                border-bottom: 1px solid #e0e0e0;
            }
            QTableWidget::item:selected {
                background-color: #007aff;
                color: white;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                color: #333333;
                padding: 6px;
                border: none;
                border-bottom: 2px solid #d0d0d0;
                font-weight: 500;
            }
        """)

        # Настройка поведения
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.verticalHeader().setVisible(False)

    def _get_table_data(self) -> List[Tuple[str, int]]:
        """Получение данных из текущей таблицы"""
        data = []
        for row in range(self.rowCount()):
            phrase = self.item(row, 1).text()
            freq_item = self.item(row, 2)
            if isinstance(freq_item, FrequencyTableWidgetItem):
                freq = freq_item.value
            else:
                freq = int(freq_item.text()) if freq_item.text().isdigit() else 0
            data.append((phrase, freq))
        return data

    def sortByColumn(self, column: int, order: Qt.SortOrder):
        """Переопределение сортировки для обновления данных и истории"""
        self.save_state()
        super().sortByColumn(column, order)
        self.current_data = self._get_table_data()
        self.history.add_state(self.current_data)

    def contextMenuEvent(self, event):
        """Создание контекстного меню"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                padding: 5px;
            }
            QMenu::item:selected {
                background-color: #007aff;
                color: white;
                border-radius: 4px;
            }
        """)

        clicked_row = self.rowAt(event.pos().y())

        if clicked_row != -1:
            delete_row_action = menu.addAction("🗑 Удалить эту фразу")
            delete_row_action.triggered.connect(lambda: self.delete_row(clicked_row))
            menu.addSeparator()

        # Действия с выделением
        select_all = menu.addAction("☑️ Выделить все")
        select_all.triggered.connect(self.select_all)

        deselect_all = menu.addAction("⬜ Снять выделение")
        deselect_all.triggered.connect(self.deselect_all)

        menu.addSeparator()

        # Действия меню
        copy_action = menu.addAction("📋 Копировать выбранные")
        copy_action.triggered.connect(self.copy_selected)

        delete_selected = menu.addAction("🗑 Удалить выбранные")
        delete_selected.triggered.connect(self.delete_selected)

        menu.addSeparator()

        remove_duplicates = menu.addAction("🔄 Удалить дубликаты")
        remove_duplicates.triggered.connect(self.remove_duplicates)

        remove_special = menu.addAction("🧹 Удалить спецсимволы и пробелы")
        remove_special.triggered.connect(self.remove_special_chars)

        remove_long = menu.addAction("✂️ Удалить фразы > 7 слов")
        remove_long.triggered.connect(self.remove_long_phrases)

        menu.addSeparator()

        sort_az = menu.addAction("⬆️ Сортировка А-Я")
        sort_az.triggered.connect(lambda: self.sort_alphabetically(False))

        sort_za = menu.addAction("⬇️ Сортировка Я-А")
        sort_za.triggered.connect(lambda: self.sort_alphabetically(True))

        sort_freq_high = menu.addAction("📊 По частотности ↓")
        sort_freq_high.triggered.connect(lambda: self.sort_by_frequency(True))

        sort_freq_low = menu.addAction("📊 По частотности ↑")
        sort_freq_low.triggered.connect(lambda: self.sort_by_frequency(False))

        menu.addSeparator()

        to_upper = menu.addAction("🔠 В ВЕРХНИЙ РЕГИСТР")
        to_upper.triggered.connect(lambda: self.convert_case(True))

        to_lower = menu.addAction("🔡 в нижний регистр")
        to_lower.triggered.connect(lambda: self.convert_case(False))

        menu.addSeparator()

        transliterate = menu.addAction("🔤 Транслитерация RU→EN")
        transliterate.triggered.connect(lambda: self.transliterate(False))

        transliterate_back = menu.addAction("🔤 Транслитерация EN→RU")
        transliterate_back.triggered.connect(lambda: self.transliterate(True))

        menu.exec(event.globalPos())

    def select_all(self):
        """Выделить все фразы"""
        for row in range(self.rowCount()):
            if self.item(row, 0):
                self.item(row, 0).setCheckState(Qt.CheckState.Checked)

    def deselect_all(self):
        """Снять выделение со всех фраз"""
        for row in range(self.rowCount()):
            if self.item(row, 0):
                self.item(row, 0).setCheckState(Qt.CheckState.Unchecked)

    def delete_selected(self):
        """Удаление выбранных фраз"""
        # Сохраняем текущее состояние
        self.save_state()

        # Собираем невыбранные фразы
        new_data = []
        for row in range(self.rowCount()):
            if self.item(row, 0).checkState() != Qt.CheckState.Checked:
                phrase = self.item(row, 1).text()
                freq_item = self.item(row, 2)
                if isinstance(freq_item, FrequencyTableWidgetItem):
                    freq = freq_item.value
                else:
                    freq = int(freq_item.text()) if freq_item.text().isdigit() else 0
                new_data.append((phrase, freq))

        # Обновляем данные
        self.current_data = new_data
        self.update_table(self.current_data, save_history=False)
        self.history.add_state(self.current_data)

    def delete_row(self, row: int):
        """Удаление одной фразы по номеру строки"""
        if row < 0 or row >= self.rowCount():
            return
        self.save_state()
        new_data = []
        for i in range(self.rowCount()):
            if i == row:
                continue
            phrase = self.item(i, 1).text()
            freq_item = self.item(i, 2)
            if isinstance(freq_item, FrequencyTableWidgetItem):
                freq = freq_item.value
            else:
                freq = int(freq_item.text()) if freq_item.text().isdigit() else 0
            new_data.append((phrase, freq))
        self.current_data = new_data
        self.update_table(self.current_data, save_history=False)
        self.history.add_state(self.current_data)

    def save_state(self):
        """Сохранение текущего состояния для истории"""
        self.history.add_state(self.current_data)

    def undo(self):
        """Отмена последнего действия"""
        state = self.history.undo()
        if state:
            self.current_data = state
            self.update_table(self.current_data, save_history=False)

    def redo(self):
        """Повтор отмененного действия"""
        state = self.history.redo()
        if state:
            self.current_data = state
            self.update_table(self.current_data, save_history=False)

    def load_phrases(self, phrases: List[Phrase]):
        """Загрузка фраз в таблицу"""
        # Сохраняем оригинальные данные
        self.original_data = [(p.text, p.frequency) for p in phrases]
        self.current_data = self.original_data.copy()
        self.history.set_initial_state(self.current_data)
        self.update_table(self.current_data, save_history=False)

    def update_table(self, data: List[Tuple[str, int]], save_history: bool = True):
        """Обновление таблицы с учетом фильтров"""
        # Сохраняем состояние в историю если нужно
        if save_history:
            self.save_state()

        self.current_data = data

        # Применяем фильтр стоп-слов
        filtered_data = data
        if self.stop_words:
            filtered_data = self.processor.filter_by_stop_words(data, self.stop_words)

        # Применяем поисковый фильтр
        display_data = filtered_data
        if self.search_text and self.search_only_matches:
            display_data = [
                (phrase, freq) for phrase, freq in filtered_data
                if self.search_text.lower() in phrase.lower()
            ]

        self.setRowCount(len(display_data))

        # Очищаем результаты поиска
        self.search_results = []

        for i, (phrase, freq) in enumerate(display_data):
            # Чекбокс
            checkbox = QTableWidgetItem()
            checkbox.setCheckState(Qt.CheckState.Unchecked)
            self.setItem(i, 0, checkbox)

            # Фраза с подсветкой поиска
            phrase_item = QTableWidgetItem(phrase)

            # Подсветка поискового запроса
            if self.search_text and self.search_text.lower() in phrase.lower():
                phrase_item.setBackground(QBrush(QColor(255, 243, 179)))  # Мягкий желтый
                phrase_item.setForeground(QBrush(QColor(50, 50, 50)))  # Темный текст
                self.search_results.append(i)

            # Цветовая индикация по частотности для всей строки
            color = self.get_frequency_color(freq)
            if not self.search_text or self.search_text.lower() not in phrase.lower():
                phrase_item.setBackground(QBrush(color))

            self.setItem(i, 1, phrase_item)

            # Частотность с правильной сортировкой
            freq_item = FrequencyTableWidgetItem(freq)
            freq_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            freq_item.setBackground(QBrush(color))

            self.setItem(i, 2, freq_item)

    def get_frequency_color(self, freq: int) -> QColor:
        """Получение цвета в зависимости от частотности"""
        if freq >= 100000:
            return QColor(255, 220, 220)  # Красноватый для высокой частотности
        elif freq >= 10000:
            return QColor(255, 235, 215)  # Оранжевый
        elif freq >= 1000:
            return QColor(255, 250, 220)  # Желтый
        elif freq >= 100:
            return QColor(235, 255, 235)  # Светло-зеленый
        else:
            return QColor(250, 250, 250)  # Очень светло-серый для низкой

    def set_stop_words(self, stop_words: Set[str]):
        """Установка стоп-слов и обновление таблицы"""
        self.stop_words = stop_words
        # Обновляем с текущими данными, а не оригинальными
        self.update_table(self.current_data, save_history=False)

    def set_search(self, text: str, only_matches: bool):
        """Установка параметров поиска"""
        self.search_text = text
        self.search_only_matches = only_matches
        self.current_search_index = 0
        self.update_table(self.current_data, save_history=False)

        # Переходим к первому результату
        if self.search_results and not only_matches:
            self.scrollToItem(self.item(self.search_results[0], 1))
            self.selectRow(self.search_results[0])

    def next_search_result(self):
        """Переход к следующему результату поиска"""
        if self.search_results:
            self.current_search_index = (self.current_search_index + 1) % len(self.search_results)
            row = self.search_results[self.current_search_index]
            self.scrollToItem(self.item(row, 1))
            self.selectRow(row)
            return self.current_search_index + 1, len(self.search_results)
        return 0, 0

    def prev_search_result(self):
        """Переход к предыдущему результату поиска"""
        if self.search_results:
            self.current_search_index = (self.current_search_index - 1) % len(self.search_results)
            row = self.search_results[self.current_search_index]
            self.scrollToItem(self.item(row, 1))
            self.selectRow(row)
            return self.current_search_index + 1, len(self.search_results)
        return 0, 0

    def get_current_data(self) -> List[Tuple[str, int]]:
        """Получение текущих данных из таблицы"""
        return self.current_data.copy()

    def copy_selected(self):
        """Копирование выбранных фраз"""
        selected = []
        for row in range(self.rowCount()):
            if self.item(row, 0).checkState() == Qt.CheckState.Checked:
                phrase = self.item(row, 1).text()
                selected.append(phrase)

        if selected:
            clipboard = QApplication.clipboard()
            clipboard.setText('\n'.join(selected))

    def remove_duplicates(self):
        """Удаление дубликатов"""
        self.save_state()
        data = self.processor.remove_duplicates(self.current_data)
        self.current_data = data
        self.update_table(data, save_history=False)
        self.history.add_state(self.current_data)

    def remove_special_chars(self):
        """Удаление спецсимволов"""
        self.save_state()
        data = self.processor.remove_special_chars(self.current_data)
        self.current_data = data
        self.update_table(data, save_history=False)
        self.history.add_state(self.current_data)

    def remove_long_phrases(self):
        """Удаление длинных фраз"""
        self.save_state()
        data = self.processor.remove_long_phrases(self.current_data, 7)
        self.current_data = data
        self.update_table(data, save_history=False)
        self.history.add_state(self.current_data)

    def convert_case(self, to_upper: bool):
        """Преобразование регистра"""
        self.save_state()
        data = self.processor.convert_case(self.current_data, to_upper)
        self.current_data = data
        self.update_table(data, save_history=False)
        self.history.add_state(self.current_data)

    def sort_alphabetically(self, reverse: bool):
        """Сортировка по алфавиту"""
        self.save_state()
        data = self.processor.sort_phrases_alphabetically(self.current_data, reverse)
        self.current_data = data
        self.update_table(data, save_history=False)
        self.history.add_state(self.current_data)

    def sort_by_frequency(self, reverse: bool):
        """Сортировка по частотности"""
        self.save_state()
        data = self.processor.sort_phrases_by_frequency(self.current_data, reverse)
        self.current_data = data
        self.update_table(data, save_history=False)
        self.history.add_state(self.current_data)

    def transliterate(self, reverse: bool = False):
        """Транслитерация фраз"""
        self.save_state()
        data = self.processor.transliterate_phrases(self.current_data, reverse)
        self.current_data = data
        self.update_table(data, save_history=False)
        self.history.add_state(self.current_data)


class FileLoader(QThread):
    """Поток для загрузки файлов"""
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
    """Виджет для работы со стоп-словами"""

    stop_words_changed = pyqtSignal(set)

    def __init__(self):
        super().__init__()
        self.stop_words = set()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # Заголовок
        header = QLabel("🚫 Стоп-слова")
        header.setFont(QFont("SF Pro Display", 14, QFont.Weight.Bold))
        layout.addWidget(header)

        # Поле ввода
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Введите стоп-слово и нажмите Enter")
        self.input_field.returnPressed.connect(self.add_stop_word)
        self.input_field.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                background-color: #ffffff;
                color: #000000;
            }
        """)
        layout.addWidget(self.input_field)

        # Список стоп-слов
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
            }
            QListWidget::item {
                padding: 4px;
            }
            QListWidget::item:selected {
                background-color: #007aff;
                color: white;
            }
        """)
        layout.addWidget(self.list_widget)

        # Кнопки управления
        btn_layout = QHBoxLayout()

        self.remove_btn = QPushButton("Удалить выбранное")
        self.remove_btn.clicked.connect(self.remove_stop_word)
        btn_layout.addWidget(self.remove_btn)

        self.clear_btn = QPushButton("Очистить все")
        self.clear_btn.clicked.connect(self.clear_stop_words)
        btn_layout.addWidget(self.clear_btn)

        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def add_stop_word(self):
        """Добавление стоп-слова"""
        word = self.input_field.text().strip().lower()
        if word and word not in self.stop_words:
            self.stop_words.add(word)
            self.list_widget.addItem(word)
            self.input_field.clear()
            self.stop_words_changed.emit(self.stop_words)

    def remove_stop_word(self):
        """Удаление выбранного стоп-слова"""
        current_item = self.list_widget.currentItem()
        if current_item:
            word = current_item.text()
            self.stop_words.discard(word)
            self.list_widget.takeItem(self.list_widget.row(current_item))
            self.stop_words_changed.emit(self.stop_words)

    def clear_stop_words(self):
        """Очистка всех стоп-слов"""
        self.stop_words.clear()
        self.list_widget.clear()
        self.stop_words_changed.emit(self.stop_words)


class GroupingWidget(QWidget):
    """Виджет для группировки фраз в виде дерева"""

    def __init__(self):
        super().__init__()
        self.groups = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # Заголовок и кнопка экспорта
        header_layout = QHBoxLayout()

        header = QLabel("📊 Группировка фраз")
        header.setFont(QFont("SF Pro Display", 14, QFont.Weight.Bold))
        header_layout.addWidget(header)

        header_layout.addStretch()

        self.export_btn = QPushButton("📥 Экспорт в Excel")
        self.export_btn.clicked.connect(self.export_groups)
        header_layout.addWidget(self.export_btn)

        layout.addLayout(header_layout)

        # Дерево групп
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Группа / Фраза", "Частотность"])
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
            }
            QTreeWidget::item {
                padding: 2px;
            }
            QTreeWidget::item:selected {
                background-color: #007aff;
                color: white;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                color: #333333;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #d0d0d0;
                font-weight: 500;
            }
        """)
        layout.addWidget(self.tree)

        self.setLayout(layout)

    def update_groups(self, phrases: List[Tuple[str, int]]):
        """Обновление групп"""
        processor = PhraseProcessor()
        self.groups = processor.group_phrases(phrases)

        self.tree.clear()

        for group_name, group_phrases in self.groups.items():
            # Создаем группу
            group_item = QTreeWidgetItem(self.tree)
            group_item.setText(0, f"📁 {group_name} ({len(group_phrases)} фраз)")
            group_item.setExpanded(True)

            # Добавляем фразы в группу
            for phrase, freq in group_phrases:
                phrase_item = QTreeWidgetItem(group_item)
                phrase_item.setText(0, phrase)
                phrase_item.setText(1, str(freq))

                # Цветовая индикация частотности
                if freq >= 100000:
                    phrase_item.setBackground(1, QBrush(QColor(255, 220, 220)))
                elif freq >= 10000:
                    phrase_item.setBackground(1, QBrush(QColor(255, 235, 215)))
                elif freq >= 1000:
                    phrase_item.setBackground(1, QBrush(QColor(255, 250, 220)))
                elif freq >= 100:
                    phrase_item.setBackground(1, QBrush(QColor(235, 255, 235)))

    def export_groups(self):
        """Экспорт групп в Excel"""
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
                        # Создаем DataFrame для группы
                        df = pd.DataFrame(group_phrases, columns=['Фраза', 'Частотность'])

                        # Обрезаем имя листа до 31 символа (ограничение Excel)
                        sheet_name = group_name[:31] if len(group_name) > 31 else group_name

                        # Записываем в отдельный лист
                        df.to_excel(writer, sheet_name=sheet_name, index=False)

                QMessageBox.information(None, "Успех", f"Группы экспортированы в {Path(file_path).name}")
            except Exception as e:
                QMessageBox.critical(None, "Ошибка", f"Не удалось экспортировать: {str(e)}")


class MainWindow(QMainWindow):
    """Главное окно приложения"""

    def __init__(self):
        super().__init__()
        self.phrases_data = []
        self.setup_ui()
        self.setup_shortcuts()
        self.setup_style()

    def setup_ui(self):
        """Настройка интерфейса"""
        self.setWindowTitle("🔑 KeyPhrase Manager - SEO инструмент")
        self.setGeometry(100, 100, 1400, 900)

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Главный layout с минимальными отступами
        main_layout = QVBoxLayout()
        # Минимальные отступы для более плотного интерфейса
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        central_widget.setLayout(main_layout)

        # Панель инструментов
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 0)

        self.load_btn = QPushButton("📁 Загрузить файлы")
        self.load_btn.clicked.connect(self.load_files)
        toolbar_layout.addWidget(self.load_btn)

        self.save_btn = QPushButton("💾 Сохранить")
        self.save_btn.clicked.connect(self.save_file)
        toolbar_layout.addWidget(self.save_btn)

        toolbar_layout.addStretch()

        self.phrase_count_label = QLabel("Фраз загружено: 0")
        self.phrase_count_label.setFont(QFont("SF Pro Display", 12))
        toolbar_layout.addWidget(self.phrase_count_label)

        self.filtered_count_label = QLabel("")
        self.filtered_count_label.setFont(QFont("SF Pro Display", 12))
        self.filtered_count_label.setStyleSheet("color: #007aff;")
        toolbar_layout.addWidget(self.filtered_count_label)

        main_layout.addLayout(toolbar_layout)

        # Панель поиска
        self.search_widget = SearchWidget()
        self.search_widget.search_changed.connect(self.on_search_changed)
        self.search_widget.prev_btn.clicked.connect(self.prev_search)
        self.search_widget.next_btn.clicked.connect(self.next_search)
        main_layout.addWidget(self.search_widget)

        # Разделитель для основного контента
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Левая панель - основная таблица
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(5)

        editor_label = QLabel("📝 Фразы")
        editor_label.setFont(QFont("SF Pro Display", 14, QFont.Weight.Bold))
        left_layout.addWidget(editor_label)

        self.main_table = MainPhraseTable()
        left_layout.addWidget(self.main_table)

        left_panel.setLayout(left_layout)
        splitter.addWidget(left_panel)

        # Правая панель - вкладки
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #d0d0d0;
                background-color: #ffffff;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #f5f5f5;
                color: #333333;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: #007aff;
                color: white;
            }
        """)

        # Вкладка стоп-слов
        self.stop_words_widget = StopWordsWidget()
        self.stop_words_widget.stop_words_changed.connect(self.on_stop_words_changed)
        self.tabs.addTab(self.stop_words_widget, "🚫 Стоп-слова")

        # Вкладка группировки
        self.grouping_widget = GroupingWidget()
        self.tabs.addTab(self.grouping_widget, "🗂 Группировка")

        splitter.addWidget(self.tabs)
        splitter.setSizes([900, 500])

        main_layout.addWidget(splitter)

        # Статус бар
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов к работе")

    def setup_shortcuts(self):
        """Настройка горячих клавиш"""
        # Cmd+Z для отмены
        undo_shortcut = QShortcut(QKeySequence("Cmd+Z"), self)
        undo_shortcut.activated.connect(self.main_table.undo)

        # Cmd+Shift+Z для повтора
        redo_shortcut = QShortcut(QKeySequence("Cmd+Shift+Z"), self)
        redo_shortcut.activated.connect(self.main_table.redo)

        # Cmd+F для поиска
        search_shortcut = QShortcut(QKeySequence("Cmd+F"), self)
        search_shortcut.activated.connect(lambda: self.search_widget.search_input.setFocus())

    def setup_style(self):
        """Настройка стилей"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QPushButton {
                background-color: #007aff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #0051d5;
            }
            QPushButton:pressed {
                background-color: #0041a8;
            }
            QLabel {
                color: #333333;
            }
        """)

    def load_files(self):
        """Загрузка файлов"""
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
            self.status_bar.showMessage("Загрузка файлов...")

    def on_files_loaded(self, phrases: List[Phrase]):
        """Обработка загруженных файлов"""
        self.phrases_data.extend(phrases)

        # Загружаем в таблицу
        self.main_table.load_phrases(self.phrases_data)

        # Обновляем счетчик
        self.update_phrase_count()

        # Обновляем группировку
        data = [(p.text, p.frequency) for p in self.phrases_data]
        self.grouping_widget.update_groups(data)

        self.status_bar.showMessage(f"Загружено {len(phrases)} фраз")

    def on_load_error(self, error: str):
        """Обработка ошибок загрузки"""
        QMessageBox.warning(self, "Ошибка", error)
        self.status_bar.showMessage("Ошибка при загрузке")

    def on_stop_words_changed(self, stop_words: Set[str]):
        """Обработка изменения стоп-слов"""
        self.main_table.set_stop_words(stop_words)
        self.update_phrase_count()

        # Обновляем группировку с учетом фильтра
        current_data = self.main_table.get_current_data()
        self.grouping_widget.update_groups(current_data)

    def on_search_changed(self, text: str, only_matches: bool):
        """Обработка изменения поиска"""
        self.main_table.set_search(text, only_matches)

        # Обновляем счетчик результатов
        if text:
            total = len(self.main_table.search_results)
            if total > 0:
                self.search_widget.update_results(1, total)
            else:
                self.search_widget.update_results(0, 0)

    def next_search(self):
        """Следующий результат поиска"""
        current, total = self.main_table.next_search_result()
        self.search_widget.update_results(current, total)

    def prev_search(self):
        """Предыдущий результат поиска"""
        current, total = self.main_table.prev_search_result()
        self.search_widget.update_results(current, total)

    def update_phrase_count(self):
        """Обновление счетчика фраз"""
        total = len(self.main_table.current_data)
        self.phrase_count_label.setText(f"Всего фраз: {total}")

        # Если есть фильтр, показываем количество после фильтрации
        if self.stop_words_widget.stop_words:
            filtered = self.main_table.rowCount()
            self.filtered_count_label.setText(f"(после фильтра: {filtered})")
        else:
            self.filtered_count_label.setText("")

    def save_file(self):
        """Сохранение файла"""
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

                self.status_bar.showMessage(f"Файл сохранен: {Path(file_path).name}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл: {str(e)}")


def main():
    """Точка входа в приложение"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
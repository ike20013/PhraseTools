#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KeyPhrase Manager Pro - Futuristic SEO Tool
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
    QCheckBox, QSpinBox, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import (
    QAction, QFont, QPalette, QColor, QBrush, QLinearGradient,
    QKeySequence, QShortcut, QTextCharFormat, QTextCursor, QPainter
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


class FuturisticButton(QPushButton):
    """Футуристическая кнопка с эффектами"""

    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setup_style()
        self.add_shadow()

    def setup_style(self):
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 25px;
                font-weight: 600;
                font-size: 14px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #764ba2, stop:1 #667eea);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #5a67d8, stop:1 #6b46c1);
            }
        """)

    def add_shadow(self):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(102, 126, 234, 100))
        shadow.setOffset(0, 5)
        self.setGraphicsEffect(shadow)


class SearchWidget(QWidget):
    """Футуристический виджет поиска"""

    search_changed = pyqtSignal(str, bool)

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # Контейнер для поиска
        search_container = QWidget()
        search_container.setStyleSheet("""
            QWidget {
                background: rgba(30, 30, 46, 0.95);
                border-radius: 30px;
                border: 1px solid rgba(102, 126, 234, 0.3);
            }
        """)
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(20, 10, 20, 10)

        # Поле поиска
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Поиск по фразам...")
        self.search_input.textChanged.connect(self.on_search_changed)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: #ffffff;
                font-size: 15px;
                padding: 5px;
            }
            QLineEdit::placeholder {
                color: rgba(255, 255, 255, 0.5);
            }
        """)
        search_layout.addWidget(self.search_input)

        # Чекбокс "Только совпадения"
        self.only_matches = QCheckBox("Только совпадения")
        self.only_matches.setStyleSheet("""
            QCheckBox {
                color: rgba(255, 255, 255, 0.8);
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid #667eea;
                background: transparent;
            }
            QCheckBox::indicator:checked {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                border: 2px solid #764ba2;
            }
        """)
        self.only_matches.toggled.connect(self.on_filter_changed)
        search_layout.addWidget(self.only_matches)

        search_container.setLayout(search_layout)
        layout.addWidget(search_container)

        # Кнопки навигации
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setFixedSize(40, 40)
        self.prev_btn.setEnabled(False)
        self.prev_btn.setStyleSheet("""
            QPushButton {
                background: rgba(102, 126, 234, 0.2);
                border: 2px solid rgba(102, 126, 234, 0.5);
                border-radius: 20px;
                color: #667eea;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover:enabled {
                background: rgba(102, 126, 234, 0.4);
                border: 2px solid #667eea;
                color: white;
            }
            QPushButton:disabled {
                background: rgba(50, 50, 50, 0.2);
                border: 2px solid rgba(100, 100, 100, 0.2);
                color: rgba(255, 255, 255, 0.2);
            }
        """)
        layout.addWidget(self.prev_btn)

        self.next_btn = QPushButton("▶")
        self.next_btn.setFixedSize(40, 40)
        self.next_btn.setEnabled(False)
        self.next_btn.setStyleSheet(self.prev_btn.styleSheet())
        layout.addWidget(self.next_btn)

        # Счетчик результатов
        self.result_label = QLabel("")
        self.result_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: 600;
                color: #00ff88;
                padding: 8px 15px;
                background: rgba(0, 255, 136, 0.1);
                border: 1px solid rgba(0, 255, 136, 0.3);
                border-radius: 20px;
            }
        """)
        layout.addWidget(self.result_label)

        layout.addStretch()
        self.setLayout(layout)

    def on_search_changed(self):
        """Изменение текста поиска"""
        text = self.search_input.text()
        self.search_changed.emit(text, self.only_matches.isChecked())

        has_text = bool(text)
        self.prev_btn.setEnabled(has_text)
        self.next_btn.setEnabled(has_text)

    def on_filter_changed(self):
        """Изменение фильтра"""
        self.on_search_changed()

    def update_results(self, current: int, total: int):
        """Обновление счетчика результатов"""
        if total > 0:
            self.result_label.setText(f"✨ {current}/{total}")
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
    """Футуристическая таблица с фразами"""

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
        self.setup_ui()

    def setup_ui(self):
        """Настройка футуристического дизайна таблицы"""
        # Настройка колонок
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["✓", "Фраза", "Частотность"])

        # Настройка ширины колонок
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(0, 40)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(2, 130)

        # Включаем сортировку
        self.setSortingEnabled(True)

        # Футуристический стиль
        self.setStyleSheet("""
            QTableWidget {
                background-color: #1a1a2e;
                color: #eaeaea;
                gridline-color: rgba(102, 126, 234, 0.2);
                border: 2px solid rgba(102, 126, 234, 0.3);
                border-radius: 15px;
                font-family: "SF Pro Display", -apple-system, sans-serif;
                font-size: 14px;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid rgba(102, 126, 234, 0.1);
            }
            QTableWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(102, 126, 234, 0.4), 
                    stop:1 rgba(118, 75, 162, 0.4));
                color: white;
            }
            QTableWidget::item:hover {
                background: rgba(102, 126, 234, 0.1);
            }
            QHeaderView::section {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #16213e, stop:1 #1a1a2e);
                color: #00ff88;
                padding: 10px;
                border: none;
                border-bottom: 2px solid rgba(0, 255, 136, 0.3);
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            QScrollBar:vertical {
                background: #1a1a2e;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #764ba2, stop:1 #667eea);
            }
        """)

        # Настройка поведения
        self.setAlternatingRowColors(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.verticalHeader().setVisible(False)

    def contextMenuEvent(self, event):
        """Создание футуристического контекстного меню"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: rgba(26, 26, 46, 0.98);
                color: #ffffff;
                border: 2px solid rgba(102, 126, 234, 0.5);
                border-radius: 15px;
                padding: 10px;
            }
            QMenu::item {
                padding: 10px 20px;
                border-radius: 8px;
                margin: 2px 0;
            }
            QMenu::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(102, 126, 234, 0.4), 
                    stop:1 rgba(118, 75, 162, 0.4));
            }
            QMenu::separator {
                height: 1px;
                background: rgba(102, 126, 234, 0.2);
                margin: 5px 0;
            }
        """)

        # Получаем текущую строку
        current_row = self.currentRow()

        # Удаление текущей фразы
        if current_row >= 0:
            delete_current = menu.addAction("🗑 Удалить эту фразу")
            delete_current.triggered.connect(lambda: self.delete_phrase(current_row))
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

        remove_special = menu.addAction("🧹 Удалить спецсимволы")
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

    def delete_phrase(self, visual_row: int):
        """Удаление конкретной фразы по визуальной строке"""
        # Сохраняем состояние
        self.save_state()

        # Получаем фразу из визуальной строки
        phrase_item = self.item(visual_row, 1)
        freq_item = self.item(visual_row, 2)

        if phrase_item and freq_item:
            phrase_to_delete = phrase_item.text()

            # Удаляем из current_data по значению, а не по индексу
            self.current_data = [
                (p, f) for p, f in self.current_data
                if p != phrase_to_delete
            ]

            self.update_table(self.current_data, save_history=False)

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
        """Удаление выбранных фраз по галочкам"""
        # Сохраняем текущее состояние
        self.save_state()

        # Собираем фразы для удаления
        phrases_to_delete = set()
        for row in range(self.rowCount()):
            if self.item(row, 0).checkState() == Qt.CheckState.Checked:
                phrase_item = self.item(row, 1)
                if phrase_item:
                    phrases_to_delete.add(phrase_item.text())

        # Удаляем из current_data по значениям
        self.current_data = [
            (p, f) for p, f in self.current_data
            if p not in phrases_to_delete
        ]

        self.update_table(self.current_data, save_history=False)

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
        self.original_data = [(p.text, p.frequency) for p in phrases]
        self.current_data = self.original_data.copy()
        self.history.set_initial_state(self.current_data)
        self.update_table(self.current_data, save_history=False)

    def update_table(self, data: List[Tuple[str, int]], save_history: bool = True):
        """Обновление таблицы с учетом фильтров"""
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

        # Отключаем сортировку на время обновления
        self.setSortingEnabled(False)

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
                phrase_item.setBackground(QBrush(QColor(0, 255, 136, 50)))
                phrase_item.setForeground(QBrush(QColor(255, 255, 255)))
                self.search_results.append(i)
            else:
                # Цветовая индикация по частотности
                color = self.get_frequency_color(freq)
                phrase_item.setBackground(QBrush(color))
                phrase_item.setForeground(QBrush(QColor(230, 230, 230)))

            self.setItem(i, 1, phrase_item)

            # Частотность с правильной сортировкой
            freq_item = FrequencyTableWidgetItem(freq)
            freq_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            # Стиль для частотности
            if freq >= 100000:
                freq_item.setForeground(QBrush(QColor(255, 100, 100)))  # Красный
            elif freq >= 10000:
                freq_item.setForeground(QBrush(QColor(255, 180, 100)))  # Оранжевый
            elif freq >= 1000:
                freq_item.setForeground(QBrush(QColor(255, 255, 100)))  # Желтый
            elif freq >= 100:
                freq_item.setForeground(QBrush(QColor(100, 255, 100)))  # Зеленый
            else:
                freq_item.setForeground(QBrush(QColor(150, 150, 150)))  # Серый

            freq_item.setFont(QFont("SF Pro Display", 12, QFont.Weight.Bold))

            self.setItem(i, 2, freq_item)

        # Включаем сортировку обратно
        self.setSortingEnabled(True)

    def get_frequency_color(self, freq: int) -> QColor:
        """Получение цвета фона в зависимости от частотности"""
        if freq >= 100000:
            return QColor(255, 100, 100, 20)  # Полупрозрачный красный
        elif freq >= 10000:
            return QColor(255, 180, 100, 20)  # Полупрозрачный оранжевый
        elif freq >= 1000:
            return QColor(255, 255, 100, 20)  # Полупрозрачный желтый
        elif freq >= 100:
            return QColor(100, 255, 100, 20)  # Полупрозрачный зеленый
        else:
            return QColor(26, 26, 46, 0)  # Прозрачный

    def set_stop_words(self, stop_words: Set[str]):
        """Установка стоп-слов и обновление таблицы"""
        self.stop_words = stop_words
        self.update_table(self.current_data, save_history=False)

    def set_search(self, text: str, only_matches: bool):
        """Установка параметров поиска"""
        self.search_text = text
        self.search_only_matches = only_matches
        self.current_search_index = 0
        self.update_table(self.current_data, save_history=False)

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
        """Получение текущих данных"""
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

    def remove_special_chars(self):
        """Удаление спецсимволов"""
        self.save_state()
        data = self.processor.remove_special_chars(self.current_data)
        self.current_data = data
        self.update_table(data, save_history=False)

    def remove_long_phrases(self):
        """Удаление длинных фраз"""
        self.save_state()
        data = self.processor.remove_long_phrases(self.current_data, 7)
        self.current_data = data
        self.update_table(data, save_history=False)

    def convert_case(self, to_upper: bool):
        """Преобразование регистра"""
        self.save_state()
        data = self.processor.convert_case(self.current_data, to_upper)
        self.current_data = data
        self.update_table(data, save_history=False)

    def sort_alphabetically(self, reverse: bool):
        """Сортировка по алфавиту"""
        self.save_state()
        data = self.processor.sort_phrases_alphabetically(self.current_data, reverse)
        self.current_data = data
        self.update_table(data, save_history=False)

    def sort_by_frequency(self, reverse: bool):
        """Сортировка по частотности"""
        self.save_state()
        data = self.processor.sort_phrases_by_frequency(self.current_data, reverse)
        self.current_data = data
        self.update_table(data, save_history=False)

    def transliterate(self, reverse: bool = False):
        """Транслитерация фраз"""
        self.save_state()
        data = self.processor.transliterate_phrases(self.current_data, reverse)
        self.current_data = data
        self.update_table(data, save_history=False)


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
    """Футуристический виджет стоп-слов"""

    stop_words_changed = pyqtSignal(set)

    def __init__(self):
        super().__init__()
        self.stop_words = set()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)

        # Заголовок
        header = QLabel("🚫 СТОП-СЛОВА")
        header.setFont(QFont("SF Pro Display", 16, QFont.Weight.Bold))
        header.setStyleSheet("color: #00ff88; letter-spacing: 2px;")
        layout.addWidget(header)

        # Поле ввода
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Введите стоп-слово...")
        self.input_field.returnPressed.connect(self.add_stop_word)
        self.input_field.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 2px solid rgba(102, 126, 234, 0.3);
                border-radius: 10px;
                background: rgba(26, 26, 46, 0.6);
                color: #ffffff;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #667eea;
                background: rgba(26, 26, 46, 0.8);
            }
        """)
        layout.addWidget(self.input_field)

        # Список стоп-слов
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: rgba(26, 26, 46, 0.4);
                color: #ffffff;
                border: 2px solid rgba(102, 126, 234, 0.2);
                border-radius: 10px;
                padding: 10px;
            }
            QListWidget::item {
                padding: 8px;
                margin: 2px 0;
                border-radius: 5px;
            }
            QListWidget::item:selected {
                background: rgba(102, 126, 234, 0.3);
            }
            QListWidget::item:hover {
                background: rgba(102, 126, 234, 0.2);
            }
        """)
        layout.addWidget(self.list_widget)

        # Кнопки управления
        btn_layout = QHBoxLayout()

        self.remove_btn = FuturisticButton("Удалить")
        self.remove_btn.clicked.connect(self.remove_stop_word)
        btn_layout.addWidget(self.remove_btn)

        self.clear_btn = FuturisticButton("Очистить")
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
    """Футуристический виджет группировки"""

    def __init__(self):
        super().__init__()
        self.groups = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)

        # Заголовок и кнопка экспорта
        header_layout = QHBoxLayout()

        header = QLabel("📊 ГРУППИРОВКА")
        header.setFont(QFont("SF Pro Display", 16, QFont.Weight.Bold))
        header.setStyleSheet("color: #00ff88; letter-spacing: 2px;")
        header_layout.addWidget(header)

        header_layout.addStretch()

        self.export_btn = FuturisticButton("📥 Экспорт")
        self.export_btn.clicked.connect(self.export_groups)
        header_layout.addWidget(self.export_btn)

        layout.addLayout(header_layout)

        # Дерево групп
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Группа / Фраза", "Частотность"])
        self.tree.setStyleSheet("""
            QTreeWidget {
                background: rgba(26, 26, 46, 0.4);
                color: #ffffff;
                border: 2px solid rgba(102, 126, 234, 0.2);
                border-radius: 10px;
                padding: 10px;
            }
            QTreeWidget::item {
                padding: 5px;
            }
            QTreeWidget::item:selected {
                background: rgba(102, 126, 234, 0.3);
            }
            QTreeWidget::item:hover {
                background: rgba(102, 126, 234, 0.2);
            }
            QHeaderView::section {
                background: transparent;
                color: #00ff88;
                padding: 8px;
                border: none;
                border-bottom: 1px solid rgba(0, 255, 136, 0.3);
                font-weight: 600;
                text-transform: uppercase;
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
            group_item.setText(0, f"📁 {group_name} ({len(group_phrases)})")
            group_item.setExpanded(True)

            # Добавляем фразы в группу
            for phrase, freq in group_phrases:
                phrase_item = QTreeWidgetItem(group_item)
                phrase_item.setText(0, phrase)
                phrase_item.setText(1, str(freq))

                # Цветовая индикация частотности
                if freq >= 100000:
                    phrase_item.setForeground(1, QBrush(QColor(255, 100, 100)))
                elif freq >= 10000:
                    phrase_item.setForeground(1, QBrush(QColor(255, 180, 100)))
                elif freq >= 1000:
                    phrase_item.setForeground(1, QBrush(QColor(255, 255, 100)))
                elif freq >= 100:
                    phrase_item.setForeground(1, QBrush(QColor(100, 255, 100)))

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
                        df = pd.DataFrame(group_phrases, columns=['Фраза', 'Частотность'])
                        sheet_name = group_name[:31] if len(group_name) > 31 else group_name
                        df.to_excel(writer, sheet_name=sheet_name, index=False)

                QMessageBox.information(None, "Успех", f"Группы экспортированы в {Path(file_path).name}")
            except Exception as e:
                QMessageBox.critical(None, "Ошибка", f"Не удалось экспортировать: {str(e)}")


class MainWindow(QMainWindow):
    """Главное футуристическое окно приложения"""

    def __init__(self):
        super().__init__()
        self.phrases_data = []
        self.setup_ui()
        self.setup_shortcuts()
        self.setup_style()

    def setup_ui(self):
        """Настройка интерфейса"""
        self.setWindowTitle("🚀 KeyPhrase Manager Pro - Future SEO Tool")
        self.setGeometry(100, 100, 1400, 900)

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Главный layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        central_widget.setLayout(main_layout)

        # Панель инструментов
        toolbar_widget = QWidget()
        toolbar_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #16213e, stop:1 #0f1627);
                border-bottom: 2px solid rgba(0, 255, 136, 0.3);
            }
        """)
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(15, 10, 15, 10)

        self.load_btn = FuturisticButton("📁 ЗАГРУЗИТЬ")
        self.load_btn.clicked.connect(self.load_files)
        toolbar_layout.addWidget(self.load_btn)

        self.save_btn = FuturisticButton("💾 СОХРАНИТЬ")
        self.save_btn.clicked.connect(self.save_file)
        toolbar_layout.addWidget(self.save_btn)

        toolbar_layout.addStretch()

        # Счетчики
        counter_widget = QWidget()
        counter_widget.setStyleSheet("""
            QWidget {
                background: rgba(0, 255, 136, 0.1);
                border: 1px solid rgba(0, 255, 136, 0.3);
                border-radius: 20px;
                padding: 5px 15px;
            }
        """)
        counter_layout = QHBoxLayout()
        counter_layout.setContentsMargins(10, 5, 10, 5)

        self.phrase_count_label = QLabel("ФРАЗ: 0")
        self.phrase_count_label.setFont(QFont("SF Pro Display", 13, QFont.Weight.Bold))
        self.phrase_count_label.setStyleSheet("color: #00ff88;")
        counter_layout.addWidget(self.phrase_count_label)

        self.filtered_count_label = QLabel("")
        self.filtered_count_label.setFont(QFont("SF Pro Display", 13))
        self.filtered_count_label.setStyleSheet("color: #667eea;")
        counter_layout.addWidget(self.filtered_count_label)

        counter_widget.setLayout(counter_layout)
        toolbar_layout.addWidget(counter_widget)

        toolbar_widget.setLayout(toolbar_layout)
        main_layout.addWidget(toolbar_widget)

        # Панель поиска
        self.search_widget = SearchWidget()
        self.search_widget.search_changed.connect(self.on_search_changed)
        self.search_widget.prev_btn.clicked.connect(self.prev_search)
        self.search_widget.next_btn.clicked.connect(self.next_search)
        main_layout.addWidget(self.search_widget)

        # Основной контент
        content_widget = QWidget()
        content_widget.setStyleSheet("background: #0f1627;")
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(10)

        # Левая панель - основная таблица
        left_panel = QWidget()
        left_panel.setStyleSheet("""
            QWidget {
                background: rgba(26, 26, 46, 0.6);
                border-radius: 15px;
                border: 1px solid rgba(102, 126, 234, 0.2);
            }
        """)
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(10, 10, 10, 10)

        editor_label = QLabel("📝 ФРАЗЫ")
        editor_label.setFont(QFont("SF Pro Display", 14, QFont.Weight.Bold))
        editor_label.setStyleSheet("color: #00ff88; letter-spacing: 1px;")
        left_layout.addWidget(editor_label)

        self.main_table = MainPhraseTable()
        left_layout.addWidget(self.main_table)

        left_panel.setLayout(left_layout)
        content_layout.addWidget(left_panel, 3)

        # Правая панель - вкладки
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                background: rgba(26, 26, 46, 0.6);
                border: 1px solid rgba(102, 126, 234, 0.2);
                border-radius: 15px;
            }
            QTabBar::tab {
                background: rgba(102, 126, 234, 0.2);
                color: #ffffff;
                padding: 10px 20px;
                margin: 0 2px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                font-weight: 600;
                text-transform: uppercase;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(102, 126, 234, 0.5), 
                    stop:1 rgba(118, 75, 162, 0.5));
                color: #00ff88;
            }
        """)

        # Вкладка стоп-слов
        self.stop_words_widget = StopWordsWidget()
        self.stop_words_widget.stop_words_changed.connect(self.on_stop_words_changed)
        self.tabs.addTab(self.stop_words_widget, "🚫 СТОП-СЛОВА")

        # Вкладка группировки
        self.grouping_widget = GroupingWidget()
        self.tabs.addTab(self.grouping_widget, "🗂 ГРУППИРОВКА")

        content_layout.addWidget(self.tabs, 1)

        content_widget.setLayout(content_layout)
        main_layout.addWidget(content_widget)

        # Статус бар
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background: #0f1627;
                color: #667eea;
                border-top: 1px solid rgba(102, 126, 234, 0.2);
                font-size: 12px;
            }
        """)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("🚀 READY TO LAUNCH")

    def setup_shortcuts(self):
        """Настройка горячих клавиш"""
        undo_shortcut = QShortcut(QKeySequence("Cmd+Z"), self)
        undo_shortcut.activated.connect(self.main_table.undo)

        redo_shortcut = QShortcut(QKeySequence("Cmd+Shift+Z"), self)
        redo_shortcut.activated.connect(self.main_table.redo)

        search_shortcut = QShortcut(QKeySequence("Cmd+F"), self)
        search_shortcut.activated.connect(lambda: self.search_widget.search_input.setFocus())

    def setup_style(self):
        """Настройка футуристического стиля"""
        self.setStyleSheet("""
            QMainWindow {
                background: #0f1627;
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
            self.status_bar.showMessage("⚡ ЗАГРУЗКА...")

    def on_files_loaded(self, phrases: List[Phrase]):
        """Обработка загруженных файлов"""
        self.phrases_data.extend(phrases)

        self.main_table.load_phrases(self.phrases_data)
        self.update_phrase_count()

        data = [(p.text, p.frequency) for p in self.phrases_data]
        self.grouping_widget.update_groups(data)

        self.status_bar.showMessage(f"✅ ЗАГРУЖЕНО {len(phrases)} ФРАЗ")

    def on_load_error(self, error: str):
        """Обработка ошибок загрузки"""
        QMessageBox.warning(self, "Ошибка", error)
        self.status_bar.showMessage("❌ ОШИБКА ЗАГРУЗКИ")

    def on_stop_words_changed(self, stop_words: Set[str]):
        """Обработка изменения стоп-слов"""
        self.main_table.set_stop_words(stop_words)
        self.update_phrase_count()

        current_data = self.main_table.get_current_data()
        self.grouping_widget.update_groups(current_data)

    def on_search_changed(self, text: str, only_matches: bool):
        """Обработка изменения поиска"""
        self.main_table.set_search(text, only_matches)

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
        self.phrase_count_label.setText(f"ФРАЗ: {total}")

        if self.stop_words_widget.stop_words:
            filtered = self.main_table.rowCount()
            self.filtered_count_label.setText(f"| ПОСЛЕ ФИЛЬТРА: {filtered}")
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

                self.status_bar.showMessage(f"💾 СОХРАНЕНО: {Path(file_path).name}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {str(e)}")


def main():
    """Точка входа в приложение"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Футуристическая палитра
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(15, 22, 39))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    app.setPalette(palette)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
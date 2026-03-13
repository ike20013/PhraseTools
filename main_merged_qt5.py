#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PhraseTools - Modern SEO Tool with License Protection
"""

import sys
import re
import copy
import json
import hashlib
import platform
import uuid
import socket
import base64
import pickle
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
import pandas as pd
from transliterate import translit

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTabWidget, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView, QMenu,
    QMessageBox, QListWidget, QGroupBox, QLineEdit,
    QComboBox, QProgressBar, QStatusBar, QTextEdit,
    QAbstractItemView, QTreeWidget, QTreeWidgetItem,
    QCheckBox, QSpinBox, QGraphicsDropShadowEffect,
    QListWidgetItem, QInputDialog, QDialog, QAction, QShortcut
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QMimeData
from PyQt5.QtGui import (
    QFont, QPalette, QColor, QBrush, QLinearGradient,
    QKeySequence, QTextCharFormat, QTextCursor, QPainter,
    QDrag, QIcon
)


class LicenseManager:
    """Менеджер лицензий для защиты приложения"""

    def __init__(self):
        self.license_file = Path.home() / ".phrasetools" / "license.key"
        self.license_file.parent.mkdir(parents=True, exist_ok=True)
        self.hardware_id = self._generate_hardware_id()

    def _generate_hardware_id(self) -> str:
        """Генерация уникального ID устройства"""
        components = []

        # MAC адрес
        try:
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff)
                            for ele in range(0, 8 * 6, 8)][::-1])
            components.append(mac)
        except:
            components.append("NO_MAC")

        # Имя компьютера
        try:
            hostname = socket.gethostname()
            components.append(hostname)
        except:
            components.append("NO_HOSTNAME")

        # Платформа и архитектура
        components.append(platform.system())
        components.append(platform.machine())

        # UUID системы (если доступен)
        try:
            if platform.system() == "Windows":
                import subprocess
                result = subprocess.run(['wmic', 'csproduct', 'get', 'UUID'],
                                        capture_output=True, text=True)
                if result.stdout:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:
                        system_uuid = lines[1].strip()
                        components.append(system_uuid)
            elif platform.system() == "Darwin":  # macOS
                import subprocess
                result = subprocess.run(['system_profiler', 'SPHardwareDataType'],
                                        capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if 'Hardware UUID' in line:
                        system_uuid = line.split(':')[1].strip()
                        components.append(system_uuid)
                        break
            elif platform.system() == "Linux":
                try:
                    with open('/sys/class/dmi/id/product_uuid', 'r') as f:
                        system_uuid = f.read().strip()
                        components.append(system_uuid)
                except:
                    pass
        except:
            pass

        # Создаем составной хеш
        combined = '|'.join(components)
        hardware_hash = hashlib.sha256(combined.encode()).hexdigest()

        # Добавляем соль для усложнения
        salt = "PhraseTools2024SecretSalt"
        final_hash = hashlib.sha512(f"{hardware_hash}{salt}".encode()).hexdigest()

        return final_hash[:32]  # Берем первые 32 символа

    def _generate_license_key(self, hardware_id: str) -> str:
        """Генерация лицензионного ключа для конкретного hardware_id"""
        secret = "SuperSecretKey2024PhraseTools"
        combined = f"{hardware_id}{secret}"

        # Многоуровневое хеширование
        hash1 = hashlib.sha256(combined.encode()).hexdigest()
        hash2 = hashlib.sha512(f"{hash1}{secret}".encode()).hexdigest()
        hash3 = hashlib.sha256(f"{hash2}{hardware_id}".encode()).hexdigest()

        # Форматируем ключ в читаемый вид (XXXX-XXXX-XXXX-XXXX)
        key = hash3[:16].upper()
        formatted_key = '-'.join([key[i:i + 4] for i in range(0, 16, 4)])

        return formatted_key

    def verify_license(self, license_key: str) -> bool:
        """Проверка лицензионного ключа"""
        expected_key = self._generate_license_key(self.hardware_id)
        return license_key.strip().upper() == expected_key

    def save_license(self, license_key: str) -> bool:
        """Сохранение лицензионного ключа"""
        if self.verify_license(license_key):
            # Шифруем ключ перед сохранением
            encrypted_data = {
                "key": license_key,
                "hardware_id": self.hardware_id,
                "activation_date": datetime.now().isoformat(),
                "checksum": hashlib.sha256(f"{license_key}{self.hardware_id}".encode()).hexdigest()
            }

            with open(self.license_file, 'w') as f:
                # Кодируем в base64 для обфускации
                json_str = json.dumps(encrypted_data)
                encoded = base64.b64encode(json_str.encode()).decode()
                f.write(encoded)

            return True
        return False

    def load_license(self) -> Optional[str]:
        """Загрузка лицензионного ключа"""
        if not self.license_file.exists():
            return None

        try:
            with open(self.license_file, 'r') as f:
                encoded = f.read()
                decoded = base64.b64decode(encoded.encode()).decode()
                data = json.loads(decoded)

                # Проверяем целостность данных
                checksum = hashlib.sha256(f"{data['key']}{data['hardware_id']}".encode()).hexdigest()
                if checksum != data['checksum']:
                    return None

                # Проверяем, что ключ для этого устройства
                if data['hardware_id'] != self.hardware_id:
                    return None

                return data['key']
        except:
            return None

    def get_device_info(self) -> str:
        """Получение информации об устройстве для отправки разработчику"""
        info = {
            "hardware_id": self.hardware_id,
            "platform": platform.system(),
            "platform_version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "hostname": socket.gethostname() if hasattr(socket, 'gethostname') else "unknown",
            "request_date": datetime.now().isoformat()
        }

        # Кодируем в base64 для удобной передачи
        json_str = json.dumps(info, indent=2)
        encoded = base64.b64encode(json_str.encode()).decode()

        # Форматируем для удобного копирования
        formatted = '\n'.join([encoded[i:i + 64] for i in range(0, len(encoded), 64)])

        return f"=== DEVICE INFO START ===\n{formatted}\n=== DEVICE INFO END ==="

    def is_licensed(self) -> bool:
        """Проверка наличия валидной лицензии"""
        license_key = self.load_license()
        if license_key:
            return self.verify_license(license_key)
        return False


class LicenseDialog(QDialog):
    """Диалог активации лицензии"""

    def __init__(self, license_manager: LicenseManager, parent=None):
        super().__init__(parent)
        self.license_manager = license_manager
        self.setWindowTitle("Активация PhraseTools")
        self.setFixedSize(500, 400)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Заголовок
        title = QLabel("Требуется активация")
        title.setFont(QFont("-apple-system", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Информация
        info_text = QLabel(
            "Для использования PhraseTools необходима лицензия.\n"
            "Скопируйте информацию об устройстве и отправьте разработчику\n"
            "для получения лицензионного ключа."
        )
        info_text.setWordWrap(True)
        info_text.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_text)

        # Информация об устройстве
        device_info_label = QLabel("Информация об устройстве:")
        device_info_label.setFont(QFont("-apple-system", 12, QFont.Bold))
        layout.addWidget(device_info_label)

        self.device_info_text = QTextEdit()
        self.device_info_text.setPlainText(self.license_manager.get_device_info())
        self.device_info_text.setReadOnly(True)
        self.device_info_text.setMaximumHeight(150)
        self.device_info_text.setStyleSheet("""
            QTextEdit {
                font-family: monospace;
                font-size: 10px;
                background-color: #f5f5f5;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        layout.addWidget(self.device_info_text)

        # Кнопка копирования
        copy_btn = QPushButton("Копировать информацию об устройстве")
        copy_btn.clicked.connect(self.copy_device_info)
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #007aff;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0051d5;
            }
        """)
        layout.addWidget(copy_btn)

        # Поле ввода ключа
        key_label = QLabel("Лицензионный ключ:")
        key_label.setFont(QFont("-apple-system", 12, QFont.Bold))
        layout.addWidget(key_label)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.key_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                font-size: 14px;
                font-family: monospace;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QLineEdit:focus {
                border: 1px solid #007aff;
            }
        """)
        layout.addWidget(self.key_input)

        # Кнопки
        btn_layout = QHBoxLayout()

        self.activate_btn = QPushButton("Активировать")
        self.activate_btn.clicked.connect(self.activate_license)
        self.activate_btn.setStyleSheet("""
            QPushButton {
                background-color: #34c759;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: 600;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #248a3d;
            }
        """)
        btn_layout.addWidget(self.activate_btn)

        self.exit_btn = QPushButton("Выход")
        self.exit_btn.clicked.connect(self.reject)
        self.exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff3b30;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: 600;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #c70000;
            }
        """)
        btn_layout.addWidget(self.exit_btn)

        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def copy_device_info(self):
        """Копирование информации об устройстве в буфер обмена"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.device_info_text.toPlainText())
        QMessageBox.information(self, "Скопировано",
                                "Информация об устройстве скопирована в буфер обмена.\n"
                                "Отправьте её разработчику для получения ключа.")

    def activate_license(self):
        """Активация лицензии"""
        license_key = self.key_input.text().strip()

        if not license_key:
            QMessageBox.warning(self, "Ошибка", "Введите лицензионный ключ")
            return

        if self.license_manager.save_license(license_key):
            QMessageBox.information(self, "Успех",
                                    "Лицензия успешно активирована!\n"
                                    "Приложение будет запущено.")
            self.accept()
        else:
            QMessageBox.critical(self, "Ошибка",
                                 "Неверный лицензионный ключ!\n"
                                 "Проверьте правильность ввода или обратитесь к разработчику.")


# Все остальные классы остаются без изменений
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


@dataclass
class PhraseList:
    """Модель списка фраз"""
    name: str
    phrases: List[Tuple[str, int]] = field(default_factory=list)
    stop_words: Set[str] = field(default_factory=set)
    folders: Dict[str, Folder] = field(default_factory=dict)
    history: HistoryManager = field(default_factory=HistoryManager)


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
                    result.append((translit(phrase, 'ru', reversed=True), freq))
                else:
                    result.append((translit(phrase, 'ru'), freq))
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
            phrase_lower = phrase.lower()
            if not any(stop.lower() in phrase_lower for stop in stop_words):
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


class AddButton(QPushButton):
    """Кнопка добавления в виде плюсика"""

    def __init__(self, parent=None):
        super().__init__("+", parent)
        self.setFixedSize(24, 24)
        self.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #007aff;
                border: 1px solid #c7c7cc;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
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

    search_changed = pyqtSignal(str, bool, bool)

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

        search_container.setLayout(search_layout)
        layout.addWidget(search_container)

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
        layout.addWidget(self.only_matches)

        self.exact_search = QCheckBox("Точный поиск")
        self.exact_search.setStyleSheet("""
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
        self.exact_search.toggled.connect(self.on_filter_changed)
        layout.addWidget(self.exact_search)

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
        self.search_changed.emit(text, self.only_matches.isChecked(), self.exact_search.isChecked())

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

    phrases_to_folder = pyqtSignal(str, list, bool, bool)  # folder_name, list of (phrase, freq), is_global, is_move

    def __init__(self, parent=None):
        super().__init__(parent)
        self.processor = PhraseProcessor()
        self.history = HistoryManager()
        self.stop_words = set()
        self.original_data = []
        self.current_data = []
        self.search_text = ""
        self.search_only_matches = False
        self.exact_search = False
        self.current_search_index = 0
        self.folders = {}  # local folders
        self.global_folders = {}  # global folders
        self.setup_ui()

    def setup_ui(self):
        """Настройка дизайна таблицы в стиле macOS"""
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["", "Фраза", "Частотность"])

        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.setColumnWidth(0, 40)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
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

        self.setAlternatingRowColors(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
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
            local_copy_checked = menu.addMenu("Копировать выбранные (галочки) в папку")
            for folder_name in self.folders.keys():
                action = local_copy_checked.addAction(folder_name)
                action.triggered.connect(lambda checked, fn=folder_name: self.add_to_folder(fn, True, False, False))

            local_move_checked = menu.addMenu("Переместить выбранные (галочки) в папку")
            for folder_name in self.folders.keys():
                action = local_move_checked.addAction(folder_name)
                action.triggered.connect(lambda checked, fn=folder_name: self.add_to_folder(fn, True, False, True))

            local_copy_highlighted = menu.addMenu("Копировать выделенные в папку")
            for folder_name in self.folders.keys():
                action = local_copy_highlighted.addAction(folder_name)
                action.triggered.connect(lambda checked, fn=folder_name: self.add_to_folder(fn, False, False, False))

            local_move_highlighted = menu.addMenu("Переместить выделенные в папку")
            for folder_name in self.folders.keys():
                action = local_move_highlighted.addAction(folder_name)
                action.triggered.connect(lambda checked, fn=folder_name: self.add_to_folder(fn, False, False, True))

        if self.global_folders:
            global_copy_checked = menu.addMenu("Копировать выбранные (галочки) в общую папку")
            for folder_name in self.global_folders.keys():
                action = global_copy_checked.addAction(folder_name)
                action.triggered.connect(lambda checked, fn=folder_name: self.add_to_folder(fn, True, True, False))

            global_move_checked = menu.addMenu("Переместить выбранные (галочки) в общую папку")
            for folder_name in self.global_folders.keys():
                action = global_move_checked.addAction(folder_name)
                action.triggered.connect(lambda checked, fn=folder_name: self.add_to_folder(fn, True, True, True))

            global_copy_highlighted = menu.addMenu("Копировать выделенные в общую папку")
            for folder_name in self.global_folders.keys():
                action = global_copy_highlighted.addAction(folder_name)
                action.triggered.connect(lambda checked, fn=folder_name: self.add_to_folder(fn, False, True, False))

            global_move_highlighted = menu.addMenu("Переместить выделенные в общую папку")
            for folder_name in self.global_folders.keys():
                action = global_move_highlighted.addAction(folder_name)
                action.triggered.connect(lambda checked, fn=folder_name: self.add_to_folder(fn, False, True, True))

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

        delete_highlighted = menu.addAction("Удалить выделенные")
        delete_highlighted.triggered.connect(self.delete_highlighted)

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

        menu.exec_(event.globalPos())

    def set_folders(self, folders: Dict[str, Folder]):
        self.folders = folders

    def set_global_folders(self, global_folders: Dict[str, Folder]):
        self.global_folders = global_folders

    def add_to_folder(self, folder_name: str, use_checked: bool, is_global: bool, is_move: bool):
        selected_phrases = []
        if use_checked:
            for row in range(self.rowCount()):
                checkbox_item = self.item(row, 0)
                if checkbox_item and checkbox_item.checkState() == Qt.Checked:
                    phrase = self.item(row, 1).text()
                    freq_item = self.item(row, 2)
                    freq = 0
                    if isinstance(freq_item, FrequencyTableWidgetItem):
                        freq = freq_item.value
                    elif freq_item:
                        freq = int(freq_item.text()) if freq_item.text().isdigit() else 0
                    selected_phrases.append((phrase, freq))
                    checkbox_item.setCheckState(Qt.Unchecked)
        else:
            selected_rows = sorted(set(item.row() for item in self.selectedItems()), reverse=False)
            for row in selected_rows:
                phrase_item = self.item(row, 1)
                if phrase_item:
                    phrase = phrase_item.text()
                    freq_item = self.item(row, 2)
                    freq = 0
                    if isinstance(freq_item, FrequencyTableWidgetItem):
                        freq = freq_item.value
                    elif freq_item:
                        freq = int(freq_item.text()) if freq_item.text().isdigit() else 0
                    selected_phrases.append((phrase, freq))

        if selected_phrases:
            self.phrases_to_folder.emit(folder_name, selected_phrases, is_global, is_move)

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
                checkbox_item.setCheckState(Qt.Checked)

    def deselect_all(self):
        for row in range(self.rowCount()):
            checkbox_item = self.item(row, 0)
            if checkbox_item:
                checkbox_item.setCheckState(Qt.Unchecked)

    def delete_selected(self):
        self.save_state()
        phrases_to_delete = set()
        for row in range(self.rowCount()):
            checkbox_item = self.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.Checked:
                phrase_item = self.item(row, 1)
                if phrase_item:
                    phrases_to_delete.add(phrase_item.text())

        self.current_data = [
            (p, f) for p, f in self.current_data
            if p not in phrases_to_delete
        ]

        self.update_table(self.current_data, save_history=False)

    def delete_highlighted(self):
        self.save_state()
        phrases_to_delete = set()
        selected_rows = set(item.row() for item in self.selectedItems())
        for row in selected_rows:
            phrase_item = self.item(row, 1)
            if phrase_item:
                phrases_to_delete.add(phrase_item.text())

        self.current_data = [
            (p, f) for p, f in self.current_data
            if p not in phrases_to_delete
        ]

        self.update_table(self.current_data, save_history=False)

    def save_state(self):
        if self.history is not None:
            self.history.add_state(self.current_data)

    def undo(self):
        if self.history is not None:
            state = self.history.undo()
            if state:
                self.current_data = state
                self.update_table(self.current_data, save_history=False)

    def redo(self):
        if self.history is not None:
            state = self.history.redo()
            if state:
                self.current_data = state
                self.update_table(self.current_data, save_history=False)

    def load_data(self, data: List[Tuple[str, int]]):
        self.original_data = data
        self.current_data = self.original_data.copy()
        if self.history is not None:
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
                if self.is_match(phrase)
            ]

        self.setSortingEnabled(False)
        self.setRowCount(len(display_data))

        for i, (phrase, freq) in enumerate(display_data):
            checkbox = CheckboxTableWidgetItem()
            checkbox.setCheckState(Qt.Unchecked)
            self.setItem(i, 0, checkbox)

            phrase_item = QTableWidgetItem(phrase)

            if self.search_text and self.is_match(phrase):
                phrase_item.setBackground(QBrush(QColor(229, 243, 255)))

            else:
                color = self.get_frequency_color(freq)
                phrase_item.setBackground(QBrush(color))

            self.setItem(i, 1, phrase_item)

            freq_item = FrequencyTableWidgetItem(freq)
            freq_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

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

    def is_match(self, phrase: str) -> bool:
        if self.exact_search:
            return bool(re.search(r'\b' + re.escape(self.search_text.lower()) + r'\b', phrase.lower()))
        else:
            return self.search_text.lower() in phrase.lower()

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

    def set_search(self, text: str, only_matches: bool, exact: bool):
        self.search_text = text
        self.search_only_matches = only_matches
        self.exact_search = exact
        self.current_search_index = 0
        self.update_table(self.current_data, save_history=False)

        if text and not only_matches:
            rows = self.get_matching_rows()
            if rows:
                self.scrollToItem(self.item(rows[0], 1))
                self.selectRow(rows[0])
                self.current_search_index = 0

    def get_matching_rows(self):
        rows = []
        for row in range(self.rowCount()):
            phrase_item = self.item(row, 1)
            if phrase_item and self.is_match(phrase_item.text()):
                rows.append(row)
        return rows

    def next_search_result(self):
        rows = self.get_matching_rows()
        if rows:
            self.current_search_index = (self.current_search_index + 1) % len(rows)
            row = rows[self.current_search_index]
            self.scrollToItem(self.item(row, 1))
            self.selectRow(row)
            return self.current_search_index + 1, len(rows)
        return 0, 0

    def prev_search_result(self):
        rows = self.get_matching_rows()
        if rows:
            self.current_search_index = (self.current_search_index - 1) % len(rows)
            row = rows[self.current_search_index]
            self.scrollToItem(self.item(row, 1))
            self.selectRow(row)
            return self.current_search_index + 1, len(rows)
        return 0, 0

    def get_current_data(self) -> List[Tuple[str, int]]:
        return self.current_data.copy()

    def copy_selected(self):
        selected = []
        for row in range(self.rowCount()):
            checkbox_item = self.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.Checked:
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
                            all_phrases.append((phrase, freq))
                    else:
                        phrases = df.iloc[:, 0].astype(str).str.strip().tolist()
                        all_phrases.extend([(p, 0) for p in phrases])

                elif path.suffix.lower() == '.txt':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        for line in lines:
                            parts = line.strip().split('\t')
                            phrase = parts[0]
                            freq = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
                            all_phrases.append((phrase, freq))

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
        header.setFont(QFont("-apple-system", 15, QFont.Bold))
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
                color: #000000;
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
                color: #000000;
            }
            QListWidget::item {
                padding: 4px;
            }
            QListWidget::item:selected {
                background-color: #e5e5ea;
                color: #000000;
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

        self.copy_btn = ModernButton("Копировать все")
        self.copy_btn.clicked.connect(self.copy_stop_words)
        btn_layout.addWidget(self.copy_btn)

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

    def copy_stop_words(self):
        if self.stop_words:
            clipboard = QApplication.clipboard()
            clipboard.setText('\n'.join(sorted(self.stop_words)))

    def load_stop_words(self, stop_words: Set[str]):
        self.stop_words = stop_words.copy()
        self.list_widget.clear()
        for word in sorted(self.stop_words):
            self.list_widget.addItem(word)

    def get_stop_words(self) -> Set[str]:
        return self.stop_words.copy()


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
        header.setFont(QFont("-apple-system", 15, QFont.Bold))
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
                color: #000000;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #e5e5ea;
                color: #000000;
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
                else:
                    phrase_item.setForeground(1, QBrush(QColor(142, 142, 147)))

    def export_groups(self):
        if not self.groups:
            QMessageBox.warning(self, "Предупреждение", "Нет данных для экспорта")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
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

                QMessageBox.information(self, "Успех", f"Группы экспортированы")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать: {str(e)}")


class FoldersWidget(QWidget):
    """Виджет для управления папками в стиле macOS"""

    folders_changed = pyqtSignal()
    phrases_back = pyqtSignal(list, bool)  # list of (folder_name, phrase, freq), is_move

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
        header.setFont(QFont("-apple-system", 15, QFont.Bold))
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
                color: #000000;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #e5e5ea;
                color: #000000;
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

        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)

        self.tree.setDragDropMode(QAbstractItemView.InternalMove)
        self.tree.setDefaultDropAction(Qt.MoveAction)

        layout.addWidget(self.tree)

        self.setLayout(layout)

    def create_folder(self):
        name, ok = QInputDialog.getText(self, "Новая папка", "Введите название папки:")
        if ok and name:
            if name not in self.folders:
                self.folders[name] = Folder(name)
                self.update_tree()
                self.folders_changed.emit()
            else:
                QMessageBox.warning(self, "Ошибка", "Папка с таким именем уже существует")

    def delete_folder(self, folder_name: str):
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить папку '{folder_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            del self.folders[folder_name]
            self.update_tree()
            self.folders_changed.emit()

    def show_context_menu(self, position):
        items = self.tree.selectedItems()
        if not items:
            return

        if len(items) == 1 and items[0].parent() is None:
            folder_name = items[0].text(0).split(" (")[0]
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

            menu.exec_(self.tree.mapToGlobal(position))
        else:
            # Assume phrases
            selected = []
            for item in items:
                if item.parent() is not None:
                    folder_name = item.parent().text(0).split(" (")[0]
                    phrase = item.text(0)
                    freq_str = item.text(1)
                    freq = int(freq_str) if freq_str.isdigit() else 0
                    selected.append((folder_name, phrase, freq))

            if selected:
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

                copy_back = menu.addAction("Копировать обратно")
                copy_back.triggered.connect(lambda: self.phrases_back.emit(selected, False))

                move_back = menu.addAction("Переместить обратно")
                move_back.triggered.connect(lambda: self.phrases_back.emit(selected, True))

                menu.addSeparator()

                remove_action = menu.addAction("Удалить из папки")
                remove_action.triggered.connect(lambda: self.batch_remove_from_folder(selected))

                menu.exec_(self.tree.mapToGlobal(position))

    def batch_remove_from_folder(self, selected: List[Tuple[str, str, int]]):
        for folder_name, phrase, _ in selected:
            if folder_name in self.folders:
                self.folders[folder_name].remove_phrase(phrase)
        self.update_tree()
        self.folders_changed.emit()

    def clear_folder(self, folder_name: str):
        if folder_name in self.folders:
            self.folders[folder_name].clear()
            self.update_tree()
            self.folders_changed.emit()

    def remove_from_folder(self, folder_name: str, phrase: str):
        if folder_name in self.folders:
            self.folders[folder_name].remove_phrase(phrase)
            self.update_tree()
            self.folders_changed.emit()

    def add_phrases_to_folder(self, data: List[Tuple[str, str, int]]):
        for folder_name, phrase, freq in data:
            if folder_name in self.folders:
                self.folders[folder_name].add_phrase(phrase, freq)
        self.update_tree()
        self.folders_changed.emit()

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
                else:
                    phrase_item.setForeground(1, QBrush(QColor(142, 142, 147)))

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

    def load_folders(self, folders: Dict[str, Folder]):
        self.folders = {k: copy.deepcopy(v) for k, v in folders.items()}
        self.update_tree()

    def get_folders(self) -> Dict[str, Folder]:
        return {k: copy.deepcopy(v) for k, v in self.folders.items()}


class PhraseTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.name = ""
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.search_widget = SearchWidget()
        layout.addWidget(self.search_widget)

        self.table = MainPhraseTable()
        layout.addWidget(self.table)

        self.setLayout(layout)


class MainWindow(QMainWindow):
    """Главное окно приложения в стиле macOS"""

    def __init__(self, license_manager: LicenseManager):
        super().__init__()
        self.license_manager = license_manager
        self.phrase_lists = {}
        self.global_stop_words = set()
        self.global_folders = {}
        self._prev_phrase_tab_index = -1
        self.current_session_path = None
        # Создаем виджеты до setup_ui
        self.stop_words_widget = StopWordsWidget()
        self.setup_ui()
        self.setup_shortcuts()
        self.setup_style()
        self.phrase_tabs.currentChanged.connect(self.on_phrase_tab_changed)
        self.phrase_tabs.tabBar().setContextMenuPolicy(Qt.CustomContextMenu)
        self.phrase_tabs.tabBar().customContextMenuRequested.connect(self.show_tab_context_menu)
        self.phrase_tabs.setTabsClosable(True)
        self.phrase_tabs.tabCloseRequested.connect(self.delete_tab)
        self.folders_widget.folders_changed.connect(self.update_current_table_folders)
        self.general_folders.folders_changed.connect(self.update_all_tables_global_folders)
        self.folders_widget.phrases_back.connect(
            lambda selected, is_move: self.on_phrases_back(selected, is_move, False))
        self.general_folders.phrases_back.connect(
            lambda selected, is_move: self.on_phrases_back(selected, is_move, True))

    def setup_ui(self):
        self.setWindowTitle("PhraseTools - Modern SEO Tool [Licensed]")
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
        save_menu = QMenu(self)
        save_list_action = save_menu.addAction("Сохранить список")
        save_list_action.triggered.connect(self.save_list)
        save_all_action = save_menu.addAction("Сохранить все")
        save_all_action.triggered.connect(self.save_all)
        self.save_btn.setMenu(save_menu)
        toolbar_layout.addWidget(self.save_btn)

        self.save_session_btn = ModernButton("Сохранить сессию")
        self.save_session_btn.clicked.connect(self.save_session)
        toolbar_layout.addWidget(self.save_session_btn)

        self.save_as_session_btn = ModernButton("Сохранить сессию как")
        self.save_as_session_btn.clicked.connect(self.save_as_session)
        toolbar_layout.addWidget(self.save_as_session_btn)

        self.load_session_btn = ModernButton("Загрузить сессию")
        self.load_session_btn.clicked.connect(self.load_session)
        toolbar_layout.addWidget(self.load_session_btn)

        toolbar_layout.addStretch()

        counter_widget = QWidget()
        counter_widget.setStyleSheet("""
            QWidget {
                background: #ffffff;
                border: 1px solid #c7c7cc;
                border-radius: 6px;
                padding: 2px 6px;
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

        splitter = QSplitter(Qt.Horizontal)
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

        header_layout = QHBoxLayout()
        header_layout.setSpacing(5)

        editor_label = QLabel("Фразы")
        editor_label.setFont(QFont("-apple-system", 13, QFont.Bold))
        editor_label.setStyleSheet("color: #000000;")
        header_layout.addWidget(editor_label)

        self.add_btn = AddButton()
        self.add_btn.clicked.connect(self.add_phrase)
        header_layout.addWidget(self.add_btn)

        header_layout.addStretch()
        left_layout.addLayout(header_layout)

        self.phrase_tabs = QTabWidget()
        # Всграунд задника главный
        self.phrase_tabs.setStyleSheet("background-color: #f2f2f7;")

        left_layout.addWidget(self.phrase_tabs)

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

        self.stop_words_widget.stop_words_changed.connect(self.on_stop_words_changed)
        self.tabs.addTab(self.stop_words_widget, "Стоп-слова")

        self.grouping_widget = GroupingWidget()
        self.tabs.addTab(self.grouping_widget, "Группировка")

        self.folders_widget = FoldersWidget()
        self.tabs.addTab(self.folders_widget, "Папки")

        self.general_tab = QTabWidget()
        self.general_stop = StopWordsWidget()
        self.general_stop.stop_words_changed.connect(self.on_global_stop_changed)
        self.general_tab.addTab(self.general_stop, "Стоп-слова")

        self.general_grouping = GroupingWidget()
        self.general_tab.addTab(self.general_grouping, "Группировка")

        self.general_folders = FoldersWidget()
        self.general_tab.addTab(self.general_folders, "Папки")
        self.tabs.addTab(self.general_tab, "Общее")

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
        self.status_bar.showMessage("Готов к работе [Лицензия активна]")

    def setup_shortcuts(self):
        undo_shortcut = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_Z), self)
        undo_shortcut.activated.connect(
            lambda: self.get_current_table().undo() if self.get_current_table() and self.get_current_table().history is not None else None)

        redo_shortcut = QShortcut(QKeySequence(Qt.CTRL + Qt.SHIFT + Qt.Key_Z), self)
        redo_shortcut.activated.connect(
            lambda: self.get_current_table().redo() if self.get_current_table() and self.get_current_table().history is not None else None)

        search_shortcut = QShortcut(QKeySequence(Qt.CTRL + Qt.Key_F), self)
        search_shortcut.activated.connect(
            lambda: self.get_current_search().search_input.setFocus() if self.get_current_search() else None)

    def setup_style(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f2f2f7;
            }
        """)

    def sync_current_tab(self):
        """Синхронизация данных текущей вкладки с self.phrase_lists"""
        current_tab = self.get_current_tab()
        if current_tab and current_tab.name in self.phrase_lists:
            current_list = self.phrase_lists[current_tab.name]
            current_list.stop_words = self.stop_words_widget.get_stop_words()
            current_list.folders = self.folders_widget.get_folders()
            current_list.phrases = current_tab.table.get_current_data()
            current_list.history = current_tab.table.history

    def show_tab_context_menu(self, pos):
        tab_bar = self.phrase_tabs.tabBar()
        index = tab_bar.tabAt(pos)
        if index >= 0:
            menu = QMenu(self)
            rename_action = menu.addAction("Переименовать")
            rename_action.triggered.connect(lambda: self.rename_tab(index))
            delete_action = menu.addAction("Удалить")
            delete_action.triggered.connect(lambda: self.delete_tab(index))
            menu.exec_(tab_bar.mapToGlobal(pos))

    def rename_tab(self, index):
        old_name = self.phrase_tabs.tabText(index)
        new_name, ok = QInputDialog.getText(self, "Переименовать вкладку", "Новое название:", text=old_name)
        if ok and new_name and new_name != old_name:
            if new_name in self.phrase_lists:
                QMessageBox.warning(self, "Ошибка", "Вкладка с таким именем уже существует")
                return
            self.phrase_tabs.setTabText(index, new_name)
            tab = self.phrase_tabs.widget(index)
            tab.name = new_name
            pl = self.phrase_lists.pop(old_name)
            pl.name = new_name
            self.phrase_lists[new_name] = pl

    def delete_tab(self, index):
        name = self.phrase_tabs.tabText(index)
        reply = QMessageBox.question(self, "Удалить вкладку", f"Удалить вкладку '{name}'?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.phrase_tabs.removeTab(index)
            del self.phrase_lists[name]
            self.update_global_grouping()

    def on_phrase_tab_changed(self, index):
        if self._prev_phrase_tab_index >= 0:
            prev_tab = self.phrase_tabs.widget(self._prev_phrase_tab_index)
            if prev_tab:
                prev_list = self.phrase_lists[prev_tab.name]
                prev_list.stop_words = self.stop_words_widget.get_stop_words()
                prev_list.folders = self.folders_widget.get_folders()
                prev_list.phrases = prev_tab.table.get_current_data()
                prev_list.history = prev_tab.table.history

        self._prev_phrase_tab_index = index

        current_tab = self.phrase_tabs.widget(index)
        if not current_tab:
            return

        self.add_btn.setEnabled(True)
        current_list = self.phrase_lists[current_tab.name]
        self.stop_words_widget.load_stop_words(current_list.stop_words)
        self.stop_words_widget.setEnabled(True)
        self.folders_widget.load_folders(current_list.folders)
        current_tab.table.load_data(current_list.phrases)
        current_tab.table.history = current_list.history
        current_tab.table.set_stop_words(current_list.stop_words | self.global_stop_words)
        current_tab.table.set_folders(current_list.folders)
        current_tab.table.set_global_folders(self.global_folders)
        self.update_grouping_widget()
        self.update_global_grouping()
        self.update_phrase_count()

    def get_current_tab(self) -> PhraseTab:
        return self.phrase_tabs.currentWidget()

    def get_current_table(self) -> MainPhraseTable:
        tab = self.get_current_tab()
        return tab.table if tab else None

    def get_current_search(self) -> SearchWidget:
        tab = self.get_current_tab()
        return tab.search_widget if tab else None

    def get_current_phrase_list(self) -> PhraseList:
        tab = self.get_current_tab()
        if tab:
            return self.phrase_lists[tab.name]
        return None

    def add_phrase(self):
        current_tab = self.get_current_tab()
        if current_tab:
            phrase, ok = QInputDialog.getText(self, "Добавить фразу", "Введите фразу:")
            if ok and phrase:
                current_table = current_tab.table
                current_table.save_state()
                current_table.current_data.append((phrase.strip(), 0))
                current_table.update_table(current_table.current_data, save_history=False)
                self.update_phrase_count()
                self.update_grouping_widget()
                self.update_global_grouping()

    def on_phrases_to_folder(self, folder_name: str, phrases: List[Tuple[str, int]], is_global: bool, is_move: bool):
        data = [(folder_name, p, f) for p, f in phrases]
        if is_global:
            self.general_folders.add_phrases_to_folder(data)
            self.global_folders = self.general_folders.get_folders()
        else:
            self.folders_widget.add_phrases_to_folder(data)
            current_list = self.get_current_phrase_list()
            if current_list:
                current_list.folders = self.folders_widget.get_folders()

        if is_move:
            # Remove from current list
            current_table = self.get_current_table()
            if current_table:
                current_table.save_state()
                phrases_set = set(p.lower().strip() for p, f in phrases)
                current_table.current_data = [(p, f) for p, f in current_table.current_data if
                                              p.lower().strip() not in phrases_set]
                current_table.update_table(current_table.current_data, save_history=False)
                current_list = self.get_current_phrase_list()
                if current_list:
                    current_list.phrases = current_table.current_data
                self.update_phrase_count()
                self.update_grouping_widget()
                self.update_global_grouping()

    def on_phrases_back(self, selected: List[Tuple[str, str, int]], is_move: bool, is_global: bool):
        current_table = self.get_current_table()
        if current_table:
            current_table.save_state()
            existing = {p.lower().strip() for p, f in current_table.current_data}
            for _, phrase, freq in selected:
                if phrase.lower().strip() not in existing:
                    current_table.current_data.append((phrase, freq))
            current_table.update_table(current_table.current_data, save_history=False)
            if is_move:
                if is_global:
                    for folder_name, phrase, _ in selected:
                        self.general_folders.remove_from_folder(folder_name, phrase)
                else:
                    self.folders_widget.batch_remove_from_folder(selected)
            current_list = self.get_current_phrase_list()
            if current_list:
                current_list.phrases = current_table.current_data
            self.update_phrase_count()
            self.update_grouping_widget()
            self.update_global_grouping()

    def load_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите файлы",
            "",
            "Supported files (*.txt *.xls *.xlsx);;Text files (*.txt);;Excel files (*.xls *.xlsx)"
        )

        if file_paths:
            name = Path(file_paths[0]).stem
            if name in self.phrase_lists:
                i = 1
                while f"{name} ({i})" in self.phrase_lists:
                    i += 1
                name = f"{name} ({i})"
            self.create_new_tab(name)
            self.loader = FileLoader(file_paths)
            self.loader.finished.connect(lambda data: self.on_files_loaded(data, name))
            self.loader.error.connect(self.on_load_error)
            self.loader.start()
            self.status_bar.showMessage("Загрузка...")

    def on_files_loaded(self, data: List[Tuple[str, int]], name: str):
        current_tab = \
        [tab for tab in [self.phrase_tabs.widget(i) for i in range(self.phrase_tabs.count())] if tab.name == name][0]
        if current_tab:
            current_list = self.phrase_lists[name]
            current_list.phrases.extend(data)
            current_tab.table.load_data(current_list.phrases)
            current_tab.table.set_stop_words(current_list.stop_words | self.global_stop_words)
            self.phrase_tabs.setCurrentWidget(current_tab)
            self.update_phrase_count()
            self.update_grouping_widget()
            self.update_global_grouping()
            self.status_bar.showMessage(f"Загружено {len(data)} фраз [Лицензия активна]")
        else:
            self.status_bar.showMessage("Ошибка загрузки")

    def on_load_error(self, error: str):
        QMessageBox.warning(self, "Ошибка", error)
        self.status_bar.showMessage("Ошибка загрузки")

    def on_stop_words_changed(self, stop_words: Set[str]):
        current_tab = self.get_current_tab()
        if current_tab:
            current_list = self.phrase_lists[current_tab.name]
            current_list.stop_words = stop_words
            current_tab.table.set_stop_words(stop_words | self.global_stop_words)
            self.update_phrase_count()
            self.update_grouping_widget()

    def on_global_stop_changed(self, stop_words: Set[str]):
        self.global_stop_words = stop_words
        for i in range(self.phrase_tabs.count()):
            tab = self.phrase_tabs.widget(i)
            pl = self.phrase_lists[tab.name]
            tab.table.set_stop_words(pl.stop_words | self.global_stop_words)
        self.update_global_grouping()
        self.update_grouping_widget()
        self.update_phrase_count()

    def on_search_changed(self, tab: PhraseTab, text: str, only_matches: bool, exact: bool):
        tab.table.set_search(text, only_matches, exact)
        if text:
            rows = tab.table.get_matching_rows()
            total = len(rows)
            if total > 0:
                tab.search_widget.update_results(1, total)
            else:
                tab.search_widget.update_results(0, 0)

    def next_search(self, tab: PhraseTab):
        current, total = tab.table.next_search_result()
        tab.search_widget.update_results(current, total)

    def prev_search(self, tab: PhraseTab):
        current, total = tab.table.prev_search_result()
        tab.search_widget.update_results(current, total)

    def update_phrase_count(self):
        current_table = self.get_current_table()
        if current_table:
            total = len(current_table.current_data)
            self.phrase_count_label.setText(f"Фраз: {total}")

            filtered = current_table.rowCount()
            if filtered != total:
                self.filtered_count_label.setText(f"(после фильтра: {filtered})")
            else:
                self.filtered_count_label.setText("")

    def update_grouping_widget(self):
        # Синхронизируем текущую вкладку для актуальных данных
        self.sync_current_tab()

        current_tab = self.get_current_tab()
        if current_tab:
            current_list = self.phrase_lists[current_tab.name]
            filtered = PhraseProcessor.filter_by_stop_words(current_list.phrases,
                                                            current_list.stop_words | self.global_stop_words)
            self.grouping_widget.update_groups(filtered)

    def update_global_grouping(self):
        # Синхронизируем текущую вкладку для актуальных данных
        self.sync_current_tab()

        all_phrases = self.get_all_phrases()
        filtered = PhraseProcessor.filter_by_stop_words(all_phrases, self.global_stop_words)
        self.general_grouping.update_groups(filtered)

    def get_all_phrases(self) -> List[Tuple[str, int]]:
        all_p = []
        for pl in self.phrase_lists.values():
            all_p.extend(pl.phrases)
        return all_p

    def save_list(self):
        # Синхронизируем текущую вкладку перед сохранением
        self.sync_current_tab()

        current_tab = self.get_current_tab()
        if current_tab:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить список",
                "",
                "Excel files (*.xlsx)"
            )

            if file_path:
                try:
                    current_list = self.phrase_lists[current_tab.name]
                    filtered_data = PhraseProcessor.filter_by_stop_words(
                        current_list.phrases, current_list.stop_words | self.global_stop_words
                    )
                    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                        df_phrases = pd.DataFrame(filtered_data, columns=['Фраза', 'Частотность'])
                        df_phrases.to_excel(writer, sheet_name='Phrases', index=False)
                        df_stop = pd.DataFrame(list(current_list.stop_words), columns=['Стоп-слова'])
                        df_stop.to_excel(writer, sheet_name='StopWords', index=False)
                    self.status_bar.showMessage(f"Сохранено: {Path(file_path).name}")
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {str(e)}")

    def save_all(self):
        # Синхронизируем текущую вкладку перед сохранением
        self.sync_current_tab()

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить все",
            "",
            "Excel files (*.xlsx)"
        )

        if file_path:
            try:
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    for name, pl in self.phrase_lists.items():
                        filtered = PhraseProcessor.filter_by_stop_words(pl.phrases,
                                                                        pl.stop_words | self.global_stop_words)
                        df_ph = pd.DataFrame(filtered, columns=['Фраза', 'Частотность'])
                        df_ph.to_excel(writer, sheet_name=f"{name}_Phrases", index=False)
                        df_stop = pd.DataFrame(list(pl.stop_words), columns=['Стоп-слова'])
                        df_stop.to_excel(writer, sheet_name=f"{name}_Stop", index=False)
                    df_global_stop = pd.DataFrame(list(self.global_stop_words), columns=['Стоп-слова'])
                    df_global_stop.to_excel(writer, sheet_name="Obshchee_Stop", index=False)
                self.status_bar.showMessage(f"Сохранено: {Path(file_path).name}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {str(e)}")

    def save_session(self):
        if self.current_session_path:
            self._save_session_to_file(self.current_session_path)
        else:
            self.save_as_session()

    def save_as_session(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Session As", "", "Session files (*.session)")
        if file_path:
            self._save_session_to_file(file_path)
            self.current_session_path = file_path

    def _save_session_to_file(self, file_path):
        # Синхронизируем текущую вкладку перед сохранением
        self.sync_current_tab()

        try:
            with open(file_path, 'wb') as f:
                pickle.dump(
                    (self.phrase_lists, self.global_stop_words, self.global_folders, self.phrase_tabs.currentIndex()),
                    f)
            self.status_bar.showMessage(f"Session saved: {Path(file_path).name}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить сессию: {str(e)}")

    def load_session(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Session", "", "Session files (*.session)")
        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    self.phrase_lists, self.global_stop_words, self.global_folders, current_index = pickle.load(f)
                # Clear tabs
                while self.phrase_tabs.count() > 0:
                    self.phrase_tabs.removeTab(0)
                # Recreate tabs
                for name, pl in self.phrase_lists.items():
                    tab = PhraseTab()
                    tab.name = name
                    tab.search_widget.search_changed.connect(
                        lambda t, o, e, tb=tab: self.on_search_changed(tb, t, o, e))
                    tab.search_widget.prev_btn.clicked.connect(lambda checked, tb=tab: self.prev_search(tb))
                    tab.search_widget.next_btn.clicked.connect(lambda checked, tb=tab: self.next_search(tb))
                    tab.table.phrases_to_folder.connect(
                        lambda fn, phrases, is_global, is_move, tb=tab: self.on_phrases_to_folder(fn, phrases,
                                                                                                  is_global, is_move))
                    self.phrase_tabs.addTab(tab, name)
                    tab.table.load_data(pl.phrases)
                    tab.table.history = pl.history
                    tab.table.set_stop_words(pl.stop_words | self.global_stop_words)
                    tab.table.set_folders(pl.folders)
                    tab.table.set_global_folders(self.global_folders)
                self.general_stop.load_stop_words(self.global_stop_words)
                self.general_folders.load_folders(self.global_folders)
                self.update_global_grouping()
                if self.phrase_tabs.count() > 0:
                    self.phrase_tabs.setCurrentIndex(min(current_index, self.phrase_tabs.count() - 1))
                    self.on_phrase_tab_changed(self.phrase_tabs.currentIndex())
                self.current_session_path = file_path
                self.status_bar.showMessage(f"Session loaded: {Path(file_path).name}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить сессию: {str(e)}")

    def create_new_tab(self, name: str):
        if name in self.phrase_lists:
            return
        phrase_list = PhraseList(name)
        self.phrase_lists[name] = phrase_list

        tab = PhraseTab()
        tab.name = name
        tab.search_widget.search_changed.connect(lambda t, o, e: self.on_search_changed(tab, t, o, e))
        tab.search_widget.prev_btn.clicked.connect(lambda: self.prev_search(tab))
        tab.search_widget.next_btn.clicked.connect(lambda: self.next_search(tab))
        tab.table.phrases_to_folder.connect(
            lambda fn, phrases, is_global, is_move: self.on_phrases_to_folder(fn, phrases, is_global, is_move))

        self.phrase_tabs.addTab(tab, name)

    def update_current_table_folders(self):
        current_table = self.get_current_table()
        if current_table:
            current_table.set_folders(self.folders_widget.folders)

    def update_all_tables_global_folders(self):
        self.global_folders = self.general_folders.get_folders()
        for i in range(self.phrase_tabs.count()):
            tab = self.phrase_tabs.widget(i)
            tab.table.set_global_folders(self.global_folders)


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(242, 242, 247))
    palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
    app.setPalette(palette)

    # Проверка лицензии
    license_manager = LicenseManager()

    if not license_manager.is_licensed():
        # Показываем диалог активации
        license_dialog = LicenseDialog(license_manager)
        if license_dialog.exec_() != QDialog.Accepted:
            # Если пользователь не активировал лицензию - выход
            sys.exit(0)

    # Запуск основного приложения
    window = MainWindow(license_manager)
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
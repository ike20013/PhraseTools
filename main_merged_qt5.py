#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PhraseTools - SEO Tools with License Protection
"""

import sys
import os
import re
import math
import copy
import json
import hashlib
import platform
import uuid
import socket
import base64
import pickle
from difflib import SequenceMatcher
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
import pandas as pd

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QTabWidget, QSplitter,
    QTableWidget, QTableWidgetItem, QHeaderView, QMenu,
    QMessageBox, QListWidget, QGroupBox, QLineEdit,
    QComboBox, QProgressBar, QStatusBar, QTextEdit, QPlainTextEdit,
    QAbstractItemView, QTreeWidget, QTreeWidgetItem,
    QCheckBox, QSpinBox, QGraphicsDropShadowEffect,
    QStyledItemDelegate, QStyleOptionViewItem, QStyle,
    QListWidgetItem, QInputDialog, QDialog, QAction, QShortcut,
    QTabBar, QStylePainter, QStyleOptionTab, QColorDialog, QToolButton,
    QDialogButtonBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, QMimeData, QEvent, QRect, QSettings
from PyQt5.QtGui import (
    QFont, QPalette, QColor, QBrush, QLinearGradient,
    QKeySequence, QTextCharFormat, QTextCursor, QPainter,
    QDrag, QIcon, QPen, QIntValidator
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
        title.setFont(QFont("Arial", 18, QFont.Bold))
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
        device_info_label.setFont(QFont("Arial", 12, QFont.Bold))
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
        key_label.setFont(QFont("Arial", 12, QFont.Bold))
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


class SettingsDialog(QDialog):
    """Диалог настроек приложения"""

    def __init__(self, current_theme_mode: str, current_theme: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setMinimumWidth(360)
        self.setModal(True)
        self.current_theme = "dark" if current_theme == "dark" else "light"
        self._build_ui(current_theme_mode)
        self._apply_style()

    def _build_ui(self, current_theme_mode: str):
        layout = QVBoxLayout()
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self.title_label = QLabel("Внешний вид")
        self.title_label.setFont(QFont("Arial", 13, QFont.Bold))
        layout.addWidget(self.title_label)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.theme_label = QLabel("Тема интерфейса:")
        row.addWidget(self.theme_label)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Системная", "system")
        self.theme_combo.addItem("Светлая", "light")
        self.theme_combo.addItem("Темная", "dark")
        idx = self.theme_combo.findData(current_theme_mode)
        self.theme_combo.setCurrentIndex(idx if idx >= 0 else 0)
        row.addWidget(self.theme_combo, 1)
        layout.addLayout(row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.ok_button = buttons.button(QDialogButtonBox.Ok)
        self.cancel_button = buttons.button(QDialogButtonBox.Cancel)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def _apply_style(self):
        if self.current_theme == "dark":
            self.setStyleSheet("""
                QDialog {
                    background-color: #1c1c1e;
                    color: #f2f2f7;
                    border: 1px solid #4b4b50;
                    border-radius: 12px;
                }
                QLabel {
                    color: #f2f2f7;
                }
                QComboBox {
                    background-color: #2c2c2e;
                    color: #f2f2f7;
                    border: 1px solid #4b4b50;
                    border-radius: 9px;
                    padding: 6px 34px 6px 10px;
                    min-height: 20px;
                }
                QComboBox:hover {
                    border-color: #5a5a60;
                }
                QComboBox:focus {
                    border: 1px solid #0a84ff;
                }
                QComboBox::drop-down {
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    width: 28px;
                    border: none;
                    border-left: 1px solid #4b4b50;
                    background-color: #3a3a3c;
                    border-top-right-radius: 9px;
                    border-bottom-right-radius: 9px;
                }
                QComboBox::down-arrow {
                    image: none;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 6px solid #b8b8bf;
                    margin-right: 8px;
                    width: 0px;
                    height: 0px;
                }
                QComboBox QAbstractItemView {
                    background-color: #2c2c2e;
                    color: #f2f2f7;
                    border: 1px solid #4b4b50;
                    outline: none;
                    selection-background-color: #3a3a3c;
                    selection-color: #ffffff;
                    padding: 4px;
                }
                QPushButton {
                    background-color: #2c2c2e;
                    color: #4da3ff;
                    border: 1px solid #4b4b50;
                    border-radius: 8px;
                    padding: 6px 12px;
                    min-width: 82px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #3a3a3c;
                }
                QPushButton:pressed {
                    background-color: #48484a;
                }
            """)
            return

        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                color: #1b1b1f;
                border: 1px solid #d7d9df;
                border-radius: 12px;
            }
            QLabel {
                color: #1b1b1f;
            }
            QComboBox {
                background-color: #ffffff;
                color: #1b1b1f;
                border: 1px solid #c7c7cc;
                border-radius: 9px;
                padding: 6px 34px 6px 10px;
                min-height: 20px;
            }
            QComboBox:hover {
                border-color: #aeb3bd;
            }
            QComboBox:focus {
                border: 1px solid #007aff;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 28px;
                border: none;
                border-left: 1px solid #d5d8de;
                background-color: #f3f5fb;
                border-top-right-radius: 9px;
                border-bottom-right-radius: 9px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #5e6674;
                margin-right: 8px;
                width: 0px;
                height: 0px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #1b1b1f;
                border: 1px solid #cfd3dc;
                outline: none;
                selection-background-color: #eaf2ff;
                selection-color: #1b1b1f;
                padding: 4px;
            }
            QPushButton {
                background-color: #ffffff;
                color: #007aff;
                border: 1px solid #c7c7cc;
                border-radius: 8px;
                padding: 6px 12px;
                min-width: 82px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #f2f4f9;
            }
            QPushButton:pressed {
                background-color: #e7ebf3;
            }
        """)

    def selected_theme_mode(self) -> str:
        mode = self.theme_combo.currentData()
        return mode if mode in {"light", "dark", "system"} else "system"


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

    def __init__(self, name: str, color: Optional[str] = None):
        self.name = name
        self.phrases: List[Tuple[str, int]] = []
        self.color = color

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
        state_copy = copy.deepcopy(state)

        # Не дублируем одинаковые соседние состояния
        if self.current_index >= 0 and self.history and self.history[self.current_index] == state_copy:
            return

        while len(self.history) > self.current_index + 1:
            self.history.pop()

        self.history.append(state_copy)
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
        """Транслитерация фраз (reverse=False: RU->EN, reverse=True: EN->RU)"""
        result = []
        for phrase, freq in phrases:
            try:
                if reverse:
                    converted = PhraseProcessor._transliterate_en_to_ru(phrase)
                else:
                    converted = PhraseProcessor._transliterate_ru_to_en(phrase)
                result.append((converted, freq))
            except Exception:
                result.append((phrase, freq))
        return result

    @staticmethod
    def _transliterate_ru_to_en(text: str) -> str:
        ru_to_en = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
            'е': 'e', 'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i',
            'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
            'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
            'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch',
            'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': "'",
            'э': 'e', 'ю': 'yu', 'я': 'ya',
        }

        out = []
        for ch in text:
            low = ch.lower()
            if low not in ru_to_en:
                out.append(ch)
                continue

            tr = ru_to_en[low]
            if ch.isupper():
                if len(tr) > 1:
                    tr = tr[0].upper() + tr[1:]
                else:
                    tr = tr.upper()
            out.append(tr)
        return ''.join(out)

    @staticmethod
    def _transliterate_en_to_ru(text: str) -> str:
        # Сначала длинные комбинации, затем одиночные буквы
        multi = {
            'shch': 'щ',
            'yo': 'ё',
            'zh': 'ж',
            'kh': 'х',
            'ts': 'ц',
            'ch': 'ч',
            'sh': 'ш',
            'yu': 'ю',
            'ya': 'я',
            'ju': 'ю',
            'ja': 'я',
            'jo': 'ё',
        }
        single = {
            'a': 'а', 'b': 'б', 'v': 'в', 'w': 'в', 'g': 'г',
            'd': 'д', 'e': 'е', 'z': 'з', 'i': 'и', 'y': 'й',
            'j': 'й', 'k': 'к', 'l': 'л', 'm': 'м', 'n': 'н',
            'o': 'о', 'p': 'п', 'r': 'р', 's': 'с', 't': 'т',
            'u': 'у', 'f': 'ф', 'h': 'х', 'c': 'к', 'q': 'к',
            'x': 'кс', "'": 'ь', '`': 'ь',
        }

        keys = sorted(multi.keys(), key=len, reverse=True)
        out = []
        i = 0
        while i < len(text):
            matched = False
            for key in keys:
                token = text[i:i + len(key)]
                if token.lower() != key:
                    continue

                ru = multi[key]
                if token.isupper() or token[:1].isupper():
                    ru = ru.upper()
                out.append(ru)
                i += len(key)
                matched = True
                break

            if matched:
                continue

            ch = text[i]
            low = ch.lower()
            if low in single:
                ru = single[low]
                if ch.isupper():
                    ru = ru.upper()
                out.append(ru)
            else:
                out.append(ch)
            i += 1

        # В обычном тексте мягкий знак должен быть строчным
        return ''.join(out).replace('Ь', 'ь')

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
        self.apply_theme("light")

    def apply_theme(self, theme: str):
        if theme == "dark":
            self.setStyleSheet("""
                QPushButton {
                    background-color: #2c2c2e;
                    color: #4da3ff;
                    border: 1px solid #4b4b50;
                    padding: 6px 12px;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #3a3a3c;
                }
                QPushButton:pressed {
                    background-color: #48484a;
                }
            """)
            return

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
        self.setObjectName("addPhraseButton")
        self.setFixedSize(24, 24)
        self.apply_theme("light")

    def apply_theme(self, theme: str):
        if theme == "dark":
            self.setStyleSheet("""
                QPushButton#addPhraseButton {
                    background-color: #2c2c2e;
                    color: #4da3ff;
                    border: 1px solid #4b4b50;
                    border-radius: 12px;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 0px;
                    text-align: center;
                }
                QPushButton#addPhraseButton:hover {
                    background-color: #3a3a3c;
                }
                QPushButton#addPhraseButton:pressed {
                    background-color: #48484a;
                }
            """)
            return

        self.setStyleSheet("""
            QPushButton#addPhraseButton {
                background-color: #ffffff;
                color: #007aff;
                border: 1px solid #c7c7cc;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                padding: 0px;
                text-align: center;
            }
            QPushButton#addPhraseButton:hover {
                background-color: #f2f2f7;
            }
            QPushButton#addPhraseButton:pressed {
                background-color: #e5e5ea;
            }
        """)


class SearchWidget(QWidget):
    """Современный виджет поиска в стиле macOS"""

    search_changed = pyqtSignal(str, bool, bool)

    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.apply_theme("light")

    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)

        # Контейнер для поиска
        self.search_container = QWidget()
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(8, 4, 8, 4)
        search_layout.setSpacing(8)

        # Поле поиска
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по фразам...")
        self.search_input.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.search_input.setMinimumHeight(22)
        self.search_input.textChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.search_input)

        self.search_container.setLayout(search_layout)
        layout.addWidget(self.search_container)

        # Чекбокс "Только совпадения"
        self.only_matches = QCheckBox("Только совпадения")
        self.only_matches.toggled.connect(self.on_filter_changed)
        layout.addWidget(self.only_matches)

        self.exact_search = QCheckBox("Точный поиск")
        self.exact_search.toggled.connect(self.on_filter_changed)
        layout.addWidget(self.exact_search)

        # Кнопки навигации
        self.prev_btn = QPushButton("◀")
        self.prev_btn.setFixedSize(30, 24)
        self.prev_btn.setEnabled(False)
        layout.addWidget(self.prev_btn)

        self.next_btn = QPushButton("▶")
        self.next_btn.setFixedSize(30, 24)
        self.next_btn.setEnabled(False)
        layout.addWidget(self.next_btn)

        # Счетчик результатов
        self.result_label = QLabel("")
        layout.addWidget(self.result_label)

        layout.addStretch()
        self.setLayout(layout)
        self.setMaximumHeight(40)

    def apply_theme(self, theme: str):
        if theme == "dark":
            self.search_container.setStyleSheet("""
                QWidget {
                    background: #1f1f23;
                    border-radius: 8px;
                    border: 1px solid #4b4b50;
                }
            """)
            self.search_input.setStyleSheet("""
                QLineEdit {
                    background: transparent;
                    border: none;
                    color: #f2f2f7;
                    font-size: 13px;
                    padding: 0px;
                    margin: 0px;
                }
                QLineEdit::placeholder {
                    color: #8e8e93;
                }
            """)
            checkbox_style = """
                QCheckBox {
                    color: #f2f2f7;
                    font-size: 12px;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
                    border-radius: 4px;
                    border: 1px solid #5a5a60;
                    background: #2c2c2e;
                }
                QCheckBox::indicator:checked {
                    background: #0a84ff;
                    border: 1px solid #0a84ff;
                }
            """
            button_style = """
                QPushButton {
                    background: #2c2c2e;
                    border: 1px solid #4b4b50;
                    border-radius: 6px;
                    color: #4da3ff;
                    font-size: 12px;
                }
                QPushButton:hover:enabled {
                    background: #3a3a3c;
                }
                QPushButton:disabled {
                    color: #5a5a60;
                }
            """
            result_color = "#8e8e93"
        else:
            self.search_container.setStyleSheet("""
                QWidget {
                    background: #ffffff;
                    border-radius: 8px;
                    border: 1px solid #c7c7cc;
                }
            """)
            self.search_input.setStyleSheet("""
                QLineEdit {
                    background: transparent;
                    border: none;
                    color: #000000;
                    font-size: 13px;
                    padding: 0px;
                    margin: 0px;
                }
                QLineEdit::placeholder {
                    color: #8e8e93;
                }
            """)
            checkbox_style = """
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
            """
            button_style = """
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
            """
            result_color = "#8e8e93"

        self.only_matches.setStyleSheet(checkbox_style)
        self.exact_search.setStyleSheet(checkbox_style)
        self.prev_btn.setStyleSheet(button_style)
        self.next_btn.setStyleSheet(button_style)
        self.result_label.setStyleSheet(f"""
            QLabel {{
                font-size: 12px;
                color: {result_color};
                padding: 0 8px;
            }}
        """)

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


class CheckboxItemDelegate(QStyledItemDelegate):
    """Кастомная отрисовка чекбоксов первой колонки без системных артефактов"""

    SIZE = 16

    def _checkbox_rect(self, option):
        x = option.rect.x() + (option.rect.width() - self.SIZE) // 2
        y = option.rect.y() + (option.rect.height() - self.SIZE) // 2
        return QRect(x, y, self.SIZE, self.SIZE)

    def paint(self, painter, option, index):
        if index.column() != 0:
            super().paint(painter, option, index)
            return

        is_dark = option.palette.color(QPalette.Base).lightness() < 128
        painter.save()
        painter.fillRect(option.rect, option.palette.base())

        box_rect = self._checkbox_rect(option)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(QPen(QColor(90, 90, 96) if is_dark else QColor(170, 170, 176), 1))
        painter.setBrush(QColor(46, 46, 50) if is_dark else QColor(255, 255, 255))
        painter.drawRect(box_rect)

        state = index.data(Qt.CheckStateRole)
        if state == Qt.Checked:
            x = box_rect.x()
            y = box_rect.y()
            painter.setPen(QPen(QColor(242, 242, 247) if is_dark else QColor(0, 0, 0), 2))
            painter.drawLine(x + 3, y + 8, x + 7, y + 12)
            painter.drawLine(x + 7, y + 12, x + 13, y + 4)

        painter.restore()

    def editorEvent(self, event, model, option, index):
        if index.column() != 0:
            return super().editorEvent(event, model, option, index)

        if not (index.flags() & Qt.ItemIsEnabled):
            return False

        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            if self._checkbox_rect(option).contains(event.pos()):
                current = index.data(Qt.CheckStateRole)
                new_state = Qt.Unchecked if current == Qt.Checked else Qt.Checked
                return model.setData(index, new_state, Qt.CheckStateRole)

        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Space:
            current = index.data(Qt.CheckStateRole)
            new_state = Qt.Unchecked if current == Qt.Checked else Qt.Checked
            return model.setData(index, new_state, Qt.CheckStateRole)

        return False


class SearchHighlightDelegate(QStyledItemDelegate):
    """Подсветка совпадений поискового запроса в колонке фраз"""

    def _find_matches(self, text: str, query: str, exact: bool) -> List[Tuple[int, int]]:
        if not text or not query:
            return []

        matches = []
        if exact:
            pattern = re.compile(r'\b' + re.escape(query) + r'\b', re.IGNORECASE)
            for m in pattern.finditer(text):
                matches.append((m.start(), m.end()))
            return matches

        text_low = text.lower()
        query_low = query.lower()
        start = 0
        while True:
            idx = text_low.find(query_low, start)
            if idx == -1:
                break
            matches.append((idx, idx + len(query)))
            start = idx + len(query)
        return matches

    def paint(self, painter, option, index):
        if index.column() != 1:
            super().paint(painter, option, index)
            return

        # В режиме редактирования рисует сам QLineEdit-редактор, не дублируем текст под ним
        if option.state & QStyle.State_Editing:
            painter.save()
            painter.fillRect(option.rect, option.palette.base())
            painter.restore()
            return

        table = self.parent()
        text = index.data(Qt.DisplayRole) or ""
        search_text = getattr(table, "search_text", "")
        exact_search = getattr(table, "exact_search", False)

        style_option = QStyleOptionViewItem(option)
        self.initStyleOption(style_option, index)
        style_option.text = ""

        style = style_option.widget.style() if style_option.widget else QApplication.style()
        style.drawControl(QStyle.CE_ItemViewItem, style_option, painter, style_option.widget)

        if not text:
            return

        matches = self._find_matches(text, search_text, exact_search)
        text_rect = option.rect.adjusted(8, 0, -4, 0)
        fm = option.fontMetrics
        baseline = text_rect.y() + (text_rect.height() + fm.ascent() - fm.descent()) // 2

        painter.save()
        painter.setClipRect(text_rect)

        is_dark = getattr(table, "current_theme", "light") == "dark"
        normal_color = QColor(242, 242, 247) if is_dark else QColor(0, 0, 0)
        painter.setPen(normal_color)

        if not matches:
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, text)
            painter.restore()
            return

        x = text_rect.x()
        last = 0
        for start, end in matches:
            if start > last:
                part = text[last:start]
                painter.drawText(x, baseline, part)
                x += fm.horizontalAdvance(part)

            matched_part = text[start:end]
            w = fm.horizontalAdvance(matched_part)
            hrect = QRect(x - 1, baseline - fm.ascent() - 1, w + 2, fm.height() + 2)
            highlight_fill = QColor(101, 83, 0, 190) if is_dark else QColor(255, 236, 153)
            highlight_border = QColor(255, 204, 0) if is_dark else QColor(186, 140, 0)
            painter.fillRect(hrect, highlight_fill)
            painter.setPen(highlight_border)
            painter.drawRect(hrect)
            painter.setPen(normal_color)
            painter.drawText(x, baseline, matched_part)
            x += w
            last = end

        if last < len(text):
            tail = text[last:]
            painter.drawText(x, baseline, tail)

        painter.restore()

    def createEditor(self, parent, option, index):
        if index.column() != 1:
            return super().createEditor(parent, option, index)

        editor = QLineEdit(parent)
        editor.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        table = self.parent()
        is_dark = getattr(table, "current_theme", "light") == "dark"
        if is_dark:
            editor.setStyleSheet("""
                QLineEdit {
                    background-color: #1c1c1e;
                    color: #f2f2f7;
                    border: 1px solid #0a84ff;
                    border-radius: 8px;
                    padding: 0px 8px;
                    margin: 0px;
                }
            """)
        else:
            editor.setStyleSheet("""
                QLineEdit {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #007aff;
                    border-radius: 8px;
                    padding: 0px 8px;
                    margin: 0px;
                }
            """)
        return editor

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect.adjusted(4, 2, -4, -2))


class FrequencyEditDelegate(QStyledItemDelegate):
    """Редактор частотности без обрезания текста"""

    def createEditor(self, parent, option, index):
        if index.column() != 2:
            return super().createEditor(parent, option, index)

        editor = QLineEdit(parent)
        editor.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        editor.setValidator(QIntValidator(0, 2147483647, editor))
        table = parent.parent() if parent is not None else None
        is_dark = getattr(table, "current_theme", "light") == "dark"
        if is_dark:
            editor.setStyleSheet("""
                QLineEdit {
                    background-color: #1c1c1e;
                    color: #f2f2f7;
                    border: 1px solid #0a84ff;
                    border-radius: 8px;
                    padding: 0px 10px;
                    margin: 0px;
                }
            """)
        else:
            editor.setStyleSheet("""
                QLineEdit {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #007aff;
                    border-radius: 8px;
                    padding: 0px 10px;
                    margin: 0px;
                }
            """)
        return editor

    def setEditorData(self, editor, index):
        value = index.data(Qt.EditRole)
        if value is None:
            value = index.data(Qt.DisplayRole)
        editor.setText(str(value) if value is not None else "")

    def setModelData(self, editor, model, index):
        value_text = editor.text().strip()
        model.setData(index, value_text if value_text else "0", Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect.adjusted(4, 2, -4, -2))


class CheckBoxHeader(QHeaderView):
    """Заголовок таблицы с чекбоксом в первой колонке"""

    check_state_changed = pyqtSignal(bool)
    sort_checked_requested = pyqtSignal(bool)

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self._is_checked = False
        self._sort_checked_desc = True
        self.setSectionsClickable(True)

    def set_checked(self, checked: bool, emit_signal: bool = False):
        checked = bool(checked)
        if self._is_checked == checked:
            return
        self._is_checked = checked
        self.updateSection(0)
        if emit_signal:
            self.check_state_changed.emit(self._is_checked)

    def is_checked(self) -> bool:
        return self._is_checked

    def paintSection(self, painter, rect, logicalIndex):
        if logicalIndex != 0:
            super().paintSection(painter, rect, logicalIndex)
            return

        is_dark = self.palette().color(QPalette.Base).lightness() < 128
        size = 16
        x = rect.x() + (rect.width() - size) // 2
        y = rect.y() + (rect.height() - size) // 2
        box_rect = QRect(x, y, size, size)

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Полностью рисуем фон секции вручную, чтобы не было системных артефактов справа
        painter.fillRect(rect, QColor(44, 44, 46) if is_dark else QColor(242, 242, 247))
        painter.setPen(QPen(QColor(75, 75, 80) if is_dark else QColor(199, 199, 204), 1))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
        painter.drawLine(rect.topRight(), rect.bottomRight())

        # Белый фон и четкая рамка, чтобы чекбокс был всегда заметен
        painter.setPen(QPen(QColor(102, 102, 108) if is_dark else QColor(150, 150, 156), 1))
        painter.setBrush(QColor(46, 46, 50) if is_dark else QColor(255, 255, 255))
        painter.drawRect(box_rect)

        if self._is_checked:
            pen = QPen(QColor(242, 242, 247) if is_dark else QColor(0, 0, 0), 2)
            painter.setPen(pen)
            painter.drawLine(x + 3, y + 8, x + 7, y + 12)
            painter.drawLine(x + 7, y + 12, x + 13, y + 4)

        painter.restore()

    def mousePressEvent(self, event):
        section_index = self.logicalIndexAt(event.pos())
        if section_index == 0:
            size = 16
            section_x = self.sectionPosition(0) if hasattr(self, "sectionPosition") else 0
            section_w = self.sectionSize(0) if hasattr(self, "sectionSize") else 40
            header_h = self.height() if hasattr(self, "height") else 24
            pos = event.pos()
            if isinstance(pos, tuple) and len(pos) >= 2:
                px, py = pos[0], pos[1]
            else:
                px, py = pos.x(), pos.y()

            box_x = section_x + (section_w - size) // 2
            box_y = (header_h - size) // 2
            inside_checkbox = (box_x <= px < box_x + size and box_y <= py < box_y + size)

            if inside_checkbox:
                self.set_checked(not self._is_checked, emit_signal=True)
            else:
                self.sort_checked_requested.emit(self._sort_checked_desc)
                self._sort_checked_desc = not self._sort_checked_desc
            event.accept()
            return
        super().mousePressEvent(event)


class DuplicateConfirmDialog(QDialog):
    """Подтверждение удаления дубликатов со списком найденных фраз"""

    def __init__(self, duplicates: List[Tuple[str, int]], duplicates_count: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Удалить дубликаты")
        self.setMinimumWidth(520)
        self.setMaximumHeight(460)
        self._build_ui(duplicates, duplicates_count)

    def _build_ui(self, duplicates: List[Tuple[str, int]], duplicates_count: int):
        layout = QVBoxLayout()
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel(f"Найдено дубликатов: {duplicates_count}")
        title.setFont(QFont("Arial", 13, QFont.Bold))
        title.setStyleSheet("color: #000000;")
        layout.addWidget(title)

        subtitle = QLabel("Список повторяющихся фраз:")
        subtitle.setStyleSheet("color: #3a3a3c; font-size: 12px;")
        layout.addWidget(subtitle)

        lst = QListWidget()
        lst.setStyleSheet("""
            QListWidget {
                background-color: #ffffff;
                border: 1px solid #c7c7cc;
                border-radius: 8px;
                color: #000000;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 5px 8px;
            }
        """)
        for phrase, total in duplicates:
            lst.addItem(f"{phrase}  (повторов: {total - 1}, всего: {total})")
        layout.addWidget(lst)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        confirm_btn = QPushButton("Удалить дубликаты")
        confirm_btn.clicked.connect(self.accept)
        confirm_btn.setDefault(True)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(confirm_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)


class MainPhraseTable(QTableWidget):
    """Современная таблица с фразами в стиле macOS"""

    phrases_to_folder = pyqtSignal(str, list, bool, bool)  # folder_name, list of (phrase, freq), is_global, is_move
    table_view_changed = pyqtSignal()   # изменился отображаемый вид (фильтр/поиск)
    table_data_changed = pyqtSignal()   # изменились данные фраз

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
        self.checked_keys = set()  # сохранение отмеченных чекбоксов между фильтрами/поиском
        self._syncing_checkboxes = False
        self.checkbox_header = None
        self.checkbox_delegate = None
        self.search_delegate = None
        self.frequency_delegate = None
        self.current_theme = "light"
        self.default_sort_column = 2
        self.default_sort_order = Qt.DescendingOrder
        self.setup_ui()
        self.itemChanged.connect(self.on_item_changed)

    def setup_ui(self):
        """Настройка дизайна таблицы в стиле macOS"""
        self.checkbox_header = CheckBoxHeader(Qt.Horizontal, self)
        self.setHorizontalHeader(self.checkbox_header)
        self.checkbox_header.check_state_changed.connect(self.on_header_checkbox_changed)
        self.checkbox_header.sort_checked_requested.connect(self.on_header_checked_sort_requested)
        self.checkbox_delegate = CheckboxItemDelegate(self)
        self.search_delegate = SearchHighlightDelegate(self)
        self.frequency_delegate = FrequencyEditDelegate(self)
        self.setItemDelegateForColumn(0, self.checkbox_delegate)
        self.setItemDelegateForColumn(1, self.search_delegate)
        self.setItemDelegateForColumn(2, self.frequency_delegate)

        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(["", "Фраза", "Частотность"])

        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.setColumnWidth(0, 40)
        self.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.setColumnWidth(2, 130)

        self.setSortingEnabled(True)
        self.horizontalHeader().setSortIndicatorShown(True)
        self.horizontalHeader().setSortIndicator(self.default_sort_column, self.default_sort_order)

        self.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                color: #000000;
                gridline-color: #e5e5ea;
                border: 1px solid #c7c7cc;
                border-radius: 8px;
                font-family: Arial;
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
        self.apply_theme("light")

    def apply_theme(self, theme: str):
        self.current_theme = "dark" if theme == "dark" else "light"
        if theme == "dark":
            self.setStyleSheet("""
                QTableWidget {
                    background-color: #1c1c1e;
                    color: #f2f2f7;
                    gridline-color: #3a3a3c;
                    border: 1px solid #4b4b50;
                    border-radius: 8px;
                    font-family: Arial;
                    font-size: 13px;
                }
                QTableWidget::item {
                    padding: 6px;
                    border-bottom: 1px solid #2c2c2e;
                }
                QTableWidget::item:selected {
                    background-color: #3a3a3c;
                    color: #ffffff;
                }
                QTableWidget::item:hover {
                    background-color: #2b2b30;
                }
                QHeaderView::section {
                    background-color: #2c2c2e;
                    color: #f2f2f7;
                    padding: 8px;
                    border: none;
                    border-bottom: 1px solid #4b4b50;
                    font-weight: 600;
                }
                QScrollBar:vertical {
                    background: #2c2c2e;
                    width: 12px;
                    border-radius: 6px;
                }
                QScrollBar::handle:vertical {
                    background: #636366;
                    border-radius: 6px;
                    min-height: 30px;
                }
                QScrollBar::handle:vertical:hover {
                    background: #7a7a7f;
                }
            """)
            self.refresh_theme_visuals()
            return

        self.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                color: #000000;
                gridline-color: #e5e5ea;
                border: 1px solid #c7c7cc;
                border-radius: 8px;
                font-family: Arial;
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
        self.refresh_theme_visuals()

    def get_frequency_text_color(self, freq: int) -> QColor:
        is_dark = self.current_theme == "dark"
        if freq >= 100000:
            return QColor(255, 69, 58) if is_dark else QColor(255, 59, 48)
        if freq >= 10000:
            return QColor(255, 159, 10) if is_dark else QColor(255, 149, 0)
        if freq >= 1000:
            return QColor(255, 214, 10) if is_dark else QColor(255, 204, 0)
        if freq >= 100:
            return QColor(48, 209, 88) if is_dark else QColor(52, 199, 36)
        return QColor(174, 174, 178) if is_dark else QColor(142, 142, 147)

    def refresh_theme_visuals(self):
        phrase_fg = QBrush(QColor(242, 242, 247) if self.current_theme == "dark" else QColor(0, 0, 0))
        for row in range(self.rowCount()):
            phrase_item = self.item(row, 1)
            freq_item = self.item(row, 2)
            if not phrase_item or not freq_item:
                continue

            try:
                freq = int(freq_item.text())
            except Exception:
                freq = 0

            phrase_item.setBackground(QBrush(self.get_frequency_color(freq)))
            if hasattr(phrase_item, "setForeground"):
                phrase_item.setForeground(phrase_fg)
            if hasattr(freq_item, "setForeground"):
                freq_item.setForeground(QBrush(self.get_frequency_text_color(freq)))

    def _resolve_active_sort(self) -> Tuple[int, Qt.SortOrder]:
        header = self.horizontalHeader()
        section = header.sortIndicatorSection()
        if section < 0 or section >= self.columnCount():
            section = self.default_sort_column
            order = self.default_sort_order
            header.setSortIndicator(section, order)
            return section, order
        return section, header.sortIndicatorOrder()

    def _apply_active_sort(self):
        section, order = self._resolve_active_sort()
        self.sortItems(section, order)

    def contextMenuEvent(self, event):
        """Создание контекстного меню в стиле macOS"""
        menu = QMenu(self)
        if getattr(self, "current_theme", "light") == "dark":
            menu.setStyleSheet("""
                QMenu {
                    background-color: #2c2c2e;
                    color: #f2f2f7;
                    border: 1px solid #4b4b50;
                    border-radius: 8px;
                    padding: 5px;
                    font-family: Arial;
                    font-size: 13px;
                }
                QMenu::item {
                    padding: 6px 20px;
                    border-radius: 4px;
                }
                QMenu::item:selected {
                    background-color: #3a3a3c;
                }
                QMenu::separator {
                    height: 1px;
                    background: #4b4b50;
                    margin: 5px 0;
                }
            """)
        else:
            menu.setStyleSheet("""
                QMenu {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #c7c7cc;
                    border-radius: 8px;
                    padding: 5px;
                    font-family: Arial;
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

        sort_checked_top = menu.addAction("Отмеченные (галочки) сверху")
        sort_checked_top.triggered.connect(lambda: self.sort_by_checked(True))

        sort_checked_bottom = menu.addAction("Отмеченные (галочки) снизу")
        sort_checked_bottom.triggered.connect(lambda: self.sort_by_checked(False))

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
        phrase_item = self.item(visual_row, 1)
        if phrase_item:
            phrase_to_delete = phrase_item.text()
            data = [
                (p, f) for p, f in self.current_data
                if p != phrase_to_delete
            ]
            self.apply_data_change(data)

    def select_all(self):
        self.set_all_checkboxes(True)

    def deselect_all(self):
        self.set_all_checkboxes(False)

    def set_all_checkboxes(self, checked: bool):
        sorting_was_enabled = False
        if hasattr(self, "isSortingEnabled"):
            try:
                sorting_was_enabled = bool(self.isSortingEnabled())
            except Exception:
                sorting_was_enabled = False

        if sorting_was_enabled and hasattr(self, "setSortingEnabled"):
            self.setSortingEnabled(False)

        self._syncing_checkboxes = True
        try:
            for row in range(self.rowCount()):
                checkbox_item = self.item(row, 0)
                if checkbox_item:
                    checkbox_item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
                    key = self._row_key(row)
                    if key is not None:
                        if checked:
                            self.checked_keys.add(key)
                        else:
                            self.checked_keys.discard(key)
        finally:
            self._syncing_checkboxes = False

        if sorting_was_enabled and hasattr(self, "setSortingEnabled"):
            self.setSortingEnabled(True)
            if hasattr(self, "_apply_active_sort"):
                self._apply_active_sort()

        if self.checkbox_header:
            self.checkbox_header.set_checked(checked, emit_signal=False)

    def on_header_checkbox_changed(self, checked: bool):
        self.set_all_checkboxes(checked)

    def on_header_checked_sort_requested(self, checked_first: bool):
        self.sort_by_checked(checked_first)

    def _row_key(self, row: int):
        phrase_item = self.item(row, 1)
        freq_item = self.item(row, 2)
        if not phrase_item or not freq_item:
            return None
        phrase = phrase_item.text()
        if isinstance(freq_item, FrequencyTableWidgetItem):
            freq = freq_item.value
        else:
            try:
                freq = int(freq_item.text())
            except Exception:
                freq = 0
        return phrase, freq

    def on_item_changed(self, item: QTableWidgetItem):
        if self._syncing_checkboxes:
            return
        if item.column() == 0:
            key = self._row_key(item.row())
            if key is not None:
                if item.checkState() == Qt.Checked:
                    self.checked_keys.add(key)
                else:
                    self.checked_keys.discard(key)
            self.update_header_checkbox_state()
            return

        if item.column() not in (1, 2):
            return

        row = item.row()
        phrase_item = self.item(row, 1)
        freq_item = self.item(row, 2)
        if not phrase_item or not freq_item:
            return

        source_index = None
        if hasattr(phrase_item, "data"):
            source_index = phrase_item.data(Qt.UserRole)

        if not isinstance(source_index, int) or source_index < 0 or source_index >= len(self.current_data):
            if 0 <= row < len(self.current_data):
                source_index = row
            else:
                return

        old_phrase, old_freq = self.current_data[source_index]
        new_phrase = phrase_item.text().strip() or old_phrase
        try:
            new_freq = int(freq_item.text())
        except Exception:
            new_freq = old_freq
        if new_freq < 0:
            new_freq = 0

        if (new_phrase, new_freq) == (old_phrase, old_freq):
            return

        data = self.current_data.copy()
        data[source_index] = (new_phrase, new_freq)

        if (old_phrase, old_freq) in self.checked_keys:
            self.checked_keys.discard((old_phrase, old_freq))
            self.checked_keys.add((new_phrase, new_freq))

        self.apply_data_change(data)

    def update_header_checkbox_state(self):
        if not self.checkbox_header or self.rowCount() == 0:
            if self.checkbox_header:
                self.checkbox_header.set_checked(False, emit_signal=False)
            return

        all_checked = True
        for row in range(self.rowCount()):
            checkbox_item = self.item(row, 0)
            if not checkbox_item or checkbox_item.checkState() != Qt.Checked:
                all_checked = False
                break
        self.checkbox_header.set_checked(all_checked, emit_signal=False)

    def delete_selected(self):
        phrases_to_delete = set()
        for row in range(self.rowCount()):
            checkbox_item = self.item(row, 0)
            if checkbox_item and checkbox_item.checkState() == Qt.Checked:
                phrase_item = self.item(row, 1)
                if phrase_item:
                    phrases_to_delete.add(phrase_item.text())

        if not phrases_to_delete:
            return

        data = [
            (p, f) for p, f in self.current_data
            if p not in phrases_to_delete
        ]
        self.apply_data_change(data)

    def delete_highlighted(self):
        phrases_to_delete = set()
        selected_rows = set(item.row() for item in self.selectedItems())
        for row in selected_rows:
            phrase_item = self.item(row, 1)
            if phrase_item:
                phrases_to_delete.add(phrase_item.text())

        if not phrases_to_delete:
            return

        data = [
            (p, f) for p, f in self.current_data
            if p not in phrases_to_delete
        ]
        self.apply_data_change(data)

    def save_state(self):
        if self.history is not None:
            self.history.add_state(self.current_data)

    def undo(self):
        if self.history is not None:
            state = self.history.undo()
            if state is not None:
                self.current_data = state
                self.update_table(self.current_data, save_history=False)
                self.table_data_changed.emit()
                return True
        return False

    def redo(self):
        if self.history is not None:
            state = self.history.redo()
            if state is not None:
                self.current_data = state
                self.update_table(self.current_data, save_history=False)
                self.table_data_changed.emit()
                return True
        return False

    def load_data(self, data: List[Tuple[str, int]]):
        self.original_data = data.copy()
        self.current_data = self.original_data.copy()
        self.checked_keys.clear()
        if self.history is not None:
            self.history.set_initial_state(self.current_data)
        self.update_table(self.current_data, save_history=False)

    def update_table(self, data: List[Tuple[str, int]], save_history: bool = True):
        self.current_data = data.copy()
        self.checked_keys = {k for k in self.checked_keys if k in set(self.current_data)}

        display_data = []
        for source_index, (phrase, freq) in enumerate(self.current_data):
            if self.stop_words:
                phrase_words = set(phrase.lower().split())
                if phrase_words.intersection(self.stop_words):
                    continue
            if self.search_text and self.search_only_matches and not self.is_match(phrase):
                continue
            display_data.append((source_index, phrase, freq))

        self.setSortingEnabled(False)
        self.setRowCount(len(display_data))
        self._syncing_checkboxes = True

        for i, (source_index, phrase, freq) in enumerate(display_data):
            checkbox = CheckboxTableWidgetItem()
            checkbox.setFlags(Qt.ItemIsEnabled)
            checkbox.setCheckState(Qt.Checked if (phrase, freq) in self.checked_keys else Qt.Unchecked)
            self.setItem(i, 0, checkbox)

            phrase_item = QTableWidgetItem(phrase)
            phrase_item.setData(Qt.UserRole, source_index)
            color = self.get_frequency_color(freq)
            phrase_item.setBackground(QBrush(color))
            is_dark = getattr(self, "current_theme", "light") == "dark"
            if hasattr(phrase_item, "setForeground"):
                phrase_item.setForeground(
                    QBrush(QColor(242, 242, 247) if is_dark else QColor(0, 0, 0))
                )

            self.setItem(i, 1, phrase_item)

            freq_item = FrequencyTableWidgetItem(freq)
            freq_item.setData(Qt.UserRole, source_index)
            freq_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if hasattr(self, "get_frequency_text_color"):
                freq_item.setForeground(QBrush(self.get_frequency_text_color(freq)))
            else:
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

        self._syncing_checkboxes = False
        self.update_header_checkbox_state()
        self.setSortingEnabled(True)
        self._apply_active_sort()
        self.table_view_changed.emit()

        if save_history:
            self.save_state()

    def is_match(self, phrase: str) -> bool:
        if self.exact_search:
            return bool(re.search(r'\b' + re.escape(self.search_text.lower()) + r'\b', phrase.lower()))
        else:
            return self.search_text.lower() in phrase.lower()

    def get_frequency_color(self, freq: int) -> QColor:
        if getattr(self, "current_theme", "light") == "dark":
            if freq >= 100000:
                return QColor(62, 24, 26)
            elif freq >= 10000:
                return QColor(66, 44, 20)
            elif freq >= 1000:
                return QColor(64, 56, 20)
            elif freq >= 100:
                return QColor(24, 62, 30)
            else:
                return QColor(28, 28, 30)

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

    def apply_data_change(self, data: List[Tuple[str, int]]) -> bool:
        if data == self.current_data:
            return False
        self.update_table(data, save_history=False)
        self.save_state()
        self.table_data_changed.emit()
        return True

    def _collect_duplicates(self) -> Tuple[List[Tuple[str, int]], int]:
        counts = {}
        labels = {}
        order = []

        for phrase, _ in self.current_data:
            key = phrase.lower().strip()
            if key not in counts:
                counts[key] = 0
                labels[key] = phrase.strip()
                order.append(key)
            counts[key] += 1

        duplicates = [(labels[k], counts[k]) for k in order if counts[k] > 1]
        duplicates_count = sum(total - 1 for _, total in duplicates)
        return duplicates, duplicates_count

    def remove_duplicates(self):
        duplicates, duplicates_count = self._collect_duplicates()
        if duplicates_count == 0:
            QMessageBox.information(self, "Дубликаты", "Дубликаты не найдены")
            return

        dialog = DuplicateConfirmDialog(duplicates, duplicates_count, self)
        if dialog.exec_() != QDialog.Accepted:
            return

        data = self.processor.remove_duplicates(self.current_data)
        self.apply_data_change(data)

    def remove_special_chars(self):
        data = self.processor.remove_special_chars(self.current_data)
        self.apply_data_change(data)

    def remove_long_phrases(self):
        data = self.processor.remove_long_phrases(self.current_data, 7)
        self.apply_data_change(data)

    def convert_case(self, to_upper: bool):
        data = self.processor.convert_case(self.current_data, to_upper)
        self.apply_data_change(data)

    def sort_alphabetically(self, reverse: bool):
        order = Qt.DescendingOrder if reverse else Qt.AscendingOrder
        self.horizontalHeader().setSortIndicator(1, order)
        data = self.processor.sort_phrases_alphabetically(self.current_data, reverse)
        self.apply_data_change(data)

    def sort_by_frequency(self, reverse: bool):
        order = Qt.DescendingOrder if reverse else Qt.AscendingOrder
        self.horizontalHeader().setSortIndicator(2, order)
        data = self.processor.sort_phrases_by_frequency(self.current_data, reverse)
        self.apply_data_change(data)

    def sort_by_checked(self, checked_first: bool = True):
        order = Qt.DescendingOrder if checked_first else Qt.AscendingOrder
        self.horizontalHeader().setSortIndicator(0, order)

        checked = set(self.checked_keys)
        indexed = list(enumerate(self.current_data))
        if checked_first:
            indexed.sort(key=lambda item: (0 if item[1] in checked else 1, item[0]))
        else:
            indexed.sort(key=lambda item: (0 if item[1] not in checked else 1, item[0]))

        data = [pair for _, pair in indexed]
        self.apply_data_change(data)

    def transliterate(self, reverse: bool = False):
        data = self.processor.transliterate_phrases(self.current_data, reverse)
        self.apply_data_change(data)


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
        self.history = HistoryManager()
        self.current_theme = "light"
        self.setup_ui()
        self.apply_theme("light")
        self.history.set_initial_state(tuple())

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.header_label = QLabel("Стоп-слова")
        self.header_label.setFont(QFont("Arial", 15, QFont.Bold))
        self.header_label.setContentsMargins(4, 0, 0, 0)
        self.header_label.setIndent(2)
        layout.addWidget(self.header_label)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Введите стоп-слово...")
        self.input_field.returnPressed.connect(self.add_stop_word)
        layout.addWidget(self.input_field)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.load_btn = ModernButton("Загрузить")
        self.load_btn.clicked.connect(self.load_from_file)
        btn_layout.addWidget(self.load_btn)

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

    def apply_theme(self, theme: str):
        self.current_theme = "dark" if theme == "dark" else "light"
        if theme == "dark":
            self.header_label.setStyleSheet("color: #f2f2f7;")
            self.input_field.setStyleSheet("""
                QLineEdit {
                    padding: 6px;
                    border: 1px solid #4b4b50;
                    border-radius: 6px;
                    background-color: #1c1c1e;
                    font-size: 13px;
                    color: #f2f2f7;
                }
                QLineEdit:focus {
                    border: 1px solid #0a84ff;
                }
            """)
            self.list_widget.setStyleSheet("""
                QListWidget {
                    background-color: #1c1c1e;
                    border: 1px solid #4b4b50;
                    border-radius: 6px;
                    padding: 5px;
                    font-size: 13px;
                    color: #f2f2f7;
                }
                QListWidget::item {
                    padding: 4px;
                }
                QListWidget::item:selected {
                    background-color: #3a3a3c;
                    color: #ffffff;
                }
            """)
            button_theme = "dark"
        else:
            self.header_label.setStyleSheet("color: #000000;")
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
            button_theme = "light"

        for btn in (self.load_btn, self.remove_btn, self.clear_btn, self.copy_btn):
            if hasattr(btn, "apply_theme"):
                btn.apply_theme(button_theme)

    def add_stop_word(self):
        word = self.input_field.text().strip().lower()
        if word and word not in self.stop_words:
            updated = set(self.stop_words)
            updated.add(word)
            self._apply_stop_words_change(updated)
            self.input_field.clear()

    def remove_stop_word(self):
        current_item = self.list_widget.currentItem()
        if current_item:
            word = current_item.text()
            updated = set(self.stop_words)
            updated.discard(word)
            self._apply_stop_words_change(updated)

    def clear_stop_words(self):
        self._apply_stop_words_change(set())

    def copy_stop_words(self):
        if self.stop_words:
            clipboard = QApplication.clipboard()
            clipboard.setText('\n'.join(sorted(self.stop_words)))

    def load_stop_words(self, stop_words: Set[str]):
        self.stop_words = stop_words.copy()
        self.list_widget.clear()
        for word in sorted(self.stop_words):
            self.list_widget.addItem(word)
        self.history.set_initial_state(tuple(sorted(self.stop_words)))

    def get_stop_words(self) -> Set[str]:
        return self.stop_words.copy()

    def load_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Загрузить стоп-слова",
            "",
            "Supported files (*.txt *.xls *.xlsx);;Text files (*.txt);;Excel files (*.xls *.xlsx)"
        )
        if file_path:
            try:
                path = Path(file_path)
                new_words = set()
                if path.suffix.lower() in ['.xls', '.xlsx']:
                    df = pd.read_excel(file_path)
                    words = df.iloc[:, 0].astype(str).str.strip().str.lower().tolist()
                    new_words = set(w for w in words if w)
                elif path.suffix.lower() == '.txt':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        new_words = set(line.strip().lower() for line in lines if line.strip())
                self._apply_stop_words_change(self.stop_words | new_words)
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Ошибка при загрузке: {str(e)}")

    def _apply_stop_words_change(self, updated: Set[str]) -> bool:
        if updated == self.stop_words:
            return False
        self.stop_words = set(updated)
        self.list_widget.clear()
        for word in sorted(self.stop_words):
            self.list_widget.addItem(word)
        self.stop_words_changed.emit(self.stop_words.copy())
        self.history.add_state(tuple(sorted(self.stop_words)))
        return True

    def undo(self) -> bool:
        state = self.history.undo()
        if state is None:
            return False
        self.stop_words = set(state)
        self.list_widget.clear()
        for word in sorted(self.stop_words):
            self.list_widget.addItem(word)
        self.stop_words_changed.emit(self.stop_words.copy())
        return True

    def redo(self) -> bool:
        state = self.history.redo()
        if state is None:
            return False
        self.stop_words = set(state)
        self.list_widget.clear()
        for word in sorted(self.stop_words):
            self.list_widget.addItem(word)
        self.stop_words_changed.emit(self.stop_words.copy())
        return True


class GroupingWidget(QWidget):
    """Виджет группировки в стиле macOS"""

    def __init__(self):
        super().__init__()
        self.groups = {}
        self.current_theme = "light"
        self.setup_ui()
        self.apply_theme("light")

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()

        self.header_label = QLabel("Группировка")
        self.header_label.setFont(QFont("Arial", 15, QFont.Bold))
        self.header_label.setContentsMargins(4, 0, 0, 0)
        self.header_label.setIndent(2)
        header_layout.addWidget(self.header_label)

        header_layout.addStretch()

        self.export_btn = ModernButton("Экспорт")
        self.export_btn.clicked.connect(self.export_groups)
        header_layout.addWidget(self.export_btn)

        layout.addLayout(header_layout)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Группа / Фраза", "Частотность"])
        layout.addWidget(self.tree)

        self.setLayout(layout)

    def apply_theme(self, theme: str):
        self.current_theme = "dark" if theme == "dark" else "light"
        if theme == "dark":
            self.header_label.setStyleSheet("color: #f2f2f7;")
            self.tree.setStyleSheet("""
                QTreeWidget {
                    background-color: #1c1c1e;
                    border: 1px solid #4b4b50;
                    border-radius: 6px;
                    padding: 5px;
                    font-size: 13px;
                    color: #f2f2f7;
                }
                QTreeWidget::item {
                    padding: 4px;
                }
                QTreeWidget::item:selected {
                    background-color: #3a3a3c;
                    color: #ffffff;
                }
                QHeaderView::section {
                    background-color: #2c2c2e;
                    color: #f2f2f7;
                    font-family: Arial;
                    padding-top: 6px;
                    padding-bottom: 6px;
                    padding-left: 10px;
                    padding-right: 6px;
                    border: none;
                    border-bottom: 1px solid #4b4b50;
                    font-weight: 600;
                }
            """)
            if hasattr(self.export_btn, "apply_theme"):
                self.export_btn.apply_theme("dark")
            return

        self.header_label.setStyleSheet("color: #000000;")
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
                font-family: Arial;
                padding-top: 6px;
                padding-bottom: 6px;
                padding-left: 10px;
                padding-right: 6px;
                border: none;
                border-bottom: 1px solid #c7c7cc;
                font-weight: 600;
            }
        """)
        if hasattr(self.export_btn, "apply_theme"):
            self.export_btn.apply_theme("light")

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


class ClusteringWidget(QWidget):
    """Кластеризация фраз: semantic / lexical / intent (оффлайн)."""
    TREE_CLUSTER_ROLE = 2001
    TREE_PHRASE_ROLE = 2002
    TREE_FREQ_ROLE = 2003

    SERVICE_TOKENS = {
        "купить", "куплю", "купим", "купите", "покупка", "покупки",
        "заказать", "заказ", "заказы", "цена", "цены", "стоимость",
        "недорого", "дешево", "дёшево", "дешевые", "дешёвые",
        "акция", "скидка", "скидки", "распродажа", "доставка", "самовывоз",
        "отзывы", "обзор", "обзоры", "фото", "видео", "сайт", "официальный",
        "каталог", "москва", "москве", "москвы", "спб", "санкт", "петербург",
        "buy", "price", "prices", "cheap", "review", "reviews",
        "official", "site", "delivery", "order", "sale", "discount",
        "online", "shop",
    }
    SERVICE_PREFIXES = (
        "достав", "скид", "акци", "распрод", "отзыв", "обзор",
        "официал", "каталог", "discount", "deliver", "review",
    )
    INTENT_ALIASES = {
        "купить": "Купить",
        "куплю": "Купить",
        "купим": "Купить",
        "купите": "Купить",
        "покупка": "Купить",
        "покупки": "Купить",
        "заказать": "Заказать",
        "заказ": "Заказать",
        "заказы": "Заказать",
        "цена": "Цены",
        "цены": "Цены",
        "стоимость": "Цены",
        "недорого": "Недорого",
        "дешево": "Недорого",
        "дёшево": "Недорого",
        "доставка": "Доставка",
        "самовывоз": "Доставка",
        "акция": "Акции",
        "скидка": "Акции",
        "скидки": "Акции",
        "распродажа": "Акции",
        "отзывы": "Отзывы",
        "обзор": "Обзоры",
        "обзоры": "Обзоры",
        "buy": "Buy",
        "order": "Order",
        "price": "Price",
        "prices": "Price",
        "review": "Reviews",
        "reviews": "Reviews",
        "sale": "Sale",
        "discount": "Sale",
    }
    INTENT_RULES = {
        "transactional": {
            "купить", "заказать", "заказ", "цена", "цены", "стоимость",
            "доставка", "оптом", "sale", "buy", "price", "order", "discount",
        },
        "informational": {
            "как", "что", "почему", "зачем", "обзор", "обзоры",
            "отзыв", "отзывы", "guide", "how", "what", "review",
        },
        "navigational": {
            "сайт", "официальный", "официальн", "вход", "логин", "login",
            "контакты", "контакт", "адрес", "телефон", "кабинет", "app",
        },
    }
    INTENT_DISPLAY = {
        "transactional": "Транзакционный",
        "informational": "Информационный",
        "navigational": "Навигационный",
        "other": "Смешанный",
    }
    _INTENT_SIGNATURE_RULES_CACHE: Optional[Dict[str, Set[str]]] = None

    def __init__(self):
        super().__init__()
        self.current_theme = "light"
        self.source_phrases: List[Tuple[str, int]] = []
        self.clusters: Dict[str, List[Tuple[str, int]]] = {}
        self._feature_cache: Dict[str, Tuple[str, Set[str], Set[str], Set[str]]] = {}
        self.setup_ui()
        self.apply_theme("light")

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()

        self.header_label = QLabel("Кластеризация")
        self.header_label.setFont(QFont("Arial", 15, QFont.Bold))
        self.header_label.setContentsMargins(4, 0, 0, 0)
        self.header_label.setIndent(2)
        header_layout.addWidget(self.header_label)

        header_layout.addStretch()

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Лексическая", "lexical")
        self.mode_combo.addItem("Семантическая", "semantic")
        self.mode_combo.addItem("Интент", "intent")
        self.mode_combo.currentIndexChanged.connect(self.rebuild_clusters)
        header_layout.addWidget(self.mode_combo)

        self.export_btn = ModernButton("Экспорт")
        self.export_btn.clicked.connect(self.export_clusters)
        header_layout.addWidget(self.export_btn)

        layout.addLayout(header_layout)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Кластер / Фраза", "Частотность"])
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_tree_context_menu)
        layout.addWidget(self.tree)

        self.setLayout(layout)

    def apply_theme(self, theme: str):
        self.current_theme = "dark" if theme == "dark" else "light"
        if self.current_theme == "dark":
            self.header_label.setStyleSheet("color: #f2f2f7;")
            self.mode_combo.setStyleSheet("""
                QComboBox {
                    background-color: #2c2c2e;
                    color: #f2f2f7;
                    border: 1px solid #4b4b50;
                    border-radius: 8px;
                    padding: 5px 30px 5px 10px;
                    min-height: 20px;
                }
                QComboBox:hover {
                    border-color: #5a5a60;
                }
                QComboBox:focus {
                    border: 1px solid #0a84ff;
                }
                QComboBox::drop-down {
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    width: 24px;
                    border: none;
                    border-left: 1px solid #4b4b50;
                    background-color: #3a3a3c;
                    border-top-right-radius: 8px;
                    border-bottom-right-radius: 8px;
                }
                QComboBox::down-arrow {
                    image: none;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 6px solid #b8b8bf;
                    margin-right: 6px;
                    width: 0px;
                    height: 0px;
                }
                QComboBox QAbstractItemView {
                    background-color: #2c2c2e;
                    color: #f2f2f7;
                    border: 1px solid #4b4b50;
                    selection-background-color: #3a3a3c;
                    selection-color: #ffffff;
                    outline: none;
                }
            """)
            self.tree.setStyleSheet("""
                QTreeWidget {
                    background-color: #1c1c1e;
                    border: 1px solid #4b4b50;
                    border-radius: 6px;
                    padding: 5px;
                    font-size: 13px;
                    color: #f2f2f7;
                }
                QTreeWidget::item {
                    padding: 4px;
                }
                QTreeWidget::item:selected {
                    background-color: #3a3a3c;
                    color: #ffffff;
                }
                QHeaderView::section {
                    background-color: #2c2c2e;
                    color: #f2f2f7;
                    font-family: Arial;
                    padding-top: 6px;
                    padding-bottom: 6px;
                    padding-left: 10px;
                    padding-right: 6px;
                    border: none;
                    border-bottom: 1px solid #4b4b50;
                    font-weight: 600;
                }
            """)
            if hasattr(self.export_btn, "apply_theme"):
                self.export_btn.apply_theme("dark")
            return

        self.header_label.setStyleSheet("color: #000000;")
        self.mode_combo.setStyleSheet("""
            QComboBox {
                background-color: #ffffff;
                color: #1b1b1f;
                border: 1px solid #c7c7cc;
                border-radius: 8px;
                padding: 5px 30px 5px 10px;
                min-height: 20px;
            }
            QComboBox:hover {
                border-color: #aeb3bd;
            }
            QComboBox:focus {
                border: 1px solid #007aff;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border: none;
                border-left: 1px solid #d5d8de;
                background-color: #f3f5fb;
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #5e6674;
                margin-right: 6px;
                width: 0px;
                height: 0px;
            }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #1b1b1f;
                border: 1px solid #cfd3dc;
                selection-background-color: #eaf2ff;
                selection-color: #1b1b1f;
                outline: none;
            }
        """)
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
                font-family: Arial;
                padding-top: 6px;
                padding-bottom: 6px;
                padding-left: 10px;
                padding-right: 6px;
                border: none;
                border-bottom: 1px solid #c7c7cc;
                font-weight: 600;
            }
        """)
        if hasattr(self.export_btn, "apply_theme"):
            self.export_btn.apply_theme("light")

    def update_clusters(self, phrases: List[Tuple[str, int]]):
        updated = [(str(p), int(f)) for p, f in (phrases or []) if str(p).strip()]
        if updated == self.source_phrases:
            return
        self.source_phrases = updated
        if len(self._feature_cache) > 50000:
            self._feature_cache.clear()
        self.rebuild_clusters()

    def rebuild_clusters(self):
        mode = self.mode_combo.currentData()
        if mode in {"semantic", "similarity"}:
            cluster_lists = self._build_clusters_by_similarity(self.source_phrases)
        elif mode == "intent":
            cluster_lists = self._build_clusters_by_intent(self.source_phrases)
        else:
            cluster_lists = self._build_clusters_by_word_overlap(self.source_phrases)

        named_clusters: Dict[str, List[Tuple[str, int]]] = {}
        used_names = defaultdict(int)
        for idx, cluster in enumerate(cluster_lists, start=1):
            base_name = self._build_cluster_name(cluster, idx, mode)
            used_names[base_name] += 1
            if used_names[base_name] > 1:
                cluster_name = f"{base_name} #{used_names[base_name]}"
            else:
                cluster_name = base_name
            named_clusters[cluster_name] = cluster

        self.clusters = named_clusters

        self.tree.clear()
        for cluster_name, cluster_phrases in self.clusters.items():
            cluster_item = QTreeWidgetItem(self.tree)
            cluster_item.setText(0, f"{cluster_name} ({len(cluster_phrases)})")
            cluster_item.setExpanded(True)
            cluster_item.setData(0, self.TREE_CLUSTER_ROLE, cluster_name)

            for phrase, freq in cluster_phrases:
                phrase_item = QTreeWidgetItem(cluster_item)
                phrase_item.setText(0, phrase)
                phrase_item.setText(1, str(freq))
                phrase_item.setData(0, self.TREE_CLUSTER_ROLE, cluster_name)
                phrase_item.setData(0, self.TREE_PHRASE_ROLE, phrase)
                phrase_item.setData(0, self.TREE_FREQ_ROLE, int(freq))

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

    @staticmethod
    def _tokenize(text: str) -> Set[str]:
        tokens = re.findall(r"[a-zA-Zа-яА-Я0-9_]+", text.lower())
        result = set()
        for token in tokens:
            if len(token) > 2 or (len(token) > 1 and any(ch.isdigit() for ch in token)):
                result.add(token)
        return result

    @staticmethod
    def _normalize(text: str) -> str:
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        return re.sub(r"\s+", " ", cleaned).strip()

    @staticmethod
    def _token_signature(token: str) -> str:
        token = token.lower().strip("_")
        if not token:
            return ""
        if token.isdigit():
            return token

        if re.search(r"[а-я]", token):
            for suffix in (
                "иями", "ями", "ами", "ого", "ему", "ыми", "ими",
                "его", "ому", "иях", "ах", "ях", "ия", "ие", "ий",
                "ой", "ый", "ая", "ое", "ые", "ов", "ев", "ам", "ям",
                "ом", "ем", "ую", "юю", "а", "я", "у", "ю", "ы", "и",
                "е", "о",
            ):
                if token.endswith(suffix) and len(token) - len(suffix) >= 3:
                    return token[:-len(suffix)]
            return token

        if re.search(r"[a-z]", token):
            if token.endswith("ies") and len(token) > 4:
                return token[:-3] + "y"
            for suffix in ("ing", "ers", "er", "ed", "es", "s"):
                if token.endswith(suffix) and len(token) - len(suffix) >= 3:
                    return token[:-len(suffix)]

        return token

    @classmethod
    def _is_service_token(cls, token: str) -> bool:
        token = token.lower()
        if token in cls.SERVICE_TOKENS:
            return True
        return any(token.startswith(prefix) for prefix in cls.SERVICE_PREFIXES)

    @classmethod
    def _intent_label_for_token(cls, token: str) -> Optional[str]:
        token = token.lower()
        if token in cls.INTENT_ALIASES:
            return cls.INTENT_ALIASES[token]
        signature = cls._token_signature(token)
        return cls.INTENT_ALIASES.get(signature)

    @classmethod
    def _intent_rule_signatures(cls) -> Dict[str, Set[str]]:
        if cls._INTENT_SIGNATURE_RULES_CACHE is not None:
            return cls._INTENT_SIGNATURE_RULES_CACHE

        result = {}
        for intent, words in cls.INTENT_RULES.items():
            signatures = {cls._token_signature(word) for word in words}
            signatures.discard("")
            result[intent] = signatures
        cls._INTENT_SIGNATURE_RULES_CACHE = result
        return result

    def _detect_intent(
            self,
            normalized: str,
            raw_tokens: Set[str],
            raw_signatures: Set[str],
            effective_signatures: Set[str]
    ) -> str:
        rule_signatures = self._intent_rule_signatures()
        scores = defaultdict(float)
        phrase_signatures = effective_signatures or raw_signatures

        for intent, signatures in rule_signatures.items():
            direct_hits = len(phrase_signatures & signatures)
            if direct_hits:
                scores[intent] += direct_hits * 1.6

            for token in raw_tokens:
                token = token.lower()
                if token in self.INTENT_RULES[intent]:
                    scores[intent] += 1.2

        if not scores:
            return "other"

        best_intent, best_score = max(scores.items(), key=lambda item: (item[1], item[0]))
        if best_score < 1.2:
            return "other"
        return best_intent

    @staticmethod
    def _token_overlap(left: Set[str], right: Set[str]) -> float:
        if not left or not right:
            return 0.0
        return len(left & right) / (min(len(left), len(right)) or 1)

    def _extract_features(self, phrase: str) -> Tuple[str, Set[str], Set[str], Set[str]]:
        cached = self._feature_cache.get(phrase)
        if cached is not None:
            return cached

        normalized = self._normalize(phrase)
        raw_tokens = self._tokenize(normalized)
        if not raw_tokens and normalized:
            raw_tokens = {normalized.replace(" ", "_")}

        raw_signatures = {
            self._token_signature(token)
            for token in raw_tokens
            if token
        }
        raw_signatures.discard("")

        effective_signatures = {
            self._token_signature(token)
            for token in raw_tokens
            if token and not self._is_service_token(token)
        }
        effective_signatures.discard("")

        packed = (
            normalized,
            frozenset(raw_tokens),
            frozenset(raw_signatures),
            frozenset(effective_signatures),
        )
        if len(self._feature_cache) <= 50000:
            self._feature_cache[phrase] = packed
        return packed

    def _build_cluster_name(self, cluster_phrases: List[Tuple[str, int]], cluster_idx: int, mode: str = "") -> str:
        if not cluster_phrases:
            return f"Кластер {cluster_idx}"

        thematic_scores = defaultdict(float)
        thematic_coverage = defaultdict(int)
        token_variants: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        intent_scores = defaultdict(float)

        for phrase, freq in cluster_phrases:
            normalized, raw_tokens, raw_signatures, effective_signatures = self._extract_features(phrase)
            weight = 1.0 + math.log1p(max(freq, 0))
            phrase_signatures = set()

            for token in raw_tokens:
                intent_label = self._intent_label_for_token(token)
                if intent_label:
                    intent_scores[intent_label] += weight

            thematic_source = effective_signatures or raw_signatures
            for token in raw_tokens:
                signature = self._token_signature(token)
                if signature not in thematic_source:
                    continue
                phrase_signatures.add(signature)
                thematic_scores[signature] += weight
                token_variants[signature][token.replace("_", " ")] += weight

            # Если после фильтра токенов ничего не осталось, добавляем нормализованный хвост фразы
            if not phrase_signatures and normalized:
                fallback_signature = self._token_signature(normalized.replace(" ", "_"))
                if fallback_signature:
                    phrase_signatures.add(fallback_signature)
                    thematic_scores[fallback_signature] += weight * 0.5
                    token_variants[fallback_signature][normalized] += weight * 0.5

            for signature in phrase_signatures:
                thematic_coverage[signature] += 1

        cluster_size = len(cluster_phrases)
        min_coverage = 2 if cluster_size >= 4 else 1

        ranked_signatures = sorted(
            thematic_scores.keys(),
            key=lambda sig: (
                thematic_scores[sig] * (1.0 + thematic_coverage[sig] / max(cluster_size, 1)),
                thematic_coverage[sig],
                len(sig),
                sig,
            ),
            reverse=True,
        )

        topic_tokens = []
        topic_seen = set()
        for signature in ranked_signatures:
            coverage = thematic_coverage[signature]
            if coverage < min_coverage and topic_tokens:
                continue

            variants = token_variants.get(signature) or {}
            token = max(variants.items(), key=lambda item: (item[1], len(item[0]), item[0]))[0] if variants else signature
            token = token.replace("_", " ").strip()
            token_lc = token.lower()
            if not token or token_lc in topic_seen:
                continue
            topic_seen.add(token_lc)
            topic_tokens.append(token)
            if len(topic_tokens) >= 3:
                break

        if not topic_tokens:
            top_phrase = max(cluster_phrases, key=lambda x: (x[1], len(x[0])))
            ordered_words = [
                word for word in self._normalize(top_phrase[0]).split()
                if len(word) > 2 and not self._is_service_token(word)
            ]
            if not ordered_words:
                ordered_words = [word for word in self._normalize(top_phrase[0]).split() if len(word) > 2]
            topic_tokens = ordered_words[:3]

        intent_label = ""
        if intent_scores:
            intent_label = max(intent_scores.items(), key=lambda item: (item[1], item[0]))[0]

        base_topic = " ".join(topic_tokens).strip()
        if len(base_topic) > 48:
            base_topic = base_topic[:48].rstrip()

        if intent_label and base_topic:
            if intent_label.lower() in base_topic.lower():
                name = base_topic
            else:
                name = f"{intent_label} | {base_topic}"
        elif base_topic:
            name = base_topic
        elif intent_label:
            name = intent_label
        else:
            top_phrase = max(cluster_phrases, key=lambda x: (x[1], len(x[0])))
            name = self._normalize(top_phrase[0])[:48].rstrip()

        if mode == "intent":
            intent_scores = defaultdict(float)
            for phrase, freq in cluster_phrases:
                normalized, raw_tokens, raw_signatures, effective_signatures = self._extract_features(phrase)
                intent = self._detect_intent(normalized, raw_tokens, raw_signatures, effective_signatures)
                intent_scores[intent] += 1.0 + math.log1p(max(freq, 0))
            if intent_scores:
                dominant_intent = max(intent_scores.items(), key=lambda item: (item[1], item[0]))[0]
                intent_label = self.INTENT_DISPLAY.get(dominant_intent, dominant_intent.capitalize())
                if intent_label and intent_label.lower() not in name.lower():
                    name = f"{intent_label} | {name}" if name else intent_label

        name = re.sub(r"\s+", " ", name).strip(" |")
        if not name:
            return f"Кластер {cluster_idx}"
        if len(name) > 60:
            name = name[:60].rstrip()
        if name[0].islower():
            name = name[0].upper() + name[1:]
        return name

    @staticmethod
    def _safe_excel_sheet_name(name: str, used_names: Set[str]) -> str:
        cleaned = re.sub(r"[:\\/?*\[\]]", " ", str(name))
        cleaned = re.sub(r"\s+", " ", cleaned).strip() or "Кластер"
        cleaned = cleaned[:31].strip() or "Кластер"

        candidate = cleaned
        counter = 2
        while candidate in used_names:
            suffix = f"_{counter}"
            base = cleaned[:max(1, 31 - len(suffix))].rstrip()
            candidate = f"{base}{suffix}".strip()
            counter += 1
        used_names.add(candidate)
        return candidate

    @staticmethod
    def _safe_export_file_stem(text: str, fallback: str = "clusters") -> str:
        cleaned = re.sub(r'[\\/:*?"<>|]+', "_", str(text))
        cleaned = re.sub(r"\s+", "_", cleaned).strip("._")
        cleaned = cleaned[:80].strip("._")
        return cleaned or fallback

    def _export_cluster_map(self, cluster_map: Dict[str, List[Tuple[str, int]]], default_file_name: str, success_text: str):
        if not cluster_map:
            QMessageBox.warning(self, "Предупреждение", "Нет данных для экспорта")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить кластеры",
            default_file_name,
            "Excel files (*.xlsx)"
        )
        if not file_path:
            return

        try:
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                used_sheet_names = set()
                for cluster_name, cluster_phrases in cluster_map.items():
                    df = pd.DataFrame(cluster_phrases, columns=['Фраза', 'Частотность'])
                    sheet_name = self._safe_excel_sheet_name(cluster_name, used_sheet_names)
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            QMessageBox.information(self, "Успех", success_text)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать: {str(e)}")

    def show_tree_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return

        self.tree.setCurrentItem(item)
        menu = QMenu(self)

        cluster_name = item.data(0, self.TREE_CLUSTER_ROLE)
        if item.parent() is None:
            export_cluster_action = menu.addAction("Экспортировать выбранный кластер")
            export_cluster_action.triggered.connect(
                lambda checked=False, cluster=cluster_name: self.export_selected_cluster(cluster)
            )
        else:
            phrase = item.data(0, self.TREE_PHRASE_ROLE) or item.text(0)
            freq_value = item.data(0, self.TREE_FREQ_ROLE)
            if freq_value is None:
                try:
                    freq_value = int(item.text(1))
                except Exception:
                    freq_value = 0

            export_phrase_action = menu.addAction("Экспортировать эту фразу")
            export_phrase_action.triggered.connect(
                lambda checked=False, c=cluster_name, p=phrase, f=int(freq_value): self.export_selected_phrase(c, p, f)
            )

            export_cluster_action = menu.addAction("Экспортировать кластер этой фразы")
            export_cluster_action.triggered.connect(
                lambda checked=False, cluster=cluster_name: self.export_selected_cluster(cluster)
            )

        menu.exec_(self.tree.viewport().mapToGlobal(pos))

    def export_selected_cluster(self, cluster_name: str):
        if not cluster_name or cluster_name not in self.clusters:
            QMessageBox.warning(self, "Предупреждение", "Выбранный кластер не найден")
            return

        file_stem = self._safe_export_file_stem(cluster_name, "cluster")
        self._export_cluster_map(
            {cluster_name: self.clusters[cluster_name]},
            f"{file_stem}.xlsx",
            f"Кластер «{cluster_name}» экспортирован"
        )

    def export_selected_phrase(self, cluster_name: str, phrase: str, freq: int):
        if not phrase:
            QMessageBox.warning(self, "Предупреждение", "Фраза не выбрана")
            return

        export_name = f"{cluster_name} | {phrase}" if cluster_name else phrase
        file_stem = self._safe_export_file_stem(phrase, "phrase")
        self._export_cluster_map(
            {export_name: [(phrase, int(freq))]},
            f"{file_stem}.xlsx",
            "Фраза экспортирована"
        )

    def _clusters_from_parent(self, phrases: List[Tuple[str, int]], parent: List[int]) -> List[List[Tuple[str, int]]]:
        groups = defaultdict(list)

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for idx, item in enumerate(phrases):
            groups[find(idx)].append(item)

        clusters = []
        for items in groups.values():
            sorted_items = sorted(items, key=lambda x: (-x[1], x[0].lower()))
            clusters.append(sorted_items)

        clusters.sort(key=lambda c: (-len(c), -sum(freq for _, freq in c), c[0][0].lower() if c else ""))
        return clusters

    def _build_clusters_by_word_overlap(self, phrases: List[Tuple[str, int]]) -> List[List[Tuple[str, int]]]:
        n = len(phrases)
        if n == 0:
            return []

        parent = list(range(n))
        size = [1] * n

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int):
            ra, rb = find(a), find(b)
            if ra != rb:
                if size[ra] < size[rb]:
                    ra, rb = rb, ra
                parent[rb] = ra
                size[ra] += size[rb]

        primary_signatures = []
        signature_df = defaultdict(int)

        for phrase, _ in phrases:
            _, _, raw_sig, eff_sig = self._extract_features(phrase)
            primary = eff_sig or raw_sig
            primary_signatures.append(primary)
            for signature in primary:
                signature_df[signature] += 1

        max_common_df = min(max(12, int(n * 0.10)), 420)
        rare_single_df = min(max(4, int(n * 0.015)), 40)
        max_phrase_tokens = 6
        pair_anchor = {}
        single_anchor = {}

        for idx in range(n):
            primary = primary_signatures[idx]
            if not primary:
                continue

            usable = [token for token in primary if signature_df[token] <= max_common_df]
            if len(usable) < 2:
                ranked = sorted(primary, key=lambda token: (signature_df[token], -len(token), token))
                usable = ranked[:min(max_phrase_tokens, len(ranked))]
            else:
                usable = sorted(usable, key=lambda token: (signature_df[token], -len(token), token))

            if len(usable) > max_phrase_tokens:
                usable = usable[:max_phrase_tokens]

            if len(usable) >= 2:
                limit = len(usable)
                for left_pos in range(limit - 1):
                    left = usable[left_pos]
                    for right_pos in range(left_pos + 1, limit):
                        right = usable[right_pos]
                        key = (left, right) if left <= right else (right, left)
                        anchor = pair_anchor.get(key)
                        if anchor is None:
                            pair_anchor[key] = idx
                        else:
                            union(idx, anchor)
                continue

            token = usable[0]
            if signature_df[token] <= rare_single_df:
                anchor = single_anchor.get(token)
                if anchor is None:
                    single_anchor[token] = idx
                else:
                    union(idx, anchor)

        return self._clusters_from_parent(phrases, parent)

    def _build_clusters_by_similarity(self, phrases: List[Tuple[str, int]]) -> List[List[Tuple[str, int]]]:
        n = len(phrases)
        if n == 0:
            return []

        parent = list(range(n))
        size = [1] * n

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int):
            ra, rb = find(a), find(b)
            if ra != rb:
                if size[ra] < size[rb]:
                    ra, rb = rb, ra
                parent[rb] = ra
                size[ra] += size[rb]

        normalized = []
        raw_signatures = []
        primary_signatures = []
        signature_df = defaultdict(int)

        for phrase, _ in phrases:
            norm, _, raw_sig, eff_sig = self._extract_features(phrase)
            normalized.append(norm)
            raw_signatures.append(raw_sig)
            primary = eff_sig or raw_sig
            primary_signatures.append(primary)
            for signature in primary:
                signature_df[signature] += 1

        scale = max(6, int(math.sqrt(n)))
        max_seed_df = min(max(16, scale * 3), 1200)
        bucket_cap = min(max(120, scale * 6), 600)
        max_candidates_per_phrase = 64
        seed_limit = 2
        min_length_ratio = 0.42

        seeds_by_idx = []
        seed_buckets = defaultdict(list)

        for idx in range(n):
            primary = primary_signatures[idx]
            if primary:
                ranked = sorted(primary, key=lambda token: (signature_df[token], -len(token), token))
                seeds = ranked[:seed_limit]
            else:
                seeds = []

            if normalized[idx]:
                parts = normalized[idx].split()
                if len(parts) >= 2:
                    prefix_seed = f"__pref__{parts[0][:8]}_{parts[1][:8]}"
                    if prefix_seed not in seeds:
                        seeds.append(prefix_seed)
                elif parts:
                    prefix_seed = f"__pref__{parts[0][:8]}"
                    if prefix_seed not in seeds:
                        seeds.append(prefix_seed)

            if not seeds and normalized[idx]:
                seeds = [f"__text__{normalized[idx][:12]}"]

            seeds_by_idx.append(seeds)
            for pos, seed in enumerate(seeds):
                bucket = seed_buckets[seed]
                if len(bucket) >= bucket_cap:
                    continue

                if seed.startswith("__pref__") or seed.startswith("__text__"):
                    bucket.append(idx)
                    continue

                token_df = signature_df.get(seed, 0)
                if token_df <= max_seed_df or pos == 0:
                    bucket.append(idx)

        normalized_lengths = [len(text) for text in normalized]

        for i in range(n):
            seed_votes = defaultdict(int)
            for seed in seeds_by_idx[i]:
                bucket = seed_buckets.get(seed)
                if not bucket:
                    continue
                for j in bucket:
                    if j <= i:
                        continue
                    seed_votes[j] += 1

            if not seed_votes:
                continue

            candidates = list(seed_votes.items())
            if len(candidates) > max_candidates_per_phrase:
                candidates.sort(
                    key=lambda item: (
                        item[1],
                        -abs(normalized_lengths[i] - normalized_lengths[item[0]]),
                    ),
                    reverse=True,
                )
                candidates = candidates[:max_candidates_per_phrase]

            primary_i = primary_signatures[i]
            raw_i = raw_signatures[i]
            len_i = normalized_lengths[i]
            norm_i = normalized[i]

            for j, votes in candidates:
                len_j = normalized_lengths[j]
                if not len_i or not len_j:
                    continue
                length_ratio = min(len_i, len_j) / max(len_i, len_j)
                if length_ratio < min_length_ratio:
                    continue

                primary_j = primary_signatures[j]
                raw_j = raw_signatures[j]

                shared_primary = len(primary_i & primary_j)
                if shared_primary == 0 and votes < 2:
                    continue

                primary_overlap = self._token_overlap(primary_i, primary_j)
                if primary_overlap < 0.2 and votes < 2:
                    continue

                shared_raw = len(raw_i & raw_j)
                raw_union_size = len(raw_i | raw_j) or 1
                primary_union_size = len(primary_i | primary_j) or 1
                raw_jaccard = shared_raw / raw_union_size
                primary_jaccard = shared_primary / primary_union_size

                coarse_score = (
                    0.45 * primary_overlap +
                    0.30 * raw_jaccard +
                    0.15 * primary_jaccard +
                    0.10 * min(votes, 2) / 2.0
                )
                if coarse_score < 0.20:
                    continue

                if shared_primary >= 2 and (primary_overlap >= 0.34 or primary_jaccard >= 0.26):
                    union(i, j)
                    continue

                if coarse_score >= 0.60 and (shared_primary >= 2 or raw_jaccard >= 0.45):
                    union(i, j)
                    continue

                norm_j = normalized[j]
                contains = norm_i in norm_j or norm_j in norm_i
                if contains and shared_primary >= 1 and length_ratio >= 0.55:
                    union(i, j)
                    continue

                if not contains and coarse_score < 0.40:
                    continue

                seq_ratio = 0.0
                if len_i <= 120 and len_j <= 120:
                    seq_ratio = SequenceMatcher(None, norm_i, norm_j).ratio()

                score = (
                    0.35 * primary_overlap +
                    0.25 * raw_jaccard +
                    0.20 * primary_jaccard +
                    0.20 * seq_ratio
                )
                if contains:
                    score += 0.06

                if score >= 0.64:
                    union(i, j)
                    continue

                if contains and seq_ratio >= 0.70 and (shared_primary >= 1 or raw_jaccard >= 0.35):
                    union(i, j)
                    continue

                if seq_ratio >= 0.88 and raw_jaccard >= 0.28:
                    union(i, j)

        return self._clusters_from_parent(phrases, parent)

    def _build_clusters_by_intent(self, phrases: List[Tuple[str, int]]) -> List[List[Tuple[str, int]]]:
        if not phrases:
            return []

        intent_groups = defaultdict(list)
        for phrase, freq in phrases:
            normalized, raw_tokens, raw_signatures, effective_signatures = self._extract_features(phrase)
            intent = self._detect_intent(normalized, raw_tokens, raw_signatures, effective_signatures)
            intent_groups[intent].append((phrase, freq))

        all_clusters = []
        ordered_intents = sorted(
            intent_groups.keys(),
            key=lambda key: (key == "other", key)
        )

        for intent in ordered_intents:
            group_phrases = intent_groups[intent]
            if len(group_phrases) <= 1:
                all_clusters.extend([[item] for item in group_phrases])
                continue

            sub_clusters = self._build_clusters_by_word_overlap(group_phrases)
            all_clusters.extend(sub_clusters)

        all_clusters.sort(
            key=lambda c: (
                -len(c),
                -sum(freq for _, freq in c),
                c[0][0].lower() if c else ""
            )
        )
        return all_clusters

    def export_clusters(self):
        self._export_cluster_map(self.clusters, "clusters.xlsx", "Кластеры экспортированы")


class FolderColorDelegate(QStyledItemDelegate):
    """Делегат для отрисовки полупрозрачного фона у строк папок"""

    COLOR_ROLE = Qt.UserRole + 101

    def paint(self, painter, option, index):
        color_hex = index.data(self.COLOR_ROLE)
        selected = bool(option.state & QStyle.State_Selected)
        hover = bool(option.state & QStyle.State_MouseOver)
        is_dark = option.palette.color(QPalette.Base).lightness() < 128
        bg = None

        if color_hex:
            bg = QColor(color_hex)
            if bg.isValid():
                if selected or hover:
                    bg = bg.darker(108)
                bg.setAlpha(92 if (selected or hover) else 72)
            else:
                bg = None
        elif selected:
            # Для обычных строк (фраз) рисуем свое серое выделение без системной синей плашки слева
            bg = QColor(58, 58, 60) if is_dark else QColor(229, 229, 234)
        elif hover and not selected:
            bg = QColor(44, 44, 46) if is_dark else QColor(242, 242, 247)

        style_option = QStyleOptionViewItem(option)

        if bg is not None:
            paint_rect = option.rect
            if index.column() == 0:
                # Закрашиваем и левую область со стрелкой разворота (где раньше был системный синий)
                paint_rect = QRect(0, option.rect.y(), option.rect.right() + 1, option.rect.height())
            painter.save()
            painter.fillRect(paint_rect, bg)

            # Левая плашка у папки всегда видна: чистый выбранный цвет без прозрачности
            if color_hex and index.column() == 0:
                accent = QColor(color_hex)
                if accent.isValid():
                    accent.setAlpha(255)
                    accent_width = max(14, min(28, option.rect.left()))
                    painter.fillRect(QRect(0, option.rect.y(), accent_width, option.rect.height()), accent)
            painter.restore()

            if selected:
                style_option.state &= ~QStyle.State_Selected

        super().paint(painter, style_option, index)


class FoldersWidget(QWidget):
    """Виджет для управления папками в стиле macOS"""

    folders_changed = pyqtSignal()
    phrases_back = pyqtSignal(list, bool)  # list of (folder_name, phrase, freq), is_move

    def __init__(self):
        super().__init__()
        self.folders = {}
        self.history = HistoryManager()
        self.current_theme = "light"
        self.setup_ui()
        self.apply_theme("light")
        self.history.set_initial_state({})

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()

        self.header_label = QLabel("Папки")
        self.header_label.setFont(QFont("Arial", 15, QFont.Bold))
        self.header_label.setContentsMargins(4, 0, 0, 0)
        self.header_label.setIndent(2)
        header_layout.addWidget(self.header_label)

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
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.setUniformRowHeights(True)
        self.tree.setMouseTracking(True)
        self.tree.viewport().setMouseTracking(True)
        self.tree.viewport().installEventFilter(self)
        self.tree.setIndentation(16)
        self.tree.setItemDelegate(FolderColorDelegate(self.tree))
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.Fixed)
        self.tree.setColumnWidth(1, 140)

        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)

        self.tree.setDragDropMode(QAbstractItemView.InternalMove)
        self.tree.setDefaultDropAction(Qt.MoveAction)

        layout.addWidget(self.tree)

        self.setLayout(layout)

    def apply_theme(self, theme: str):
        self.current_theme = "dark" if theme == "dark" else "light"
        if theme == "dark":
            self.header_label.setStyleSheet("color: #f2f2f7;")
            self.new_folder_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0a84ff;
                    color: #ffffff;
                    border: 1px solid #0a84ff;
                    padding: 6px 14px;
                    border-radius: 10px;
                    font-weight: 700;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #339bff;
                }
                QPushButton:pressed {
                    background-color: #0066d1;
                }
            """)
            self.export_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2c2c2e;
                    color: #4da3ff;
                    border: 1px solid #4b4b50;
                    padding: 6px 14px;
                    border-radius: 10px;
                    font-weight: 700;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #3a3a3c;
                    border-color: #5a5a60;
                }
                QPushButton:pressed {
                    background-color: #48484a;
                }
            """)
            self.tree.setStyleSheet("""
                QTreeWidget {
                    background-color: #1c1c1e;
                    alternate-background-color: #242428;
                    border: 1px solid #4b4b50;
                    border-radius: 10px;
                    padding: 8px;
                    font-size: 13px;
                    color: #f2f2f7;
                    outline: 0;
                    show-decoration-selected: 1;
                }
                QTreeWidget::item {
                    padding: 6px 8px;
                    border-radius: 0px;
                }
                QTreeWidget::item:hover {
                    background-color: transparent;
                }
                QTreeWidget::item:selected,
                QTreeWidget::item:selected:active,
                QTreeWidget::item:selected:!active {
                    background-color: #3a3a3c;
                    color: #ffffff;
                }
                QHeaderView::section {
                    background-color: #2c2c2e;
                    color: #f2f2f7;
                    font-family: Arial;
                    padding: 8px 8px 8px 12px;
                    border: none;
                    border-bottom: 1px solid #4b4b50;
                    font-weight: 700;
                }
                QTreeView::branch:has-siblings:!adjoins-item {
                    border-image: none;
                    border-left: 1px solid #4b4b50;
                }
                QTreeView::branch:selected {
                    background: transparent;
                }
            """)
            return

        self.header_label.setStyleSheet("color: #000000;")
        self.new_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #0a84ff;
                color: #ffffff;
                border: 1px solid #0071e6;
                padding: 6px 14px;
                border-radius: 10px;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #339bff;
            }
            QPushButton:pressed {
                background-color: #0066d1;
            }
        """)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #0a84ff;
                border: 1px solid #c7c7cc;
                padding: 6px 14px;
                border-radius: 10px;
                font-weight: 700;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #f6f8fc;
                border-color: #b8c0cc;
            }
            QPushButton:pressed {
                background-color: #e9edf5;
            }
        """)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #ffffff;
                alternate-background-color: #f8faff;
                border: 1px solid #cfd3dc;
                border-radius: 10px;
                padding: 8px;
                font-size: 13px;
                color: #202124;
                outline: 0;
                show-decoration-selected: 1;
            }
            QTreeWidget::item {
                padding: 6px 8px;
                border-radius: 0px;
            }
            QTreeWidget::item:hover {
                background-color: transparent;
            }
            QTreeWidget::item:selected,
            QTreeWidget::item:selected:active,
            QTreeWidget::item:selected:!active {
                background-color: #e5e5ea;
                color: #111111;
            }
            QHeaderView::section {
                background-color: #f3f5fb;
                color: #1b1b1d;
                font-family: Arial;
                padding: 8px 8px 8px 12px;
                border: none;
                border-bottom: 1px solid #d5d9e2;
                font-weight: 700;
            }
            QTreeView::branch:has-siblings:!adjoins-item {
                border-image: none;
                border-left: 1px solid #d7dce6;
            }
            QTreeView::branch:selected {
                background: transparent;
            }
        """)

    def _menu_style(self) -> str:
        if self.current_theme == "dark":
            return """
                QMenu {
                    background-color: #2c2c2e;
                    color: #f2f2f7;
                    border: 1px solid #4b4b50;
                    border-radius: 8px;
                    padding: 5px;
                    font-size: 13px;
                }
                QMenu::item {
                    padding: 6px 20px;
                    border-radius: 4px;
                }
                QMenu::item:selected {
                    background-color: #3a3a3c;
                }
            """
        return """
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
        """

    def eventFilter(self, obj, event):
        if obj is self.tree.viewport() and event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            pos = event.pos()
            item = self.tree.itemAt(pos)
            if item and item.parent() is None:
                index = self.tree.indexAt(pos)
                if index.isValid() and index.column() == 0:
                    rect = self.tree.visualRect(index)
                    if pos.x() < rect.left():
                        folder_name = item.text(0).split(" (")[0]
                        self.choose_folder_color(folder_name)
                        event.accept()
                        return True
        return super().eventFilter(obj, event)

    def create_folder(self):
        name, ok = QInputDialog.getText(self, "Новая папка", "Введите название папки:")
        if ok and name:
            if name not in self.folders:
                before = self._folders_snapshot()
                self.folders[name] = Folder(name)
                self._commit_if_changed(before)
            else:
                QMessageBox.warning(self, "Ошибка", "Папка с таким именем уже существует")

    def rename_folder(self, old_name: str) -> bool:
        if old_name not in self.folders:
            return False

        new_name, ok = QInputDialog.getText(
            self,
            "Переименовать папку",
            "Новое название папки:",
            text=old_name
        )
        if not ok:
            return False

        new_name = new_name.strip()
        if not new_name:
            QMessageBox.warning(self, "Ошибка", "Название папки не может быть пустым")
            return False
        if new_name == old_name:
            return False
        if new_name in self.folders:
            QMessageBox.warning(self, "Ошибка", "Папка с таким именем уже существует")
            return False

        before = self._folders_snapshot()
        renamed_folders = {}
        for folder_name, folder in self.folders.items():
            if folder_name == old_name:
                folder.name = new_name
                renamed_folders[new_name] = folder
            else:
                renamed_folders[folder_name] = folder
        self.folders = renamed_folders
        return self._commit_if_changed(before)

    def delete_folder(self, folder_name: str):
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить папку '{folder_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            before = self._folders_snapshot()
            del self.folders[folder_name]
            self._commit_if_changed(before)

    def show_context_menu(self, position):
        items = self.tree.selectedItems()
        if not items:
            return

        if len(items) == 1 and items[0].parent() is None:
            folder_name = items[0].text(0).split(" (")[0]
            menu = QMenu(self)
            menu.setStyleSheet(self._menu_style())

            rename_action = menu.addAction("Переименовать папку")
            rename_action.triggered.connect(lambda: self.rename_folder(folder_name))

            menu.addSeparator()

            delete_action = menu.addAction("Удалить папку")
            delete_action.triggered.connect(lambda: self.delete_folder(folder_name))

            clear_action = menu.addAction("Очистить папку")
            clear_action.triggered.connect(lambda: self.clear_folder(folder_name))

            menu.addSeparator()

            color_action = menu.addAction("Изменить цвет...")
            color_action.triggered.connect(lambda: self.choose_folder_color(folder_name))

            reset_color_action = menu.addAction("Сбросить цвет")
            reset_color_action.triggered.connect(lambda: self.set_folder_color(folder_name, None))

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
                menu.setStyleSheet(self._menu_style())

                copy_back = menu.addAction("Копировать обратно")
                copy_back.triggered.connect(lambda: self.phrases_back.emit(selected, False))

                move_back = menu.addAction("Переместить обратно")
                move_back.triggered.connect(lambda: self.phrases_back.emit(selected, True))

                menu.addSeparator()

                remove_action = menu.addAction("Удалить из папки")
                remove_action.triggered.connect(lambda: self.batch_remove_from_folder(selected))

                menu.exec_(self.tree.mapToGlobal(position))

    def batch_remove_from_folder(self, selected: List[Tuple[str, str, int]]):
        before = self._folders_snapshot()
        for folder_name, phrase, _ in selected:
            if folder_name in self.folders:
                self.folders[folder_name].remove_phrase(phrase)
        self._commit_if_changed(before)

    def clear_folder(self, folder_name: str):
        if folder_name in self.folders:
            before = self._folders_snapshot()
            self.folders[folder_name].clear()
            self._commit_if_changed(before)

    def remove_from_folder(self, folder_name: str, phrase: str):
        if folder_name in self.folders:
            before = self._folders_snapshot()
            self.folders[folder_name].remove_phrase(phrase)
            self._commit_if_changed(before)

    def add_phrases_to_folder(self, data: List[Tuple[str, str, int]]):
        before = self._folders_snapshot()
        for folder_name, phrase, freq in data:
            if folder_name in self.folders:
                self.folders[folder_name].add_phrase(phrase, freq)
        self._commit_if_changed(before)

    def choose_folder_color(self, folder_name: str):
        folder = self.folders.get(folder_name)
        if not folder:
            return

        initial = QColor(folder.color) if folder.color else QColor(36, 46, 66)
        color = QColorDialog.getColor(initial, self, f"Цвет папки: {folder_name}")
        if color.isValid():
            self.set_folder_color(folder_name, color.name())

    def set_folder_color(self, folder_name: str, color: Optional[str]) -> bool:
        folder = self.folders.get(folder_name)
        if not folder:
            return False

        normalized = None
        if color:
            qcolor = QColor(color)
            if not qcolor.isValid():
                return False
            normalized = qcolor.name()

        before = self._folders_snapshot()
        folder.color = normalized
        return self._commit_if_changed(before)

    def update_tree(self):
        self.tree.clear()
        folder_font = QFont("Arial", 13, QFont.DemiBold)
        phrase_font = QFont("Arial", 12)
        default_folder_color = QColor(36, 46, 66)
        folder_icon = self.style().standardIcon(QStyle.SP_DirIcon)
        is_dark = getattr(self, "current_theme", "light") == "dark"
        text_color = QColor(242, 242, 247) if is_dark else QColor(0, 0, 0)
        phrase_color = QColor(230, 230, 235) if is_dark else QColor(34, 34, 38)

        for folder_name, folder in self.folders.items():
            folder_color = QColor(folder.color) if getattr(folder, "color", None) else default_folder_color
            if not folder_color.isValid():
                folder_color = default_folder_color
            folder_fg = QBrush(text_color)
            folder_bg = None
            if getattr(folder, "color", None):
                tint_color = QColor(folder_color)
                tint_color.setAlpha(52)
                folder_bg = QBrush(tint_color)

            folder_item = QTreeWidgetItem(self.tree)
            folder_item.setText(0, f"{folder_name} ({len(folder.phrases)})")
            folder_item.setIcon(0, folder_icon)
            folder_item.setFont(0, folder_font)
            folder_item.setFont(1, folder_font)
            folder_item.setForeground(0, folder_fg)
            folder_item.setForeground(1, folder_fg)
            folder_item.setData(0, FolderColorDelegate.COLOR_ROLE, getattr(folder, "color", None))
            folder_item.setData(1, FolderColorDelegate.COLOR_ROLE, getattr(folder, "color", None))
            if folder_bg is not None:
                folder_item.setBackground(0, folder_bg)
                folder_item.setBackground(1, folder_bg)
            folder_item.setExpanded(True)

            for phrase, freq in folder.phrases:
                phrase_item = QTreeWidgetItem(folder_item)
                phrase_item.setText(0, phrase)
                phrase_item.setText(1, str(freq))
                phrase_item.setFont(0, phrase_font)
                phrase_item.setFont(1, phrase_font)
                phrase_item.setForeground(0, QBrush(phrase_color))

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
        for folder in self.folders.values():
            if not hasattr(folder, "color"):
                folder.color = None
        self.update_tree()
        self.history.set_initial_state(self._folders_snapshot())

    def get_folders(self) -> Dict[str, Folder]:
        return {k: copy.deepcopy(v) for k, v in self.folders.items()}

    def _folders_snapshot(self) -> Dict[str, Dict[str, object]]:
        snapshot = {}
        for folder_name, folder in self.folders.items():
            snapshot[folder_name] = {
                "phrases": [(phrase, freq) for phrase, freq in folder.phrases],
                "color": folder.color if getattr(folder, "color", None) else None,
            }
        return snapshot

    def _load_from_snapshot(self, snapshot: Dict[str, object]):
        restored = {}
        for folder_name, data in snapshot.items():
            phrases = data
            color = None
            if isinstance(data, dict):
                phrases = data.get("phrases", [])
                color = data.get("color")

            folder = Folder(folder_name, color=color)
            folder.phrases = [(phrase, freq) for phrase, freq in phrases]
            restored[folder_name] = folder
        self.folders = restored
        self.update_tree()
        self.folders_changed.emit()

    def _commit_if_changed(self, before_snapshot: Dict[str, Dict[str, object]]) -> bool:
        after_snapshot = self._folders_snapshot()
        if after_snapshot == before_snapshot:
            return False
        self.update_tree()
        self.folders_changed.emit()
        self.history.add_state(after_snapshot)
        return True

    def undo(self) -> bool:
        state = self.history.undo()
        if state is None:
            return False
        self._load_from_snapshot(state)
        return True

    def redo(self) -> bool:
        state = self.history.redo()
        if state is None:
            return False
        self._load_from_snapshot(state)
        return True


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


class NoClipTabBar(QTabBar):
    """TabBar с ручной отрисовкой текста без клиппинга первого символа"""

    def __init__(self, parent=None, text_left_padding: int = 10, text_right_padding: int = 10):
        super().__init__(parent)
        self.text_left_padding = text_left_padding
        self.text_right_padding = text_right_padding
        self.close_button_gap = 2
        self.setElideMode(Qt.ElideRight)

    def tabSizeHint(self, index):
        size = super().tabSizeHint(index)
        size.setWidth(min(size.width(), 320))
        return size

    def paintEvent(self, event):
        painter = QStylePainter(self)
        for index in range(self.count()):
            option = QStyleOptionTab()
            self.initStyleOption(option, index)

            painter.drawControl(QStyle.CE_TabBarTabShape, option)

            left_btn = self.tabButton(index, QTabBar.LeftSide)
            right_btn = self.tabButton(index, QTabBar.RightSide)
            left_reserve = max(self.text_left_padding, 8)
            right_reserve = max(self.text_right_padding, 4)
            if left_btn and left_btn.isVisible():
                left_width = max(left_btn.width(), left_btn.sizeHint().width())
                left_reserve = max(left_reserve, left_width + 8)
            if right_btn and right_btn.isVisible():
                right_width = max(
                    right_btn.width(),
                    right_btn.sizeHint().width(),
                    self.style().pixelMetric(QStyle.PM_TabCloseIndicatorWidth, option, self)
                )
                right_reserve = max(right_reserve, right_width + self.close_button_gap)

            text_rect = option.rect.adjusted(left_reserve, 0, -right_reserve, 0)

            text = option.fontMetrics.elidedText(option.text, Qt.ElideRight, max(0, text_rect.width()))

            painter.save()
            tab_font = self.font()
            if index == self.currentIndex():
                tab_font.setBold(True)
            painter.setFont(tab_font)
            color = self.tabTextColor(index)
            if not color.isValid():
                color = option.palette.color(QPalette.WindowText)
            painter.setPen(color)
            painter.setClipRect(option.rect.adjusted(1, 0, -1, 0))
            painter.drawText(
                text_rect,
                int(Qt.AlignVCenter | Qt.AlignLeft | Qt.TextShowMnemonic | Qt.TextDontClip),
                text
            )
            painter.restore()


class TabCloseButton(QPushButton):
    """Современная кнопка закрытия вкладки"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(22, 22)
        self.setFocusPolicy(Qt.NoFocus)
        self.setStyleSheet("border: none; background: transparent;")

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        if self._hover:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 18))
            painter.drawEllipse(self.rect().adjusted(1, 1, -1, -1))

        pen = QPen(QColor(62, 62, 66), 2.2)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawLine(6, 6, self.width() - 7, self.height() - 7)
        painter.drawLine(self.width() - 7, 6, 6, self.height() - 7)


class TabBarWithPlus(NoClipTabBar):
    add_requested = pyqtSignal()
    close_requested = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent, text_left_padding=10, text_right_padding=10)
        self.min_tab_width = 120
        self.max_tab_width = 280
        self.active_tab_min_width = 140
        self._hover_tab = -1
        self.setExpanding(False)
        self.setUsesScrollButtons(True)
        self.setMinimumHeight(30)
        self.setMouseTracking(True)
        self.currentChanged.connect(self._update_close_buttons_visibility)
        self.plus_button = QPushButton("+", self)
        self.plus_button.setObjectName("tabPlusButton")
        self.plus_button.setFixedSize(24, 24)
        self.plus_button.setStyleSheet("""
            QPushButton#tabPlusButton {
                background-color: #ffffff;
                color: #007aff;
                border: 1px solid #c7c7cc;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                padding: 0px;
                text-align: center;
            }
            QPushButton#tabPlusButton:hover {
                background-color: #f2f2f7;
            }
            QPushButton#tabPlusButton:pressed {
                background-color: #e5e5ea;
            }
        """)
        self.plus_button.clicked.connect(self.add_requested.emit)
        self._refresh_close_buttons()
        self._reposition_plus_button()

    def tabSizeHint(self, index):
        size = super().tabSizeHint(index)
        width = min(size.width(), self.max_tab_width)
        width = max(width, self.min_tab_width)
        if index == self.currentIndex():
            width = max(width, self.active_tab_min_width)
        size.setWidth(width)
        return size

    def _on_close_clicked(self):
        sender_btn = self.sender()
        if sender_btn is None:
            return
        for index in range(self.count()):
            if self.tabButton(index, QTabBar.RightSide) is sender_btn:
                self.close_requested.emit(index)
                return

    def _refresh_close_buttons(self):
        for index in range(self.count()):
            btn = self.tabButton(index, QTabBar.RightSide)
            if not isinstance(btn, TabCloseButton):
                close_btn = TabCloseButton(self)
                close_btn.clicked.connect(self._on_close_clicked)
                self.setTabButton(index, QTabBar.RightSide, close_btn)
        self._update_close_buttons_visibility()

    def _update_close_buttons_visibility(self):
        current = self.currentIndex()
        for index in range(self.count()):
            btn = self.tabButton(index, QTabBar.RightSide)
            if not isinstance(btn, TabCloseButton):
                continue
            show_close = (index == current) or (index == self._hover_tab)
            if btn.isVisible() != show_close:
                btn.setVisible(show_close)
        self.update()

    def _reposition_plus_button(self):
        if self.count() > 0:
            last_index = self.count() - 1
            last_rect = self.tabRect(last_index)
            last_right = last_rect.right()
            right_btn = self.tabButton(last_index, QTabBar.RightSide)
            if right_btn and right_btn.isVisible():
                last_right = max(last_right, right_btn.geometry().right())
            x = last_right + 8
        else:
            x = 6

        x = min(x, max(6, self.width() - self.plus_button.width() - 4))
        y = (self.height() - self.plus_button.height()) // 2
        self.plus_button.move(x, y)
        self.plus_button.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_close_buttons()
        self._reposition_plus_button()
        self._update_close_buttons_visibility()

    def mouseMoveEvent(self, event):
        hovered = self.tabAt(event.pos())
        if hovered != self._hover_tab:
            self._hover_tab = hovered
            self._update_close_buttons_visibility()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self._hover_tab != -1:
            self._hover_tab = -1
            self._update_close_buttons_visibility()
        super().leaveEvent(event)

    def tabInserted(self, index):
        super().tabInserted(index)
        self._refresh_close_buttons()
        self._reposition_plus_button()
        self._update_close_buttons_visibility()
        self.update()

    def tabRemoved(self, index):
        super().tabRemoved(index)
        self._refresh_close_buttons()
        self._reposition_plus_button()
        self._update_close_buttons_visibility()
        self.update()

    def wheelEvent(self, event):
        if self.scroll_tabs_by_wheel_event(event):
            event.accept()
            return
        event.ignore()

    def _extract_wheel_delta(self, event) -> int:
        angle = event.angleDelta()
        pixel = event.pixelDelta()

        ax = angle.x()
        ay = angle.y()
        px = pixel.x()
        py = pixel.y()

        # На macOS (трекпад) часто приходят pixelDelta и/или горизонтальная ось.
        # Выбираем доминирующую ось и сводим к одному "горизонтальному" направлению.
        if abs(ax) >= abs(ay) and ax != 0:
            return -ax
        if ay != 0:
            return ay
        if abs(px) >= abs(py) and px != 0:
            return -px
        if py != 0:
            return py
        return 0

    def scroll_tabs_by_wheel_event(self, event) -> bool:
        return self.scroll_tabs_by_wheel(self._extract_wheel_delta(event))

    def scroll_tabs_by_wheel(self, delta_y: int) -> bool:
        if delta_y == 0:
            return False

        # Колесо прокручивает ленту вкладок (как стрелки), не меняя активную вкладку
        left_btn = None
        right_btn = None
        for btn in self.findChildren(QToolButton):
            if not btn.isVisible() or not btn.isEnabled():
                continue
            arrow = btn.arrowType()
            if arrow == Qt.LeftArrow:
                left_btn = btn
            elif arrow == Qt.RightArrow:
                right_btn = btn

        if left_btn is None or right_btn is None:
            buttons = [b for b in self.findChildren(QToolButton) if b.isVisible() and b.isEnabled()]
            if len(buttons) < 2:
                return False
            buttons_sorted = sorted(buttons, key=lambda b: b.x())
            left_btn, right_btn = buttons_sorted[0], buttons_sorted[-1]

        target_btn = left_btn if delta_y > 0 else right_btn
        steps = max(1, abs(delta_y) // 120)
        for _ in range(steps):
            if not target_btn.isEnabled():
                break
            target_btn.click()

        return True


class MainWindow(QMainWindow):
    """Главное окно приложения в стиле macOS"""

    def __init__(self, license_manager: LicenseManager):
        super().__init__()
        self.license_manager = license_manager
        self.theme_mode = "system"
        self.current_theme = "light"
        self.phrase_lists = {}
        self.global_stop_words = set()
        self.global_folders = {}
        self._prev_phrase_tab_index = -1
        self._shortcuts = []
        self.current_session_path = None
        # Создаем виджеты до setup_ui
        self.stop_words_widget = StopWordsWidget()
        self.setup_ui()
        self.setup_shortcuts()
        self.setup_native_menu()
        self.apply_theme(self.theme_mode)
        self.phrase_tabs.currentChanged.connect(self.on_phrase_tab_changed)
        self.tabs.currentChanged.connect(self.on_side_tab_changed)
        self.general_tab.currentChanged.connect(self.on_general_tab_changed)
        self.phrase_tabs.tabBar().setContextMenuPolicy(Qt.CustomContextMenu)
        self.phrase_tabs.tabBar().customContextMenuRequested.connect(self.show_tab_context_menu)
        self.phrase_tabs.setTabsClosable(False)
        self.folders_widget.folders_changed.connect(self.update_current_table_folders)
        self.general_folders.folders_changed.connect(self.update_all_tables_global_folders)
        self.folders_widget.phrases_back.connect(
            lambda selected, is_move: self.on_phrases_back(selected, is_move, False))
        self.general_folders.phrases_back.connect(
            lambda selected, is_move: self.on_phrases_back(selected, is_move, True))
        QApplication.instance().installEventFilter(self)

    def setup_ui(self):
        self.setWindowTitle("PhraseTools - SEO Tools [Licensed]")
        self.setGeometry(100, 100, 1400, 900)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        central_widget.setLayout(main_layout)

        self.toolbar_widget = QWidget()
        self.toolbar_widget.setStyleSheet("""
            QWidget {
                background-color: #f2f2f7;
                border-bottom: 1px solid #c7c7cc;
            }
        """)
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(10, 5, 10, 5)
        toolbar_layout.setSpacing(8)

        self.settings_btn = QToolButton()
        self.settings_btn.setObjectName("settingsToolbarButton")
        self.settings_btn.setToolTip("Настройки")
        self.settings_btn.setText("⚙")
        self.settings_btn.setFont(QFont("Arial", 15, QFont.Bold))
        self.settings_btn.setFixedSize(34, 30)
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.setPopupMode(QToolButton.InstantPopup)
        self._build_settings_menu()
        toolbar_layout.addWidget(self.settings_btn)

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

        self.counter_widget = QWidget()
        self.counter_widget.setStyleSheet("""
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
        self.phrase_count_label.setFont(QFont("Arial", 12))
        self.phrase_count_label.setStyleSheet("color: #000000;")
        counter_layout.addWidget(self.phrase_count_label)

        self.filtered_count_label = QLabel("")
        self.filtered_count_label.setFont(QFont("Arial", 12))
        self.filtered_count_label.setStyleSheet("color: #8e8e93;")
        counter_layout.addWidget(self.filtered_count_label)

        self.counter_widget.setLayout(counter_layout)
        toolbar_layout.addWidget(self.counter_widget)

        self.toolbar_widget.setLayout(toolbar_layout)
        self.toolbar_widget.setMaximumHeight(40)
        main_layout.addWidget(self.toolbar_widget)

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

        self.editor_label = QLabel("Фразы")
        self.editor_label.setFont(QFont("Arial", 13, QFont.Bold))
        self.editor_label.setStyleSheet("color: #000000;")
        self.editor_label.setContentsMargins(4, 0, 0, 0)
        self.editor_label.setIndent(2)
        header_layout.addWidget(self.editor_label)

        self.add_btn = AddButton()
        self.add_btn.clicked.connect(self.add_phrase)
        header_layout.addWidget(self.add_btn)

        header_layout.addStretch()
        left_layout.addLayout(header_layout)

        self.phrase_tabs = QTabWidget()
        self.phrase_tabs.setTabBarAutoHide(False)
        self.phrase_tabs.setStyleSheet("""
            QTabWidget::pane {
                background-color: #ffffff;
                border: 1px solid #c7c7cc;
                border-radius: 10px;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #eef0f4;
                color: #2c2c2e;
                font-family: Arial;
                border: 1px solid #c7c7cc;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding-top: 8px;
                padding-bottom: 8px;
                padding-left: 10px;
                padding-right: 10px;
                margin-left: 0px;
                margin-right: 0px;
                min-height: 20px;
                text-align: left;
            }
            QTabBar::tab:hover:!selected {
                background-color: #f7f8fb;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #000000;
                font-weight: 600;
                border-color: #b7bcc6;
            }
        """)

        custom_tab_bar = TabBarWithPlus()
        self.phrase_tabs.setTabBar(custom_tab_bar)
        custom_tab_bar.plus_button.hide()
        custom_tab_bar.close_requested.connect(self.delete_tab)
        self._phrase_tab_bar = custom_tab_bar
        self._phrase_tab_bar.installEventFilter(self)
        self.phrase_tabs.installEventFilter(self)

        self.new_list_plus_btn = QPushButton("+", self.phrase_tabs)
        self.new_list_plus_btn.setObjectName("newListPlusButton")
        self.new_list_plus_btn.setCursor(Qt.PointingHandCursor)
        self.new_list_plus_btn.setFixedSize(24, 24)
        self.new_list_plus_btn.setToolTip("Создать новый список")
        self.new_list_plus_btn.setStyleSheet("""
            QPushButton#newListPlusButton {
                background-color: #ffffff;
                color: #007aff;
                border: 1px solid #c7c7cc;
                border-radius: 12px;
                font-size: 16px;
                font-weight: 700;
                padding: 0px;
            }
            QPushButton#newListPlusButton:hover {
                background-color: #f2f2f7;
            }
            QPushButton#newListPlusButton:pressed {
                background-color: #e5e5ea;
            }
        """)
        self.new_list_plus_btn.clicked.connect(self.create_new_list)
        self.new_list_plus_btn.show()
        self._reposition_phrase_tab_plus()

        left_layout.addWidget(self.phrase_tabs)

        left_panel.setLayout(left_layout)
        splitter.addWidget(left_panel)

        self.tabs = QTabWidget()
        self.tabs.setTabBar(NoClipTabBar(text_left_padding=10, text_right_padding=10))
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #c7c7cc;
                background-color: #ffffff;
                border-radius: 10px;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #eef0f4;
                color: #2c2c2e;
                font-family: Arial;
                border: 1px solid #c7c7cc;
                border-bottom: none;
                padding-top: 7px;
                padding-bottom: 7px;
                padding-left: 10px;
                padding-right: 10px;
                margin-left: 0px;
                margin-right: 0px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                text-align: left;
            }
            QTabBar::tab:hover:!selected {
                background-color: #f7f8fb;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #000000;
                font-weight: 600;
                border-color: #b7bcc6;
            }
        """)

        self.stop_words_widget.stop_words_changed.connect(self.on_stop_words_changed)
        self.tabs.addTab(self.stop_words_widget, "Стоп-слова")

        self.grouping_widget = GroupingWidget()
        self.tabs.addTab(self.grouping_widget, "Группировка")

        self.clustering_widget = ClusteringWidget()
        self.tabs.addTab(self.clustering_widget, "Кластеризация")

        self.folders_widget = FoldersWidget()
        self.tabs.addTab(self.folders_widget, "Папки")

        self.general_tab = QTabWidget()
        self.general_tab.setTabBar(NoClipTabBar(text_left_padding=10, text_right_padding=10))
        self.general_tab.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #d4d7de;
                background-color: #fbfbfd;
                border-radius: 8px;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #f3f4f8;
                color: #4a4a4f;
                font-family: Arial;
                border: 1px solid #d4d7de;
                border-bottom: none;
                padding-top: 6px;
                padding-bottom: 6px;
                padding-left: 10px;
                padding-right: 10px;
                margin-left: 0px;
                margin-right: 0px;
                border-top-left-radius: 7px;
                border-top-right-radius: 7px;
                text-align: left;
            }
            QTabBar::tab:selected {
                background-color: #fbfbfd;
                color: #1f1f21;
                font-weight: 600;
                border-color: #c7ccd6;
            }
        """)
        self.general_stop = StopWordsWidget()
        self.general_stop.stop_words_changed.connect(self.on_global_stop_changed)
        self.general_tab.addTab(self.general_stop, "Стоп-слова")

        self.general_grouping = GroupingWidget()
        self.general_tab.addTab(self.general_grouping, "Группировка")

        self.general_clustering = ClusteringWidget()
        self.general_tab.addTab(self.general_clustering, "Кластеризация")

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
        shortcut_bindings = [
            (QKeySequence(QKeySequence.Undo), self.perform_undo),
            (QKeySequence(QKeySequence.Redo), self.perform_redo),
            (QKeySequence(Qt.CTRL + Qt.SHIFT + Qt.Key_Z), self.perform_redo),
            (QKeySequence(QKeySequence.Find), self.focus_search),
        ]

        for sequence, handler in shortcut_bindings:
            shortcut = QShortcut(sequence, self)
            shortcut.setContext(Qt.ApplicationShortcut)
            shortcut.activated.connect(handler)
            self._shortcuts.append(shortcut)

    def setup_native_menu(self):
        """Настройки в системной строке меню macOS (и обычном menubar на других ОС)."""
        menu_bar = self.menuBar()
        menu_bar.setNativeMenuBar(True)

        self.app_menu = menu_bar.addMenu("PhraseTools")

        self.preferences_action = QAction("Настройки…", self)
        self.preferences_action.setMenuRole(QAction.PreferencesRole)
        self.preferences_action.setShortcut(QKeySequence("Ctrl+,"))
        self.preferences_action.triggered.connect(self.open_settings)
        self.app_menu.addAction(self.preferences_action)

    def perform_undo(self):
        if self._undo_redo_text_focus(redo=False):
            return

        if self._perform_panel_undo_redo(redo=False):
            self.update_phrase_count()
            self.update_grouping_widget()
            self.update_global_grouping()

    def perform_redo(self):
        if self._undo_redo_text_focus(redo=True):
            return

        if self._perform_panel_undo_redo(redo=True):
            self.update_phrase_count()
            self.update_grouping_widget()
            self.update_global_grouping()

    def focus_search(self):
        current_search = self.get_current_search()
        if current_search:
            current_search.search_input.setFocus()

    def _reposition_phrase_tab_plus(self):
        if not hasattr(self, "phrase_tabs") or not hasattr(self, "new_list_plus_btn"):
            return
        tab_bar = self.phrase_tabs.tabBar()
        if tab_bar is None:
            return

        reserve = self.new_list_plus_btn.width() + 10
        desired_bar_width = max(120, self.phrase_tabs.width() - reserve - 4)
        if tab_bar.width() != desired_bar_width:
            tab_bar.setFixedWidth(desired_bar_width)

        x = tab_bar.x() + tab_bar.width() + 4
        max_x = max(6, self.phrase_tabs.width() - self.new_list_plus_btn.width() - 6)
        x = min(max(6, x), max_x)
        y = tab_bar.y() + (tab_bar.height() - self.new_list_plus_btn.height()) // 2
        self.new_list_plus_btn.move(x, y)
        self.new_list_plus_btn.raise_()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and self._handle_global_undo_redo_key(event):
            return True
        if hasattr(self, "_phrase_tab_bar") and obj in (self._phrase_tab_bar, self.phrase_tabs) and event.type() == QEvent.Wheel:
            if self._phrase_tab_bar.scroll_tabs_by_wheel_event(event):
                return True
        if hasattr(self, "_phrase_tab_bar") and obj in (self._phrase_tab_bar, self.phrase_tabs) and event.type() in (
                QEvent.Resize, QEvent.Show, QEvent.LayoutRequest):
            self._reposition_phrase_tab_plus()
        return super().eventFilter(obj, event)

    def _is_descendant_of(self, widget: QWidget, container: QWidget) -> bool:
        current = widget
        while current is not None:
            if current is container:
                return True
            current = current.parentWidget()
        return False

    def _undo_redo_text_focus(self, redo: bool) -> bool:
        focused = QApplication.focusWidget()
        if isinstance(focused, QLineEdit):
            if redo:
                focused.redo()
            else:
                focused.undo()
            return True

        if isinstance(focused, (QTextEdit, QPlainTextEdit)) and not focused.isReadOnly():
            if redo:
                focused.redo()
            else:
                focused.undo()
            return True

        return False

    def _perform_panel_undo_redo(self, redo: bool) -> bool:
        focused = QApplication.focusWidget()
        if focused:
            if self._is_descendant_of(focused, self.stop_words_widget):
                return self.stop_words_widget.redo() if redo else self.stop_words_widget.undo()
            if self._is_descendant_of(focused, self.general_stop):
                return self.general_stop.redo() if redo else self.general_stop.undo()
            if self._is_descendant_of(focused, self.folders_widget):
                return self.folders_widget.redo() if redo else self.folders_widget.undo()
            if self._is_descendant_of(focused, self.general_folders):
                return self.general_folders.redo() if redo else self.general_folders.undo()

        current_table = self.get_current_table()
        if current_table:
            return current_table.redo() if redo else current_table.undo()
        return False

    def _handle_global_undo_redo_key(self, event) -> bool:
        modifiers = event.modifiers()
        has_cmd_or_ctrl = bool(modifiers & (Qt.ControlModifier | Qt.MetaModifier))
        if not has_cmd_or_ctrl:
            return False

        key = event.key()
        text = event.text().lower() if event.text() else ""
        has_shift = bool(modifiers & Qt.ShiftModifier)

        is_undo = (
            not has_shift and
            (key == Qt.Key_Z or text in {"z", "я"})
        )
        is_redo = (
            (has_shift and (key == Qt.Key_Z or text in {"z", "я"})) or
            (key == Qt.Key_Y or text in {"y", "н"})
        )

        if is_undo:
            self.perform_undo()
            return True
        if is_redo:
            self.perform_redo()
            return True
        return False

    def _build_settings_menu(self):
        self.settings_menu = QMenu(self.settings_btn)
        self.settings_menu.setObjectName("settingsToolbarMenu")

        theme_section = self.settings_menu.addSection("Тема")
        theme_section.setEnabled(False)

        self.theme_system_action = self.settings_menu.addAction("Системная")
        self.theme_system_action.setCheckable(True)
        self.theme_system_action.triggered.connect(lambda: self.apply_theme("system"))

        self.theme_light_action = self.settings_menu.addAction("Светлая")
        self.theme_light_action.setCheckable(True)
        self.theme_light_action.triggered.connect(lambda: self.apply_theme("light"))

        self.theme_dark_action = self.settings_menu.addAction("Темная")
        self.theme_dark_action.setCheckable(True)
        self.theme_dark_action.triggered.connect(lambda: self.apply_theme("dark"))

        self.settings_menu.addSeparator()
        self.open_settings_action = self.settings_menu.addAction("Открыть настройки…")
        self.open_settings_action.triggered.connect(self.open_settings)

        self.settings_btn.setMenu(self.settings_menu)
        self._sync_theme_menu_state()

    def _sync_theme_menu_state(self):
        if not hasattr(self, "theme_system_action"):
            return
        self.theme_system_action.setChecked(self.theme_mode == "system")
        self.theme_light_action.setChecked(self.theme_mode == "light")
        self.theme_dark_action.setChecked(self.theme_mode == "dark")

    def _refresh_tab_widget_style(self, tab_widget: QTabWidget):
        if not tab_widget:
            return
        style = tab_widget.style()
        if style:
            style.unpolish(tab_widget)
            style.polish(tab_widget)
        tab_bar = tab_widget.tabBar() if hasattr(tab_widget, "tabBar") else None
        if tab_bar:
            bar_style = tab_bar.style()
            if bar_style:
                bar_style.unpolish(tab_bar)
                bar_style.polish(tab_bar)
            tab_bar.update()
        tab_widget.update()

    def showEvent(self, event):
        super().showEvent(event)
        if not getattr(self, "_theme_post_show_applied", False):
            self._theme_post_show_applied = True
            QTimer.singleShot(0, lambda: self.apply_theme(self.theme_mode))

    def open_settings(self):
        dialog = SettingsDialog(self.theme_mode, self.current_theme, self)
        if dialog.exec_() == QDialog.Accepted:
            self.apply_theme(dialog.selected_theme_mode())

    def _is_system_dark_theme(self) -> bool:
        try:
            if sys.platform == "darwin":
                mode = QSettings("Apple Global Domain", "").value("AppleInterfaceStyle")
                return str(mode).strip().lower() == "dark"
        except Exception:
            pass

        try:
            if sys.platform.startswith("win"):
                import winreg
                with winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER,
                        r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
                ) as key:
                    apps_use_light_theme = winreg.QueryValueEx(key, "AppsUseLightTheme")[0]
                    return int(apps_use_light_theme) == 0
        except Exception:
            pass

        gtk_theme = os.environ.get("GTK_THEME", "")
        if isinstance(gtk_theme, str) and "dark" in gtk_theme.lower():
            return True

        app = QApplication.instance()
        if app:
            return app.palette().color(QPalette.Window).lightness() < 128
        return False

    def _resolve_theme(self) -> str:
        if self.theme_mode == "dark":
            return "dark"
        if self.theme_mode == "light":
            return "light"
        return "dark" if self._is_system_dark_theme() else "light"

    def _build_palette(self, theme: str) -> QPalette:
        palette = QPalette()
        if theme == "dark":
            palette.setColor(QPalette.Window, QColor(22, 22, 24))
            palette.setColor(QPalette.WindowText, QColor(242, 242, 247))
            palette.setColor(QPalette.Base, QColor(28, 28, 30))
            palette.setColor(QPalette.AlternateBase, QColor(36, 36, 40))
            palette.setColor(QPalette.Text, QColor(242, 242, 247))
            palette.setColor(QPalette.Button, QColor(44, 44, 46))
            palette.setColor(QPalette.ButtonText, QColor(242, 242, 247))
            palette.setColor(QPalette.Highlight, QColor(10, 132, 255))
            palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
            palette.setColor(QPalette.ToolTipBase, QColor(44, 44, 46))
            palette.setColor(QPalette.ToolTipText, QColor(242, 242, 247))
            return palette

        palette.setColor(QPalette.Window, QColor(242, 242, 247))
        palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
        palette.setColor(QPalette.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.AlternateBase, QColor(242, 242, 247))
        palette.setColor(QPalette.Text, QColor(0, 0, 0))
        palette.setColor(QPalette.Button, QColor(255, 255, 255))
        palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))
        palette.setColor(QPalette.Highlight, QColor(0, 122, 255))
        palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
        palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
        return palette

    def apply_theme(self, mode: Optional[str] = None):
        if mode in {"light", "dark", "system"}:
            self.theme_mode = mode
        self._sync_theme_menu_state()

        self.current_theme = self._resolve_theme()
        app = QApplication.instance()
        if app:
            app.setPalette(self._build_palette(self.current_theme))

        self.setup_style()
        self._apply_layout_theme()
        self._apply_child_theme()

    def _apply_layout_theme(self):
        is_dark = self.current_theme == "dark"
        if is_dark:
            self.toolbar_widget.setStyleSheet("""
                QWidget {
                    background-color: #1f1f23;
                    border-bottom: 1px solid #4b4b50;
                }
            """)
            self.counter_widget.setStyleSheet("""
                QWidget {
                    background: #2c2c2e;
                    border: 1px solid #4b4b50;
                    border-radius: 6px;
                    padding: 2px 6px;
                }
            """)
            self.phrase_count_label.setStyleSheet("color: #f2f2f7;")
            self.filtered_count_label.setStyleSheet("color: #a1a1a6;")
            self.editor_label.setStyleSheet("color: #f2f2f7;")
            self.status_bar.setStyleSheet("""
                QStatusBar {
                    background-color: #1f1f23;
                    color: #a1a1a6;
                    border-top: 1px solid #4b4b50;
                    font-size: 12px;
                }
            """)
            self.new_list_plus_btn.setStyleSheet("""
                QPushButton#newListPlusButton {
                    background-color: #2c2c2e;
                    color: #4da3ff;
                    border: 1px solid #4b4b50;
                    border-radius: 12px;
                    font-size: 16px;
                    font-weight: 700;
                    padding: 0px;
                }
                QPushButton#newListPlusButton:hover {
                    background-color: #3a3a3c;
                }
                QPushButton#newListPlusButton:pressed {
                    background-color: #48484a;
                }
            """)
            self.phrase_tabs.setStyleSheet("""
                QTabWidget::pane {
                    background-color: #1c1c1e;
                    border: 1px solid #4b4b50;
                    border-radius: 10px;
                    top: -1px;
                }
                QTabBar::tab {
                    background-color: #2c2c2e;
                    color: #b8b8bf;
                    font-family: Arial;
                    border: 1px solid #4b4b50;
                    border-bottom: none;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    padding-top: 8px;
                    padding-bottom: 8px;
                    padding-left: 10px;
                    padding-right: 10px;
                    margin-left: 0px;
                    margin-right: 0px;
                    min-height: 20px;
                    text-align: left;
                }
                QTabBar::tab:hover:!selected {
                    background-color: #3a3a3c;
                }
                QTabBar::tab:selected {
                    background-color: #1c1c1e;
                    color: #f2f2f7;
                    font-weight: 600;
                    border-color: #5a5a60;
                }
            """)
            self.tabs.setStyleSheet("""
                QTabWidget::pane {
                    border: 1px solid #4b4b50;
                    background-color: #1c1c1e;
                    border-radius: 10px;
                    top: -1px;
                }
                QTabBar::tab {
                    background-color: #2c2c2e;
                    color: #b8b8bf;
                    font-family: Arial;
                    border: 1px solid #4b4b50;
                    border-bottom: none;
                    padding-top: 7px;
                    padding-bottom: 7px;
                    padding-left: 10px;
                    padding-right: 10px;
                    margin-left: 0px;
                    margin-right: 0px;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    text-align: left;
                }
                QTabBar::tab:hover:!selected {
                    background-color: #3a3a3c;
                }
                QTabBar::tab:selected {
                    background-color: #1c1c1e;
                    color: #f2f2f7;
                    font-weight: 600;
                    border-color: #5a5a60;
                }
            """)
            self.general_tab.setStyleSheet("""
                QTabWidget::pane {
                    border: 1px solid #4b4b50;
                    background-color: #1a1a1d;
                    border-radius: 8px;
                    top: -1px;
                }
                QTabBar::tab {
                    background-color: #2c2c2e;
                    color: #b8b8bf;
                    font-family: Arial;
                    border: 1px solid #4b4b50;
                    border-bottom: none;
                    padding-top: 6px;
                    padding-bottom: 6px;
                    padding-left: 10px;
                    padding-right: 10px;
                    margin-left: 0px;
                    margin-right: 0px;
                    border-top-left-radius: 7px;
                    border-top-right-radius: 7px;
                    text-align: left;
                }
                QTabBar::tab:selected {
                    background-color: #1a1a1d;
                    color: #f2f2f7;
                    font-weight: 600;
                    border-color: #5a5a60;
                }
            """)
            self._refresh_tab_widget_style(self.phrase_tabs)
            self._refresh_tab_widget_style(self.tabs)
            self._refresh_tab_widget_style(self.general_tab)
            self.add_btn.apply_theme("dark")
            return

        self.toolbar_widget.setStyleSheet("""
            QWidget {
                background-color: #f2f2f7;
                border-bottom: 1px solid #c7c7cc;
            }
        """)
        self.counter_widget.setStyleSheet("""
            QWidget {
                background: #ffffff;
                border: 1px solid #c7c7cc;
                border-radius: 6px;
                padding: 2px 6px;
            }
        """)
        self.phrase_count_label.setStyleSheet("color: #000000;")
        self.filtered_count_label.setStyleSheet("color: #8e8e93;")
        self.editor_label.setStyleSheet("color: #000000;")
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #f2f2f7;
                color: #8e8e93;
                border-top: 1px solid #c7c7cc;
                font-size: 12px;
            }
        """)
        self.new_list_plus_btn.setStyleSheet("""
            QPushButton#newListPlusButton {
                background-color: #ffffff;
                color: #007aff;
                border: 1px solid #c7c7cc;
                border-radius: 12px;
                font-size: 16px;
                font-weight: 700;
                padding: 0px;
            }
            QPushButton#newListPlusButton:hover {
                background-color: #f2f2f7;
            }
            QPushButton#newListPlusButton:pressed {
                background-color: #e5e5ea;
            }
        """)
        self.phrase_tabs.setStyleSheet("""
            QTabWidget::pane {
                background-color: #ffffff;
                border: 1px solid #c7c7cc;
                border-radius: 10px;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #eef0f4;
                color: #2c2c2e;
                font-family: Arial;
                border: 1px solid #c7c7cc;
                border-bottom: none;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding-top: 8px;
                padding-bottom: 8px;
                padding-left: 10px;
                padding-right: 10px;
                margin-left: 0px;
                margin-right: 0px;
                min-height: 20px;
                text-align: left;
            }
            QTabBar::tab:hover:!selected {
                background-color: #f7f8fb;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #000000;
                font-weight: 600;
                border-color: #b7bcc6;
            }
        """)
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #c7c7cc;
                background-color: #ffffff;
                border-radius: 10px;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #eef0f4;
                color: #2c2c2e;
                font-family: Arial;
                border: 1px solid #c7c7cc;
                border-bottom: none;
                padding-top: 7px;
                padding-bottom: 7px;
                padding-left: 10px;
                padding-right: 10px;
                margin-left: 0px;
                margin-right: 0px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                text-align: left;
            }
            QTabBar::tab:hover:!selected {
                background-color: #f7f8fb;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #000000;
                font-weight: 600;
                border-color: #b7bcc6;
            }
        """)
        self.general_tab.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #d4d7de;
                background-color: #fbfbfd;
                border-radius: 8px;
                top: -1px;
            }
            QTabBar::tab {
                background-color: #f3f4f8;
                color: #4a4a4f;
                font-family: Arial;
                border: 1px solid #d4d7de;
                border-bottom: none;
                padding-top: 6px;
                padding-bottom: 6px;
                padding-left: 10px;
                padding-right: 10px;
                margin-left: 0px;
                margin-right: 0px;
                border-top-left-radius: 7px;
                border-top-right-radius: 7px;
                text-align: left;
            }
            QTabBar::tab:selected {
                background-color: #fbfbfd;
                color: #1f1f21;
                font-weight: 600;
                border-color: #c7ccd6;
            }
        """)
        self._refresh_tab_widget_style(self.phrase_tabs)
        self._refresh_tab_widget_style(self.tabs)
        self._refresh_tab_widget_style(self.general_tab)
        self.add_btn.apply_theme("light")

    def _apply_child_theme(self):
        theme = self.current_theme
        for btn in (
                self.load_btn,
                self.save_btn,
                self.save_session_btn,
                self.save_as_session_btn,
                self.load_session_btn
        ):
            if hasattr(btn, "apply_theme"):
                btn.apply_theme(theme)

        for panel in (
                self.stop_words_widget,
                self.grouping_widget,
                self.clustering_widget,
                self.folders_widget,
                self.general_stop,
                self.general_grouping,
                self.general_clustering,
                self.general_folders
        ):
            if hasattr(panel, "apply_theme"):
                panel.apply_theme(theme)

        for i in range(self.phrase_tabs.count()):
            tab = self.phrase_tabs.widget(i)
            if not tab:
                continue
            if hasattr(tab.search_widget, "apply_theme"):
                tab.search_widget.apply_theme(theme)
            if hasattr(tab.table, "apply_theme"):
                tab.table.apply_theme(theme)

    def setup_style(self):
        if self.current_theme == "dark":
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #161618;
                    color: #f2f2f7;
                }
                QDialog {
                    background-color: #1c1c1e;
                    color: #f2f2f7;
                }
                QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
                    background-color: #1c1c1e;
                    color: #f2f2f7;
                    border: 1px solid #4b4b50;
                    border-radius: 8px;
                    padding: 6px 8px;
                    selection-background-color: #0a84ff;
                    selection-color: #ffffff;
                }
                QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {
                    border: 1px solid #0a84ff;
                }
                QPushButton {
                    background-color: #2c2c2e;
                    color: #4da3ff;
                    border: 1px solid #4b4b50;
                    border-radius: 8px;
                    padding: 6px 12px;
                    font-weight: 600;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #3a3a3c;
                }
                QPushButton:pressed {
                    background-color: #48484a;
                }
                QPushButton:disabled {
                    color: #8e8e93;
                    background-color: #2a2a2d;
                    border-color: #404045;
                }
                QToolButton#settingsToolbarButton {
                    background-color: #2c2c2e;
                    color: #4da3ff;
                    border: 1px solid #4b4b50;
                    border-radius: 15px;
                    padding: 0px;
                    font-size: 16px;
                    font-weight: 700;
                    min-width: 30px;
                    min-height: 30px;
                }
                QToolButton#settingsToolbarButton:hover {
                    background-color: #3a3a3c;
                }
                QToolButton#settingsToolbarButton:pressed {
                    background-color: #48484a;
                }
                QToolButton#settingsToolbarButton::menu-indicator {
                    image: none;
                    width: 0px;
                }
                QInputDialog QLabel {
                    color: #f2f2f7;
                }
                QInputDialog QLineEdit, QInputDialog QTextEdit, QInputDialog QPlainTextEdit {
                    background-color: #1c1c1e;
                    color: #f2f2f7;
                }
                QMenu {
                    background-color: #2c2c2e;
                    color: #f2f2f7;
                    border: 1px solid #4b4b50;
                }
                QMenu::item:selected {
                    background-color: #3a3a3c;
                }
                QMenu#settingsToolbarMenu {
                    background-color: #2c2c2e;
                    color: #f2f2f7;
                    border: 1px solid #4b4b50;
                    border-radius: 10px;
                    padding: 6px;
                }
                QMenu#settingsToolbarMenu::item {
                    padding: 7px 18px;
                    border-radius: 6px;
                }
                QMenu#settingsToolbarMenu::item:selected {
                    background-color: #3a3a3c;
                }
                QMenu#settingsToolbarMenu::separator {
                    height: 1px;
                    background: #4b4b50;
                    margin: 6px 4px;
                }
            """)
            return

        self.setStyleSheet("""
            QMainWindow {
                background-color: #f2f2f7;
                color: #000000;
            }
            QDialog {
                background-color: #f2f2f7;
                color: #000000;
            }
            QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #c7c7cc;
                border-radius: 8px;
                padding: 6px 8px;
                selection-background-color: #007aff;
                selection-color: #ffffff;
            }
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {
                border: 1px solid #007aff;
            }
            QPushButton {
                background-color: #ffffff;
                color: #007aff;
                border: 1px solid #c7c7cc;
                border-radius: 8px;
                padding: 6px 12px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #f2f2f7;
            }
            QPushButton:pressed {
                background-color: #e5e5ea;
            }
            QPushButton:disabled {
                color: #8e8e93;
                background-color: #f2f2f7;
                border-color: #d1d1d6;
            }
            QToolButton#settingsToolbarButton {
                background-color: #ffffff;
                color: #007aff;
                border: 1px solid #c7c7cc;
                border-radius: 15px;
                padding: 0px;
                font-size: 16px;
                font-weight: 700;
                min-width: 30px;
                min-height: 30px;
            }
            QToolButton#settingsToolbarButton:hover {
                background-color: #f2f2f7;
            }
            QToolButton#settingsToolbarButton:pressed {
                background-color: #e5e5ea;
            }
            QToolButton#settingsToolbarButton::menu-indicator {
                image: none;
                width: 0px;
            }
            QInputDialog QLabel {
                color: #000000;
            }
            QInputDialog QLineEdit, QInputDialog QTextEdit, QInputDialog QPlainTextEdit {
                background-color: #ffffff;
                color: #000000;
            }
            QMenu#settingsToolbarMenu {
                background-color: #ffffff;
                color: #111114;
                border: 1px solid #cfd3dc;
                border-radius: 10px;
                padding: 6px;
            }
            QMenu#settingsToolbarMenu::item {
                padding: 7px 18px;
                border-radius: 6px;
            }
            QMenu#settingsToolbarMenu::item:selected {
                background-color: #edf3ff;
            }
            QMenu#settingsToolbarMenu::separator {
                height: 1px;
                background: #d8dce5;
                margin: 6px 4px;
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
            self.update_phrase_count()
            self._reposition_phrase_tab_plus()

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
        if current_tab.table.history.current_index < 0:
            current_tab.table.history.set_initial_state(current_tab.table.current_data)
        current_tab.table.set_stop_words(current_list.stop_words | self.global_stop_words)
        current_tab.table.set_folders(current_list.folders)
        current_tab.table.set_global_folders(self.global_folders)
        self.update_grouping_widget()
        self.update_global_grouping()
        self.update_phrase_count()

    def on_side_tab_changed(self, index: int):
        current_widget = self.tabs.widget(index)
        if current_widget is self.clustering_widget:
            self.update_grouping_widget()
            return
        if current_widget is self.general_tab and self.general_tab.currentWidget() is self.general_clustering:
            self.update_global_grouping()

    def on_general_tab_changed(self, index: int):
        if self.tabs.currentWidget() is not self.general_tab:
            return
        if self.general_tab.widget(index) is self.general_clustering:
            self.update_global_grouping()

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
            phrases_text, ok = QInputDialog.getMultiLineText(
                self,
                "Добавить фразы",
                "Введите фразы (каждая с новой строки):"
            )
            if ok and phrases_text:
                phrases = [line.strip() for line in phrases_text.splitlines() if line.strip()]
                if not phrases:
                    return

                current_table = current_tab.table
                updated_data = current_table.current_data + [(phrase, 0) for phrase in phrases]
                if current_table.apply_data_change(updated_data):
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
                phrases_set = set(p.lower().strip() for p, f in phrases)
                updated_data = [(p, f) for p, f in current_table.current_data if
                                p.lower().strip() not in phrases_set]
                if current_table.apply_data_change(updated_data):
                    current_list = self.get_current_phrase_list()
                    if current_list:
                        current_list.phrases = current_table.current_data
                    self.update_phrase_count()
                    self.update_grouping_widget()
                    self.update_global_grouping()

    def on_phrases_back(self, selected: List[Tuple[str, str, int]], is_move: bool, is_global: bool):
        current_table = self.get_current_table()
        if current_table:
            existing = {p.lower().strip() for p, f in current_table.current_data}
            updated_data = current_table.current_data.copy()
            for _, phrase, freq in selected:
                if phrase.lower().strip() not in existing:
                    updated_data.append((phrase, freq))
                    existing.add(phrase.lower().strip())
            current_table.apply_data_change(updated_data)
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

    def create_new_list(self):
        name, ok = QInputDialog.getText(self, "Новый список", "Введите название списка:")
        if ok and name:
            if name in self.phrase_lists:
                QMessageBox.warning(self, "Ошибка", "Список с таким именем уже существует")
                return
            self.create_new_tab(name)
            current_tab = [tab for tab in [self.phrase_tabs.widget(i) for i in range(self.phrase_tabs.count())] if tab.name == name][0]
            if current_tab:
                current_list = self.phrase_lists[name]
                current_tab.table.load_data([])
                current_tab.table.set_stop_words(current_list.stop_words | self.global_stop_words)
                self.phrase_tabs.setCurrentWidget(current_tab)
                self.update_phrase_count()
                self.update_grouping_widget()
                self.update_global_grouping()
                self.status_bar.showMessage(f"Создан новый пустой список: {name}")

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
        if self.get_current_tab() is tab:
            self.update_phrase_count()
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
        if not current_table:
            self.phrase_count_label.setText("Фраз: 0")
            self.filtered_count_label.setText("")
            return

        total = len(current_table.current_data)
        self.phrase_count_label.setText(f"Фраз: {total}")

        filtered = current_table.rowCount()
        if filtered != total:
            self.filtered_count_label.setText(f"(после фильтра: {filtered})")
        else:
            self.filtered_count_label.setText("")

    def on_table_view_changed(self, tab: PhraseTab):
        if self.get_current_tab() is tab:
            self.update_phrase_count()

    def on_table_data_changed(self, tab: PhraseTab):
        if tab and tab.name in self.phrase_lists:
            self.phrase_lists[tab.name].phrases = tab.table.get_current_data()

        if self.get_current_tab() is tab:
            self.update_phrase_count()
            self.update_grouping_widget()
            self.update_global_grouping()
        else:
            self.update_global_grouping()

    def update_grouping_widget(self):
        # Синхронизируем текущую вкладку для актуальных данных
        self.sync_current_tab()

        current_tab = self.get_current_tab()
        if current_tab:
            current_list = self.phrase_lists[current_tab.name]
            filtered = PhraseProcessor.filter_by_stop_words(current_list.phrases,
                                                            current_list.stop_words | self.global_stop_words)
            self.grouping_widget.update_groups(filtered)
            if (
                    hasattr(self, "clustering_widget")
                    and self.clustering_widget
                    and hasattr(self, "tabs")
                    and self.tabs.currentWidget() is self.clustering_widget
            ):
                self.clustering_widget.update_clusters(filtered)

    def update_global_grouping(self):
        # Синхронизируем текущую вкладку для актуальных данных
        self.sync_current_tab()

        all_phrases = self.get_all_phrases()
        filtered = PhraseProcessor.filter_by_stop_words(all_phrases, self.global_stop_words)
        self.general_grouping.update_groups(filtered)
        if (
                hasattr(self, "general_clustering")
                and self.general_clustering
                and hasattr(self, "tabs")
                and hasattr(self, "general_tab")
                and self.tabs.currentWidget() is self.general_tab
                and self.general_tab.currentWidget() is self.general_clustering
        ):
            self.general_clustering.update_clusters(filtered)

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
                    tab.table.table_view_changed.connect(lambda tb=tab: self.on_table_view_changed(tb))
                    tab.table.table_data_changed.connect(lambda tb=tab: self.on_table_data_changed(tb))
                    self.phrase_tabs.addTab(tab, name)
                    tab.table.load_data(pl.phrases)
                    tab.table.history = pl.history
                    if tab.table.history.current_index < 0:
                        tab.table.history.set_initial_state(tab.table.current_data)
                    tab.table.set_stop_words(pl.stop_words | self.global_stop_words)
                    tab.table.set_folders(pl.folders)
                    tab.table.set_global_folders(self.global_folders)
                self.general_stop.load_stop_words(self.global_stop_words)
                self.general_folders.load_folders(self.global_folders)
                self.update_global_grouping()
                self._reposition_phrase_tab_plus()
                self.apply_theme(self.theme_mode)
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
        phrase_list.history.set_initial_state([])
        self.phrase_lists[name] = phrase_list

        tab = PhraseTab()
        tab.name = name
        tab.search_widget.search_changed.connect(lambda t, o, e: self.on_search_changed(tab, t, o, e))
        tab.search_widget.prev_btn.clicked.connect(lambda: self.prev_search(tab))
        tab.search_widget.next_btn.clicked.connect(lambda: self.next_search(tab))
        tab.table.phrases_to_folder.connect(
            lambda fn, phrases, is_global, is_move: self.on_phrases_to_folder(fn, phrases, is_global, is_move))
        tab.table.table_view_changed.connect(lambda: self.on_table_view_changed(tab))
        tab.table.table_data_changed.connect(lambda: self.on_table_data_changed(tab))

        self.phrase_tabs.addTab(tab, name)
        if hasattr(tab.search_widget, "apply_theme"):
            tab.search_widget.apply_theme(self.current_theme)
        if hasattr(tab.table, "apply_theme"):
            tab.table.apply_theme(self.current_theme)
        self._reposition_phrase_tab_plus()

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

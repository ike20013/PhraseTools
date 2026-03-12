#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PhraseTools License Key Generator
Генератор лицензионных ключей для разработчика
"""

import sys
import json
import base64
import hashlib
from datetime import datetime
from pathlib import Path

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QLineEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QFileDialog,
    QGroupBox, QSpinBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPalette, QColor


class LicenseKeyGenerator:
    """Генератор лицензионных ключей"""

    def __init__(self):
        self.secret = "SuperSecretKey2024PhraseTools"
        self.generated_keys = []

    def decode_device_info(self, encoded_info: str) -> dict:
        """Декодирование информации об устройстве"""
        try:
            # Убираем форматирование
            clean_encoded = encoded_info.replace("=== DEVICE INFO START ===", "")
            clean_encoded = clean_encoded.replace("=== DEVICE INFO END ===", "")
            clean_encoded = clean_encoded.replace("\n", "").strip()

            # Декодируем из base64
            decoded = base64.b64decode(clean_encoded.encode()).decode()
            return json.loads(decoded)
        except Exception as e:
            raise ValueError(f"Ошибка декодирования: {str(e)}")

    def generate_key_for_hardware(self, hardware_id: str) -> str:
        """Генерация ключа для конкретного hardware_id"""
        combined = f"{hardware_id}{self.secret}"

        # Многоуровневое хеширование (должно совпадать с основной программой)
        hash1 = hashlib.sha256(combined.encode()).hexdigest()
        hash2 = hashlib.sha512(f"{hash1}{self.secret}".encode()).hexdigest()
        hash3 = hashlib.sha256(f"{hash2}{hardware_id}".encode()).hexdigest()

        # Форматируем ключ в читаемый вид
        key = hash3[:16].upper()
        formatted_key = '-'.join([key[i:i + 4] for i in range(0, 16, 4)])

        return formatted_key

    def generate_from_device_info(self, device_info_text: str) -> dict:
        """Генерация ключа из информации об устройстве"""
        device_info = self.decode_device_info(device_info_text)
        hardware_id = device_info.get('hardware_id')

        if not hardware_id:
            raise ValueError("Hardware ID не найден в информации об устройстве")

        license_key = self.generate_key_for_hardware(hardware_id)

        result = {
            "license_key": license_key,
            "hardware_id": hardware_id,
            "device_info": device_info,
            "generated_at": datetime.now().isoformat(),
            "hostname": device_info.get('hostname', 'unknown'),
            "platform": device_info.get('platform', 'unknown')
        }

        self.generated_keys.append(result)
        return result

    def export_keys(self, filepath: str):
        """Экспорт сгенерированных ключей"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.generated_keys, f, indent=2, ensure_ascii=False)

    def import_keys(self, filepath: str):
        """Импорт ранее сгенерированных ключей"""
        with open(filepath, 'r', encoding='utf-8') as f:
            self.generated_keys = json.load(f)
        return self.generated_keys


class GeneratorWindow(QMainWindow):
    """Главное окно генератора лицензий"""

    def __init__(self):
        super().__init__()
        self.generator = LicenseKeyGenerator()
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("PhraseTools License Generator")
        self.setGeometry(100, 100, 900, 700)

        # Установка стиля
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #0084ff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #0066cc;
            }
            QPushButton:pressed {
                background-color: #004499;
            }
            QTextEdit {
                font-family: monospace;
                font-size: 11px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 5px;
            }
            QLineEdit {
                padding: 5px;
                border: 1px solid #cccccc;
                border-radius: 4px;
                font-size: 12px;
            }
            QTableWidget {
                background-color: white;
                gridline-color: #dddddd;
                font-size: 11px;
            }
            QTableWidget::item:selected {
                background-color: #0084ff;
                color: white;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        central_widget.setLayout(main_layout)

        # Заголовок
        title = QLabel("Генератор лицензионных ключей PhraseTools")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Группа ввода
        input_group = QGroupBox("Информация об устройстве")
        input_layout = QVBoxLayout()

        input_label = QLabel("Вставьте информацию об устройстве от пользователя:")
        input_layout.addWidget(input_label)

        self.device_info_input = QTextEdit()
        self.device_info_input.setPlaceholderText(
            "=== DEVICE INFO START ===\n"
            "...\n"
            "=== DEVICE INFO END ==="
        )
        self.device_info_input.setMaximumHeight(150)
        input_layout.addWidget(self.device_info_input)

        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)

        # Кнопка генерации
        generate_btn = QPushButton("Сгенерировать ключ")
        generate_btn.clicked.connect(self.generate_key)
        generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #34c759;
                font-size: 14px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #2ca345;
            }
        """)
        main_layout.addWidget(generate_btn)

        # Группа результата
        result_group = QGroupBox("Сгенерированный ключ")
        result_layout = QVBoxLayout()

        self.result_label = QLabel("Лицензионный ключ появится здесь")
        self.result_label.setFont(QFont("monospace", 14, QFont.Bold))
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 2px solid #0084ff;
                border-radius: 4px;
                padding: 10px;
                color: #0084ff;
            }
        """)
        result_layout.addWidget(self.result_label)

        # Информация об устройстве
        self.device_details = QLabel("")
        self.device_details.setWordWrap(True)
        self.device_details.setStyleSheet("color: #666666; font-size: 11px;")
        result_layout.addWidget(self.device_details)

        # Кнопка копирования
        copy_btn = QPushButton("Копировать ключ")
        copy_btn.clicked.connect(self.copy_key)
        result_layout.addWidget(copy_btn)

        result_group.setLayout(result_layout)
        main_layout.addWidget(result_group)

        # История ключей
        history_group = QGroupBox("История сгенерированных ключей")
        history_layout = QVBoxLayout()

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels([
            "Ключ", "Hostname", "Платформа", "Дата"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        history_layout.addWidget(self.history_table)

        # Кнопки управления историей
        history_buttons = QHBoxLayout()

        export_btn = QPushButton("Экспорт истории")
        export_btn.clicked.connect(self.export_history)
        history_buttons.addWidget(export_btn)

        import_btn = QPushButton("Импорт истории")
        import_btn.clicked.connect(self.import_history)
        history_buttons.addWidget(import_btn)

        clear_btn = QPushButton("Очистить")
        clear_btn.clicked.connect(self.clear_history)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff3b30;
            }
            QPushButton:hover {
                background-color: #cc2e26;
            }
        """)
        history_buttons.addWidget(clear_btn)

        history_layout.addLayout(history_buttons)

        history_group.setLayout(history_layout)
        main_layout.addWidget(history_group)

        # Информация для разработчика
        info_label = QLabel(
            "⚠️ ВНИМАНИЕ: Храните этот генератор в безопасности!\n"
            "Каждый ключ привязан к конкретному устройству и будет работать только на нем."
        )
        info_label.setStyleSheet("""
            QLabel {
                background-color: #fff3cd;
                border: 1px solid #ffc107;
                border-radius: 4px;
                padding: 8px;
                color: #856404;
                font-size: 11px;
            }
        """)
        main_layout.addWidget(info_label)

    def generate_key(self):
        """Генерация ключа из введенной информации"""
        device_info_text = self.device_info_input.toPlainText().strip()

        if not device_info_text:
            QMessageBox.warning(self, "Ошибка", "Введите информацию об устройстве")
            return

        try:
            result = self.generator.generate_from_device_info(device_info_text)

            # Отображаем ключ
            self.result_label.setText(result['license_key'])
            self.result_label.setStyleSheet("""
                QLabel {
                    background-color: #d4f4dd;
                    border: 2px solid #34c759;
                    border-radius: 4px;
                    padding: 10px;
                    color: #1d5e2e;
                }
            """)

            # Отображаем детали
            self.device_details.setText(
                f"Hardware ID: {result['hardware_id'][:16]}...\n"
                f"Hostname: {result['hostname']}\n"
                f"Platform: {result['platform']}\n"
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

            # Добавляем в историю
            self.update_history_table()

            # Копируем в буфер обмена автоматически
            clipboard = QApplication.clipboard()
            clipboard.setText(result['license_key'])

            QMessageBox.information(self, "Успех",
                                    "Ключ сгенерирован и скопирован в буфер обмена!")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сгенерировать ключ:\n{str(e)}")

    def copy_key(self):
        """Копирование ключа в буфер обмена"""
        key_text = self.result_label.text()
        if key_text and key_text != "Лицензионный ключ появится здесь":
            clipboard = QApplication.clipboard()
            clipboard.setText(key_text)
            QMessageBox.information(self, "Скопировано", "Ключ скопирован в буфер обмена")

    def update_history_table(self):
        """Обновление таблицы истории"""
        self.history_table.setRowCount(len(self.generator.generated_keys))

        for i, key_info in enumerate(self.generator.generated_keys):
            self.history_table.setItem(i, 0, QTableWidgetItem(key_info['license_key']))
            self.history_table.setItem(i, 1, QTableWidgetItem(key_info.get('hostname', 'unknown')))
            self.history_table.setItem(i, 2, QTableWidgetItem(key_info.get('platform', 'unknown')))

            date_str = key_info.get('generated_at', '')
            if date_str:
                try:
                    date = datetime.fromisoformat(date_str)
                    date_str = date.strftime('%Y-%m-%d %H:%M')
                except:
                    pass
            self.history_table.setItem(i, 3, QTableWidgetItem(date_str))

    def export_history(self):
        """Экспорт истории в файл"""
        if not self.generator.generated_keys:
            QMessageBox.warning(self, "Предупреждение", "История пуста")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить историю ключей",
            f"phrasetools_keys_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON файлы (*.json)"
        )

        if filepath:
            try:
                self.generator.export_keys(filepath)
                QMessageBox.information(self, "Успех", f"История сохранена в {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {str(e)}")

    def import_history(self):
        """Импорт истории из файла"""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Загрузить историю ключей",
            "",
            "JSON файлы (*.json)"
        )

        if filepath:
            try:
                self.generator.import_keys(filepath)
                self.update_history_table()
                QMessageBox.information(self, "Успех", f"Загружено {len(self.generator.generated_keys)} ключей")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить: {str(e)}")

    def clear_history(self):
        """Очистка истории"""
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите очистить всю историю?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.generator.generated_keys = []
            self.history_table.setRowCount(0)


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = GeneratorWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import StringProperty, ListProperty
from kivy.metrics import dp
from kivy.graphics import Color, Line, Ellipse

from kivymd.app import MDApp
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRectangleFlatIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.toast import toast

import json
import os
import uuid
import re
from datetime import date, timedelta


def get_data_file():
    try:
        app = MDApp.get_running_app()
        user_dir = app.user_data_dir
    except Exception:
        user_dir = "."
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    return os.path.join(user_dir, "trainings.json")


# Словарь названий месяцев на русском (именительный и родительный падежи + сокращения)
MONTH_NAMES = {
    "январь": 1, "января": 1, "янв": 1, "01": 1, "1": 1,
    "февраль": 2, "февраля": 2, "фев": 2, "02": 2, "2": 2,
    "март": 3, "марта": 3, "мар": 3, "03": 3, "3": 3,
    "апрель": 4, "апреля": 4, "апр": 4, "04": 4, "4": 4,
    "май": 5, "мая": 5, "05": 5, "5": 5,
    "июнь": 6, "июня": 6, "июн": 6, "06": 6, "6": 6,
    "июль": 7, "июля": 7, "июл": 7, "07": 7, "7": 7,
    "август": 8, "августа": 8, "авг": 8, "08": 8, "8": 8,
    "сентябрь": 9, "сентября": 9, "сен": 9, "сент": 9, "09": 9, "9": 9,
    "октябрь": 10, "октября": 10, "окт": 10, "10": 10,
    "ноябрь": 11, "ноября": 11, "ноя": 11, "11": 11,
    "декабрь": 12, "декабря": 12, "дек": 12, "12": 12,
}

MONTH_DISPLAY = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля",
    5: "мая", 6: "июня", 7: "июля", 8: "августа",
    9: "сентября", 10: "октября", 11: "ноября", 12: "декабря",
}


def parse_month(text):
    """Принимает строку (цифра или название месяца) и возвращает номер месяца (1-12) или None."""
    if text is None:
        return None
    key = text.strip().lower()
    if key in MONTH_NAMES:
        return MONTH_NAMES[key]
    # Попробуем как число без ведущих нулей
    try:
        num = int(key)
        if 1 <= num <= 12:
            return num
    except ValueError:
        pass
    return None


def parse_exercise(description):
    """
    Извлекает числовой показатель и нормализованное название упражнения из описания.
    Например: "20 отжиманий" -> ("отжиманий", 20.0)
              "прыгать 30 раз" -> ("прыгать", 30.0)
    Возвращает (название, значение) или (None, None), если число не найдено.
    """
    if not description:
        return None, None

    match = re.search(r'(\d+(?:[.,]\d+)?)', description)
    if not match:
        return None, None

    value_str = match.group(1).replace(',', '.')
    try:
        value = float(value_str)
    except ValueError:
        return None, None

    name_part = description[:match.start()] + " " + description[match.end():]
    name_part = name_part.lower()
    # убираем слово "раз"/"раза"/"разок" и т.п., оно не несёт смысловой нагрузки
    name_part = re.sub(r'\bраз\w*\b', '', name_part)
    name_part = re.sub(r'\s+', ' ', name_part).strip(" .,!;:-")

    if not name_part:
        name_part = "показатель"

    return name_part, value


def collect_exercise_points(app_data, start_date, end_date):
    """
    Проходит по всем датам и тренировкам, извлекает числовые показатели
    и группирует их по названию упражнения в пределах указанного диапазона дат.
    Возвращает словарь {название: [(дата, значение), ...]}, отсортированный по дате.
    """
    groups = {}
    for date_obj in app_data:
        try:
            d = date(date_obj["year"], date_obj["month"], date_obj["day"])
        except (KeyError, ValueError, TypeError):
            continue

        if d < start_date or d > end_date:
            continue

        for task in date_obj.get("tasks", []):
            name, value = parse_exercise(task.get("description", ""))
            if name is None:
                continue
            groups.setdefault(name, []).append((d, value))

    for name in groups:
        groups[name].sort(key=lambda pair: pair[0])

    return groups


KV = '''
#:import dp kivy.metrics.dp

<DateCard>:
    orientation: "vertical"
    size_hint_y: None
    height: dp(70)
    padding: dp(16), dp(10)
    radius: [16, 16, 16, 16]
    elevation: 2
    md_bg_color: app.theme_cls.bg_light if hasattr(app.theme_cls, "bg_light") else (0.95, 0.95, 0.97, 1)
    ripple_behavior: True

    MDBoxLayout:
        orientation: "horizontal"

        MDLabel:
            text: root.date_str
            font_style: "H6"
            valign: "center"
            theme_text_color: "Primary"

        MDIconButton:
            icon: "chevron-right"
            theme_text_color: "Secondary"
            pos_hint: {"center_y": 0.5}


<TaskCard>:
    orientation: "vertical"
    size_hint_y: None
    height: dp(80)
    padding: dp(14), dp(8)
    radius: [16, 16, 16, 16]
    elevation: 2
    md_bg_color: root.card_bg_color

    MDBoxLayout:
        orientation: "horizontal"
        spacing: dp(8)

        MDLabel:
            id: desc_label
            text: root.description
            theme_text_color: "Custom"
            text_color: root.text_color_value
            valign: "center"
            shorten: False

        MDIconButton:
            icon: "check-bold"
            theme_text_color: "Custom"
            text_color: (1, 1, 1, 1) if root.status == "done" else ((0, 0.6, 0, 1) if root.status != "failed" else (1, 1, 1, 0.6))
            on_release: root.toggle_done()

        MDIconButton:
            icon: "close-thick"
            theme_text_color: "Custom"
            text_color: (1, 1, 1, 1) if root.status == "failed" else ((0.8, 0, 0, 1) if root.status != "done" else (1, 1, 1, 0.6))
            on_release: root.toggle_failed()


<DatesScreen>:
    name: "dates_screen"

    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            title: "Мои тренировки"
            elevation: 4
            right_action_items: [["delete", lambda x: root.confirm_clear_all()]]

        ScrollView:
            MDList:
                id: dates_list
                padding: dp(10), dp(10)
                spacing: dp(10)

    MDFloatingActionButton:
        icon: "plus"
        pos_hint: {"right": 0.95, "y": 0.04}
        md_bg_color: app.theme_cls.primary_color
        on_release: root.open_add_date_dialog()

    MDRectangleFlatIconButton:
        icon: "chart-line"
        text: "Показать результат"
        pos_hint: {"x": 0.04, "y": 0.04}
        on_release: root.open_results_screen()


<TasksScreen>:
    name: "tasks_screen"

    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            id: tasks_top_bar
            title: "Тренировки"
            elevation: 4
            left_action_items: [["arrow-left", lambda x: root.go_back()]]

        ScrollView:
            MDList:
                id: tasks_list
                padding: dp(10), dp(10)
                spacing: dp(10)

    MDFloatingActionButton:
        icon: "plus"
        pos_hint: {"right": 0.95, "y": 0.04}
        md_bg_color: app.theme_cls.primary_color
        on_release: root.open_add_task_dialog()


<ResultsScreen>:
    name: "results_screen"

    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            title: "Результат прогресса"
            elevation: 4
            left_action_items: [["arrow-left", lambda x: root.go_back()]]

        MDBoxLayout:
            orientation: "horizontal"
            size_hint_y: None
            height: dp(56)
            padding: dp(6), dp(4)
            spacing: dp(4)

            MDFlatButton:
                text: "Неделя"
                on_release: root.set_range_week()

            MDFlatButton:
                text: "Месяц"
                on_release: root.set_range_month()

            MDFlatButton:
                text: "Всё время"
                on_release: root.set_range_all_time()

            MDFlatButton:
                text: "Свой период"
                on_release: root.open_custom_range_dialog()

        ScrollView:
            MDBoxLayout:
                id: results_container
                orientation: "vertical"
                spacing: dp(16)
                padding: dp(14), dp(14)
                size_hint_y: None
                height: self.minimum_height
'''


class DateCard(MDCard):
    date_str = StringProperty("")
    date_id = StringProperty("")

    def on_release(self):
        pass


class TaskCard(MDCard):
    description = StringProperty("")
    task_id = StringProperty("")
    status = StringProperty("pending")
    text_color_value = ListProperty([0, 0, 0, 1])
    card_bg_color = ListProperty([0.95, 0.95, 0.97, 1])

    DEFAULT_BG = (0.95, 0.95, 0.97, 1)
    DONE_BG = (0.20, 0.70, 0.32, 1)      # зелёный фон всей карточки
    FAILED_BG = (0.85, 0.20, 0.20, 1)    # красный фон всей карточки

    def update_colors(self):
        app = MDApp.get_running_app()
        if self.status == "done":
            self.card_bg_color = self.DONE_BG
            self.text_color_value = (1, 1, 1, 1)
        elif self.status == "failed":
            self.card_bg_color = self.FAILED_BG
            self.text_color_value = (1, 1, 1, 1)
        else:
            self.card_bg_color = self.DEFAULT_BG
            self.text_color_value = app.theme_cls.text_color

    def toggle_done(self):
        if self.status == "done":
            self.status = "pending"
        else:
            self.status = "done"
        self.update_colors()
        screen = MDApp.get_running_app().sm.get_screen("tasks_screen")
        screen.update_task_status(self.task_id, self.status)

    def toggle_failed(self):
        if self.status == "failed":
            self.status = "pending"
        else:
            self.status = "failed"
        self.update_colors()
        screen = MDApp.get_running_app().sm.get_screen("tasks_screen")
        screen.update_task_status(self.task_id, self.status)


class LineChartWidget(FloatLayout):
    """
    Простой линейный график прогресса по одному упражнению.
    Рисуется вручную на canvas — без сторонних библиотек (важно для сборки APK).
    Цвет линии: зелёный — рост, красный — спад, синий — без изменений.
    """

    def __init__(self, points, exercise_name, **kwargs):
        # points: список кортежей (datetime.date, значение), отсортированный по дате
        super().__init__(**kwargs)
        self.points = points
        self.exercise_name = exercise_name
        self.size_hint_y = None
        self.height = dp(230)
        self.bind(size=self._redraw, pos=self._redraw)
        self._redraw()

    def _redraw(self, *args):
        self.canvas.after.clear()
        self.clear_widgets()

        if not self.points or self.width == 0:
            return

        values = [p[1] for p in self.points]
        min_val = min(values)
        max_val = max(values)
        if max_val == min_val:
            max_val = min_val + 1

        if self.points[-1][1] > self.points[0][1]:
            line_color = (0.20, 0.70, 0.32, 1)
            trend_text = "Рост"
        elif self.points[-1][1] < self.points[0][1]:
            line_color = (0.85, 0.20, 0.20, 1)
            trend_text = "Спад"
        else:
            line_color = (0.25, 0.45, 0.85, 1)
            trend_text = "Без изменений"

        title_label = MDLabel(
            text="{} — {}".format(self.exercise_name.capitalize(), trend_text),
            size_hint=(1, None),
            height=dp(28),
            pos_hint={"top": 1},
            halign="center",
            bold=True,
        )
        self.add_widget(title_label)

        padding_left = dp(46)
        padding_right = dp(20)
        padding_top = dp(48)
        padding_bottom = dp(36)

        chart_width = self.width - padding_left - padding_right
        chart_height = self.height - padding_top - padding_bottom

        if chart_width <= 0 or chart_height <= 0:
            return

        n = len(self.points)
        step_x = chart_width / (n - 1) if n > 1 else 0

        coords = []
        for i, (d, value) in enumerate(self.points):
            x = self.x + padding_left + (step_x * i if n > 1 else chart_width / 2)
            y_ratio = (value - min_val) / (max_val - min_val)
            y = self.y + padding_bottom + y_ratio * chart_height
            coords.append((x, y))

        with self.canvas.after:
            Color(0.6, 0.6, 0.6, 1)
            Line(
                points=[
                    self.x + padding_left, self.y + padding_bottom,
                    self.x + padding_left, self.y + self.height - padding_top,
                ],
                width=1,
            )
            Line(
                points=[
                    self.x + padding_left, self.y + padding_bottom,
                    self.x + self.width - padding_right, self.y + padding_bottom,
                ],
                width=1,
            )

            Color(*line_color)
            if len(coords) > 1:
                flat_points = []
                for cx, cy in coords:
                    flat_points.extend([cx, cy])
                Line(points=flat_points, width=dp(2))

            for cx, cy in coords:
                Color(*line_color)
                Ellipse(pos=(cx - dp(4), cy - dp(4)), size=(dp(8), dp(8)))

        for i, (d, value) in enumerate(self.points):
            cx, cy = coords[i]
            value_text = str(int(value)) if value == int(value) else str(value)

            val_label = MDLabel(
                text=value_text,
                size_hint=(None, None),
                size=(dp(50), dp(20)),
                pos=(cx - dp(25), cy + dp(6)),
                halign="center",
                font_style="Caption",
            )
            self.add_widget(val_label)

            date_label = MDLabel(
                text=d.strftime("%d.%m"),
                size_hint=(None, None),
                size=(dp(60), dp(20)),
                pos=(cx - dp(30), self.y + dp(4)),
                halign="center",
                font_style="Caption",
            )
            self.add_widget(date_label)


class DatesScreen(Screen):
    dialog = None

    def on_pre_enter(self, *args):
        self.refresh_dates()

    def refresh_dates(self):
        app = MDApp.get_running_app()
        dates_list = self.ids.dates_list
        dates_list.clear_widgets()
        for date_obj in app.data:
            card = DateCard(
                date_str=date_obj["date_str"],
                date_id=date_obj["id"]
            )
            card.bind(on_release=lambda inst, d=date_obj: self.open_tasks_screen(d))
            dates_list.add_widget(card)

    def open_tasks_screen(self, date_obj):
        app = MDApp.get_running_app()
        tasks_screen = app.sm.get_screen("tasks_screen")
        tasks_screen.load_date(date_obj["id"])
        app.sm.current = "tasks_screen"

    def open_results_screen(self):
        app = MDApp.get_running_app()
        app.sm.current = "results_screen"

    def open_add_date_dialog(self):
        content = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            size_hint_y=None,
            height=dp(90),
            padding=(dp(10), dp(10))
        )

        row = MDBoxLayout(orientation="horizontal", spacing=dp(10))

        self.day_field = MDTextField(
            hint_text="ДД",
            input_filter="int",
            max_text_length=2,
        )
        # Поле месяца теперь текстовое: можно ввести "05" или "май"
        self.month_field = MDTextField(
            hint_text="Месяц (05 или май)",
            max_text_length=12,
        )
        self.year_field = MDTextField(
            hint_text="ГГГГ",
            input_filter="int",
            max_text_length=4,
        )

        row.add_widget(self.day_field)
        row.add_widget(self.month_field)
        row.add_widget(self.year_field)
        content.add_widget(row)

        self.dialog = MDDialog(
            title="Добавить дату",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(
                    text="ОТМЕНА",
                    on_release=lambda x: self.dialog.dismiss()
                ),
                MDFlatButton(
                    text="ДОБАВИТЬ",
                    on_release=lambda x: self.add_date()
                ),
            ],
        )
        self.dialog.open()

    def add_date(self):
        day = self.day_field.text.strip()
        month_text = self.month_field.text.strip()
        year = self.year_field.text.strip()

        if not (day and month_text and year):
            toast("Заполните все поля")
            return

        month_i = parse_month(month_text)
        if month_i is None:
            toast("Не удалось распознать месяц")
            return

        try:
            day_i = int(day)
            year_i = int(year)
            if not (1 <= day_i <= 31 and 1900 <= year_i <= 2200):
                toast("Некорректная дата")
                return
        except ValueError:
            toast("Введите корректные числа для дня и года")
            return

        date_str = "{:02d}.{:02d}.{:04d}".format(day_i, month_i, year_i)

        app = MDApp.get_running_app()
        new_date = {
            "id": str(uuid.uuid4()),
            "day": day_i,
            "month": month_i,
            "year": year_i,
            "date_str": date_str,
            "tasks": []
        }
        app.data.append(new_date)
        app.save_data()
        self.dialog.dismiss()
        self.refresh_dates()

    def confirm_clear_all(self):
        self.clear_dialog = MDDialog(
            title="Удалить все данные?",
            text="Это действие удалит все даты и тренировки безвозвратно.",
            buttons=[
                MDFlatButton(
                    text="ОТМЕНА",
                    on_release=lambda x: self.clear_dialog.dismiss()
                ),
                MDFlatButton(
                    text="УДАЛИТЬ",
                    text_color=(0.8, 0, 0, 1),
                    on_release=lambda x: self.clear_all_data()
                ),
            ],
        )
        self.clear_dialog.open()

    def clear_all_data(self):
        app = MDApp.get_running_app()
        app.data = []
        app.save_data()
        self.clear_dialog.dismiss()
        self.refresh_dates()
        toast("Все данные удалены")


class TasksScreen(Screen):
    current_date_id = StringProperty("")
    dialog = None

    def load_date(self, date_id):
        self.current_date_id = date_id
        date_obj = self.find_date_obj()
        if date_obj:
            self.ids.tasks_top_bar.title = "Тренировки {}".format(date_obj["date_str"])
        self.refresh_tasks()

    def find_date_obj(self):
        app = MDApp.get_running_app()
        for d in app.data:
            if d["id"] == self.current_date_id:
                return d
        return None

    def refresh_tasks(self):
        tasks_list = self.ids.tasks_list
        tasks_list.clear_widgets()
        date_obj = self.find_date_obj()
        if not date_obj:
            return
        for task in date_obj["tasks"]:
            card = TaskCard(
                description=task["description"],
                task_id=task["id"],
                status=task["status"]
            )
            card.update_colors()
            tasks_list.add_widget(card)

    def go_back(self):
        app = MDApp.get_running_app()
        app.sm.current = "dates_screen"

    def open_add_task_dialog(self):
        self.task_field = MDTextField(
            hint_text="Описание тренировки",
            multiline=True,
        )

        content = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            size_hint_y=None,
            height=dp(80),
            padding=(dp(10), dp(10))
        )
        content.add_widget(self.task_field)

        self.dialog = MDDialog(
            title="Добавить тренировку",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(
                    text="ОТМЕНА",
                    on_release=lambda x: self.dialog.dismiss()
                ),
                MDFlatButton(
                    text="ДОБАВИТЬ",
                    on_release=lambda x: self.add_task()
                ),
            ],
        )
        self.dialog.open()

    def add_task(self):
        description = self.task_field.text.strip()
        if not description:
            toast("Введите описание")
            return

        app = MDApp.get_running_app()
        date_obj = self.find_date_obj()
        if date_obj is None:
            self.dialog.dismiss()
            return

        new_task = {
            "id": str(uuid.uuid4()),
            "description": description,
            "status": "pending"
        }
        date_obj["tasks"].append(new_task)
        app.save_data()
        self.dialog.dismiss()
        self.refresh_tasks()

    def update_task_status(self, task_id, status):
        app = MDApp.get_running_app()
        date_obj = self.find_date_obj()
        if not date_obj:
            return
        for task in date_obj["tasks"]:
            if task["id"] == task_id:
                task["status"] = status
                break
        app.save_data()


class ResultsScreen(Screen):
    custom_dialog = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.range_start = None
        self.range_end = None

    def on_pre_enter(self, *args):
        if self.range_start is None or self.range_end is None:
            self.set_range_all_time()
        else:
            self.render_charts()

    def go_back(self):
        app = MDApp.get_running_app()
        app.sm.current = "dates_screen"

    def set_range_week(self):
        today = date.today()
        self.range_start = today - timedelta(days=7)
        self.range_end = today
        self.render_charts()

    def set_range_month(self):
        today = date.today()
        self.range_start = today - timedelta(days=30)
        self.range_end = today
        self.render_charts()

    def set_range_all_time(self):
        app = MDApp.get_running_app()
        all_dates = []
        for d_obj in app.data:
            try:
                all_dates.append(date(d_obj["year"], d_obj["month"], d_obj["day"]))
            except (KeyError, ValueError, TypeError):
                continue

        if all_dates:
            self.range_start = min(all_dates)
            self.range_end = max(all_dates)
        else:
            self.range_start = date.today()
            self.range_end = date.today()

        self.render_charts()

    def open_custom_range_dialog(self):
        content = MDBoxLayout(
            orientation="vertical",
            spacing=dp(10),
            size_hint_y=None,
            height=dp(230),
            padding=(dp(10), dp(10)),
        )

        content.add_widget(MDLabel(text="С:", size_hint_y=None, height=dp(20)))
        row1 = MDBoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(48))
        self.start_day = MDTextField(hint_text="ДД", input_filter="int", max_text_length=2)
        self.start_month = MDTextField(hint_text="Месяц (05 или май)", max_text_length=12)
        self.start_year = MDTextField(hint_text="ГГГГ", input_filter="int", max_text_length=4)
        row1.add_widget(self.start_day)
        row1.add_widget(self.start_month)
        row1.add_widget(self.start_year)
        content.add_widget(row1)

        content.add_widget(MDLabel(text="По:", size_hint_y=None, height=dp(20)))
        row2 = MDBoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(48))
        self.end_day = MDTextField(hint_text="ДД", input_filter="int", max_text_length=2)
        self.end_month = MDTextField(hint_text="Месяц (05 или май)", max_text_length=12)
        self.end_year = MDTextField(hint_text="ГГГГ", input_filter="int", max_text_length=4)
        row2.add_widget(self.end_day)
        row2.add_widget(self.end_month)
        row2.add_widget(self.end_year)
        content.add_widget(row2)

        self.custom_dialog = MDDialog(
            title="Свой период",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(text="ОТМЕНА", on_release=lambda x: self.custom_dialog.dismiss()),
                MDFlatButton(text="ПОКАЗАТЬ", on_release=lambda x: self.apply_custom_range()),
            ],
        )
        self.custom_dialog.open()

    def apply_custom_range(self):
        try:
            s_day = int(self.start_day.text.strip())
            s_year = int(self.start_year.text.strip())
            s_month = parse_month(self.start_month.text.strip())

            e_day = int(self.end_day.text.strip())
            e_year = int(self.end_year.text.strip())
            e_month = parse_month(self.end_month.text.strip())

            if s_month is None or e_month is None:
                toast("Не удалось распознать месяц")
                return

            start = date(s_year, s_month, s_day)
            end = date(e_year, e_month, e_day)
        except (ValueError, AttributeError):
            toast("Проверьте корректность введённых дат")
            return

        if start > end:
            start, end = end, start

        self.range_start = start
        self.range_end = end
        self.custom_dialog.dismiss()
        self.render_charts()

    def render_charts(self):
        container = self.ids.results_container
        container.clear_widgets()

        app = MDApp.get_running_app()
        groups = collect_exercise_points(app.data, self.range_start, self.range_end)

        period_label = MDLabel(
            text="Период: {} — {}".format(
                self.range_start.strftime("%d.%m.%Y"),
                self.range_end.strftime("%d.%m.%Y"),
            ),
            size_hint_y=None,
            height=dp(30),
            halign="center",
            bold=True,
        )
        container.add_widget(period_label)

        if not groups:
            container.add_widget(
                MDLabel(
                    text="Нет данных за выбранный период.\nДобавьте тренировки с числом (например, «20 отжиманий»).",
                    size_hint_y=None,
                    height=dp(80),
                    halign="center",
                )
            )
            return

        grown = 0
        declined = 0
        flat = 0

        for name, points in groups.items():
            if len(points) == 1:
                only_value = points[0][1]
                value_text = str(int(only_value)) if only_value == int(only_value) else str(only_value)
                container.add_widget(
                    MDLabel(
                        text="{}: недостаточно данных (только 1 запись — {})".format(
                            name.capitalize(), value_text
                        ),
                        size_hint_y=None,
                        height=dp(40),
                        halign="center",
                    )
                )
                continue

            chart = LineChartWidget(points=points, exercise_name=name)
            container.add_widget(chart)

            if points[-1][1] > points[0][1]:
                grown += 1
            elif points[-1][1] < points[0][1]:
                declined += 1
            else:
                flat += 1

        overall = "Итог: рост — {}, спад — {}, без изменений — {}".format(grown, declined, flat)
        container.add_widget(
            MDLabel(
                text=overall,
                size_hint_y=None,
                height=dp(40),
                bold=True,
                halign="center",
            )
        )


class TrainingApp(MDApp):
    data = []

    def build(self):
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Blue"
        self.load_data()

        self.sm = MDScreenManager()
        Builder.load_string(KV)

        dates_screen = DatesScreen(name="dates_screen")
        tasks_screen = TasksScreen(name="tasks_screen")
        results_screen = ResultsScreen(name="results_screen")

        self.sm.add_widget(dates_screen)
        self.sm.add_widget(tasks_screen)
        self.sm.add_widget(results_screen)
        self.sm.current = "dates_screen"

        return self.sm

    def load_data(self):
        file_path = get_data_file()
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = []
        else:
            self.data = []

    def save_data(self):
        file_path = get_data_file()
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("Ошибка сохранения данных:", e)


if __name__ == "__main__":
    TrainingApp().run()

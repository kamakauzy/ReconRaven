"""Timeline Screen - Activity history visualization"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen


class TimelineScreen(Screen):
    """Timeline visualization screen."""

    def __init__(self, api, **kwargs):
        super().__init__(**kwargs)
        self.api = api
        self._build_ui()

    def _build_ui(self):
        """Build the UI layout."""
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Header
        header = Label(
            text='[b]📊 Activity Timeline[/b]',
            markup=True,
            font_size='24sp',
            size_hint=(1, None),
            height=50
        )
        layout.add_widget(header)

        # Stats summary
        self.stats_label = Label(
            text='Loading statistics...',
            font_size='16sp',
            size_hint=(1, None),
            height=200,
            halign='left',
            valign='top'
        )
        self.stats_label.bind(size=self.stats_label.setter('text_size'))
        layout.add_widget(self.stats_label)

        # Spacer
        layout.add_widget(Label(size_hint=(1, 1)))

        # Time range buttons
        time_box = BoxLayout(orientation='horizontal', size_hint=(1, None), height=60, spacing=10)
        for label, hours in [('1h', 1), ('6h', 6), ('24h', 24), ('7d', 168)]:
            btn = Button(
                text=label,
                font_size='18sp',
                background_color=(0.3, 0.3, 0.3, 1),
                on_press=lambda x, h=hours: self._set_timerange(h)
            )
            time_box.add_widget(btn)
        layout.add_widget(time_box)

        refresh_btn = Button(
            text='Refresh',
            font_size='18sp',
            size_hint=(1, None),
            height=60,
            background_color=(0.2, 0.4, 0.6, 1),
            on_press=lambda x: self.update()
        )
        layout.add_widget(refresh_btn)

        self.add_widget(layout)

    def _set_timerange(self, hours):
        """Set time range for timeline."""
        print(f"Timeline range: {hours} hours")
        self.update()

    def update(self):
        """Update screen data."""
        stats = self.api.get_stats()

        if stats:
            text = (
                f"[b]Database Statistics[/b]\n\n"
                f"Baseline Frequencies: {stats.get('baseline_frequencies', 0)}\n"
                f"Total Detections: {stats.get('total_detections', 0)}\n"
                f"Anomalies: {stats.get('anomalies', 0)}\n"
                f"Identified Devices: {stats.get('identified_devices', 0)}\n"
                f"Transcripts: {stats.get('transcripts', 0)}\n"
                f"Recordings: {stats.get('recordings_count', 0)}\n\n"
                f"[b]Storage[/b]\n"
                f"Database: {stats.get('storage', {}).get('database_mb', 0):.1f} MB\n"
                f"Recordings: {stats.get('storage', {}).get('recordings_mb', 0):.1f} MB\n"
                f"Total: {stats.get('storage', {}).get('total_mb', 0):.1f} MB"
            )
            self.stats_label.text = text
        else:
            self.stats_label.text = '[b]API Disconnected[/b]\n\nCannot retrieve statistics.'


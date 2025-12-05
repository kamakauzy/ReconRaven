"""Signals Screen - Real-time signal monitoring"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView


class SignalsScreen(Screen):
    """Signals monitoring screen."""

    def __init__(self, api, **kwargs):
        super().__init__(**kwargs)
        self.api = api
        self._build_ui()

    def _build_ui(self):
        """Build the UI layout."""
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Header
        header = Label(
            text='[b]🔍 Signal Monitoring[/b]',
            markup=True,
            font_size='24sp',
            size_hint=(1, None),
            height=50,
            color=(1, 1, 1, 1)
        )
        layout.add_widget(header)

        # Status bar
        self.status_label = Label(
            text='Status: Loading...',
            font_size='16sp',
            size_hint=(1, None),
            height=40,
            color=(0.7, 0.7, 0.7, 1)
        )
        layout.add_widget(self.status_label)

        # Scrollable anomaly list
        scroll = ScrollView(size_hint=(1, 1))
        self.anomaly_grid = GridLayout(
            cols=1,
            spacing=5,
            size_hint_y=None
        )
        self.anomaly_grid.bind(minimum_height=self.anomaly_grid.setter('height'))
        scroll.add_widget(self.anomaly_grid)
        layout.add_widget(scroll)

        # Control buttons
        controls = BoxLayout(orientation='horizontal', size_hint=(1, None), height=60, spacing=10)

        self.scan_btn = Button(
            text='Start Scan',
            font_size='18sp',
            background_color=(0.2, 0.6, 0.2, 1),
            on_press=self._toggle_scan
        )
        controls.add_widget(self.scan_btn)

        refresh_btn = Button(
            text='Refresh',
            font_size='18sp',
            background_color=(0.2, 0.2, 0.6, 1),
            on_press=lambda x: self.update()
        )
        controls.add_widget(refresh_btn)

        layout.add_widget(controls)

        self.add_widget(layout)

    def update(self):
        """Update screen data from API."""
        # Get scan status
        status = self.api.get_scan_status()
        if status:
            scanning = status.get('scanning', False)
            self.status_label.text = f"Status: {'Scanning' if scanning else 'Idle'} | Anomalies: {status.get('anomalies_detected', 0)} | Baseline: {status.get('baseline_frequencies', 0)}"
            self.scan_btn.text = 'Stop Scan' if scanning else 'Start Scan'
            self.scan_btn.background_color = (0.6, 0.2, 0.2, 1) if scanning else (0.2, 0.6, 0.2, 1)
        else:
            self.status_label.text = 'Status: API Disconnected'

        # Get anomalies
        anomalies = self.api.get_anomalies(limit=20)

        # Clear grid
        self.anomaly_grid.clear_widgets()

        if not anomalies:
            no_data = Label(
                text='No anomalies detected',
                font_size='18sp',
                size_hint_y=None,
                height=60,
                color=(0.6, 0.6, 0.6, 1)
            )
            self.anomaly_grid.add_widget(no_data)
        else:
            for anomaly in anomalies:
                freq = anomaly.get('frequency', 0) / 1e6  # Convert to MHz
                power = anomaly.get('power', 0)

                btn = Button(
                    text=f"{freq:.3f} MHz - {power:.1f} dB",
                    font_size='18sp',
                    size_hint_y=None,
                    height=60,
                    background_color=(0.3, 0.3, 0.3, 1),
                    on_press=lambda x, f=freq: self._anomaly_selected(f)
                )
                self.anomaly_grid.add_widget(btn)

    def _toggle_scan(self, instance):
        """Toggle scanning on/off."""
        status = self.api.get_scan_status()
        if status and status.get('scanning'):
            self.api.stop_scan()
        else:
            self.api.start_scan()
        self.update()

    def _anomaly_selected(self, frequency):
        """Handle anomaly selection."""
        print(f"Selected anomaly: {frequency} MHz")
        # Could show details dialog here


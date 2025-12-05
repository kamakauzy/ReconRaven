"""Network Screen - Device correlation visualization"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView


class NetworkScreen(Screen):
    """Network analysis screen."""

    def __init__(self, api, **kwargs):
        super().__init__(**kwargs)
        self.api = api
        self._build_ui()

    def _build_ui(self):
        """Build the UI layout."""
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Header
        header = Label(
            text='[b]🕸️ Network Analysis[/b]',
            markup=True,
            font_size='24sp',
            size_hint=(1, None),
            height=50
        )
        layout.add_widget(header)

        # Device list
        scroll = ScrollView(size_hint=(1, 1))
        self.device_grid = GridLayout(
            cols=1,
            spacing=5,
            size_hint_y=None
        )
        self.device_grid.bind(minimum_height=self.device_grid.setter('height'))
        scroll.add_widget(self.device_grid)
        layout.add_widget(scroll)

        self.add_widget(layout)

    def update(self):
        """Update screen data."""
        devices = self.api.get_devices(min_confidence=0.7)

        self.device_grid.clear_widgets()

        if not devices:
            no_data = Label(
                text='No devices identified yet',
                font_size='18sp',
                size_hint_y=None,
                height=60,
                color=(0.6, 0.6, 0.6, 1)
            )
            self.device_grid.add_widget(no_data)
        else:
            for device in devices:
                freq = device.get('frequency', 0) / 1e6 if device.get('frequency') else 0
                device_type = device.get('device_type', 'Unknown')
                confidence = device.get('confidence', 0) * 100

                label = Label(
                    text=f"{freq:.3f} MHz: {device_type}\nConfidence: {confidence:.0f}%",
                    font_size='16sp',
                    size_hint_y=None,
                    height=80,
                    halign='left',
                    valign='middle'
                )
                label.bind(size=label.setter('text_size'))
                self.device_grid.add_widget(label)


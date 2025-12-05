"""Voice Screen - Voice monitoring controls"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.textinput import TextInput


class VoiceScreen(Screen):
    """Voice monitoring screen."""

    def __init__(self, api, **kwargs):
        super().__init__(**kwargs)
        self.api = api
        self._build_ui()

    def _build_ui(self):
        """Build the UI layout."""
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Header
        header = Label(
            text='[b]📡 Voice Monitoring[/b]',
            markup=True,
            font_size='24sp',
            size_hint=(1, None),
            height=50
        )
        layout.add_widget(header)

        # Frequency input
        freq_box = BoxLayout(orientation='horizontal', size_hint=(1, None), height=60, spacing=10)
        freq_box.add_widget(Label(text='Frequency (MHz):', font_size='18sp', size_hint=(0.4, 1)))
        self.freq_input = TextInput(
            text='146.52',
            multiline=False,
            font_size='24sp',
            input_filter='float',
            size_hint=(0.6, 1)
        )
        freq_box.add_widget(self.freq_input)
        layout.add_widget(freq_box)

        # Mode selection
        mode_box = BoxLayout(orientation='horizontal', size_hint=(1, None), height=60, spacing=10)
        modes = ['FM', 'AM', 'USB', 'LSB']
        for mode in modes:
            btn = Button(
                text=mode,
                font_size='18sp',
                background_color=(0.3, 0.3, 0.3, 1),
                on_press=lambda x, m=mode: self._set_mode(m)
            )
            mode_box.add_widget(btn)
        layout.add_widget(mode_box)

        self.selected_mode = 'FM'
        self.status_label = Label(
            text=f'Mode: {self.selected_mode}',
            font_size='18sp',
            size_hint=(1, None),
            height=40
        )
        layout.add_widget(self.status_label)

        # Spacer
        layout.add_widget(Label(size_hint=(1, 1)))

        # Control buttons
        controls = BoxLayout(orientation='horizontal', size_hint=(1, None), height=80, spacing=10)

        monitor_btn = Button(
            text='Start Monitoring',
            font_size='20sp',
            background_color=(0.2, 0.6, 0.2, 1),
            on_press=self._start_monitoring
        )
        controls.add_widget(monitor_btn)

        record_btn = Button(
            text='Record',
            font_size='20sp',
            background_color=(0.6, 0.2, 0.2, 1),
            on_press=self._start_recording
        )
        controls.add_widget(record_btn)

        layout.add_widget(controls)

        self.add_widget(layout)

    def _set_mode(self, mode):
        """Set demodulation mode."""
        self.selected_mode = mode
        self.status_label.text = f'Mode: {mode}'

    def _start_monitoring(self, instance):
        """Start voice monitoring."""
        try:
            freq = float(self.freq_input.text)
            print(f"Starting voice monitoring: {freq} MHz {self.selected_mode}")
            self.api.demodulate_frequency(freq, self.selected_mode, duration=60)
            self.status_label.text = f'Monitoring {freq} MHz ({self.selected_mode})'
        except ValueError:
            self.status_label.text = 'Invalid frequency'

    def _start_recording(self, instance):
        """Start recording."""
        try:
            freq = float(self.freq_input.text)
            print(f"Recording: {freq} MHz {self.selected_mode}")
            self.api.demodulate_frequency(freq, self.selected_mode, duration=10)
            self.status_label.text = f'Recording {freq} MHz'
        except ValueError:
            self.status_label.text = 'Invalid frequency'

    def update(self):
        """Update screen data."""
        # Voice screen doesn't need periodic updates


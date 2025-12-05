"""Transcripts Screen - Voice transcript search and viewing"""

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput


class TranscriptsScreen(Screen):
    """Transcripts viewing screen."""

    def __init__(self, api, **kwargs):
        super().__init__(**kwargs)
        self.api = api
        self._build_ui()

    def _build_ui(self):
        """Build the UI layout."""
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Header
        header = Label(
            text='[b]💬 Voice Transcripts[/b]',
            markup=True,
            font_size='24sp',
            size_hint=(1, None),
            height=50
        )
        layout.add_widget(header)

        # Search box
        search_box = BoxLayout(orientation='horizontal', size_hint=(1, None), height=50, spacing=10)
        self.search_input = TextInput(
            hint_text='Search transcripts...',
            multiline=False,
            font_size='18sp',
            size_hint=(0.7, 1)
        )
        search_box.add_widget(self.search_input)

        search_btn = Button(
            text='Search',
            font_size='18sp',
            size_hint=(0.3, 1),
            background_color=(0.2, 0.4, 0.6, 1),
            on_press=lambda x: self.update()
        )
        search_box.add_widget(search_btn)
        layout.add_widget(search_box)

        # Transcript list
        scroll = ScrollView(size_hint=(1, 1))
        self.transcript_grid = GridLayout(
            cols=1,
            spacing=10,
            size_hint_y=None,
            padding=5
        )
        self.transcript_grid.bind(minimum_height=self.transcript_grid.setter('height'))
        scroll.add_widget(self.transcript_grid)
        layout.add_widget(scroll)

        self.add_widget(layout)

    def update(self):
        """Update screen data."""
        query = self.search_input.text
        transcripts = self.api.get_transcripts(query=query, limit=20)

        self.transcript_grid.clear_widgets()

        if not transcripts:
            no_data = Label(
                text='No transcripts found' if query else 'No transcripts available',
                font_size='18sp',
                size_hint_y=None,
                height=60,
                color=(0.6, 0.6, 0.6, 1)
            )
            self.transcript_grid.add_widget(no_data)
        else:
            for transcript in transcripts:
                text = transcript.get('text', 'No text')
                freq = transcript.get('frequency', 0) / 1e6 if transcript.get('frequency') else 0
                confidence = transcript.get('confidence', 0) * 100
                timestamp = transcript.get('timestamp', '')

                label = Label(
                    text=f"[b]{freq:.3f} MHz[/b] ({confidence:.0f}%)\n{timestamp}\n{text}",
                    markup=True,
                    font_size='14sp',
                    size_hint_y=None,
                    height=100,
                    halign='left',
                    valign='top',
                    color=(0.9, 0.9, 0.9, 1)
                )
                label.bind(size=label.setter('text_size'))
                self.transcript_grid.add_widget(label)


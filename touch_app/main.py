"""ReconRaven Touch App - Main Entry Point

Kivy touchscreen application for ReconRaven.
Optimized for 800x480 7" displays.
"""

import os


# Set Kivy config before importing kivy
os.environ['KIVY_NO_CONSOLELOG'] = '1'  # Reduce console spam

from kivy.app import App
from kivy.clock import Clock
from kivy.config import Config
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, SlideTransition

from touch_app.api_client import ReconRavenAPI
from touch_app.screens.network import NetworkScreen
from touch_app.screens.signals import SignalsScreen
from touch_app.screens.timeline import TimelineScreen
from touch_app.screens.transcripts import TranscriptsScreen
from touch_app.screens.voice import VoiceScreen


# Configure for touchscreen
Config.set('graphics', 'width', '800')
Config.set('graphics', 'height', '480')
Config.set('graphics', 'resizable', False)
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')  # Prevent right-click issues


class ReconRavenTouchApp(App):
    """Main Kivy application."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.api = ReconRavenAPI()
        self.screen_manager = None
        self.nav_bar = None
        self.update_interval = 10  # seconds

    def build(self):
        """Build the UI."""
        # Set dark theme colors
        Window.clearcolor = (0.1, 0.1, 0.1, 1)

        # Main layout
        root = BoxLayout(orientation='vertical')

        # Screen manager for tabs
        self.screen_manager = ScreenManager(transition=SlideTransition())

        # Add screens
        self.screen_manager.add_widget(SignalsScreen(name='signals', api=self.api))
        self.screen_manager.add_widget(NetworkScreen(name='network', api=self.api))
        self.screen_manager.add_widget(VoiceScreen(name='voice', api=self.api))
        self.screen_manager.add_widget(TranscriptsScreen(name='transcripts', api=self.api))
        self.screen_manager.add_widget(TimelineScreen(name='timeline', api=self.api))

        root.add_widget(self.screen_manager)

        # Bottom navigation bar
        self.nav_bar = self._create_nav_bar()
        root.add_widget(self.nav_bar)

        # Schedule periodic updates
        Clock.schedule_interval(self._update_current_screen, self.update_interval)

        # Initial screen update
        Clock.schedule_once(lambda dt: self._update_current_screen(dt), 0.5)

        return root

    def _create_nav_bar(self):
        """Create bottom navigation bar with tab buttons."""
        nav = BoxLayout(
            orientation='horizontal',
            size_hint=(1, None),
            height=60,
            spacing=2
        )

        tabs = [
            ('🔍\nSignals', 'signals'),
            ('🕸️\nNetwork', 'network'),
            ('📡\nVoice', 'voice'),
            ('💬\nTranscripts', 'transcripts'),
            ('📊\nTimeline', 'timeline')
        ]

        for label, screen_name in tabs:
            btn = Button(
                text=label,
                font_size='14sp',
                background_color=(0.2, 0.2, 0.2, 1),
                background_normal='',
                on_press=lambda x, name=screen_name: self._switch_tab(name)
            )
            nav.add_widget(btn)

        return nav

    def _switch_tab(self, screen_name):
        """Switch to a different tab."""
        self.screen_manager.current = screen_name
        # Update the screen immediately
        current_screen = self.screen_manager.current_screen
        if hasattr(current_screen, 'update'):
            current_screen.update()

    def _update_current_screen(self, dt):
        """Periodically update the current screen."""
        current_screen = self.screen_manager.current_screen
        if hasattr(current_screen, 'update'):
            try:
                current_screen.update()
            except Exception as e:
                print(f"Error updating screen: {e}")

    def on_stop(self):
        """Cleanup when app closes."""
        # Cancel update timer
        Clock.unschedule(self._update_current_screen)
        return True


def main():
    """Run the touchscreen application."""
    print("="*60)
    print("  ReconRaven Touchscreen Application")
    print("="*60)
    print("  Optimized for 800x480 7\" displays")
    print("  Connect to API at: http://localhost:5001")
    print("="*60)
    print()

    ReconRavenTouchApp().run()


if __name__ == '__main__':
    main()


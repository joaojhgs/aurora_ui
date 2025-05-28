from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QTextEdit, QLineEdit, QPushButton, 
                            QLabel, QScrollArea, QFrame, QTextBrowser, QSizePolicy, QSpacerItem)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QThread, QSize, QUrl
from PyQt6.QtGui import QIcon, QColor, QPalette, QFont

import sys
import os
import markdown
import re
from datetime import datetime
from threading import Thread
import queue

# Import database functionality
from modules.database import get_message_history_service
from modules.config.config_manager import config_manager

class MessageWidget(QFrame):
    """Custom widget to display messages in the chat history"""
    def __init__(self, message, is_user=False, parent=None, dark_mode=False, source_type=None):
        super().__init__(parent)
        self.is_user = is_user
        self.dark_mode = dark_mode
        self.source_type = source_type  # "Text" or "STT" or None
        
        # Set up the frame appearance
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        
        # Process the message and get its length immediately for use throughout init
        message_str = str(message)
        content_length = len(message_str.strip())
        
        # Create main layout with balanced spacing for proper text display
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 5, 8, 5)
        main_layout.setSpacing(3)
        
        # Create top bar with timestamp, role label and source type
        top_bar = QHBoxLayout()
        
        # Add timestamp
        timestamp = QLabel(datetime.now().strftime("%H:%M:%S"))
        if self.dark_mode:
            timestamp.setStyleSheet("color: #AAAAAA; font-size: 10px; background-color: transparent;")
        else:
            timestamp.setStyleSheet("color: #777777; font-size: 10px; background-color: transparent;")
        
        # Create role tag (User or Assistant)
        role_tag = QLabel("User" if self.is_user else "Assistant")
        if self.dark_mode:
            role_tag.setStyleSheet(f"""
                color: {'white' if self.dark_mode else 'white'};
                background-color: {'#9C27B0' if self.is_user else '#673AB7'};
                border-radius: 10px;
                padding: 2px 6px;
                margin-right: 4px;
                font-size: 10px;
                font-weight: bold;
            """)
        else:
            role_tag.setStyleSheet(f"""
                color: white;
                background-color: {'#1565C0' if self.is_user else '#00796B'};
                border-radius: 10px;
                padding: 2px 6px;
                margin-right: 4px;
                font-size: 10px;
                font-weight: bold;
            """)
        
        # Create source tag if applicable (Text or STT)
        source_tag = None
        if self.is_user and self.source_type:
            source_tag = QLabel(self.source_type)
            source_tag.setStyleSheet(f"""
                color: {'white' if self.dark_mode else 'white'};
                background-color: {'#555555' if source_type == 'Text' else '#1E8E3E'};
                border-radius: 10px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: bold;
            """)
        
        # Add widgets to top bar based on alignment
        if self.is_user:
            # For user messages, tags go on left, timestamp on right
            if source_tag:
                top_bar.addWidget(role_tag)
                top_bar.addWidget(source_tag)
            else:
                top_bar.addWidget(role_tag)
            top_bar.addStretch()
            top_bar.addWidget(timestamp)
        else:
            # For assistant messages, timestamp on left, tag on right
            top_bar.addWidget(timestamp)
            top_bar.addStretch()
            top_bar.addWidget(role_tag)
            if source_tag:
                top_bar.addWidget(source_tag)
        
        main_layout.addLayout(top_bar)
        
        # Check if this might be markdown content
        has_markdown = False
        if not is_user:
            has_markdown = (
                '```' in message_str or  # code blocks
                re.search(r'\*\*.+\*\*', message_str) or  # bold
                re.search(r'\*.+\*', message_str) or  # italic
                re.search(r'#+\s', message_str) or  # headers
                re.search(r'^\s*[-*+]\s', message_str, re.MULTILINE) or  # list items
                '|' in message_str or  # potential tables
                '[' in message_str and '](' in message_str  # links
            )
        
        # Add message content with appropriate widget
        if has_markdown:
            # Convert markdown to HTML
            html_content = markdown.markdown(
                message_str,
                extensions=['fenced_code', 'codehilite', 'tables']
            )
            
            # Create a text browser for rich text display
            message_display = QTextBrowser()
            message_display.setOpenExternalLinks(True)
            message_display.setHtml(html_content)
            message_display.setReadOnly(True)
            
            # Style it based on the theme
            if self.dark_mode:
                message_display.setStyleSheet("""
                    background-color: transparent;
                    color: #E0E0E0;
                    border: none;
                    selection-background-color: #444444;
                    padding: 5px;
                """)
                
                # Add custom CSS for dark mode code blocks
                html_content = html_content.replace(
                    "<pre><code>", 
                    "<pre style='background-color: #222222; border: 1px solid #444444; border-radius: 5px; padding: 8px; overflow-x: auto;'><code style='color: #E0E0E0;'>"
                )
            else:
                message_display.setStyleSheet("""
                    background-color: transparent;
                    color: #333333;
                    border: none;
                    selection-background-color: #E3F2FD;
                    padding: 5px;
                """)
                
                # Add custom CSS for light mode code blocks
                html_content = html_content.replace(
                    "<pre><code>", 
                    "<pre style='background-color: #F5F5F5; border: 1px solid #E0E0E0; border-radius: 5px; padding: 8px; overflow-x: auto;'><code style='color: #333333;'>"
                )
            
            message_display.setHtml(html_content)
            message_display.document().setDefaultStyleSheet("""
                h1, h2, h3 { margin-top: 0.3em; margin-bottom: 0.3em; }
                p { margin-top: 0.3em; margin-bottom: 0.3em; }
                ul, ol { margin-top: 0.3em; margin-bottom: 0.3em; margin-left: 15px; padding-left: 15px; }
                li { margin-bottom: 0.2em; }
                pre { margin: 0.5em 0; white-space: pre-wrap; }
                code { font-family: monospace; white-space: pre-wrap; }
                table { border-collapse: collapse; margin: 0.5em 0; }
                th, td { border: 1px solid #CCCCCC; padding: 6px; }
                img { max-width: 100%; height: auto; }
            """)
            
            # Make the widget size adjust to content appropriately
            message_display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            message_display.setMinimumHeight(30) # Reasonable minimum height
            
            # Calculate required height with appropriate padding
            document_height = message_display.document().size().height() + 20
            message_display.setMinimumHeight(int(min(document_height, 500)))
            
            # For markdown content, we need to handle width differently
            document_width = message_display.document().idealWidth() 
            
            # Set width based on content to ensure proper display
            if document_width < 50:
                # Very minimal content
                message_display.setMinimumWidth(int(max(document_width + 50, 150)))
            elif document_width < 200:
                # Short/medium content
                message_display.setMinimumWidth(int(document_width + 60))
            else:
                # Longer content
                message_display.setMinimumWidth(int(document_width + 40))
                
            # Cap maximum width
            message_display.setMaximumWidth(650)
            
            main_layout.addWidget(message_display)
        else:
            # Use a simple QLabel for plain text display
            message_label = QLabel(message_str)
            message_label.setWordWrap(True)
            message_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            
            # Use appropriate size policy for text
            message_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
            
            # Make sure text gets proper rendering space
            fm = message_label.fontMetrics()
            line_spacing = fm.lineSpacing()
            line_count = message_str.count('\n') + 1
            
            # Calculate how much height we need for this text
            text_height = line_count * line_spacing + 15
            
            # Set proper height for the text
            message_label.setMinimumHeight(text_height)
            
            # Determine appropriate width based on content length
            # content_length already defined at the top
            
            # Calculate a width that fits the content nicely
            text_width = fm.horizontalAdvance(message_str[:min(30, content_length)]) + 20
            
            # Set minimum width based on content length for better appearance
            if content_length < 10:
                # For very short messages, ensure a reasonable minimum width
                message_label.setMinimumWidth(max(text_width, 80))
            else:
                # Let width be determined by content with some padding
                message_label.setMinimumWidth(0)  # Let the layout handle it
                
            # Apply appropriate text styling with padding
            if self.is_user:
                if self.dark_mode:
                    message_label.setStyleSheet("""
                        color: #121212; 
                        font-weight: bold; 
                        background-color: transparent; 
                        font-size: 14px; 
                        padding: 6px; 
                        margin: 4px;
                    """)
                else:
                    message_label.setStyleSheet("""
                        color: white; 
                        font-weight: bold; 
                        background-color: transparent; 
                        font-size: 14px; 
                        padding: 6px; 
                        margin: 4px;
                    """)
            else:
                if self.dark_mode:
                    message_label.setStyleSheet("""
                        color: #E0E0E0; 
                        background-color: transparent; 
                        font-size: 14px; 
                        padding: 6px; 
                        margin: 4px;
                    """)
                else:
                    message_label.setStyleSheet("""
                        color: #333333; 
                        background-color: transparent; 
                        font-size: 14px; 
                        padding: 6px; 
                        margin: 4px;
                    """)
            
            main_layout.addWidget(message_label)
        
        # Use proper margins for content
        main_layout.setContentsMargins(10, 8, 10, 8)
        
        # Set size policy to allow the bubble to shrink to content
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        
        # RESPONSIVE SIZING IMPROVEMENT: Calculate proper width based on content and parent width
        def update_bubble_size():
            parent_width = self.parent().width() if self.parent() else 800
            max_width = min(int(parent_width * 0.8), 650)  # Cap at 80% of parent width
            
            # Get content width
            content_width = 0
            for i in range(main_layout.count()):
                item = main_layout.itemAt(i)
                if item and item.widget():
                    widget_width = item.widget().sizeHint().width()
                    content_width = max(content_width, widget_width)
            
            # Determine minimum width based on content length
            if has_markdown:
                # For markdown content, use the values already calculated
                min_width = message_display.minimumWidth() + 20
            else:
                # For text content, calculate based on message length
                if content_length < 10:
                    # Very short messages get proper padding
                    min_width = max(content_width + 40, 80)
                elif content_length < 30:
                    # Short messages
                    min_width = max(content_width + 30, 120)
                else:
                    # Regular messages
                    min_width = content_width + 20
            
            # Set width constraints - allow bubble to grow only as needed
            self.setMinimumWidth(min(min_width, max_width))
            self.setMaximumWidth(max_width)
        
        # Call once immediately to set initial size
        update_bubble_size()
        
        # Install event filter to handle resize events
        class ResizeEventFilter(QObject):
            def __init__(self, target_widget, update_func):
                super().__init__()
                self.update_func = update_func
                self.target_widget = target_widget
            
            def eventFilter(self, obj, event):
                from PyQt6.QtCore import QEvent
                if obj == self.target_widget and event.type() == QEvent.Type.Resize:
                    self.update_func()
                return False
        
        # Apply resize event filter to parent if available
        if self.parent():
            self.parent().installEventFilter(ResizeEventFilter(self.parent(), update_bubble_size))
        
        # Apply styles to the frame with appropriate margins based on message source
        side_margin = 20 if content_length < 20 else 40  # Less margin for short messages
        
        if self.is_user:
            if self.dark_mode:
                self.setStyleSheet(f"""
                    background-color: #BB86FC; 
                    border-radius: 12px; 
                    padding: 5px;
                    margin-left: {side_margin}px;
                """)
            else:
                self.setStyleSheet(f"""
                    background-color: #2196F3; 
                    border-radius: 12px; 
                    padding: 5px;
                    margin-left: {side_margin}px;
                """)
        else:
            if self.dark_mode:
                self.setStyleSheet(f"""
                    background-color: #333333; 
                    border-radius: 12px; 
                    padding: 5px;
                    margin-right: {side_margin}px;
                """)
            else:
                self.setStyleSheet(f"""
                    background-color: #F5F5F5; 
                    border-radius: 12px; 
                    padding: 5px;
                    margin-right: {side_margin}px;
                """)
        
        # Force the widget to shrink to fit its content exactly
        self.adjustSize()
        
    def resizeEvent(self, event):
        """Handle resize events to adjust bubble sizing"""
        super().resizeEvent(event)
        
        # Get parent width for responsive sizing
        parent_width = self.parent().width() if self.parent() else 800
        
        # Limit maximum width to a percentage of parent width
        max_width = min(int(parent_width * 0.8), 650)
        self.setMaximumWidth(max_width)

class StatusIndicator(QLabel):
    """Status indicator widget to show current system state"""
    def __init__(self, parent=None, dark_mode=False):
        super().__init__(parent)
        self.dark_mode = dark_mode
        self.setText("Idle")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(40)
        self.setMaximumHeight(40)
        self.set_idle()
    
    def set_idle(self):
        self.setText("Idle - Say 'Jarvis' to activate")
        if self.dark_mode:
            self.setStyleSheet("""
                color: #BBBBBB;
                font-weight: bold;
                font-size: 14px;
                background-color: #282828;
                border-radius: 12px;
                padding: 8px;
                border: 1px solid #444444;
            """)
        else:
            self.setStyleSheet("""
                color: #777777;
                font-weight: bold;
                font-size: 14px;
                background-color: #F5F5F5;
                border-radius: 12px;
                padding: 8px;
                border: 1px solid #E0E0E0;
            """)
    
    def set_listening(self):
        self.setText("Listening...")
        self.setStyleSheet("""
            color: white;
            font-weight: bold;
            font-size: 14px;
            background-color: #4CAF50;
            border-radius: 12px;
            padding: 8px;
            border: none;
        """)
    
    def set_processing(self):
        self.setText("Processing...")
        self.setStyleSheet("""
            color: white;
            font-weight: bold;
            font-size: 14px;
            background-color: #2196F3;
            border-radius: 12px;
            padding: 8px;
            border: none;
        """)
    
    def set_speaking(self):
        self.setText("Speaking...")
        self.setStyleSheet("""
            color: white;
            font-weight: bold;
            font-size: 14px;
            background-color: #FF9800;
            border-radius: 12px;
            padding: 8px;
            border: none;
        """)

class AuroraSignals(QObject):
    """Signal class for communicating between threads"""
    message_received = pyqtSignal(str, bool, object)  # message, is_user, source_type
    status_changed = pyqtSignal(str)  # status name

class AuroraUI(QMainWindow):
    """Main UI class for Aurora"""
    def __init__(self):
        super().__init__()
        
        # UI version
        self.version = "1.0.1"
        
        # Dark mode setting
        from modules.config.config_manager import config_manager
        self.dark_mode = config_manager.get('ui.dark_mode', False)
        
        # Setup the UI
        self.init_ui()
        
        # Setup signals
        self.signals = AuroraSignals()
        self.signals.message_received.connect(self.add_message)
        self.signals.status_changed.connect(self.update_status)
        
        # Message queue for thread-safe access
        self.message_queue = queue.Queue()
        
        # Store original STT and TTS callbacks
        self.original_on_recording_start = None
        self.original_on_recording_stop = None
        self.original_on_wakeword_detected = None
        self.original_on_wakeword_detection_start = None
        self.original_on_audio_stream_start = None
        self.original_on_audio_stream_stop = None
        
        # Debug mode for verbose logging
        self.debug_mode = config_manager.get('ui.debug', False)
        
        # Store last UI message to avoid duplication
        self._last_ui_message = None
        
        # Initialize database message history service
        self.message_history = get_message_history_service()
        
        # Load today's messages or show welcome message
        self.load_todays_messages()
        
    def load_todays_messages(self):
        """Load today's messages from database or show welcome message if none exist"""
        try:
            # Get today's messages from database
            today_messages = self.message_history.get_today_messages()
            
            if today_messages:
                print(f"UI: Loading {len(today_messages)} messages from today")
                # Add each message to the UI
                for msg in today_messages:
                    # Use the Message model methods to get UI properties
                    is_user = msg.is_user_message()
                    source_type = msg.get_ui_source_type()
                    
                    # Add message to UI without storing in database again
                    self._add_message_to_ui_only(msg.content, is_user, source_type)
                    
                print("UI: Loaded persisted messages from today")
            else:
                print("UI: No messages from today, showing welcome message")
                # Show welcome message if no messages today
                self._show_welcome_message()
                
        except Exception as e:
            print(f"Error loading today's messages: {e}")
            # Fallback to welcome message
            self._show_welcome_message()
    
    def _show_welcome_message(self):
        """Show the welcome message"""
        welcome_markdown = f"""
# Welcome to Aurora AI Assistant v{self.version}

You can interact with the assistant in two ways:
- Say **"Jarvis"** to activate voice input
- Type your message in the text box below

### Features
- Voice commands with Speech-to-Text
- Text input with detailed responses
- Markdown formatting support
- Dark mode toggle

**Start by asking a question!**
"""
        self._add_message_to_ui_only(welcome_markdown, False, None)
    
    def _add_message_to_ui_only(self, message, is_user=False, source_type=None):
        """Add a message to UI without storing in database (for loading persisted messages)"""
        print(f"UI: Adding message to UI only: '{message[:30]}...' User: {is_user} Source: {source_type}")
        
        message_widget = MessageWidget(message, is_user, dark_mode=self.dark_mode, source_type=source_type)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, message_widget)
        
        # Scroll to bottom
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self._ensure_scroll_to_bottom)

    def init_ui(self):
        """Initialize the UI components"""
        self.setWindowTitle("Aurora AI Voice & Text Assistant")
        self.setMinimumSize(800, 600)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Status indicator
        self.status_indicator = StatusIndicator(dark_mode=self.dark_mode)
        main_layout.addWidget(self.status_indicator, 0)
        
        # Add some spacing
        main_layout.addSpacing(5)
        
        # Chat history area
        chat_scroll = QScrollArea()
        chat_scroll.setWidgetResizable(True)
        chat_scroll.setFrameShape(QFrame.Shape.NoFrame)  # Remove border for cleaner look
        
        chat_widget = QWidget()
        
        # Set background color based on theme
        if self.dark_mode:
            chat_widget.setStyleSheet("background-color: #121212;")
        else:
            chat_widget.setStyleSheet("background-color: white;")
            
        # Set chat layout for balanced spacing
        self.chat_layout = QVBoxLayout(chat_widget)
        self.chat_layout.setContentsMargins(10, 10, 10, 10)
        self.chat_layout.setSpacing(8)  # Proper spacing between messages
        self.chat_layout.addStretch()
        chat_scroll.setWidget(chat_widget)
        main_layout.addWidget(chat_scroll, stretch=1)
        
        # Bottom panel for input
        bottom_panel = QWidget()
        if self.dark_mode:
            bottom_panel.setStyleSheet("background-color: #1E1E1E; border-top: 1px solid #333333; padding: 10px;")
        else:
            bottom_panel.setStyleSheet("background-color: #F5F5F5; border-top: 1px solid #E0E0E0; padding: 10px;")
        
        bottom_layout = QVBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(5, 10, 5, 5)
        
        # Input area
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(10)
        
        # Text input
        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("Type your message here...")
        self.input_field.setMaximumHeight(80)
        
        # Handle keyboard events to intercept Return key
        from PyQt6.QtGui import QKeyEvent
        from PyQt6.QtCore import Qt
        
        # Subclass QTextEdit to handle key events
        class EnterTextEdit(QTextEdit):
            def __init__(self, parent, send_callback):
                super().__init__(parent)
                self.send_callback = send_callback
                
            def keyPressEvent(self, event):
                # If Return/Enter key is pressed without Shift, send the message
                if (event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter) and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    self.send_callback()
                    return
                # If Shift+Enter is pressed, insert a newline
                super().keyPressEvent(event)
        
        # Replace the standard QTextEdit with our custom one
        self.input_field = EnterTextEdit(self, self.send_message)
        self.input_field.setPlaceholderText("Type your message here (press Enter to send, Shift+Enter for newline)...")
        self.input_field.setMaximumHeight(80)
        
        # Round the corners of the input field
        if self.dark_mode:
            self.input_field.setStyleSheet("""
                QTextEdit {
                    background-color: #2D2D2D;
                    color: #E0E0E0;
                    border: 1px solid #444444;
                    border-radius: 12px;
                    padding: 8px 12px;
                    font-size: 14px;
                }
            """)
        else:
            self.input_field.setStyleSheet("""
                QTextEdit {
                    background-color: white;
                    color: #333333;
                    border: 1px solid #CCCCCC;
                    border-radius: 12px;
                    padding: 8px 12px;
                    font-size: 14px;
                }
            """)
        
        input_layout.addWidget(self.input_field, stretch=1)
        
        # Send button - styled to look modern
        self.send_button = QPushButton("Send")
        self.send_button.setMinimumHeight(40)
        self.send_button.setMaximumWidth(100)
        
        if self.dark_mode:
            self.send_button.setStyleSheet("""
                QPushButton {
                    background-color: #BB86FC;
                    color: #121212;
                    border: none;
                    border-radius: 12px;
                    padding: 8px 16px;
                    font-weight: bold;
                    font-size: 13px;
                }
                
                QPushButton:hover {
                    background-color: #A66EFC;
                }
                
                QPushButton:pressed {
                    background-color: #7B41CE;
                }
            """)
        else:
            self.send_button.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 12px;
                    padding: 8px 16px;
                    font-weight: bold;
                    font-size: 13px;
                }
                
                QPushButton:hover {
                    background-color: #1976D2;
                }
                
                QPushButton:pressed {
                    background-color: #0D47A1;
                }
            """)
        
        self.send_button.clicked.connect(self.send_message)
        input_layout.addWidget(self.send_button)
        
        bottom_layout.addLayout(input_layout)
        
        # Voice control buttons
        voice_layout = QHBoxLayout()
        voice_layout.setContentsMargins(0, 5, 0, 0)
        voice_layout.setSpacing(10)
        
        # Stop button
        self.stop_button = QPushButton("Stop Speaking")
        self.stop_button.setMinimumHeight(35)
        self.stop_button.clicked.connect(self.stop_voice)
        
        # Dark mode toggle
        self.dark_mode_button = QPushButton("Toggle Dark Mode")
        self.dark_mode_button.setMinimumHeight(35)
        self.dark_mode_button.clicked.connect(self.toggle_dark_mode)
        
        # Style the control buttons
        button_style = """
            QPushButton {
                background-color: %s;
                color: %s;
                border: none;
                border-radius: 8px;
                padding: 4px 12px;
                font-size: 12px;
            }
            
            QPushButton:hover {
                background-color: %s;
            }
            
            QPushButton:pressed {
                background-color: %s;
            }
        """
        
        if self.dark_mode:
            self.stop_button.setStyleSheet(button_style % ('#333333', '#E0E0E0', '#444444', '#222222'))
            self.dark_mode_button.setStyleSheet(button_style % ('#333333', '#E0E0E0', '#444444', '#222222'))
        else:
            self.stop_button.setStyleSheet(button_style % ('#E0E0E0', '#333333', '#CCCCCC', '#BBBBBB'))
            self.dark_mode_button.setStyleSheet(button_style % ('#E0E0E0', '#333333', '#CCCCCC', '#BBBBBB'))
        
        voice_layout.addWidget(self.stop_button)
        voice_layout.addWidget(self.dark_mode_button)
        voice_layout.addStretch(1)  # Add stretch to align buttons to the left
        
        bottom_layout.addLayout(voice_layout)
        
        main_layout.addWidget(bottom_panel)
        
        # Set app style
        self.apply_style()
    
    def apply_style(self):
        """Apply custom styling to the application"""
        if self.dark_mode:
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #1E1E1E;
                    color: #E0E0E0;
                }
                
                QWidget {
                    background-color: #1E1E1E;
                    color: #E0E0E0;
                }
                
                QScrollArea {
                    border: none;
                    background-color: #121212;
                }
                
                QScrollBar:vertical {
                    background: #2D2D2D;
                    width: 10px;
                    margin: 0px;
                }
                
                QScrollBar::handle:vertical {
                    background: #555555;
                    min-height: 20px;
                    border-radius: 5px;
                }
                
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                
                QScrollBar:horizontal {
                    background: #2D2D2D;
                    height: 10px;
                    margin: 0px;
                }
                
                QScrollBar::handle:horizontal {
                    background: #555555;
                    min-width: 20px;
                    border-radius: 5px;
                }
                
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                    width: 0px;
                }
                
                QLabel {
                    font-size: 14px;
                    color: #E0E0E0;
                }
                
                QTextBrowser {
                    background-color: transparent;
                    color: #E0E0E0;
                    border: none;
                    selection-background-color: #444444;
                }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow {
                    background-color: white;
                    color: #333333;
                }
                
                QWidget {
                    background-color: white;
                    color: #333333;
                }
                
                QScrollArea {
                    border: none;
                    background-color: white;
                }
                
                QScrollBar:vertical {
                    background: #F5F5F5;
                    width: 10px;
                    margin: 0px;
                }
                
                QScrollBar::handle:vertical {
                    background: #CCCCCC;
                    min-height: 20px;
                    border-radius: 5px;
                }
                
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                
                QScrollBar:horizontal {
                    background: #F5F5F5;
                    height: 10px;
                    margin: 0px;
                }
                
                QScrollBar::handle:horizontal {
                    background: #CCCCCC;
                    min-width: 20px;
                    border-radius: 5px;
                }
                
                QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                    width: 0px;
                }
                
                QLabel {
                    font-size: 14px;
                    color: #333333;
                }
                
                QTextBrowser {
                    background-color: transparent;
                    color: #333333;
                    border: none;
                    selection-background-color: #E3F2FD;
                }
            """)
    
    def add_message(self, message, is_user=False, source_type=None):
        """Add a message to the chat history and store in database
        
        Args:
            message: The message text to display
            is_user: Whether this is a user message (True) or AI response (False)
            source_type: The source of the message ("Text", "STT", or None)
        """
        # Debug logging
        print(f"UI: Adding message to chat: '{message[:30]}...' User: {is_user} Source: {source_type}")
        
        # Add to UI
        message_widget = MessageWidget(message, is_user, dark_mode=self.dark_mode, source_type=source_type)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, message_widget)
        
        # Store in database
        try:
            # Store message in database using appropriate method
            if is_user:
                if source_type == "STT":
                    self.message_history.store_user_voice_message(str(message))
                else:
                    self.message_history.store_user_text_message(str(message))
            else:
                self.message_history.store_assistant_message(str(message))
            
            print(f"UI: Stored message in database (User: {is_user}, Source: {source_type})")
            
        except Exception as e:
            print(f"Error storing message in database: {e}")
        
        # Scroll to bottom - use a brief delay to ensure the UI has updated
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self._ensure_scroll_to_bottom)
    
    def _ensure_scroll_to_bottom(self):
        """Scroll to the bottom of the chat area"""
        scroll_area = self.findChild(QScrollArea)
        if scroll_area:
            vsb = scroll_area.verticalScrollBar()
            vsb.setValue(vsb.maximum())
    
    def send_message(self):
        """Handle sending a text message"""
        message = self.input_field.toPlainText().strip()
        if not message:
            return
        
        print(f"UI: Sending message: {message[:30] if len(message) > 30 else message}")
        
        # IMPORTANT: Add user message to chat with 'Text' source type
        self.add_message(message, is_user=True, source_type="Text")
        print(f"UI: Added user message to UI")
        
        # Clear input field
        self.input_field.clear()
        
        # Set a flag to indicate this was processed by the UI
        # This will be checked by the graph updates hook to avoid duplicate display
        self._last_ui_message = message
        print(f"UI: Set last UI message: {message[:30] if len(message) > 30 else message}")
        
        # Process message
        self.process_message(message)
    
    def process_message(self, message):
        """Process the user message and get a response"""
        # Update status
        self.update_status("processing")
        
        # Convert to string for consistent handling
        message_str = str(message)
        
        # Create a thread to process the message to avoid UI freezing
        def process_in_thread():
            try:
                # Import the text-only processing function for UI input
                from modules.langgraph.graph import process_text_input
                
                print(f"UI: Processing text input in thread: {message_str[:30]}...")
                
                # Use the text-only processing function (no TTS)
                response = process_text_input(message)
                
                # Update the UI with the response
                if response and response != "END":
                    print(f"UI: Received text response: {response[:30]}...")
                    # IMPORTANT: Add response to UI (since we're not using TTS hook)
                    # No source type since it's an AI response
                    self.signals.message_received.emit(response, False, None)
                
                # Reset status
                self.signals.status_changed.emit("idle")
            except Exception as e:
                print(f"Error in processing thread: {e}")
                self.signals.status_changed.emit("idle")
        
        # Start processing thread
        Thread(target=process_in_thread, daemon=True).start()
    
    def update_status(self, status):
        """Update the status indicator"""
        if self.debug_mode:
            print(f"UI Status changed to: {status}")
            
        if status == "idle":
            self.status_indicator.set_idle()
        elif status == "listening":
            self.status_indicator.set_listening()
        elif status == "processing":
            self.status_indicator.set_processing()
        elif status == "speaking":
            self.status_indicator.set_speaking()
    
    def process_stt_message(self, text):
        """Process a message coming from STT"""
        print(f"UI: Processing STT message: {text}")
        
        # Update status to show we're processing
        self.signals.status_changed.emit("processing")
        
        # Create a custom message object to track the source
        # This helps us avoid duplicating the message in the UI
        class STTMessage:
            def __init__(self, text):
                self.text = text
                self.from_stt = True
                # Time marker used to uniquely identify this message
                from datetime import datetime
                self.timestamp = datetime.now().timestamp()
            
            def __str__(self):
                return self.text
        
        # Process the STT message - the UI update will happen in ui_stream_graph_updates
        stt_msg = STTMessage(text)
        print(f"UI: Sending marked STT message to processing: {text[:30]}...")
        
        # Process in a thread to avoid blocking UI
        def process_in_thread():
            try:
                # Import here to avoid circular imports
                # Use stream_graph_updates for STT which will use TTS
                from modules.langgraph.graph import stream_graph_updates
                
                # Let stream_graph_updates handle the UI update through our hook
                response = stream_graph_updates(stt_msg)
                
                if response and response != "END":
                    print(f"UI: Received STT response: {response[:30]}...")
                    # IMPORTANT: Add response to UI explicitly to ensure it's displayed
                    # This is a fallback in case the TTS hook doesn't work correctly
                    self.signals.message_received.emit(response, False, None)
                    print(f"UI: Explicitly added STT response to chat")
                
            except Exception as e:
                print(f"Error processing STT message: {e}")
                self.signals.status_changed.emit("idle")
                
        # Start processing in a separate thread
        Thread(target=process_in_thread, daemon=True).start()
    
    def stop_voice(self):
        """Stop voice processing"""
        from modules.text_to_speech.tts import stop
        print("UI: Stopping voice")
        stop()
        self.update_status("idle")
        
    def toggle_dark_mode(self):
        """Toggle between dark and light mode"""
        self.dark_mode = not self.dark_mode
        
        # Update the UI style
        self.apply_style()
        
        # Update status indicator
        self.status_indicator.dark_mode = self.dark_mode
        self.status_indicator.set_idle()
        
        # Update chat widget background
        chat_scroll = self.findChild(QScrollArea)
        if chat_scroll and chat_scroll.widget():
            if self.dark_mode:
                chat_scroll.widget().setStyleSheet("background-color: #121212;")
            else:
                chat_scroll.widget().setStyleSheet("background-color: white;")
        
        # Update bottom panel
        for widget in self.findChildren(QWidget):
            if hasattr(widget, 'styleSheet') and 'border-top: 1px solid' in widget.styleSheet():
                if self.dark_mode:
                    widget.setStyleSheet("background-color: #1E1E1E; border-top: 1px solid #333333; padding: 10px;")
                else:
                    widget.setStyleSheet("background-color: #F5F5F5; border-top: 1px solid #E0E0E0; padding: 10px;")
        
        # Update input field style
        if self.dark_mode:
            self.input_field.setStyleSheet("""
                QTextEdit {
                    background-color: #2D2D2D;
                    color: #E0E0E0;
                    border: 1px solid #444444;
                    border-radius: 12px;
                    padding: 8px 12px;
                    font-size: 14px;
                }
            """)
        else:
            self.input_field.setStyleSheet("""
                QTextEdit {
                    background-color: white;
                    color: #333333;
                    border: 1px solid #CCCCCC;
                    border-radius: 12px;
                    padding: 8px 12px;
                    font-size: 14px;
                }
            """)
        
        # Update buttons style
        button_style = """
            QPushButton {
                background-color: %s;
                color: %s;
                border: none;
                border-radius: 8px;
                padding: 4px 12px;
                font-size: 12px;
            }
            
            QPushButton:hover {
                background-color: %s;
            }
            
            QPushButton:pressed {
                background-color: %s;
            }
        """
        
        if self.dark_mode:
            self.stop_button.setStyleSheet(button_style % ('#333333', '#E0E0E0', '#444444', '#222222'))
            self.dark_mode_button.setStyleSheet(button_style % ('#333333', '#E0E0E0', '#444444', '#222222'))
            self.send_button.setStyleSheet("""
                QPushButton {
                    background-color: #BB86FC;
                    color: #121212;
                    border: none;
                    border-radius: 12px;
                    padding: 8px 16px;
                    font-weight: bold;
                    font-size: 13px;
                }
                
                QPushButton:hover {
                    background-color: #A66EFC;
                }
                
                QPushButton:pressed {
                    background-color: #7B41CE;
                }
            """)
        else:
            self.stop_button.setStyleSheet(button_style % ('#E0E0E0', '#333333', '#CCCCCC', '#BBBBBB'))
            self.dark_mode_button.setStyleSheet(button_style % ('#E0E0E0', '#333333', '#CCCCCC', '#BBBBBB'))
            self.send_button.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 12px;
                    padding: 8px 16px;
                    font-weight: bold;
                    font-size: 13px;
                }
                
                QPushButton:hover {
                    background-color: #1976D2;
                }
                
                QPushButton:pressed {
                    background-color: #0D47A1;
                }
            """)
        
        # Refresh existing messages
        for i in range(self.chat_layout.count()):
            widget = self.chat_layout.itemAt(i).widget()
            if isinstance(widget, MessageWidget):
                # Create a new message widget with the same content but updated styling
                message_content = ""
                source_type = None
                is_user = widget.is_user
                
                # Find the original message content
                for child in widget.findChildren(QLabel) + widget.findChildren(QTextBrowser):
                    if not child.styleSheet() or "font-size: 10px" not in child.styleSheet():
                        # This is not a timestamp or source tag, it's the main content
                        if isinstance(child, QLabel):
                            message_content = child.text()
                        elif isinstance(child, QTextBrowser):
                            message_content = child.toPlainText()
                
                # Find source type if it exists
                for child in widget.findChildren(QLabel):
                    if "border-radius: 10px" in child.styleSheet() and child.text() in ["Text", "STT"]:
                        source_type = child.text()
                
                # Remove the old widget
                old_widget = self.chat_layout.takeAt(i).widget()
                old_widget.deleteLater()
                
                # Create and add a new widget with the same content
                new_widget = MessageWidget(message_content, is_user, dark_mode=self.dark_mode, source_type=source_type)
                self.chat_layout.insertWidget(i, new_widget)
        
        # Save preference to environment variable
        config_manager.get('ui.dark_mode') == 'true' if self.dark_mode else 'false'
    
    # Methods to hook into the existing STT/TTS system
    def hook_into_systems(self):
        """Connect UI to the existing STT and TTS systems"""
        # Import the necessary modules
        import modules.speech_to_text.stt as stt
        import modules.text_to_speech.tts as tts
        from modules.speech_to_text.audio_recorder import AudioToTextRecorder
        
        # Store original callbacks
        self.original_on_recording_start = stt.on_recording_start
        self.original_on_recording_stop = stt.on_recording_stop
        self.original_on_wakeword_detected = stt.on_wakeword_detected
        self.original_on_wakeword_detection_start = stt.on_wakeword_detection_start
        
        # Override callbacks to update UI
        def ui_on_recording_start():
            print("UI: Recording started")
            self.signals.status_changed.emit("listening")
            if self.original_on_recording_start:
                self.original_on_recording_start()
        
        def ui_on_recording_stop():
            print("UI: Recording stopped")
            self.signals.status_changed.emit("processing")
            if self.original_on_recording_stop:
                self.original_on_recording_stop()
        
        def ui_on_wakeword_detected():
            print("UI: Wakeword detected")
            self.signals.status_changed.emit("listening")
            if self.original_on_wakeword_detected:
                self.original_on_wakeword_detected()
                
        def ui_on_wakeword_detection_start():
            print("UI: Listening for wakeword")
            self.signals.status_changed.emit("idle")
            if self.original_on_wakeword_detection_start:
                self.original_on_wakeword_detection_start()
        
        # Replace the original STT callbacks
        stt.on_recording_start = ui_on_recording_start
        stt.on_recording_stop = ui_on_recording_stop
        stt.on_wakeword_detected = ui_on_wakeword_detected
        stt.on_wakeword_detection_start = ui_on_wakeword_detection_start
        
        # Store original audio stream callbacks from TTS
        self.original_on_audio_stream_start = tts.on_audio_stream_start
        self.original_on_audio_stream_stop = tts.on_audio_stream_stop
        
        # Create enhanced audio stream callbacks
        def ui_on_audio_stream_start():
            print("UI: Audio stream started")
            # Update the UI in the main thread
            self.signals.status_changed.emit("speaking")
            # Call the original callback
            if self.original_on_audio_stream_start:
                self.original_on_audio_stream_start()
                
        def ui_on_audio_stream_stop():
            print("UI: Audio stream stopped")
            # Update the UI in the main thread
            self.signals.status_changed.emit("idle")
            # Call the original callback
            if self.original_on_audio_stream_stop:
                self.original_on_audio_stream_stop()
        
        # Replace the TTS audio stream callbacks
        from RealtimeTTS import TextToAudioStream

        tts.stream = TextToAudioStream(tts.engine, frames_per_buffer=256, on_audio_stream_start=ui_on_audio_stream_start, on_audio_stream_stop=ui_on_audio_stream_stop)
        
        # Patch the main processing function
        from modules.langgraph import graph as lg
        original_stream_graph_updates = lg.stream_graph_updates
        
        def ui_stream_graph_updates(user_input):
            try:
                # Convert to string for logging
                input_str = str(user_input)
                
                # Log first 30 chars of input, safely
                if len(input_str) > 30:
                    log_str = input_str[:30] + "..."
                else:
                    log_str = input_str
                    
                print(f"UI: Processing user input: {log_str}")
                
                # Track if this is an STT message for deduplication later
                is_stt_message = hasattr(user_input, 'from_stt') and user_input.from_stt
                
                # IMPORTANT: Check input source and display user message accordingly
                if is_stt_message:
                    # This is from STT - add to UI first, then process
                    print(f"UI: Adding STT message to chat: {log_str}")
                    self.signals.message_received.emit(input_str, True, "STT")
                elif hasattr(self, '_last_ui_message') and self._last_ui_message == input_str:
                    # Message from text input - already displayed in send_message
                    print(f"UI: Message from UI input, already displayed")
                    # Reset the flag to avoid future conflicts
                    self._last_ui_message = None
                else:
                    # Any other source - add to UI to be safe
                    print(f"UI: Adding message to chat from unknown source: {log_str}")
                    self.signals.message_received.emit(input_str, True, None)
                
                # Call the original function - only used by STT which needs TTS output
                print("UI: Calling original stream_graph_updates")
                response = original_stream_graph_updates(user_input)
                
                # No need to manually add the response to UI here as:
                # 1. For STT: We now explicitly add the response in process_stt_message
                # 2. For UI text: We don't use this function anymore (process_text_input is used)
                
                return response
            except Exception as e:
                print(f"Error in UI stream_graph_updates: {e}")
                self.signals.status_changed.emit("idle")
                return "Error processing request"
        
        # Replace the original function with our patched version
        lg.stream_graph_updates = ui_stream_graph_updates

# For testing the UI independently
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AuroraUI()
    window.show()
    sys.exit(app.exec())

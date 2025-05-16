# Aurora UI Module

This module provides a graphical user interface for the Aurora voice assistant, supporting both voice and text-based interactions.

## Features

- Text chat interface for typing messages to the assistant
- Display of conversation history
- Status indicators showing when the system is:
  - Idle
  - Listening
  - Processing
  - Speaking
- Voice control buttons for manual activation and stopping
- Full integration with existing STT and TTS functionality

## Setup

To set up the UI module, run the setup script:

```bash
pip install -r requirements.txt
```

This will install the required PyQt6 dependencies.

## Usage

The UI is automatically launched when running the main.py script. You can:

1. Type messages in the text field and click "Send" to interact via text
2. Click "Activate Voice" to manually trigger voice input
3. Say the wake word "Jarvis" to activate voice input via the wake word system
4. Click "Stop" to stop any ongoing voice output

## Architecture

The UI module hooks into the existing STT and TTS systems through callback replacements, ensuring that all existing functionality continues to work while adding visual representation of the interaction.

The interface is built with PyQt6 and runs in the main thread, while speech recognition and processing occur in background threads to keep the UI responsive.

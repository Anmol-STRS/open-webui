"""
Check what models are configured and being used
"""
import sys
import os
import io

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Silence warnings
import warnings
warnings.filterwarnings('ignore')

from open_webui.models.chats import Chats

print("Checking models used in chats...\n")

chats = Chats.get_chats()

for chat in chats:
    print(f"Chat: {chat.title}")
    chat_payload = chat.chat if isinstance(chat.chat, dict) else {}

    # Get messages
    history = chat_payload.get("history", {})
    messages = history.get("messages", {})

    if isinstance(messages, dict):
        for msg_id, message in messages.items():
            if message.get('role') == 'assistant':
                model = message.get('model', 'unknown')
                modelName = message.get('modelName', 'unknown')
                print(f"  Assistant message:")
                print(f"    Model ID: {model}")
                print(f"    Model Name: {modelName}")

                # Check if message has any info field
                if 'info' in message:
                    print(f"    Info field: {message['info']}")
                else:
                    print(f"    No 'info' field found")

                if 'usage' in message:
                    print(f"    Usage field: {message['usage']}")
                else:
                    print(f"    No 'usage' field found")
                print()

# Check environment configuration
print("\n" + "="*60)
print("Checking OpenAI API configuration...")

from open_webui.env import OPENAI_API_BASE_URLS, OPENAI_API_KEYS, ENABLE_OPENAI_API

print(f"ENABLE_OPENAI_API: {ENABLE_OPENAI_API}")
print(f"OPENAI_API_BASE_URLS: {OPENAI_API_BASE_URLS}")
print(f"Has API keys configured: {bool(OPENAI_API_KEYS)}")

# Check for Ollama
try:
    from open_webui.env import OLLAMA_BASE_URLS, ENABLE_OLLAMA_API
    print(f"\nENABLE_OLLAMA_API: {ENABLE_OLLAMA_API}")
    print(f"OLLAMA_BASE_URLS: {OLLAMA_BASE_URLS}")
except:
    pass

print("\nDone!")

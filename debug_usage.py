"""
Debug script to check if usage data exists in chat messages
"""
import sys
import os
import io

# Fix encoding for Windows console
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Silence warnings during import
import warnings
warnings.filterwarnings('ignore')

from open_webui.models.chats import Chats

# Import functions directly to avoid main.py execution
import json

def _extract_usage_payload(message: dict):
    if not isinstance(message, dict):
        return None

    usage = message.get("usage")
    if isinstance(usage, dict):
        return usage

    info = message.get("info")
    if isinstance(info, dict):
        nested_usage = info.get("usage")
        if isinstance(nested_usage, dict):
            return nested_usage

    return None

def _iter_chat_messages(chat_payload: dict):
    if not isinstance(chat_payload, dict):
        return

    seen_ids = set()

    # Check history.messages
    history = chat_payload.get("history")
    if isinstance(history, dict):
        messages = history.get("messages")
        if isinstance(messages, dict):
            for message in messages.values():
                if isinstance(message, dict):
                    message_id = message.get("id")
                    if message_id and message_id not in seen_ids:
                        seen_ids.add(message_id)
                        yield message

    # Check messages
    messages = chat_payload.get("messages")
    if isinstance(messages, (dict, list)):
        if isinstance(messages, dict):
            messages = messages.values()
        for message in messages:
            if isinstance(message, dict):
                message_id = message.get("id")
                if message_id and message_id not in seen_ids:
                    seen_ids.add(message_id)
                    yield message

print("Starting usage data check...")

# Get all chats
chats = Chats.get_chats()
print(f"\nFound {len(chats)} total chats")

# Check each chat for usage data
for chat in chats:
    print(f"\n{'='*60}")
    print(f"Chat ID: {chat.id}")
    print(f"Title: {chat.title}")
    print(f"User ID: {chat.user_id}")

    chat_payload = chat.chat if isinstance(chat.chat, dict) else {}

    # Check messages
    message_count = 0
    usage_count = 0

    messages_list = list(_iter_chat_messages(chat_payload))
    message_count = len(messages_list)

    for idx, message in enumerate(messages_list, 1):
        usage_payload = _extract_usage_payload(message)

        if usage_payload:
            usage_count += 1
            print(f"\n  Message {idx}/{message_count}:")
            print(f"    Role: {message.get('role', 'unknown')}")
            print(f"    Message ID: {message.get('id', 'no-id')[:8]}...")
            print(f"    Has usage: YES")
            print(f"    Usage keys: {list(usage_payload.keys())}")
        elif idx <= 3:  # Show first 3 messages without usage
            print(f"\n  Message {idx}/{message_count}:")
            print(f"    Role: {message.get('role', 'unknown')}")
            print(f"    Has usage: NO")
            # Check what keys exist
            print(f"    Available keys: {list(message.keys())}")

    print(f"\n  Summary: {message_count} messages, {usage_count} with usage data")

    # Also check structure
    if message_count > 0:
        print(f"\n  Chat structure:")
        print(f"    Has 'messages': {bool(chat_payload.get('messages'))}")
        print(f"    Has 'history': {bool(chat_payload.get('history'))}")
        if chat_payload.get('history'):
            hist_msgs = chat_payload.get('history', {}).get('messages')
            print(f"    History has 'messages': {bool(hist_msgs)}")
            if hist_msgs and isinstance(hist_msgs, dict):
                print(f"    History message count: {len(hist_msgs)}")

print(f"\n{'='*60}")
print("Debug complete!")

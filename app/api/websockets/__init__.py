"""WebSocket endpoints for realtime roleplay sessions.

Step 18 scope: connection lifecycle, heartbeat, and a scripted mock
conversation driving transcript/streaming/session-update messages. No LLM
or voice provider is called here — see mock_conversation.py — those get
wired in once this protocol layer is proven out.
"""

"""Serialize memory-heavy CPU services; generator and vision caches are exclusive."""
import threading
LOCK=threading.RLock()

"""
Jira Poller — background daemon that polls Jira every 30 seconds for new
"To Do" tickets and enqueues them for the PACE pipeline.

Start via FastAPI lifespan:
    poller_thread = start_poller()
    worker_thread = start_worker()

Stop on shutdown:
    stop_poller()
"""
import threading
import logging
from queue import Queue, Empty

from jira.jira_client import search_tickets
from orchestrator.pace_orchestrator import run_pace

logger = logging.getLogger(__name__)

POLL_INTERVAL = 30  # seconds
JIRA_JQL = 'project=AA AND status="To Do" AND labels NOT IN (pace-in-progress, pace-shipped)'

# Shared state
ticket_queue: Queue = Queue()
_seen_tickets: set[str] = set()
_stop_event: threading.Event = threading.Event()


# ── Public API ────────────────────────────────────────────────────────────────

def start_poller() -> threading.Thread:
    """Start the Jira polling daemon thread."""
    thread = threading.Thread(target=_poll_loop, daemon=True, name="jira-poller")
    thread.start()
    logger.info("Jira poller started (interval=%ds, jql=%r)", POLL_INTERVAL, JIRA_JQL)
    return thread


def start_worker() -> threading.Thread:
    """Start the PACE pipeline worker daemon thread."""
    thread = threading.Thread(target=_worker_loop, daemon=True, name="pace-worker")
    thread.start()
    logger.info("PACE worker started")
    return thread


def stop_poller() -> None:
    """Signal both threads to stop."""
    _stop_event.set()
    logger.info("Jira poller stop requested")


def queue_depth() -> int:
    return ticket_queue.qsize()


def seen_count() -> int:
    return len(_seen_tickets)


# ── Internal loops ────────────────────────────────────────────────────────────

def _poll_loop() -> None:
    while not _stop_event.is_set():
        try:
            tickets = search_tickets(JIRA_JQL)
            for ticket in tickets:
                ticket_id = ticket["id"]
                if ticket_id not in _seen_tickets:
                    _seen_tickets.add(ticket_id)
                    ticket_queue.put(ticket_id)
                    logger.info("Queued new ticket: %s", ticket_id)
        except Exception as e:
            logger.warning("Jira poll failed: %s", e)

        _stop_event.wait(timeout=POLL_INTERVAL)


def _worker_loop() -> None:
    """Process one ticket at a time (serialized to avoid git branch conflicts)."""
    while not _stop_event.is_set():
        try:
            ticket_id = ticket_queue.get(timeout=5)
        except Empty:
            continue
        try:
            logger.info("PACE pipeline starting for ticket: %s", ticket_id)
            result = run_pace(ticket_id)
            logger.info("PACE pipeline complete for %s: %s",
                        ticket_id, result.get("pipeline_decision"))
        except Exception as e:
            logger.error("PACE pipeline failed for %s: %s", ticket_id, e)
        finally:
            ticket_queue.task_done()

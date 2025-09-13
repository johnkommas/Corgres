import socket

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
import os
import json
import shutil
import uuid
from typing import Dict, Optional, List, Set, Any
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio

from src.data.etl import get_column_mapping_template, validate_main_unit_measurement, validate_alternative_unit_measurement, read_excel, validate_column_values, load_row_mappings, add_row_mapping
from src.utils.logger import get_api_logger, get_app_logger, get_data_processing_logger, get_error_logger, get_all_logs
from src.email.email_scanner import get_emails_with_attachments, save_attachment_from_email, list_mail_folders
from src.data.column_mapper import add_mapping, get_suggestions
from src.pricing.engine import PricingEngine, PricingRequest, load_tariffs, KG_PER_M2


# Function to process logs and generate statistics
def process_logs_for_stats(logs, log_type='all', days=7, start_date=None, end_date=None):
    """
    Process logs and generate statistics for charts

    Args:
        logs: List of log entries
        log_type: Type of logs to filter (all, api, app, data_processing, database, errors)
        days: Number of days to include
        start_date: Start date for filtering (format: YYYY-MM-DD)
        end_date: End date for filtering (format: YYYY-MM-DD)

    Returns:
        Dictionary with statistics
    """
    # Filter logs by type if specified
    if log_type != 'all':
        logs = [log for log in logs if log['type'] == log_type]

    # Filter logs by date range
    filtered_logs = []
    if start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        end = end.replace(hour=23, minute=59, second=59)  # Include the entire end day

        for log in logs:
            log_date = log['timestamp']
            if start <= log_date <= end:
                filtered_logs.append(log)
    else:
        # Use the last N days
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered_logs = [log for log in logs if log['timestamp'] >= cutoff_date]

    # Initialize counters
    stats = {
        'total': len(filtered_logs),
        'by_level': defaultdict(int),
        'by_logger': defaultdict(int),
        'by_day': defaultdict(int),
        'by_hour': defaultdict(int),
        'time_series': defaultdict(lambda: defaultdict(int)),
        'message_counts': defaultdict(int)  # For tracking common messages
    }

    # Process each log entry
    for log in filtered_logs:
        # Check if the log message uses tabs or dashes as separators
        if "\t" in log['message']:
            # New format with tabs
            log_parts = log['message'].split("\t")
            if len(log_parts) >= 3:
                log_level_part = log_parts[2].strip()
                # Handle format with brackets
                if log_level_part.startswith("[") and log_level_part.endswith("]"):
                    log_level = log_level_part[1:-1]  # Remove brackets
                else:
                    log_level = log_level_part
                stats['by_level'][log_level] += 1
        else:
            # Old format with dashes
            log_parts = log['message'].split(' - ')
            if len(log_parts) >= 3:
                log_level_part = log_parts[2].strip()
                # Handle both formats (with or without brackets)
                if log_level_part.startswith("[") and log_level_part.endswith("]"):
                    log_level = log_level_part[1:-1]  # Remove brackets
                else:
                    log_level = log_level_part
                stats['by_level'][log_level] += 1

        # Count by logger type
        stats['by_logger'][log['type']] += 1

        # Count by day
        day = log['timestamp'].strftime('%Y-%m-%d')
        stats['by_day'][day] += 1

        # Count by hour
        hour = log['timestamp'].strftime('%H')
        stats['by_hour'][hour] += 1

        # Time series data (by day and log level)
        day = log['timestamp'].strftime('%Y-%m-%d')

        # Extract message content for common messages tracking
        actual_message = ""

        # Check if the log message uses tabs or dashes as separators
        if "\t" in log['message']:
            # New format with tabs
            log_parts = log['message'].split("\t")
            if len(log_parts) >= 3:
                log_level_part = log_parts[2].strip()
                # Handle format with brackets
                if log_level_part.startswith("[") and log_level_part.endswith("]"):
                    log_level = log_level_part[1:-1]  # Remove brackets
                else:
                    log_level = log_level_part
                stats['time_series'][day][log_level] += 1

                # Extract actual message content (parts after the log level)
                if len(log_parts) >= 4:
                    actual_message = log_parts[3].strip()
        else:
            # Old format with dashes
            log_parts = log['message'].split(' - ')
            if len(log_parts) >= 3:
                log_level_part = log_parts[2].strip()
                # Handle both formats (with or without brackets)
                if log_level_part.startswith("[") and log_level_part.endswith("]"):
                    log_level = log_level_part[1:-1]  # Remove brackets
                else:
                    log_level = log_level_part
                stats['time_series'][day][log_level] += 1

                # Extract actual message content (parts after the log level)
                if len(log_parts) >= 4:
                    actual_message = log_parts[3].strip()

        # Count message occurrences if we have a valid message
        if actual_message:
            stats['message_counts'][actual_message] += 1

    # Convert defaultdicts to regular dicts for JSON serialization
    stats['by_level'] = dict(stats['by_level'])
    stats['by_logger'] = dict(stats['by_logger'])
    stats['by_day'] = dict(stats['by_day'])
    stats['by_hour'] = dict(stats['by_hour'])
    stats['time_series'] = {k: dict(v) for k, v in stats['time_series'].items()}

    # Convert message counts to array of objects sorted by count
    message_counts = dict(stats['message_counts'])
    common_messages = [
        {'message': message, 'count': count}
        for message, count in message_counts.items()
    ]
    # Sort by count in descending order and limit to top 10
    common_messages.sort(key=lambda x: x['count'], reverse=True)
    stats['common_messages'] = common_messages[:10]

    # Remove the message_counts from the final stats
    del stats['message_counts']

    return stats

# Initialize loggers
api_logger = get_api_logger()
app_logger = get_app_logger()
data_logger = get_data_processing_logger()
error_logger = get_error_logger()

# Create directories if they don't exist
os.makedirs("src/static", exist_ok=True)
os.makedirs("src/data/uploads", exist_ok=True)
os.makedirs("src/data/processed", exist_ok=True)

# Initialize pricing engine tariffs
TARIFFS_BASE = os.path.join("src", "pricing", "tariffs")
try:
    PRICING_TARIFFS = load_tariffs(TARIFFS_BASE)
    PRICING_ENGINE = PricingEngine(PRICING_TARIFFS)
    app_logger.info("Pricing engine initialized with tariffs")
except Exception as e:
    PRICING_TARIFFS = None
    PRICING_ENGINE = None
    error_logger.error(f"Failed to initialize pricing engine: {e}")

api = FastAPI(
    title="Softone ERP Excel Formatter",
    description="An application to process Excel files for Softone ERP system",
    version="1.0.0",
    docs_url=None,  # Disable Swagger UI
    redoc_url=None  # Disable ReDoc
)


# Log application startup
app_logger.info("Application starting up")

# Add CORS middleware
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        # Active connections
        self.active_connections: List[WebSocket] = []
        # Active users per application (kept for backward compatibility with frontend; populated from app_visitors)
        self.active_users: Dict[str, List[str]] = {
            "excel-formatter": [],
            "retail-pricing": []
        }
        # Unique visitor IDs per application (authoritative source for per-app unique counts)
        self.app_visitors: Dict[str, Set[str]] = {
            "excel-formatter": set(),
            "retail-pricing": set()
        }
        # Dictionary to track unique visitors by visitor ID
        self.unique_visitors: Dict[str, Dict] = {}
        # Dictionary to map connection IDs to visitor IDs
        self.connection_to_visitor: Dict[str, str] = {}
        # Dictionary to track browsers per visitor
        self.visitor_browsers: Dict[str, Set[str]] = {}
        # Dictionary to track tabs per visitor
        self.visitor_tabs: Dict[str, Set[str]] = {}
        # Dictionary to track platform information per visitor
        self.visitor_platforms: Dict[str, Dict[str, str]] = {}
        # Dictionary to track masked IP per visitor
        self.visitor_ips: Dict[str, str] = {}
        # Dictionary to track device info (type and OS) per visitor
        self.visitor_device: Dict[str, Dict[str, str]] = {}
        # Dictionary to track network/host name per visitor (best-effort)
        self.visitor_nets: Dict[str, str] = {}
        # Dictionary to track last heartbeat time for each connection
        self.last_heartbeat: Dict[str, datetime] = {}
        # Heartbeat timeout in seconds (30 seconds)
        self.heartbeat_timeout = 30

    async def connect(self, websocket: WebSocket, connection_id: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Record initial heartbeat
        self.last_heartbeat[connection_id] = datetime.now()
        # Send current state to the new connection
        await self.send_personal_message({"active_users": self.active_users}, websocket)

    def disconnect(self, websocket: WebSocket, connection_id: str = None):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

        # Remove heartbeat record if connection_id is provided
        if connection_id and connection_id in self.last_heartbeat:
            del self.last_heartbeat[connection_id]

    def record_heartbeat(self, connection_id: str):
        """Record a heartbeat for the given connection"""
        self.last_heartbeat[connection_id] = datetime.now()

    async def cleanup_stale_connections(self):
        """Check for stale connections and clean them up"""
        now = datetime.now()
        stale_connections = []

        # Find stale connections
        for connection_id, last_time in list(self.last_heartbeat.items()):
            if (now - last_time).total_seconds() > self.heartbeat_timeout:
                stale_connections.append(connection_id)

        # Clean up stale connections
        for connection_id in stale_connections:
            api_logger.info(f"Cleaning up stale connection: {connection_id}")

            # Remove from last_heartbeat
            if connection_id in self.last_heartbeat:
                del self.last_heartbeat[connection_id]

            # If we have a visitor ID for this connection, update their data
            if connection_id in self.connection_to_visitor:
                visitor_id = self.connection_to_visitor[connection_id]
                if visitor_id in self.unique_visitors and "connections" in self.unique_visitors[visitor_id]:
                    if connection_id in self.unique_visitors[visitor_id]["connections"]:
                        self.unique_visitors[visitor_id]["connections"].remove(connection_id)

                    # If this was the last connection for this visitor, clean up their data
                    if len(self.unique_visitors[visitor_id]["connections"]) == 0:
                        # Remove tabs for this visitor
                        if visitor_id in self.visitor_tabs:
                            del self.visitor_tabs[visitor_id]

                        # Remove browsers for this visitor
                        if visitor_id in self.visitor_browsers:
                            del self.visitor_browsers[visitor_id]

                        # Remove platform info for this visitor
                        if visitor_id in self.visitor_platforms:
                            del self.visitor_platforms[visitor_id]

                        # Remove visitor from all apps (unique visitor tracking)
                        for app_name, vset in self.app_visitors.items():
                            if visitor_id in vset:
                                vset.remove(visitor_id)
                                # Sync list representation
                                self.active_users[app_name] = list(vset)
                        # Remove visitor from unique_visitors
                        del self.unique_visitors[visitor_id]

                # Remove the connection mapping
                del self.connection_to_visitor[connection_id]

            # Remove the user from all apps
            for app in self.active_users:
                if connection_id in self.active_users[app]:
                    self.active_users[app].remove(connection_id)

        # If we cleaned up any connections, broadcast the updated state
        if stale_connections:
            await broadcast_presence()

    async def broadcast(self, message: dict):
        # Add total active users and unique visitors to the message
        message["total_active_users"] = sum(len(users) for users in self.active_users.values())
        message["unique_visitors"] = len(self.unique_visitors)

        # Add browser and tab statistics if available
        browsers_count = sum(len(browsers) for browsers in self.visitor_browsers.values())
        tabs_count = sum(len(tabs) for tabs in self.visitor_tabs.values())
        message["browser_count"] = browsers_count
        message["tab_count"] = tabs_count

        # Add visitor hierarchy data for the diagram
        message["visitor_hierarchy"] = self.get_visitor_hierarchy()

        for connection in self.active_connections:
            await connection.send_json(message)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        # Add total active users and unique visitors to the message
        message["total_active_users"] = sum(len(users) for users in self.active_users.values())
        message["unique_visitors"] = len(self.unique_visitors)

        # Add browser and tab statistics if available
        browsers_count = sum(len(browsers) for browsers in self.visitor_browsers.values())
        tabs_count = sum(len(tabs) for tabs in self.visitor_tabs.values())
        message["browser_count"] = browsers_count
        message["tab_count"] = tabs_count

        # Add visitor hierarchy data for the diagram
        message["visitor_hierarchy"] = self.get_visitor_hierarchy()

        await websocket.send_json(message)

    def get_visitor_hierarchy(self):
        """
        Generate a hierarchical data structure for visualization

        Returns:
            dict: A hierarchical data structure with visitors, devices, browsers, and tabs
        """
        # Create the root node for the hierarchy
        hierarchy = {
            "name": "Unique Users",
            "value": len(self.unique_visitors),
            "children": []
        }

        # Group visitors by platform (device type)
        platforms = {}

        for visitor_id, visitor_data in self.unique_visitors.items():
            # Get all browsers used by this visitor
            browsers = self.visitor_browsers.get(visitor_id, set())

            for browser in browsers:
                # Get platform information from stored data
                platform = "Unknown"

                # Check if we have platform information for this browser
                if visitor_id in self.visitor_platforms and browser in self.visitor_platforms[visitor_id]:
                    platform_info = self.visitor_platforms[visitor_id][browser]

                    # Use platform information to determine device type
                    if platform_info == "iPhone":
                        platform = "iPhone"
                    elif platform_info == "iPad":
                        platform = "Tablet"
                    elif "Mac" in platform_info:
                        platform = "Laptop"
                    elif "Win" in platform_info:
                        platform = "PC"
                    elif "Android" in platform_info:
                        platform = "Android Phone"
                    else:
                        # Check user agent for additional clues
                        if visitor_id in self.visitor_platforms and "user_agents" in self.visitor_platforms[visitor_id] and browser in self.visitor_platforms[visitor_id]["user_agents"]:
                            user_agent = self.visitor_platforms[visitor_id]["user_agents"][browser]

                            if "iPhone" in user_agent:
                                platform = "iPhone"
                            elif "iPad" in user_agent:
                                platform = "Tablet"
                            elif "Android" in user_agent:
                                platform = "Android Phone"
                            elif "Mobile" in user_agent:
                                platform = "Mobile"
                            elif "Windows" in user_agent:
                                platform = "PC"
                            elif "Macintosh" in user_agent:
                                platform = "Laptop"
                            else:
                                # Fallback to browser-based detection
                                if "Mobile" in browser or "Android" in browser or "iPhone" in browser or "iPad" in browser:
                                    if "iPad" in browser:
                                        platform = "Tablet"
                                    elif "iPhone" in browser:
                                        platform = "iPhone"
                                    elif "Android" in browser:
                                        platform = "Android Phone"
                                    else:
                                        platform = "Mobile"
                                elif "Windows" in browser:
                                    platform = "PC"
                                elif "Mac" in browser or "Safari" in browser:
                                    platform = "Laptop"
                                else:
                                    platform = "Other"
                        else:
                            # Fallback to browser-based detection
                            if "Mobile" in browser or "Android" in browser or "iPhone" in browser or "iPad" in browser:
                                if "iPad" in browser:
                                    platform = "Tablet"
                                elif "iPhone" in browser:
                                    platform = "iPhone"
                                elif "Android" in browser:
                                    platform = "Android Phone"
                                else:
                                    platform = "Mobile"
                            elif "Windows" in browser:
                                platform = "PC"
                            elif "Mac" in browser or "Safari" in browser:
                                platform = "Laptop"
                            else:
                                platform = "Other"
                else:
                    # Fallback to browser-based detection
                    if "Mobile" in browser or "Android" in browser or "iPhone" in browser or "iPad" in browser:
                        if "iPad" in browser:
                            platform = "Tablet"
                        elif "iPhone" in browser:
                            platform = "iPhone"
                        elif "Android" in browser:
                            platform = "Android Phone"
                        else:
                            platform = "Mobile"
                    elif "Windows" in browser:
                        platform = "PC"
                    elif "Mac" in browser or "Safari" in browser:
                        platform = "Laptop"
                    else:
                        platform = "Other"

                # Add to platforms dictionary
                if platform not in platforms:
                    platforms[platform] = {
                        "name": platform,
                        "value": 0,
                        "children": {}
                    }

                # Increment count for this platform
                platforms[platform]["value"] += 1

                # Add browser to this platform if not already present
                if browser not in platforms[platform]["children"]:
                    platforms[platform]["children"][browser] = {
                        "name": browser,
                        "value": 0,
                        "children": []
                    }

                # Increment count for this browser
                platforms[platform]["children"][browser]["value"] += 1

                # Add tabs for this visitor and browser
                tabs = self.visitor_tabs.get(visitor_id, set())
                for tab in tabs:
                    platforms[platform]["children"][browser]["children"].append({
                        "name": f"Tab {tab[:8]}...",
                        "value": 1
                    })

        # Convert the platforms dictionary to a list for the hierarchy
        for platform, platform_data in platforms.items():
            platform_node = {
                "name": f"{platform} ({platform_data['value']} Users)",
                "value": platform_data["value"],
                "children": []
            }

            # Add browsers as children of the platform
            for browser, browser_data in platform_data["children"].items():
                browser_node = {
                    "name": f"{browser} ({browser_data['value']} Users)",
                    "value": browser_data["value"],
                    "children": browser_data["children"]
                }
                platform_node["children"].append(browser_node)

            hierarchy["children"].append(platform_node)

        return hierarchy

    async def add_user_to_app(self, app: str, visitor_id: str):
        # Ensure structures exist for the app
        if app not in self.app_visitors:
            self.app_visitors[app] = set()
        if app not in self.active_users:
            self.active_users[app] = []
        # Add visitor to the app's unique visitor set
        before_count = len(self.app_visitors[app])
        self.app_visitors[app].add(visitor_id)
        # Keep active_users list in sync (for frontend consumption)
        self.active_users[app] = list(self.app_visitors[app])
        # Only broadcast if there was a change in unique visitors
        if len(self.app_visitors[app]) != before_count:
            await self.broadcast({"active_users": self.active_users})

    async def remove_user_from_app(self, app: str, visitor_id: str):
        # Remove from authoritative set if present
        if app in self.app_visitors and visitor_id in self.app_visitors[app]:
            self.app_visitors[app].remove(visitor_id)
            # Sync list representation
            self.active_users[app] = list(self.app_visitors[app])
            await self.broadcast({"active_users": self.active_users})

# Initialize connection manager
manager = ConnectionManager()

# Serve static files
api.mount("/static", StaticFiles(directory="src/static"), name="static")
api.mount("/images", StaticFiles(directory="src/static/images"), name="images")
api.mount("/css", StaticFiles(directory="src/static/css"), name="css")

@api.get("/", response_class=HTMLResponse)
async def root():
    """
    Root endpoint that serves the selection.html file
    """
    api_logger.info("Serving selection.html")
    with open("src/static/selection.html", encoding="utf-8") as f:
        return f.read()

@api.get("/access-closed", response_class=HTMLResponse)
async def access_closed():
    """
    Informational page shown when access is closed for security reasons.
    """
    api_logger.info("Serving access-closed.html")
    filepath = "src/static/access-closed.html"
    if os.path.exists(filepath):
        with open(filepath, encoding="utf-8") as f:
            return f.read()
    # Fallback minimal HTML if the file is missing
    return HTMLResponse(content=(
        "<html><head><title>Access Restricted</title>" 
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<style>body{font-family:Arial,Helvetica,sans-serif;background:#0f172a;color:#e2e8f0;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}"
        ".card{max-width:720px;background:#111827;border:1px solid #374151;border-radius:12px;padding:28px;box-shadow:0 10px 25px rgba(0,0,0,0.4)}"
        ".title{font-size:1.6rem;margin:0 0 12px;color:#f87171} .muted{color:#9ca3af} a.btn{display:inline-block;margin-top:18px;padding:10px 14px;background:#2563eb;color:#fff;text-decoration:none;border-radius:8px}"
        "code{background:#1f2937;padding:2px 6px;border-radius:6px}</style></head><body>"
        "<div class='card'><h1 class='title'>Access temporarily restricted</h1>"
        "<p class='muted'>For security reasons and to protect sensitive HR data, access to this application is currently closed from this port or network path.</p>"
        "<p class='muted'>Please access the service via the approved internal link (e.g., port <code>8000</code>) if you have authorization, or contact your administrator.</p>"
        "</div></body></html>"
    ), status_code=200)

@api.get("/excel-formatter", response_class=HTMLResponse)
async def excel_formatter():
    """
    Endpoint that serves the Excel Formatter application (index.html)
    """
    api_logger.info("Serving Excel Formatter (index.html)")
    with open("src/static/index.html", encoding="utf-8") as f:
        return f.read()

@api.get("/pricing", response_class=HTMLResponse)
async def retail_pricing():
    """
    Endpoint that serves the Retail Pricing Calculator (pricing.html)
    """
    api_logger.info("Serving Retail Pricing Calculator (pricing.html)")
    with open("src/static/pricing.html", encoding="utf-8") as f:
        return f.read()

@api.get("/pricing/slabs", response_class=HTMLResponse)
async def retail_pricing_slabs():
    """
    Endpoint that serves the SLABs Pricing Calculator (slabs.html)
    """
    api_logger.info("Serving SLABs Pricing Calculator (slabs.html)")
    filepath = "src/static/slabs.html"
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="SLABs page not found")
    with open(filepath, encoding="utf-8") as f:
        return f.read()

# Helper to mask client IPs for privacy-safe display

def mask_ip(ip: str) -> str:
    if not ip:
        return ""
    if ":" in ip:  # IPv6 simple mask
        parts = ip.split(":")
        return ":".join(parts[:3] + ["…"]) if len(parts) > 3 else ip
    parts = ip.split(".")
    return ".".join(parts[:3] + ["xxx"]) if len(parts) == 4 else ip

# Best-effort resolve network/host name for IP without blocking event loop
async def resolve_net_name(visitor_id: str, ip: str):
    try:
        if not ip:
            return
        # Avoid resolving repeatedly
        if manager.visitor_nets.get(visitor_id):
            return
        hostname = await asyncio.to_thread(socket.gethostbyaddr, ip)
        if isinstance(hostname, tuple):
            host = hostname[0]
        else:
            host = str(hostname)
        # Basic sanity check
        if host and host != ip and not host.endswith(".in-addr.arpa"):
            manager.visitor_nets[visitor_id] = host
            await broadcast_presence()
    except Exception:
        # Ignore resolution errors/timeouts
        pass

# Broadcast richer presence payload to all WS clients
async def broadcast_presence():
    try:
        payload = {
            "type": "presence",
            "apps": {app: list(vset) for app, vset in manager.app_visitors.items()},
            "visitors": [
                {
                    "visitorId": vid,
                    "ip": manager.visitor_ips.get(vid, ""),
                    "browsers": list(manager.visitor_browsers.get(vid, [])),
                    "tabs": len(manager.visitor_tabs.get(vid, [])),
                    "deviceType": manager.visitor_device.get(vid, {}).get("deviceType", ""),
                    "deviceModel": manager.visitor_device.get(vid, {}).get("model", ""),
                    "os": manager.visitor_device.get(vid, {}).get("os", ""),
                    "net": manager.visitor_nets.get(vid, ""),
                }
                for vid in manager.unique_visitors.keys()
            ],
        }
        await manager.broadcast(payload)
    except Exception as e:
        api_logger.error(f"presence broadcast error: {e}")

# Presence snapshot endpoint (optional)
@api.get("/presence")
async def presence():
    return JSONResponse({
        "apps": {app: list(vset) for app, vset in manager.app_visitors.items()},
        "visitors": [
            {
                "visitorId": vid,
                "ip": manager.visitor_ips.get(vid, ""),
                "browsers": list(manager.visitor_browsers.get(vid, [])),
                "tabs": len(manager.visitor_tabs.get(vid, [])),
                "deviceType": manager.visitor_device.get(vid, {}).get("deviceType", ""),
                "deviceModel": manager.visitor_device.get(vid, {}).get("model", ""),
                "os": manager.visitor_device.get(vid, {}).get("os", ""),
                "net": manager.visitor_nets.get(vid, ""),
            }
            for vid in manager.unique_visitors.keys()
        ],
    })

@api.websocket("/ws/app-status")
async def websocket_app_status(websocket: WebSocket):
    """
    WebSocket endpoint for app status updates
    """
    # Generate a unique ID for this connection
    connection_id = str(uuid.uuid4())
    visitor_id = None

    try:
        await manager.connect(websocket, connection_id)
        api_logger.info(f"WebSocket connection established: {connection_id}")

        # Capture client IP from headers (respect proxies)
        try:
            xff = websocket.headers.get("x-forwarded-for") or websocket.headers.get("x-real-ip")
            client_ip = (xff.split(",")[0].strip() if xff else getattr(websocket.client, "host", None))
        except Exception:
            client_ip = None

        # Start background task to clean up stale connections
        background_tasks = BackgroundTasks()
        background_tasks.add_task(cleanup_stale_connections_task)

        while True:
            # Wait for messages from the client with a timeout
            try:
                data = await asyncio.wait_for(websocket.receive_json(), timeout=manager.heartbeat_timeout)
                api_logger.info(f"WebSocket message received: {data}")

                # Record heartbeat for this connection
                manager.record_heartbeat(connection_id)

                # Process the message
                if "action" in data:
                    # Handle heartbeat
                    if data["action"] == "heartbeat":
                        # Send a pong response
                        await websocket.send_json({"action": "pong"})
                        continue

                    # Handle visitor identification
                    if data["action"] == "identify" and "visitorId" in data:
                        visitor_id = data["visitorId"]
                        browser_info = data.get("browserInfo", {})
                        tab_id = data.get("tabId", "unknown_tab")

                        # Store the mapping from connection to visitor
                        manager.connection_to_visitor[connection_id] = visitor_id

                        # Add or update visitor information
                        if visitor_id not in manager.unique_visitors:
                            manager.unique_visitors[visitor_id] = {
                                "first_seen": datetime.now().isoformat(),
                                "connections": [connection_id]
                            }
                            manager.visitor_browsers[visitor_id] = set()
                            manager.visitor_tabs[visitor_id] = set()
                            manager.visitor_platforms[visitor_id] = {}
                        else:
                            if connection_id not in manager.unique_visitors[visitor_id]["connections"]:
                                manager.unique_visitors[visitor_id]["connections"].append(connection_id)

                        # Update browser information if available
                        if browser_info and "browser" in browser_info:
                            browser_name = browser_info["browser"]
                            manager.visitor_browsers[visitor_id].add(browser_name)

                            # Store platform information
                            if "platform" in browser_info:
                                platform_name = browser_info["platform"]
                                manager.visitor_platforms[visitor_id][browser_name] = platform_name

                            # Store user agent for additional device detection
                            if "userAgent" in browser_info:
                                user_agent = browser_info["userAgent"]
                                if "user_agents" not in manager.visitor_platforms[visitor_id]:
                                    manager.visitor_platforms[visitor_id]["user_agents"] = {}
                                manager.visitor_platforms[visitor_id]["user_agents"][browser_name] = user_agent

                            # Store device info (type and OS) if provided by client
                            dev_type = browser_info.get("deviceType") or browser_info.get("device_type")
                            os_name = browser_info.get("os") or browser_info.get("osName") or browser_info.get("os_name")
                            dev_model = browser_info.get("deviceModel") or browser_info.get("device_model")
                            if dev_type or os_name or dev_model:
                                manager.visitor_device[visitor_id] = {
                                    "deviceType": dev_type or "",
                                    "os": os_name or "",
                                    "model": dev_model or "",
                                }

                        # Update tab information
                        if tab_id:
                            manager.visitor_tabs[visitor_id].add(tab_id)

                        # Store masked IP for this visitor and resolve net name asynchronously
                        try:
                            if client_ip:
                                manager.visitor_ips[visitor_id] = mask_ip(client_ip)
                                # Kick off best-effort reverse lookup for network/host name
                                try:
                                    asyncio.create_task(resolve_net_name(visitor_id, client_ip))
                                except Exception:
                                    pass
                        except Exception:
                            pass

                        api_logger.info(f"Identified visitor: {visitor_id} using {browser_info.get('browser', 'unknown')} browser, tab: {tab_id}")

                        # Broadcast updated presence stats
                        await broadcast_presence()

                    # Handle app actions if app is specified
                    elif "app" in data:
                        app = data["app"]
                        # Resolve visitor id robustly
                        vid = data.get("visitorId") or visitor_id or manager.connection_to_visitor.get(connection_id) or connection_id

                        if data["action"] == "join":
                            await manager.add_user_to_app(app, vid)
                            api_logger.info(f"User {vid} joined {app}")
                            await broadcast_presence()

                        elif data["action"] == "leave":
                            await manager.remove_user_from_app(app, vid)
                            api_logger.info(f"User {vid} left {app}")
                            await broadcast_presence()

            except asyncio.TimeoutError:
                # Connection timed out, check if it's still active
                if connection_id in manager.last_heartbeat:
                    now = datetime.now()
                    last_time = manager.last_heartbeat[connection_id]
                    if (now - last_time).total_seconds() > manager.heartbeat_timeout:
                        # Connection is stale, close it
                        api_logger.info(f"Connection timed out: {connection_id}")
                        break
                else:
                    # No heartbeat record, close the connection
                    api_logger.info(f"No heartbeat record for connection: {connection_id}")
                    break

    except WebSocketDisconnect:
        api_logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        api_logger.error(f"WebSocket error: {str(e)}")
    finally:
        # Clean up when the connection is closed
        manager.disconnect(websocket, connection_id)

        # Determine visitor id for this connection early (before we delete the mapping)
        vid_to_remove = manager.connection_to_visitor.get(connection_id) if connection_id in manager.connection_to_visitor else None

        # If we have a visitor ID for this connection, update their data
        if vid_to_remove is not None:
            visitor_id = vid_to_remove
            if visitor_id in manager.unique_visitors and "connections" in manager.unique_visitors[visitor_id]:
                if connection_id in manager.unique_visitors[visitor_id]["connections"]:
                    manager.unique_visitors[visitor_id]["connections"].remove(connection_id)

                # If this was the last connection for this visitor, clean up their data
                if len(manager.unique_visitors[visitor_id]["connections"]) == 0:
                    # Remove tabs for this visitor
                    if visitor_id in manager.visitor_tabs:
                        del manager.visitor_tabs[visitor_id]

                    # Remove browsers for this visitor
                    if visitor_id in manager.visitor_browsers:
                        del manager.visitor_browsers[visitor_id]

                    # Remove platform info for this visitor
                    if visitor_id in manager.visitor_platforms:
                        del manager.visitor_platforms[visitor_id]

                    # Remove visitor from unique_visitors
                    del manager.unique_visitors[visitor_id]

        # Remove the user from all apps. If this was the last connection for this visitor, remove their visitor_id from apps.
        last_conn = False
        if vid_to_remove is None:
            # Fallback: we can only remove by connection id (in case join used connection id)
            for app in manager.active_users:
                if connection_id in manager.active_users[app]:
                    await manager.remove_user_from_app(app, connection_id)
        else:
            # If visitor entry no longer exists or has zero connections, it's the last
            if vid_to_remove not in manager.unique_visitors:
                last_conn = True
            else:
                if len(manager.unique_visitors[vid_to_remove].get("connections", [])) == 0:
                    last_conn = True
            if last_conn:
                for app in list(manager.app_visitors.keys()):
                    await manager.remove_user_from_app(app, vid_to_remove)

        # Now it's safe to remove the connection mapping
        if connection_id in manager.connection_to_visitor:
            del manager.connection_to_visitor[connection_id]

        await broadcast_presence()
        api_logger.info(f"WebSocket connection closed: {connection_id}")

# Background task to clean up stale connections
async def cleanup_stale_connections_task():
    """Background task to periodically clean up stale connections"""
    while True:
        try:
            await manager.cleanup_stale_connections()
        except Exception as e:
            error_logger.error(f"Error cleaning up stale connections: {str(e)}")

        # Wait for 30 seconds before checking again
        await asyncio.sleep(30)

@api.get("/logs", response_class=HTMLResponse)
async def logs_page():
    """
    Endpoint that serves the logs.html file
    """
    api_logger.info("Serving logs.html")
    try:
        with open("src/static/logs.html", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        error_logger.error("logs.html not found")
        raise HTTPException(status_code=404, detail="Logs page not found")

@api.get("/api/logs")
async def get_logs(limit: int = None):
    """
    API endpoint to get logs

    Args:
        limit: Maximum number of log entries to return. If None, returns all logs.
    """
    api_logger.info(f"Retrieving logs with limit {limit}")
    try:
        logs = get_all_logs(max_entries=limit)
        return {"logs": logs}
    except Exception as e:
        error_msg = f"Error retrieving logs: {str(e)}"
        error_logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@api.get("/api/logs/stats")
async def get_log_stats(
    log_type: str = 'all',
    days: int = 7,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = None
):
    """
    API endpoint to get log statistics for charts

    Args:
        log_type: Type of logs to filter (all, api, app, data_processing, database, errors)
        days: Number of days to include
        start_date: Start date for filtering (format: YYYY-MM-DD)
        end_date: End date for filtering (format: YYYY-MM-DD)
        limit: Maximum number of log entries to process. If None, processes all logs.

    Returns:
        Dictionary with log statistics
    """
    api_logger.info(f"Retrieving log statistics: type={log_type}, days={days}, start_date={start_date}, end_date={end_date}")
    try:
        # Get logs
        logs = get_all_logs(max_entries=limit)

        # Process logs for statistics
        stats = process_logs_for_stats(logs, log_type, days, start_date, end_date)

        return stats
    except Exception as e:
        error_msg = f"Error retrieving log statistics: {str(e)}"
        error_logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@api.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload an Excel file for processing
    """
    api_logger.info(f"Received file upload: {file.filename}")

    if not file.filename.endswith(('.xls', '.xlsx')):
        error_msg = f"Invalid file type: {file.filename}"
        error_logger.warning(error_msg)
        raise HTTPException(status_code=400, detail="Only Excel files (.xls, .xlsx) are allowed")

    # Generate a unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    filename = f"{timestamp}_{unique_id}_{file.filename}"
    file_path = os.path.join("src/data/uploads", filename)

    # Save the uploaded file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        api_logger.info(f"File saved to {file_path}")
    except Exception as e:
        error_msg = f"Error saving file: {str(e)}"
        error_logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

    # Read the Excel file to get column names
    from src.data.etl import read_excel, get_unique_column_values
    try:
        df = read_excel(file_path)
        column_names = df.columns.tolist()
        data_logger.info(f"Read Excel file with {len(df)} rows and {len(column_names)} columns")

        # Get suggestions for column mapping based on previous mappings
        suggestions = get_suggestions(column_names)
        data_logger.info(f"Generated {len(suggestions)} column mapping suggestions")

        # Get unique values for each column
        unique_values = get_unique_column_values(df)
        data_logger.info(f"Extracted unique values for {len(unique_values)} columns")
    except Exception as e:
        error_msg = f"Error reading column names: {str(e)}"
        error_logger.error(error_msg)
        column_names = []
        suggestions = {}
        unique_values = {}

    return {"filename": filename, "file_path": file_path, "column_names": column_names, "suggestions": suggestions, "unique_values": unique_values}

@api.get("/mail-folders/")
async def get_mail_folders():
    """
    List all available mail folders in the Gmail account

    Returns:
        List of available mail folders
    """
    api_logger.info("Listing available mail folders")

    try:
        # Check if the required environment variables are set
        gmail_user = os.getenv("GMAIL_USER")
        gmail_pass = os.getenv("GMAIL_PASS")

        if not gmail_user or not gmail_pass:
            error_msg = "Missing Gmail credentials. Please check your environment variables."
            error_logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

        # Get all available mail folders
        folders = list_mail_folders()

        # Check if the configured folder exists
        configured_folder = os.getenv("MAIL_FOLDER", "INBOX")
        folder_exists = configured_folder in folders

        return {
            "folders": folders,
            "configured_folder": configured_folder,
            "folder_exists": folder_exists
        }
    except Exception as e:
        error_msg = f"Error listing mail folders: {str(e)}"
        error_logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@api.get("/scan-emails/")
async def scan_emails(days: int = 7, folders: str = None):
    """
    Scan emails for Excel attachments

    Args:
        days (int): Number of days to look back for emails
        folders (str): Comma-separated list of folders to scan

    Returns:
        List of emails with Excel attachments
    """
    api_logger.info(f"Scanning emails for Excel attachments (last {days} days)")

    try:
        # Check if the required environment variables are set
        gmail_user = os.getenv("GMAIL_USER")
        gmail_pass = os.getenv("GMAIL_PASS")

        # Parse folders parameter or use default from environment
        mail_folders = []
        if folders:
            mail_folders = folders.split(',')
            api_logger.info(f"Using folders from request: {mail_folders}")
        else:
            # If no folders specified, use the configured folder from environment
            default_folder = os.getenv("MAIL_FOLDER", "INBOX")
            mail_folders = [default_folder]
            api_logger.info(f"Using default folder from environment: {default_folder}")

        if not gmail_user or not gmail_pass:
            error_msg = "Missing Gmail credentials. Please check your environment variables."
            error_logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

        api_logger.info(f"Scanning folders: {mail_folders}")

        # Get emails with attachments from all selected folders
        emails = get_emails_with_attachments(days, mail_folders)

        # If no emails were found, it could be due to an error or just no matching emails
        if not emails:
            # Check the error logs to see if there was an error
            # This is a simple approach - in a production app, you might want to use a more robust method
            api_logger.info("No emails with Excel attachments found. This could be normal or due to an error.")

        # Remove raw attachment data from response
        for email in emails:
            if "_raw_attachments" in email:
                del email["_raw_attachments"]

        return {"emails": emails}
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error scanning emails: {str(e)}"
        error_logger.error(error_msg)

        # Provide more specific error messages based on the exception
        if "authentication failed" in str(e).lower() or "login failed" in str(e).lower():
            error_msg = "Gmail authentication failed. Please check your credentials."
        elif "select failed" in str(e).lower() or "folder not found" in str(e).lower():
            error_msg = f"Failed to select mail folder '{os.getenv('MAIL_FOLDER', 'INBOX')}'. The folder may not exist."
        elif "network" in str(e).lower() or "connect" in str(e).lower():
            error_msg = "Network error while connecting to Gmail. Please check your internet connection."

        raise HTTPException(status_code=500, detail=error_msg)

@api.post("/fetch-attachment/")
async def fetch_attachment(email_id: str = Form(...), attachment_index: int = Form(0), folders: str = Form(None)):
    """
    Fetch an attachment from an email and save it to the uploads directory

    Args:
        email_id (str): ID of the email
        attachment_index (int): Index of the attachment to fetch
        folders (str): Comma-separated list of folders to scan

    Returns:
        Information about the saved attachment
    """
    api_logger.info(f"Fetching attachment {attachment_index} from email {email_id}")

    try:
        # Parse folders parameter
        mail_folders = None
        if folders:
            mail_folders = folders.split(',')
            api_logger.info(f"Using folders from request: {mail_folders}")

        # Get all emails with attachments from the specified folders
        # Use a reasonable default search range to cover older emails
        emails = get_emails_with_attachments(days=30, folders=mail_folders)

        # Find the email with the specified ID
        email_data = None
        for email in emails:
            if email["id"] == email_id:
                email_data = email
                break

        # If email not found, try with broader search (all folders, extended time range)
        if not email_data:
            api_logger.info(f"Email {email_id} not found with initial search, trying broader search")
            # Try searching in all available folders with extended time range (60 days)
            emails_broader = get_emails_with_attachments(days=60, folders=None)
            for email in emails_broader:
                if email["id"] == email_id:
                    email_data = email
                    api_logger.info(f"Found email {email_id} in broader search")
                    break

        if not email_data:
            # Provide more helpful error message
            folder_info = f" in folders {mail_folders}" if mail_folders else ""
            error_msg = f"Email with ID {email_id} not found{folder_info}. The email may be in a different folder or older than the search range."
            error_logger.error(error_msg)
            raise HTTPException(status_code=404, detail=error_msg)

        # Save the attachment
        file_path = save_attachment_from_email(email_data, attachment_index)

        if not file_path:
            error_msg = f"Failed to save attachment from email {email_id}"
            error_logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

        # Get the filename from the path
        filename = os.path.basename(file_path)

        # Read the Excel file to get column names
        from src.data.etl import read_excel, get_unique_column_values
        try:
            df = read_excel(file_path)
            column_names = df.columns.tolist()
            data_logger.info(f"Read Excel file with {len(df)} rows and {len(column_names)} columns")

            # Get suggestions for column mapping based on previous mappings
            suggestions = get_suggestions(column_names)
            data_logger.info(f"Generated {len(suggestions)} column mapping suggestions")

            # Get unique values for each column
            unique_values = get_unique_column_values(df)
            data_logger.info(f"Extracted unique values for {len(unique_values)} columns")
        except Exception as e:
            error_msg = f"Error reading column names: {str(e)}"
            error_logger.error(error_msg)
            column_names = []
            suggestions = {}
            unique_values = {}

        return {"filename": filename, "file_path": file_path, "column_names": column_names, "suggestions": suggestions, "unique_values": unique_values}
    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Error fetching attachment: {str(e)}"
        error_logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@api.get("/column-mapping-template/")
async def get_mapping_template():
    """
    Get a template for column mapping
    """
    api_logger.info("Retrieving column mapping template")
    template = get_column_mapping_template()
    return template

@api.post("/process/")
async def process_file(
    background_tasks: BackgroundTasks,
    filename: str = Form(...),
    column_mapping: str = Form(...),
    value_mapping: Optional[str] = Form(None),
    accept_auto_mapping: Optional[str] = Form(None),
    skip_auto_mapping: Optional[str] = Form(None)
):
    """
    Process an Excel file with the provided column mapping
    """
    api_logger.info(f"Processing file: {filename}")
    api_logger.info(f"accept_auto_mapping: {accept_auto_mapping}, type: {type(accept_auto_mapping)}")
    api_logger.info(f"skip_auto_mapping: {skip_auto_mapping}, type: {type(skip_auto_mapping)}")

    try:
        # Parse the column mapping JSON
        mapping_dict = json.loads(column_mapping)
        data_logger.info(f"Column mapping: {mapping_dict}")

        # Parse value mapping if provided
        value_mapping_dict = {}
        if value_mapping:
            value_mapping_dict = json.loads(value_mapping)
            data_logger.info(f"Value mapping: {value_mapping_dict}")

        # Validate the input file exists
        input_path = os.path.join("src/data/uploads", filename)
        if not os.path.exists(input_path):
            error_msg = f"File {filename} not found"
            error_logger.error(error_msg)
            raise HTTPException(status_code=404, detail=error_msg)

        # Read the Excel file
        df = read_excel(input_path)

        # Map columns according to the mapping
        from src.data.etl import map_columns
        df = map_columns(df, mapping_dict)

        # Load existing row mappings
        row_mappings = load_row_mappings()
        data_logger.info(f"Loaded row mappings for {len(row_mappings)} columns")

        # Check if there are any values that would be mapped
        potential_mappings = {}
        for column, mappings in row_mappings.items():
            if column in df.columns:
                # Find values in the dataframe that have mappings
                column_values = df[column].astype(str).unique().tolist()
                applicable_mappings = {}
                for val in column_values:
                    if val in mappings:
                        applicable_mappings[val] = mappings[val]

                if applicable_mappings:
                    potential_mappings[column] = applicable_mappings

        # If there are potential mappings and no value_mapping provided, and skip_auto_mapping is not set,
        # return them to the frontend for confirmation
        api_logger.info(f"Checking conditions for auto mapping confirmation:")
        api_logger.info(f"  - potential_mappings: {bool(potential_mappings)}")
        api_logger.info(f"  - value_mapping: {bool(value_mapping)}")
        api_logger.info(f"  - skip_auto_mapping: {bool(skip_auto_mapping)}")
        api_logger.info(f"  - accept_auto_mapping: {bool(accept_auto_mapping)}")

        if potential_mappings and not value_mapping and not skip_auto_mapping and not accept_auto_mapping:
            api_logger.info(f"Found potential mappings: {potential_mappings}")
            api_logger.info("Returning potential mappings to frontend for confirmation")
            return {
                "auto_mapping_available": True,
                "potential_mappings": potential_mappings
            }

        # Log the decision based on flags
        if accept_auto_mapping and accept_auto_mapping.lower() == 'true':
            api_logger.info("User accepted automatic mappings")
        elif skip_auto_mapping and skip_auto_mapping.lower() == 'true':
            api_logger.info("User declined automatic mappings")
        elif not potential_mappings:
            api_logger.info("No potential mappings found")
        else:
            api_logger.info("Proceeding with normal processing")

        # Apply existing row mappings to the data if:
        # 1. accept_auto_mapping is set to 'true' (user explicitly accepted the mappings)
        # 2. There are no potential mappings (no auto-mapping scenario)
        # 3. value_mapping is provided (user has provided manual mappings)
        if (accept_auto_mapping and accept_auto_mapping.lower() == 'true') or not potential_mappings or value_mapping:
            # Log which condition triggered the mapping application
            if accept_auto_mapping and accept_auto_mapping.lower() == 'true':
                data_logger.info("Applying mappings because user accepted automatic mappings")
            elif not potential_mappings:
                data_logger.info("Applying mappings because no potential mappings were found")
            elif value_mapping:
                data_logger.info("Applying mappings because user provided manual mappings")
            for column, mappings in row_mappings.items():
                if column in df.columns:
                    data_logger.info(f"Applying existing row mappings to {column}")
                    # Replace values according to the mapping
                    df[column] = df[column].map(
                        lambda x: mappings.get(str(x), x) if str(x) in mappings else x
                    )

        # Validate Main Unit Measurement values
        validation_result = validate_main_unit_measurement(df)
        data_logger.info(f"Main Unit Measurement validation result: {validation_result}")

        # Validate Alternative Unit Measurement values
        alt_validation_result = validate_alternative_unit_measurement(df)
        data_logger.info(f"Alternative Unit Measurement validation result: {alt_validation_result}")

        # If either validation failed and no value mapping provided, return validation result
        if ((not validation_result["valid"] or not alt_validation_result["valid"]) and not value_mapping):
            api_logger.info("Validation failed. Returning validation result to frontend.")
            # If Main Unit Measurement validation failed, mark Alternative Unit Measurement as invalid too
            if not validation_result["valid"]:
                # Create a combined validation result that includes both fields
                combined_result = validation_result.copy()
                combined_result["alt_unit_invalid"] = True
                combined_result["alt_unit_column"] = alt_validation_result.get("column", "Alternative Unit Measurement")
                # Include the detailed validation result for Alternative Unit Measurement
                combined_result["alt_validation_result"] = alt_validation_result
                return {
                    "validation_required": True,
                    "validation_result": combined_result
                }
            # If only Alternative Unit Measurement validation failed, return that result
            elif not alt_validation_result["valid"]:
                return {
                    "validation_required": True,
                    "validation_result": alt_validation_result
                }

        # If value mapping provided, apply it to the data
        if value_mapping_dict:
            # Determine which column to apply the mapping to
            # If Main Unit Measurement validation failed, use that column
            if not validation_result["valid"]:
                primary_column = validation_result.get("column", "Main Unit Measurement")
                # Also apply to Alternative Unit Measurement if Main Unit Measurement failed
                secondary_column = "Alternative Unit Measurement"
                apply_to_both = True
            # If Alternative Unit Measurement validation failed, use that column
            elif not alt_validation_result["valid"]:
                primary_column = alt_validation_result.get("column", "Alternative Unit Measurement")
                secondary_column = None
                apply_to_both = False
            # Default to Main Unit Measurement if neither failed
            else:
                primary_column = validation_result.get("column", "Main Unit Measurement")
                secondary_column = None
                apply_to_both = False

            # Apply mapping to primary column
            if primary_column in df.columns:
                data_logger.info(f"Applying value mapping to {primary_column}")
                # Replace values according to the mapping
                df[primary_column] = df[primary_column].map(
                    lambda x: value_mapping_dict.get(x, x) if x in value_mapping_dict else x
                )

                # Store the mappings for future use
                for original_value, mapped_value in value_mapping_dict.items():
                    add_row_mapping(primary_column, original_value, mapped_value)

                # Apply the same mapping to secondary column if needed
                if apply_to_both and secondary_column in df.columns:
                    data_logger.info(f"Also applying value mapping to {secondary_column}")
                    # Replace values according to the mapping
                    df[secondary_column] = df[secondary_column].map(
                        lambda x: value_mapping_dict.get(x, x) if x in value_mapping_dict else x
                    )

                    # Store the mappings for future use for the secondary column as well
                    for original_value, mapped_value in value_mapping_dict.items():
                        add_row_mapping(secondary_column, original_value, mapped_value)

                # Validate again after mapping
                # Use the same acceptable values as the first validation
                if primary_column == 'Main Unit Measurement':
                    validation_result = validate_main_unit_measurement(df)
                    # Also validate Alternative Unit Measurement if we applied mapping to both
                    if apply_to_both:
                        alt_validation_result = validate_alternative_unit_measurement(df)
                elif primary_column == 'Alternative Unit Measurement':
                    validation_result = validate_alternative_unit_measurement(df)
                else:
                    validation_result = validate_column_values(df, primary_column)
                data_logger.info(f"Validation result after mapping: {validation_result}")

                # If still invalid, return error
                if not validation_result["valid"] or (apply_to_both and not alt_validation_result["valid"]):
                    error_msg = f"Invalid values after mapping"
                    error_logger.error(error_msg)
                    raise HTTPException(status_code=400, detail=error_msg)

        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"processed_{timestamp}_{filename}"
        output_path = os.path.join("src/data/processed", output_filename)

        # Export to Excel
        from src.data.etl import export_to_excel
        result_path = export_to_excel(df, output_path)
        data_logger.info(f"ETL process completed. Output file: {result_path}")

        # Store column mapping for future use
        data_logger.info(f"Storing column mapping for future use")
        add_mapping(mapping_dict)

        api_logger.info(f"File processed successfully: {output_filename}")
        return {"message": "File processed successfully", "output_filename": output_filename}

    except json.JSONDecodeError:
        error_msg = "Invalid column mapping format"
        error_logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
    except Exception as e:
        error_msg = f"Error processing file: {str(e)}"
        error_logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@api.get("/download/{filename}")
async def download_file(filename: str):
    """
    Download a processed Excel file and clear processed and uploads folders
    """
    api_logger.info(f"Download requested for file: {filename}")

    file_path = os.path.join("src/data/processed", filename)
    if not os.path.exists(file_path):
        error_msg = f"File {filename} not found"
        error_logger.error(error_msg)
        raise HTTPException(status_code=404, detail=error_msg)

    api_logger.info(f"Serving file for download: {file_path}")
    response = FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Clear processed and uploads folders after download
    try:
        # Keep the current file being downloaded
        current_file = os.path.basename(file_path)

        # Clear processed folder (except the file being downloaded)
        for file in os.listdir("src/data/processed"):
            if file != current_file:
                file_to_remove = os.path.join("src/data/processed", file)
                if os.path.isfile(file_to_remove):
                    os.remove(file_to_remove)
                    api_logger.info(f"Removed processed file: {file}")

        # Clear uploads folder
        for file in os.listdir("src/data/uploads"):
            file_to_remove = os.path.join("src/data/uploads", file)
            if os.path.isfile(file_to_remove):
                os.remove(file_to_remove)
                api_logger.info(f"Removed uploaded file: {file}")

        api_logger.info("Processed and uploads folders cleared successfully")
    except Exception as e:
        error_msg = f"Error clearing folders: {str(e)}"
        error_logger.error(error_msg)
        # Don't raise an exception here to ensure the download still works

    return response

@api.get("/api/flash-files")
async def flash_files():
    """
    Delete all files in the processed and uploads folders
    Returns the count of deleted files
    """
    api_logger.info("Flash Files requested")

    deleted_count = 0

    try:
        # Count files before deletion
        processed_files = [f for f in os.listdir("src/data/processed") if os.path.isfile(os.path.join("src/data/processed", f))]
        uploads_files = [f for f in os.listdir("src/data/uploads") if os.path.isfile(os.path.join("src/data/uploads", f))]

        total_files = len(processed_files) + len(uploads_files)

        # Clear processed folder
        for file in processed_files:
            file_to_remove = os.path.join("src/data/processed", file)
            os.remove(file_to_remove)
            deleted_count += 1
            api_logger.info(f"Removed processed file: {file}")

        # Clear uploads folder
        for file in uploads_files:
            file_to_remove = os.path.join("src/data/uploads", file)
            os.remove(file_to_remove)
            deleted_count += 1
            api_logger.info(f"Removed uploaded file: {file}")

        api_logger.info(f"Processed and uploads folders cleared successfully. Deleted {deleted_count} files.")
        return {"message": "Folders cleared successfully", "deleted_count": deleted_count}

    except Exception as e:
        error_msg = f"Error clearing folders: {str(e)}"
        error_logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@api.get("/api/files-count")
async def get_files_count():
    """
    Get the count of files in the processed and uploads folders
    """
    api_logger.info("Files count requested")

    try:
        # Count files
        processed_files = [f for f in os.listdir("src/data/processed") if os.path.isfile(os.path.join("src/data/processed", f))]
        uploads_files = [f for f in os.listdir("src/data/uploads") if os.path.isfile(os.path.join("src/data/uploads", f))]

        total_files = len(processed_files) + len(uploads_files)

        api_logger.info(f"Files count: {total_files} (Processed: {len(processed_files)}, Uploads: {len(uploads_files)})")
        return {
            "total": total_files,
            "processed": len(processed_files),
            "uploads": len(uploads_files)
        }

    except Exception as e:
        error_msg = f"Error counting files: {str(e)}"
        error_logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@api.post("/api/pricing/calc")
async def pricing_calc(payload: Dict[str, Any]):
    """
    Calculate Retail Price and detailed costs using the PricingEngine.
    Expects JSON with keys: qty_m2, buy_price_eur_m2, pallets_count, pallet_type, origin, destination, margin.
    Defaults applied if missing.
    """
    api_logger.info(f"Pricing calculation requested: {payload}")
    if PRICING_ENGINE is None:
        raise HTTPException(status_code=500, detail="Pricing engine not initialized")

    try:
        # Apply defaults and validate types
        qty_m2 = float(payload.get("qty_m2", 0))
        buy_price = float(payload.get("buy_price_eur_m2", 0))
        pallets_count = int(payload.get("pallets_count", 1))
        pallet_type = str(payload.get("pallet_type", "eu"))
        origin = str(payload.get("origin", "ES"))
        destination = str(payload.get("destination", "GR-mainland"))
        margin = float(payload.get("margin", 0.40))
        transport_mode = str(payload.get("transport_mode", "road"))

        # Enforce minimum 1 pallet (do not allow 0)
        if pallets_count < 1:
            raise HTTPException(status_code=400, detail="pallets_count must be >= 1")

        # Optional manual freight override (used for Poland)
        freight_override = payload.get("freight_override_eur", None)
        try:
            freight_override = float(freight_override) if freight_override is not None else None
        except Exception:
            freight_override = None

        # Enforce Groupage availability only for Spain (ES) and Poland (PL)
        if origin not in ("ES", "PL") and transport_mode == "groupage":
            transport_mode = "road"

        req = PricingRequest(
            buy_price_eur_m2=buy_price,
            qty_m2=qty_m2,
            kg_per_m2=float(payload.get("kg_per_m2", KG_PER_M2)),
            pallets_count=pallets_count,
            pallet_type=pallet_type,  # type: ignore
            origin=origin,            # type: ignore
            destination=destination,  # type: ignore
            margin=margin,
            transport_mode=transport_mode,  # type: ignore
            freight_override_eur=freight_override,
            include_pallet_cost=bool(payload.get("include_pallet_cost", True))
        )
        result = PRICING_ENGINE.calculate(req)
        api_logger.info("Pricing calculation completed successfully")
        return JSONResponse(content=result)
    except ValueError as ve:
        error_logger.error(f"Pricing validation error: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        error_logger.error(f"Pricing calculation failed: {e}")
        raise HTTPException(status_code=500, detail="Internal error during pricing calculation")

@api.post("/api/pricing/slabs/calc")
async def pricing_calc_slabs(payload: Dict[str, Any]):
    """
    SLABs calculator.
    Input: brand (infinity|mirage), thickness (6|12|20), units, buy_price_eur_m2 (preferred) or buy_per_unit (legacy), pack (auto|crate|a-frame)
    Logic:
     - load slab details
     - select spec by brand+thickness
     - propose package type by comparing units to crate_max_units (if units > crate_max_units -> a-frame else crate)
     - allow override by pack
     - compute number of palettes = ceil(units / max_units_for_selected_package)
     - handling cost and shipping cost per palette
     - total gross weight = unit_weight * units + palette_weight * palettes
     - freight via IT tariffs (hermes_it.json bands)
     - total cost and retail per m² with 40% margin (or payload.margin if provided)
    """
    try:
        brand = str(payload.get("brand", "infinity")).lower()
        thickness = int(payload.get("thickness", 6))
        units = int(payload.get("units", 0))
        # Preferred: price per square meter; Legacy: price per unit
        try:
            buy_price_eur_m2 = float(payload.get("buy_price_eur_m2")) if payload.get("buy_price_eur_m2") is not None else None
        except Exception:
            buy_price_eur_m2 = None
        try:
            legacy_buy_per_unit = float(payload.get("buy_per_unit")) if payload.get("buy_per_unit") is not None else None
        except Exception:
            legacy_buy_per_unit = None
        pack = str(payload.get("pack", "auto")).lower()
        margin = float(payload.get("margin", 0.40))
        destination = str(payload.get("destination", "GR-mainland"))
        if units <= 0:
            raise ValueError("units must be > 0")
        if not (0 < margin < 1):
            raise ValueError("margin must be between 0 and 1 (e.g., 0.40)")

        # Load slab details JSON
        with open("src/pricing/slabs/slab_details.json", encoding="utf-8") as f:
            cfg = json.load(f)

        # palette config lookup
        palette_map = {p["type"]: p for p in cfg.get("palette", [])}
        ship_cfg = cfg.get("palette_shipping", {})

        if brand not in ("infinity", "mirage"):
            raise ValueError("Unsupported brand (use 'infinity' or 'mirage')")
        specs = cfg.get(brand, [])
        # Prefer exact match on thickness + dimensions if provided
        dim = str(payload.get("dimensions", "")).strip()
        spec = None
        if dim:
            spec = next((s for s in specs if int(s.get("thickness")) == thickness and str(s.get("dimensions", "")).strip().lower() == dim.lower()), None)
        if not spec:
            spec = next((s for s in specs if int(s.get("thickness")) == thickness), None)
        if not spec:
            raise ValueError("No spec found for selected brand/thickness (and dimensions if provided)")

        warnings = []
        weight_per_unit = float(spec.get("weight_kg_per_unit", 0))
        crate_max = spec.get("crate_max_units")
        aframe_max = spec.get("a-frame_max_units")
        smpu = float(spec.get("smpu") or 0)
        if smpu <= 0:
            # Try compute from dimensions if present (e.g., "160x320" cm)
            dims = str(spec.get("dimensions", ""))
            if "x" in dims:
                try:
                    a, b = dims.lower().split("x")
                    smpu = round((float(a)/100.0) * (float(b)/100.0), 2)
                except Exception:
                    pass
        if smpu <= 0:
            warnings.append("Άγνωστο m² ανά τεμάχιο (smpu). Τα αποτελέσματα ανά m² ίσως δεν είναι ακριβή.")

        # Resolve purchase price inputs (prefer per m²)
        computed_buy_per_unit = 0.0
        resolved_buy_price_eur_m2 = None
        if buy_price_eur_m2 is not None:
            resolved_buy_price_eur_m2 = float(buy_price_eur_m2)
            if smpu and smpu > 0:
                computed_buy_per_unit = resolved_buy_price_eur_m2 * smpu
        if legacy_buy_per_unit is not None:
            # If both provided, prefer per m² but keep legacy for reference
            if (buy_price_eur_m2 is not None) and (smpu and smpu > 0):
                warnings.append("Δόθηκαν και τιμή αγοράς ανά m² και τιμή ανά τεμάχιο. Χρησιμοποιείται η τιμή ανά m².")
            else:
                computed_buy_per_unit = float(legacy_buy_per_unit)
                if smpu and smpu > 0:
                    try:
                        resolved_buy_price_eur_m2 = computed_buy_per_unit / smpu
                    except Exception:
                        resolved_buy_price_eur_m2 = None
        # Final fallbacks
        if resolved_buy_price_eur_m2 is None:
            try:
                resolved_buy_price_eur_m2 = float(buy_price_eur_m2) if buy_price_eur_m2 is not None else (float(legacy_buy_per_unit)/smpu if (legacy_buy_per_unit is not None and smpu and smpu>0) else 0.0)
            except Exception:
                resolved_buy_price_eur_m2 = 0.0
        buy_per_unit = float(computed_buy_per_unit)

        # Proposal
        proposed = "crate"
        if isinstance(crate_max, int) and units > crate_max:
            proposed = "a-frame"
        # If no crate_max, default propose a-frame for safety on larger shipments
        if crate_max in (None, 0):
            if units > 0:
                proposed = "a-frame"

        selected_pack = proposed if pack == "auto" else ("a-frame" if pack == "a-frame" else "crate")
        # Enforce: if crate not allowed (crate_max <= 0), do not allow selecting crate
        if (crate_max in (None, 0)) and selected_pack == "crate":
            selected_pack = "a-frame"
            warnings.append("Crate packaging is not available for this selection; switched to A-Frame.")

        # Determine capacity per palette for selected pack
        def capacity_for(pack_type: str) -> int:
            if pack_type == "crate":
                # crate not allowed if capacity not a positive int
                if isinstance(crate_max, int) and crate_max > 0:
                    return crate_max
                return 0
            else:
                if isinstance(aframe_max, int) and aframe_max > 0:
                    return aframe_max
            # Fallbacks
            if pack_type == "a-frame" and isinstance(crate_max, int) and crate_max > 0:
                # assume A-frame holds at least as many as crate
                return max(crate_max, 1)
            # final fallback
            return max(int(units), 1)

        cap = capacity_for(selected_pack)
        from math import ceil

        # Mixed packaging optimization (only when pack == auto)
        breakdown = []  # list of pallets per type with units allocations
        pallets_by_type = {"crate": 0, "a-frame": 0}
        units_left = units
        primary = selected_pack
        alt = "a-frame" if primary == "crate" else "crate"
        primary_cap = capacity_for(primary)
        alt_cap = capacity_for(alt)

        if pack == "auto":
            # Auto allocation with business rules:
            # 1) If units fit in one crate (and crate is allowed), use one crate.
            # 2) Else if units fit in one A-frame, use one A-frame.
            # 3) Else allocate full A-frames first, then if remainder fits in a crate use one crate, otherwise one more A-frame.
            def valid_cap(x):
                return isinstance(x, int) and x > 0

            if valid_cap(crate_max) and units <= crate_max:
                pallets_by_type["crate"] += 1
                breakdown.append({"type": "crate", "capacity": int(crate_max), "units": int(units)})
                units_left = 0
                selected_pack = "crate"
                cap = int(crate_max)
            elif valid_cap(aframe_max) and units <= aframe_max:
                pallets_by_type["a-frame"] += 1
                breakdown.append({"type": "a-frame", "capacity": int(aframe_max), "units": int(units)})
                units_left = 0
                selected_pack = "a-frame"
                cap = int(aframe_max)
            else:
                # Use A-frames as primary for large shipments
                if not valid_cap(aframe_max):
                    # Fallback: if a-frame capacity unknown, fall back to crate-only logic
                    primary_cap = primary_cap or (crate_max if valid_cap(crate_max) else int(units))
                full_af = 0 if not valid_cap(aframe_max) else units // int(aframe_max)
                if full_af > 0:
                    pallets_by_type["a-frame"] += int(full_af)
                    breakdown.extend([
                        {"type": "a-frame", "capacity": int(aframe_max), "units": int(aframe_max)}
                        for _ in range(int(full_af))
                    ])
                remainder = units - (int(full_af) * (int(aframe_max) if valid_cap(aframe_max) else 0))
                if remainder > 0:
                    if valid_cap(crate_max) and remainder <= int(crate_max):
                        pallets_by_type["crate"] += 1
                        breakdown.append({"type": "crate", "capacity": int(crate_max), "units": int(remainder)})
                    else:
                        # One more A-frame for the remainder
                        pallets_by_type["a-frame"] += 1
                        rem_cap = int(aframe_max) if valid_cap(aframe_max) else int(max(1, remainder))
                        breakdown.append({"type": "a-frame", "capacity": rem_cap, "units": int(remainder)})
                units_left = 0
                # For mixed or large, set selected_pack to a-frame (dominant)
                selected_pack = "a-frame"
                cap = int(aframe_max) if valid_cap(aframe_max) else int(crate_max) if valid_cap(crate_max) else int(units)
        else:
            # Manual pack: uniform type
            pallets_needed = max(1, ceil(units / max(1, primary_cap)))
            pallets_by_type[primary] = pallets_needed
            # fill breakdown rows (all primary)
            for i in range(pallets_needed):
                filled = primary_cap if i < pallets_needed - 1 else (units - primary_cap * (pallets_needed - 1))
                breakdown.append({"type": primary, "capacity": primary_cap, "units": int(max(0, filled))})

        pallets = pallets_by_type["crate"] + pallets_by_type["a-frame"]

        # Costs: handling per palette (sum per type)
        handling_cost = 0.0
        for t, cnt in pallets_by_type.items():
            if cnt > 0:
                pc = palette_map.get(t)
                if not pc:
                    raise ValueError(f"Palette configuration missing for type {t}")
                handling_cost += cnt * float(pc.get("price_per_unit", 0))

        # Palette shipping (first + additional)
        first = float(ship_cfg.get("first_palette_eur", 0))
        add = float(ship_cfg.get("additional_palette_eur", 0))
        pallet_shipping = first + max(0, pallets-1) * add

        # Weights
        kg_tiles = units * weight_per_unit
        kg_palettes = 0.0
        for t, cnt in pallets_by_type.items():
            if cnt > 0:
                pc = palette_map.get(t)
                kg_palettes += cnt * float(pc.get("weight_kg", 0))
        kg_total = kg_tiles + kg_palettes

        # Freight via IT bands
        it_tariff = PRICING_TARIFFS.get("it_freight") if PRICING_TARIFFS else None
        def freight_it(kg: float) -> float:
            if not it_tariff:
                return 0.0
            for band in it_tariff.get("bands", []):
                if band["min_kg"] <= kg <= band["max_kg"]:
                    flat = float(band.get("flat_eur", 0))
                    per = float(band.get("eur_per_kg", 0))
                    return flat if flat > 0 else kg * per
            return kg * float(it_tariff.get("default_eur_per_kg", 0))
        freight = freight_it(kg_total)

        # Destination extras: Crete surcharge per pallet type (CRATE vs A-FRAME)
        crete_extra = 0.0
        crete_breakdown = []
        try:
            if destination == "GR-crete":
                # New rule (2025-09-13):
                # - 150€ per CRATE pallet
                # - 170€ per A-FRAME pallet
                crate_cnt = int(pallets_by_type.get("crate", 0) or 0)
                aframe_cnt = int(pallets_by_type.get("a-frame", 0) or 0)
                if crate_cnt > 0:
                    amt = crate_cnt * 150.0
                    crete_extra += amt
                    crete_breakdown.append({"type": "crate", "pallets": crate_cnt, "rate": 150.0, "amount": round(amt, 2)})
                if aframe_cnt > 0:
                    amt = aframe_cnt * 170.0
                    crete_extra += amt
                    crete_breakdown.append({"type": "a-frame", "pallets": aframe_cnt, "rate": 170.0, "amount": round(amt, 2)})
        except Exception:
            crete_extra = 0.0
            crete_breakdown = []

        # Goods and totals
        cost_goods = buy_per_unit * units
        logistics = handling_cost + pallet_shipping + freight + crete_extra
        total_cost = cost_goods + logistics

        total_m2 = units * smpu if smpu > 0 else None
        cost_per_m2 = (total_cost / total_m2) if total_m2 and total_m2 > 0 else None
        sell_per_m2 = (cost_per_m2 / (1.0 - margin)) if (cost_per_m2 and (0 < margin < 1)) else None

        result = {
            "inputs": {
                "brand": brand,
                "thickness": thickness,
                "units": units,
                "buy_price_eur_m2": round(resolved_buy_price_eur_m2 if resolved_buy_price_eur_m2 is not None else 0.0, 4),
                "buy_per_unit": round(buy_per_unit, 4),
                "pack": pack,
                "applied_pack": selected_pack,
                "destination": destination,
                "margin": margin
            },
            "selection": {
                "package_type": selected_pack,
                "pallets": pallets,
                "capacity_per_palette": cap,
                "package_mix": bool(pallets_by_type.get("crate",0) and pallets_by_type.get("a-frame",0)),
                "pallets_by_type": {"crate": pallets_by_type.get("crate",0), "a-frame": pallets_by_type.get("a-frame",0)},
                "breakdown": breakdown
            },
            "weights": {
                "kg_tiles": round(kg_tiles, 2),
                "kg_palettes": round(kg_palettes, 2),
                "kg_total": round(kg_total, 2)
            },
            "cost": {
                "cost_goods": round(cost_goods, 2),
                "pallet_handling": round(handling_cost, 2),
                "pallet_shipping": round(pallet_shipping, 2),
                "freight_it": round(freight, 2),
                "gr_crete_extra": round(crete_extra, 2),
                "gr_crete_extra_breakdown": crete_breakdown,
                "logistics": round(logistics, 2),
                "total_cost": round(total_cost, 2),
                "cost_per_m2": round(cost_per_m2, 2) if cost_per_m2 is not None else None
            },
            "pricing": {
                "sell_price_per_m2": round(sell_per_m2, 2) if sell_per_m2 is not None else None,
                "margin": margin,
                "markup_equiv": (round((sell_per_m2 / cost_per_m2) - 1.0, 4) if (sell_per_m2 is not None and cost_per_m2 not in (None, 0)) else None)
            },
            "assumptions": {
                "smpu": smpu,
                "crate_max_units": crate_max,
                "a_frame_max_units": aframe_max
            },
            "warnings": warnings
        }
        # Additional warning for missing a-frame capacity when user forces a-frame
        if pack == "a-frame" and not isinstance(aframe_max, int):
            result["warnings"].append("Άγνωστη χωρητικότητα A-Frame για αυτή την επιλογή. Υποτέθηκε ελάχιστη χωρητικότητα.")
        # Mixed packaging info
        if result.get("selection", {}).get("package_mix"):
            c = result["selection"]["pallets_by_type"].get("crate",0)
            a = result["selection"]["pallets_by_type"].get("a-frame",0)
            result["warnings"].append(f"Μικτή συσκευασία: {a} A-FRAME + {c} CRATE.")

        # Edge-case example check from description: Infinity, 6mm, 15 units => propose A-Frame 1 palette, Crate => 2 palettes
        # Our logic now also optimizes remainder to Crate if it fits.

        return JSONResponse(content=result)
    except ValueError as ve:
        error_logger.error(f"SLABs pricing validation error: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        error_logger.error(f"SLABs pricing calculation failed: {e}")
        raise HTTPException(status_code=500, detail="Internal error during SLABs pricing calculation")
    """
    Calculate Retail Price and detailed costs using the PricingEngine.
    Expects JSON with keys: qty_m2, buy_price_eur_m2, pallets_count, pallet_type, origin, destination, margin.
    Defaults applied if missing.
    """
    api_logger.info(f"Pricing calculation requested: {payload}")
    if PRICING_ENGINE is None:
        raise HTTPException(status_code=500, detail="Pricing engine not initialized")

    try:
        # Apply defaults and validate types
        qty_m2 = float(payload.get("qty_m2", 0))
        buy_price = float(payload.get("buy_price_eur_m2", 0))
        pallets_count = int(payload.get("pallets_count", 1))
        pallet_type = str(payload.get("pallet_type", "eu"))
        origin = str(payload.get("origin", "ES"))
        destination = str(payload.get("destination", "GR-mainland"))
        margin = float(payload.get("margin", 0.40))
        transport_mode = str(payload.get("transport_mode", "road"))

        # Enforce Groupage availability only for Spain (ES)
        if origin != "ES" and transport_mode == "groupage":
            transport_mode = "road"

        req = PricingRequest(
            buy_price_eur_m2=buy_price,
            qty_m2=qty_m2,
            kg_per_m2=float(payload.get("kg_per_m2", KG_PER_M2)),
            pallets_count=pallets_count,
            pallet_type=pallet_type,  # type: ignore
            origin=origin,            # type: ignore
            destination=destination,  # type: ignore
            margin=margin,
            transport_mode=transport_mode  # type: ignore
        )
        result = PRICING_ENGINE.calculate(req)
        api_logger.info("Pricing calculation completed successfully")
        return JSONResponse(content=result)
    except ValueError as ve:
        error_logger.error(f"Pricing validation error: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        error_logger.error(f"Pricing calculation failed: {e}")
        raise HTTPException(status_code=500, detail="Internal error during pricing calculation")

def get_ip_address():
    """
    Gets the local IP address by connecting to Google's DNS server.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]

def ensure_folders_exist():
    """
    Ensure that required folders exist
    """
    required_folders = ["src/data/processed", "src/data/uploads"]
    for folder in required_folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
            app_logger.info(f"Created folder: {folder}")
        else:
            app_logger.info(f"Folder exists: {folder}")

if __name__ == "__main__":
    # Check if websockets package is installed, if not install it
    try:
        import websockets
    except ImportError:
        import subprocess
        import sys
        app_logger.info("Installing websockets package...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets"])
        app_logger.info("websockets package installed successfully")

    import uvicorn
    host = "0.0.0.0"  # Listen on all available network interfaces
    my_ip = get_ip_address()  # Get the actual IP address for display purposes
    port = 3000

    # Ensure required folders exist
    ensure_folders_exist()

    app_logger.info(f"Starting server on {my_ip}:{port}")
    app_logger.info(f"Server will be accessible at http://{my_ip}:{port} from other devices on the network")
    uvicorn.run("main:api", host=my_ip, port=port, log_level="info", reload=False)

# Corgres - Business Data Automation Platform

Transform your business data workflows with intelligent automation. Corgres streamlines the complex process of converting Excel files into ERP-ready formats, while providing comprehensive email integration and real-time monitoring capabilities.

## Why Choose Corgres?

**Save Hours of Manual Work** - What used to take hours of manual data manipulation now happens in minutes with intelligent column mapping and automated data transformation.

**Eliminate Data Entry Errors** - Built-in validation ensures your data meets ERP requirements before processing, preventing costly mistakes and system rejections.

**Seamless Email Integration** - Automatically scan your emails for data files and process them without manual intervention, perfect for handling supplier data feeds.

**Real-Time Visibility** - Monitor processing status in real-time with live updates, so you always know when your data is ready.

**Enterprise-Ready** - Designed for businesses that need reliable, scalable data processing with comprehensive logging and error tracking.

## What Corgres Does

🔄 **Intelligent Data Transformation**
- Converts Excel files to Softone ERP compatible format
- Smart column mapping that learns from your data patterns
- Automatic data validation and error detection

📧 **Email Automation**
- Scans email folders for data attachments
- Processes files automatically from trusted sources
- Reduces manual file handling and speeds up workflows

📊 **Real-Time Monitoring**
- Live processing status updates
- Comprehensive logging and analytics
- Performance tracking and optimization insights

🎯 **Business Value**
- Reduce data processing time by up to 90%
- Eliminate manual mapping errors
- Streamline supplier data integration
- Improve data quality and consistency

## Getting Started

Corgres is designed to be simple and intuitive. No complex setup or technical expertise required.

**Quick Start:**
1. Install dependencies: `pip install -r requirements.txt`
2. Run the server: `python main.py`
3. Open your browser to `http://localhost:3000`
4. Upload your Excel file and follow the steps to process and download

**Email Integration Setup:**
Set the following environment variables (e.g., in a .env file) if you plan to use email scanning:
- `GMAIL_USER` and `GMAIL_PASS`
- Optional: `MAIL_FOLDER` (defaults to `INBOX`)

Then use:
- List folders: GET `/mail-folders/`
- Scan emails: GET `/scan-emails/?days=7&folders=INBOX`

**Web Interface:**
Access Corgres through any modern web browser - no client installation needed.

## Application Hub & Real-Time Unique Visitors

The landing “Application Hub” (/) shows available apps (Excel Formatter, Retail Pricing) with live status and counts.

- Status: Each card shows “Available” or “In Use”.
- Count: The number shown is unique visitors per app (not connections). A single person with multiple tabs or windows counts as 1 for that app.
- Identification: Visitors are identified by a persistent visitorId stored in localStorage.
- Per‑app tracking: Joining an app adds your visitorId to that app; leaving removes it.

### How it works under the hood
- The browser establishes a WebSocket to `/ws/app-status` and sends:
  - `identify` once (includes visitorId, browser/platform, tab id)
  - `heartbeat` every 15 seconds
  - `join` on app entry and `leave` on exit
- The server considers a connection stale if it hasn’t received a heartbeat for 30 seconds. On last-connection cleanup, the visitor is removed from the app’s unique count and from the global stats.

### Why “In Use” can flip back to “Available” while you’re still on a phone
Mobile browsers often throttle or suspend background tabs and even foreground pages during inactivity or screen lock. When heartbeats pause for >30 seconds, the server will mark the connection stale and remove your visitor from counts until a new message arrives (e.g., upon reconnect or interaction).

Mitigations and options:
- Keep the device awake or screen on while actively using the app.
- Ensure the tab remains in the foreground; avoid OS power-saving modes that suspend networking.
- If your environment requires longer tolerance, you can increase the heartbeat timeout in code.
  - In `main.py`, ConnectionManager sets `self.heartbeat_timeout = 30` (seconds). Adjusting this value increases tolerance to backgrounding but delays stale cleanup.

### Troubleshooting live status
- Open the Logs page: navigate to `/logs` to view recent events.
- Check API logs under `src/logs/api/` and errors under `src/logs/errors/`.
- Look for entries like “WebSocket message received”, “heartbeat”, “Cleaning up stale connection”, or “User X joined/left app”.

## Supported Data Fields

Corgres handles all essential product and logistics data fields required by modern ERP systems, including:

**Product Information:** Barcodes, descriptions, measurements, and specifications
**Inventory Management:** Stock levels, reorder points, and storage locations  
**Logistics Data:** Packaging dimensions, weights, and shipping information
**Business Rules:** VAT categories, unit measurements, and pricing structures

The intelligent mapping system automatically recognizes common field names and suggests appropriate mappings, making the process seamless regardless of your source data format.

## Why Businesses Choose Corgres

**Proven Results:** Companies using Corgres report significant time savings and improved data accuracy in their ERP integration processes.

**Reliable & Secure:** Built with enterprise-grade security and reliability standards to handle your critical business data.

**Future-Proof:** Regular updates ensure compatibility with evolving ERP systems and data formats.

**Support When You Need It:** Comprehensive logging and error tracking help identify and resolve any issues quickly.

---

## Change Log (excerpt)
- 2025-08-26: Application Hub switched to unique visitor counting per app. Heartbeat-based cleanup added; mobile backgrounding behavior documented.

## Ready to Transform Your Data Workflows?

Stop wasting time on manual data processing. Join the businesses already using Corgres to streamline their ERP data integration and focus on what matters most - growing their business.

**Get Started Today:**
- Clone the repository and run `python main.py`
- Open your browser to `http://localhost:3000`
- Upload your first Excel file and experience the difference

Transform your data. Transform your business. **Try Corgres now.**


"""Tests for the ingestion parsers against the synthetic scenario formats.

These mirror the exact formats of datasets/synthetic/*.txt so the parser
fixes (Windows EVTX text routing, Android logcat hash/filename extraction,
network JSON timeline flattening) are locked in.
"""

from app.ingestion.registry import detect_format, parse_file

PC_INSIDER = """\
8/20/2026 9:14:00 AM | INFO | 4688 | Security | File "Q3_financials.xlsx" copied to USB device SanDisk Ultra
8/20/2026 9:30:00 AM | INFO | 4688 | Email | Outbound email sent to external recipient - subject: "RE: Financial Report"
8/20/2026 9:45:00 AM | INFO | 1204 | WinINet | Network connection to 203.0.113.42:443 closed
"""

PC_RANSOM = """\
8/21/2026 2:05:00 PM | INFO | 8832 | Windows PowerShell | Script block logging: Downloading payload from https://malicious-phish.example.com/invoice_2026.zip
8/21/2026 2:07:05 PM | INFO | 8832 | Security | Process created: C:\\Users\\victim\\Downloads\\invoice_2026.exe (PID: 7721)
8/21/2026 2:08:00 PM | WARNING | 7721 | Sysmon | File write: C:\\Users\\victim\\Documents\\report.docx -> report.docx.locked
8/21/2026 2:09:00 PM | INFO | 7721 | Sysmon | File created: C:\\Users\\victim\\Desktop\\README_DECRYPT.txt
8/21/2026 2:10:00 PM | INFO | 7721 | Sysmon | Network connection: 198.51.100.23:443 (outbound HTTPS)
"""

MOBILE_LOGCAT = """\
08-20 09:17:05.456  1234  1234 I StorageManager: File received via MTP: Q3_financials.xlsx (245760 bytes)
08-20 09:17:15.012  1234  1234 D FileChecksum: SHA-256: a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef12345678
08-20 09:22:05.234  2345  2345 I BluetoothOpp: Sending file: Q3_financials.xlsx to DESKTOP-PC-04771
08-20 09:29:00.456  3456  3456 I EmailApp: Attaching file: Q3_financials.xlsx (245760 bytes)
08-20 09:30:00.012  3456  3456 I EmailApp: Email sent to external-recipient@foreign-domain.com
"""

NETWORK_JSON = """\
{
  "scenario": "insider_data_exfiltration",
  "devices": [{"id": "PC-04771"}, {"id": "MOBILE-2291"}],
  "timeline_events": [
    {"timestamp": "2026-08-20T09:14:00Z", "device": "PC-04771", "action": "file_copy", "object": "Q3_financials.xlsx", "hash": "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef12345678"},
    {"timestamp": "2026-08-20T09:30:00Z", "device": "MOBILE-2291", "action": "email_sent", "ip_address": "203.0.113.42"}
  ]
}
"""


def test_windows_evtx_detects_txt_content():
    parser = detect_format("scenario_pc.txt", PC_INSIDER.encode())
    assert parser is not None
    assert parser.source_type == "windows_evtx"


def test_windows_evtx_parses_single_digit_dates_and_ips():
    events = parse_file("scenario_pc.txt", PC_INSIDER.encode())
    assert len(events) == 3
    assert events[0].timestamp is not None
    assert events[0].timestamp.strftime("%m/%d/%Y %H:%M") == "08/20/2026 09:14"
    assert events[0].object == "Q3_financials.xlsx"
    assert events[0].action == "usb_transfer"
    assert events[2].ip_address == "203.0.113.42"
    assert events[2].action == "network_connection"


def test_windows_evtx_parses_ransomware_chain():
    events = parse_file("pc.txt", PC_RANSOM.encode())
    action = {e.action for e in events}
    assert "download_complete" in action
    assert "process_start" in action
    assert "file_write" in action
    assert "ransom_note_created" in action
    file_write = next(e for e in events if e.action == "file_write")
    assert ".locked" in file_write.object
    assert any(e.ip_address == "198.51.100.23" for e in events)


def test_android_logcat_extracts_hash_and_filenames():
    events = parse_file("mobile_logcat.txt", MOBILE_LOGCAT.encode())
    sha = "a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef12345678"
    checksum = next(e for e in events if e.action == "file_checksum")
    assert checksum.object == "Q3_financials.xlsx"
    assert checksum.file_hash == sha[:64]
    received = next(e for e in events if e.action == "file_received")
    assert received.object == "Q3_financials.xlsx"
    assert any(e.action == "email_sent" for e in events)


def test_network_json_keeps_timeline_events():
    events = parse_file("scenario.json", NETWORK_JSON.encode())
    assert len(events) == 2
    hashes = [e.file_hash for e in events if e.file_hash]
    assert len(hashes) == 1 and hashes[0].startswith("a1b2c3d4")
    assert any(e.action == "email_sent" and e.ip_address == "203.0.113.42" for e in events)

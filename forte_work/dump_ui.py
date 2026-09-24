#!/usr/bin/env python3
"""Dump HTML structure (skip base64 data) for UI redesign."""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

path = r"C:\Users\Jhonatan\Desktop\PREACH_FLOW_V08_ADD_TRACKS.html"

with open(path, "r", encoding="utf-8", errors="surrogateescape") as f:
    for i, line in enumerate(f, 1):
        if i <= 71:
            s = line.rstrip("\r\n")
            print("%d|%s" % (i, s))
        elif 72 <= i <= 85:
            s = line.rstrip("\r\n")
            shown = s[:90]
            if len(s) > 90:
                shown += "...[len=%d]" % len(s)
            print("%d|%s" % (i, shown))
        elif i >= 86:
            s = line.rstrip("\r\n")
            print("%d|%s" % (i, s))
        if i >= 498:
            break

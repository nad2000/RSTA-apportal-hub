#!/usr/bin/env python
"""
.procmailrc
:0Wc:
| env python email_receiver.py
"""
import datetime
import email
import importlib
import os
import sys
from pathlib import Path

import django

if __name__ == "__main__":
    env_name = os.getenv("ENV", "local")
    # fall back to local if
    try:
        importlib.import_module(f"config.settings.{env_name}")
    except ModuleNotFoundError:
        parent_dir = os.path.basename(os.getcwd())
        env_name = parent_dir if parent_dir in ["dev", "prod", "test"] else "local"
    current_path = Path(__file__).parent.resolve()
    sys.path.append(str(current_path / "portal"))

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"config.settings.{env_name}")

    django.setup()

    from portal.models import MailLog

    full_msg = open(sys.argv[1]).read() if len(sys.argv) > 1 else sys.stdin.read()
    msg = email.message_from_string(full_msg)

    to = msg["to"]
    subject = msg["subject"]
    body = msg["body"]

    for part in msg.walk():
        message_id = part["message-id"]
        if not message_id:
            continue
        message_id = message_id.split("@")[0][1:]
        if not message_id:
            continue
        ml = MailLog.where(token=message_id).first()
        if ml:
            ml.error = f"{subject}\n{datetime.datetime.now()}"
            ml.was_sent_successfully = False
            ml.save()
            break

    # with open("_%s-%s.txt" % (msg["from"], subject), "w") as f:
    #     f.write(full_msg)

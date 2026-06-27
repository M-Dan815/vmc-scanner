# test_gmail.py
# ─────────────────────────────────────────────────────────────────────────────
# Sends a test email to verify Gmail App Password configuration.
# ─────────────────────────────────────────────────────────────────────────────

import smtplib
import sys
from datetime       import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText

import config


def test_gmail():
    print()
    print("VMC Cipher B Scanner — Gmail Connection Test")
    print("─" * 48)
    print(f"Sender    : {config.GMAIL_SENDER}")
    print(f"Recipient : {config.GMAIL_RECIPIENT}")
    print()

    now_str = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    plain = f"""
VMC Cipher B + Divergences Alert
────────────────────────────────────────────

✅  GMAIL TEST — Configuration Successful

  Asset       : BTCUSDT (test)
  Timeframe   : Daily (test)
  Signal      : 🟢 Big Green Dot — BUY (test)
  WT1 Value   : -65.1234 (simulated)
  Sent At     : {now_str}

────────────────────────────────────────────
Your VMC Cipher B Scanner is correctly configured.
Real signals will arrive after the next candle close.
    """.strip()

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: Arial, sans-serif; background: #f0f0f0; padding: 20px; }}
    .box {{ max-width: 480px; margin: 0 auto; background: #fff;
            border-radius: 8px; overflow: hidden;
            box-shadow: 0 2px 12px rgba(0,0,0,0.10); }}
    .hdr {{ background: #1b7f3e; padding: 24px; text-align: center; color: #fff; }}
    .hdr h2 {{ margin: 0; font-size: 18px; }}
    .hdr p  {{ margin: 6px 0 0; font-size: 13px; opacity: 0.85; }}
    .body {{ padding: 24px; }}
    .ok  {{ background: #e8f5e9; border-left: 4px solid #2e7d32;
            border-radius: 4px; padding: 14px 16px; margin-bottom: 20px; }}
    .ok strong {{ color: #1b5e20; font-size: 16px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    td {{ padding: 9px 4px; border-bottom: 1px solid #eee;
          font-size: 13px; color: #333; }}
    td.k {{ font-weight: 600; color: #666; width: 36%; }}
    .ftr {{ background: #fafafa; text-align: center;
            padding: 12px; font-size: 11px; color: #aaa; }}
  </style>
</head>
<body>
<div class="box">
  <div class="hdr">
    <h2>VMC Cipher B + Divergences</h2>
    <p>Alert Scanner — Gmail Test</p>
  </div>
  <div class="body">
    <div class="ok">
      <strong>✅ Gmail configuration successful!</strong><br>
      <span style="font-size:13px;color:#2e7d32;">
        Your scanner is ready to send live alerts.
      </span>
    </div>
    <table>
      <tr><td class="k">Asset</td>      <td>BTCUSDT (test)</td></tr>
      <tr><td class="k">Timeframe</td>  <td>Daily (test)</td></tr>
      <tr><td class="k">Signal</td>     <td>🟢 Big Green Dot — BUY (test)</td></tr>
      <tr><td class="k">WT1 Value</td>  <td>-65.1234 (simulated)</td></tr>
      <tr><td class="k">Sent At</td>    <td>{now_str}</td></tr>
    </table>
  </div>
  <div class="ftr">
    Automated alert · VMC Cipher B Scanner · No TradingView limits
  </div>
</div>
</body>
</html>"""

    msg = MIMEMultipart('alternative')
    msg['Subject'] = "✅ VMC Cipher B Scanner — Gmail Test Successful"
    msg['From']    = config.GMAIL_SENDER
    msg['To']      = config.GMAIL_RECIPIENT

    msg.attach(MIMEText(plain, 'plain', 'utf-8'))
    msg.attach(MIMEText(html,  'html',  'utf-8'))

    print("Connecting to Gmail SMTP (smtp.gmail.com:465)...")

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            print("Connected. Authenticating...")
            smtp.login(config.GMAIL_SENDER, config.GMAIL_APP_PASS)
            print("Authenticated. Sending test email...")
            smtp.sendmail(
                config.GMAIL_SENDER,
                config.GMAIL_RECIPIENT,
                msg.as_string()
            )

        print()
        print("✅ Test email sent successfully!")
        print(f"   Check inbox: {config.GMAIL_RECIPIENT}")
        print()
        return True

    except smtplib.SMTPAuthenticationError:
        print()
        print("❌ Authentication failed.")
        print("   Check GMAIL_SENDER and GMAIL_APP_PASS in .env")
        print()
        return False

    except smtplib.SMTPConnectError:
        print()
        print("❌ Could not connect to Gmail SMTP.")
        print("   Check network/firewall: port 465 must be open outbound.")
        print()
        return False

    except Exception as exc:
        print()
        print(f"❌ Unexpected error: {exc}")
        print()
        return False


if __name__ == '__main__':
    success = test_gmail()
    sys.exit(0 if success else 1)
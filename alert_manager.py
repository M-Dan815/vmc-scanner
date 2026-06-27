# alert_manager.py
# ─────────────────────────────────────────────────────────────────────────────
# Manages alert deduplication and Gmail delivery.
#
# Three signal types only:
#   BIG_GREEN  → bullish crossover below -60       → BUY
#   BIG_RED    → any bearish crossover             → SELL
#   YELLOW_BUY → bullish crossover between -60/+40 → BUY
#
# Timestamps shown in both UTC and Pacific Time (PT) via pytz.
# ─────────────────────────────────────────────────────────────────────────────

import json
import logging
import smtplib
import pytz
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from pathlib import Path

import config

logger = logging.getLogger(__name__)


class AlertManager:

    def __init__(self):
        self.history_file = Path(config.ALERT_HISTORY_FILE)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self._history: dict = self._load_history()
        logger.info(
            f"AlertManager initialised. "
            f"History entries loaded: {len(self._history)}"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # DEDUPLICATION
    # ─────────────────────────────────────────────────────────────────────────

    def _load_history(self) -> dict:
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as exc:
                logger.warning(f"Alert history unreadable ({exc}). Starting fresh.")
        return {}

    def _save_history(self):
        if len(self._history) > config.MAX_HISTORY_ENTRIES:
            overflow = len(self._history) - config.MAX_HISTORY_ENTRIES
            old_keys = list(self._history.keys())[:overflow]
            for key in old_keys:
                del self._history[key]
            logger.debug(f"Pruned {overflow} old history entries.")

        with open(self.history_file, 'w') as f:
            json.dump(self._history, f, indent=2, default=str)

    def _make_key(self, signal: dict) -> str:
        ts = signal['timestamp']
        ts_str = ts.isoformat() if hasattr(ts, 'isoformat') else str(ts)
        return (
            f"{signal['symbol']}_"
            f"{signal['timeframe']}_"
            f"{signal['signal_type']}_"
            f"{ts_str}"
        )

    def is_duplicate(self, signal: dict) -> bool:
        return self._make_key(signal) in self._history

    def record_alert(self, signal: dict):
        key = self._make_key(signal)
        self._history[key] = {
            'sent_at':   datetime.now(timezone.utc).isoformat(),
            'symbol':    signal['symbol'],
            'timeframe': signal['timeframe'],
            'signal':    signal['signal_type'],
            'group':     signal.get('group', 'keep_an_eye'),
            'wt1':       signal['wt1'],
        }
        self._save_history()
        logger.debug(f"Alert recorded: {key}")

    # ─────────────────────────────────────────────────────────────────────────
    # TIME HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    def _format_utc(self, ts) -> str:
        try:
            if hasattr(ts, 'astimezone'):
                return ts.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        except Exception:
            pass
        return str(ts)

    def _format_pacific(self, ts) -> str:
        """
        Returns timestamp as Pacific Time using pytz.
        Handles PST/PDT automatically.
        """
        try:
            if hasattr(ts, 'astimezone'):
                pacific = pytz.timezone("America/Los_Angeles")
                return ts.astimezone(pacific).strftime('%Y-%m-%d %I:%M %p PT')
        except Exception as exc:
            logger.warning(f"Could not convert to Pacific Time: {exc}")
        return str(ts)

    # ─────────────────────────────────────────────────────────────────────────
    # EMAIL COMPOSITION
    # ─────────────────────────────────────────────────────────────────────────

    def _compose_email(self, signal: dict) -> tuple[str, str, str]:
        signal_type  = signal['signal_type']
        group        = signal.get('group', 'keep_an_eye')
        signal_label = signal.get('signal_label', signal_type)

        # ── Signal styling ────────────────────────────────────────────────
        if signal_type == 'BIG_GREEN':
            emoji        = '🟢'
            action       = 'BUY'
            header_color = '#1b7f3e'
            accent_color = '#2e7d32'
            bg_tint      = '#e8f5e9'
            border_color = '#66bb6a'

        elif signal_type == 'BIG_RED':
            emoji        = '🔴'
            action       = 'SELL'
            header_color = '#c62828'
            accent_color = '#d32f2f'
            bg_tint      = '#ffebee'
            border_color = '#ef9a9a'

        elif signal_type == 'YELLOW_BUY':
            emoji        = '🟡'
            action       = 'BUY'
            header_color = '#f9a825'
            accent_color = '#f57f17'
            bg_tint      = '#fff8e1'
            border_color = '#ffd54f'

        else:
            emoji        = '⚪'
            action       = 'INFO'
            header_color = '#455a64'
            accent_color = '#546e7a'
            bg_tint      = '#eceff1'
            border_color = '#b0bec5'

        # ── Group formatting ──────────────────────────────────────────────
        if group == 'holdings':
            group_prefix = '🚨 URGENT — HOLDING'
            group_label  = '🚨 HOLDING'
            group_color  = '#b71c1c' if action == 'SELL' else '#1b5e20'
            urgency_note = '⚠️ This is one of your HOLDINGS. Act promptly.'
        else:
            group_prefix = '👀 Keep an Eye'
            group_label  = '👀 Keep an Eye'
            group_color  = '#e65100' if action == 'SELL' else '#2e7d32'
            urgency_note = 'This is a Watch List asset. Review when convenient.'

        symbol           = signal['symbol']
        tf_label         = signal.get('tf_label', signal['timeframe'])
        wt1              = signal['wt1']
        time_utc         = self._format_utc(signal['timestamp'])
        time_pst         = self._format_pacific(signal['timestamp'])
        asset_type_label = '📊 Stock' if signal.get('asset_type') == 'stock' else '🪙 Crypto'

        # ── Subject ───────────────────────────────────────────────────────
        subject = f"{emoji} {group_prefix} | {symbol} | {tf_label} | {action}"

        # ── Plain Text ────────────────────────────────────────────────────
        plain = f"""
VMC Cipher B + Divergences Alert
{'─' * 44}

{emoji}  {signal_label}

  Group            : {group_label}
  Asset            : {symbol}
  Type             : {asset_type_label}
  Timeframe        : {tf_label}
  Signal           : {signal_label}
  WT1 Value        : {wt1}
  Candle Time (UTC): {time_utc}
  Candle Time (PT) : {time_pst}

  {urgency_note}

{'─' * 44}
Automated alert from your VMC Cipher B Scanner.
        """.strip()

        # ── HTML ──────────────────────────────────────────────────────────
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>VMC Cipher B Alert</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
      background-color: #f0f0f0;
      padding: 24px 16px;
    }}
    .wrapper {{
      max-width: 500px;
      margin: 0 auto;
      background: #ffffff;
      border-radius: 10px;
      overflow: hidden;
      box-shadow: 0 4px 16px rgba(0,0,0,0.10);
    }}
    .header {{
      background: {header_color};
      padding: 28px 24px 22px;
      text-align: center;
    }}
    .header .title {{
      font-size: 20px;
      font-weight: 700;
      color: #ffffff;
      letter-spacing: 0.3px;
    }}
    .header .subtitle {{
      font-size: 13px;
      color: rgba(255,255,255,0.80);
      margin-top: 6px;
    }}
    .group-band {{
      background: {group_color};
      padding: 10px 24px;
      text-align: center;
      font-size: 14px;
      font-weight: 700;
      color: #ffffff;
      letter-spacing: 0.5px;
    }}
    .signal-band {{
      background: {bg_tint};
      border-top: 3px solid {border_color};
      border-bottom: 1px solid {border_color};
      padding: 20px 24px;
      display: flex;
      align-items: center;
      gap: 14px;
    }}
    .signal-emoji  {{ font-size: 42px; line-height: 1; }}
    .signal-name   {{ font-size: 20px; font-weight: 700; color: {accent_color}; }}
    .signal-symbol {{ font-size: 15px; color: #555; margin-top: 3px; }}
    .details       {{ padding: 20px 24px; }}
    table          {{ width: 100%; border-collapse: collapse; }}
    td {{
      padding: 11px 4px;
      font-size: 14px;
      color: #333;
      border-bottom: 1px solid #f0f0f0;
      vertical-align: middle;
    }}
    td.key {{
      font-weight: 600;
      color: #666;
      width: 42%;
      padding-right: 8px;
    }}
    td.val {{ color: #111; font-weight: 500; }}
    .urgency {{
      margin: 16px 0 0;
      padding: 12px 14px;
      background: #fff8e1;
      border-left: 4px solid #f9a825;
      border-radius: 4px;
      font-size: 13px;
      color: #555;
      line-height: 1.5;
    }}
    .footer {{
      background: #fafafa;
      border-top: 1px solid #ececec;
      padding: 14px 24px;
      text-align: center;
      font-size: 11px;
      color: #aaa;
      line-height: 1.6;
    }}
  </style>
</head>
<body>
  <div class="wrapper">

    <div class="header">
      <div class="title">VMC Cipher B + Divergences</div>
      <div class="subtitle">WaveTrend Signal Detected</div>
    </div>

    <div class="group-band">{group_label}</div>

    <div class="signal-band">
      <div class="signal-emoji">{emoji}</div>
      <div>
        <div class="signal-name">{signal_label}</div>
        <div class="signal-symbol">{symbol} &nbsp;·&nbsp; {tf_label}</div>
      </div>
    </div>

    <div class="details">
      <table>
        <tr>
          <td class="key">Group</td>
          <td class="val" style="color:{group_color}; font-weight:700;">
            {group_label}
          </td>
        </tr>
        <tr>
          <td class="key">Asset</td>
          <td class="val">{symbol}</td>
        </tr>
        <tr>
          <td class="key">Type</td>
          <td class="val">{asset_type_label}</td>
        </tr>
        <tr>
          <td class="key">Timeframe</td>
          <td class="val">{tf_label}</td>
        </tr>
        <tr>
          <td class="key">Signal</td>
          <td class="val" style="color:{accent_color}; font-weight:700;">
            {signal_label}
          </td>
        </tr>
        <tr>
          <td class="key">WT1 Value</td>
          <td class="val">{wt1}</td>
        </tr>
        <tr>
          <td class="key">Candle Time (UTC)</td>
          <td class="val">{time_utc}</td>
        </tr>
        <tr>
          <td class="key">Candle Time (PT)</td>
          <td class="val">{time_pst}</td>
        </tr>
      </table>

      <div class="urgency">{urgency_note}</div>
    </div>

    <div class="footer">
      Automated alert &nbsp;·&nbsp; VMC Cipher B Scanner<br>
      No TradingView alert limits &nbsp;·&nbsp; No Discord dependency
    </div>

  </div>
</body>
</html>"""

        return subject, plain, html

    # ─────────────────────────────────────────────────────────────────────────
    # GMAIL DELIVERY
    # ─────────────────────────────────────────────────────────────────────────

    def send_alert(self, signal: dict) -> bool:
        """
        Sends a formatted Gmail alert.
        Returns True on success, False on failure.
        Never raises — scanner continues on email error.
        """
        try:
            subject, plain_body, html_body = self._compose_email(signal)

            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From']    = config.GMAIL_SENDER
            msg['To']      = config.GMAIL_RECIPIENT

            msg.attach(MIMEText(plain_body, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_body,  'html',  'utf-8'))

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(config.GMAIL_SENDER, config.GMAIL_APP_PASS)
                smtp.sendmail(
                    config.GMAIL_SENDER,
                    config.GMAIL_RECIPIENT,
                    msg.as_string()
                )

            logger.info(
                f"✉  Alert sent → {signal['symbol']} | "
                f"{signal.get('group', '?')} | "
                f"{signal['timeframe']} | {signal['signal_type']}"
            )
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error(
                "Gmail authentication failed. "
                "Verify GMAIL_SENDER and GMAIL_APP_PASS in .env"
            )
            return False

        except smtplib.SMTPRecipientsRefused:
            logger.error(f"Gmail rejected recipient: {config.GMAIL_RECIPIENT}")
            return False

        except smtplib.SMTPException as exc:
            logger.error(f"SMTP error: {exc}", exc_info=True)
            return False

        except Exception as exc:
            logger.error(
                f"Unexpected error sending alert: {exc}",
                exc_info=True
            )
            return False
# manual_trigger.py
# ─────────────────────────────────────────────────────────────────────────────
# Manual trigger for the VMC Cipher B Scanner.
# Runs the full signal detection + email alert pipeline immediately,
# without waiting for the scheduler.
#
# Usage:
#   python manual_trigger.py              → scan all timeframes
#   python manual_trigger.py --tf 1w     → scan weekly only
#   python manual_trigger.py --tf 4h     → scan 4H only
#   python manual_trigger.py --tf 1d     → scan daily only
#   python manual_trigger.py --tf 1M     → scan monthly only
#   python manual_trigger.py --no-dedup  → ignore duplicate history (resend all)
# ─────────────────────────────────────────────────────────────────────────────

import argparse
import logging
import logging.handlers
import os
import sys
from datetime import datetime, timezone

import config
from scanner import VMCScanner


# ─────────────────────────────────────────────────────────────────────────────
# LOGGING SETUP
# ─────────────────────────────────────────────────────────────────────────────

def setup_logging():
    os.makedirs('logs', exist_ok=True)
    os.makedirs('data', exist_ok=True)

    log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt     = '%(asctime)s [%(levelname)-8s] %(name)s: %(message)s',
        datefmt = '%Y-%m-%d %H:%M:%S'
    )

    # File handler — appends to the same log as the scheduler
    file_handler = logging.handlers.RotatingFileHandler(
        filename    = config.LOG_FILE,
        maxBytes    = config.LOG_MAX_BYTES,
        backupCount = config.LOG_BACKUP_COUNT,
        encoding    = 'utf-8'
    )
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


# ─────────────────────────────────────────────────────────────────────────────
# BANNER
# ─────────────────────────────────────────────────────────────────────────────

def print_banner(timeframes: list[str], no_dedup: bool):
    logger = logging.getLogger('manual_trigger')
    now    = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')

    tf_labels = [config.TIMEFRAME_LABELS.get(tf, tf) for tf in timeframes]

    logger.info("=" * 58)
    logger.info("  VMC Cipher B — Manual Trigger")
    logger.info("=" * 58)
    logger.info(f"  Triggered at   : {now}")
    logger.info(f"  Timeframes     : {', '.join(tf_labels)}")
    logger.info(f"  Dedup active   : {'NO — resending all signals' if no_dedup else 'YES — skipping duplicates'}")
    logger.info(f"  Alert target   : {config.GMAIL_RECIPIENT}")
    logger.info("=" * 58)


# ─────────────────────────────────────────────────────────────────────────────
# RESULTS SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(results: dict[str, list[dict]]):
    logger = logging.getLogger('manual_trigger')

    total_alerts = sum(len(v) for v in results.values())

    logger.info("=" * 58)
    logger.info("  Manual Trigger Complete — Summary")
    logger.info("=" * 58)

    if total_alerts == 0:
        logger.info("  No new signals found across scanned timeframes.")
    else:
        logger.info(f"  Total alerts sent: {total_alerts}")
        logger.info("")

        for tf, signals in results.items():
            if not signals:
                continue
            tf_label = config.TIMEFRAME_LABELS.get(tf, tf)
            logger.info(f"  {tf_label} ({len(signals)} alert(s)):")
            for sig in signals:
                emoji = {
                    'BIG_GREEN':  '🟢',
                    'BIG_RED':    '🔴',
                    'YELLOW_BUY': '🟡',
                }.get(sig['signal_type'], '⚪')
                logger.info(
                    f"    {emoji} {sig['symbol']:12s} | "
                    f"{sig['signal_type']:12s} | "
                    f"WT1={sig['wt1']:>9.4f} | "
                    f"{sig.get('group', '?')}"
                )

    logger.info("=" * 58)


# ─────────────────────────────────────────────────────────────────────────────
# NO-DEDUP PATCH
# ─────────────────────────────────────────────────────────────────────────────

def patch_no_dedup(scanner: VMCScanner):
    """
    Monkey-patches AlertManager.is_duplicate to always return False.
    This forces all signals to be re-sent regardless of history.
    Used when --no-dedup flag is passed.
    """
    scanner.alert_manager.is_duplicate = lambda signal: False
    logging.getLogger('manual_trigger').warning(
        "Deduplication DISABLED — all signals will be re-sent "
        "even if already in alert history."
    )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='VMC Cipher B — Manual Scan Trigger',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  python manual_trigger.py                 Scan all timeframes
  python manual_trigger.py --tf 1w         Weekly scan only
  python manual_trigger.py --tf 4h         4-Hour scan only
  python manual_trigger.py --tf 1d         Daily scan only
  python manual_trigger.py --tf 1M         Monthly scan only
  python manual_trigger.py --tf 1w --tf 1M Weekly + Monthly
  python manual_trigger.py --no-dedup      Resend all signals (ignore history)
        """
    )

    parser.add_argument(
        '--tf',
        action  = 'append',
        choices = ['4h', '1d', '1w', '1M'],
        dest    = 'timeframes',
        metavar = 'TIMEFRAME',
        help    = (
            'Timeframe to scan. Can be repeated.\n'
            'Choices: 4h, 1d, 1w, 1M\n'
            'Default: all timeframes'
        ),
    )

    parser.add_argument(
        '--no-dedup',
        action  = 'store_true',
        default = False,
        help    = (
            'Disable deduplication — resend all signals\n'
            'even if already sent previously.'
        ),
    )

    args = parser.parse_args()

    # Default: all timeframes if none specified
    timeframes = args.timeframes if args.timeframes else config.TIMEFRAMES

    setup_logging()
    logger = logging.getLogger('manual_trigger')

    print_banner(timeframes, args.no_dedup)

    # Initialise scanner (loads watchlist + alert manager)
    try:
        scanner = VMCScanner()
    except Exception as exc:
        logger.critical(f"Failed to initialise scanner: {exc}", exc_info=True)
        sys.exit(1)

    logger.info(
        f"Watchlist: {len(scanner.watchlist)} active assets — "
        f"{sum(1 for a in scanner.watchlist if a['group'] == 'holdings')} holdings, "
        f"{sum(1 for a in scanner.watchlist if a['group'] == 'keep_an_eye')} keep an eye"
    )

    # Apply no-dedup patch if requested
    if args.no_dedup:
        patch_no_dedup(scanner)

    # Run scans
    results: dict[str, list[dict]] = {}

    for tf in timeframes:
        tf_label = config.TIMEFRAME_LABELS.get(tf, tf)
        logger.info(f"Starting {tf_label} scan...")
        try:
            results[tf] = scanner.scan_timeframe(tf)
        except Exception as exc:
            logger.error(
                f"{tf_label} scan failed: {exc}",
                exc_info=True
            )
            results[tf] = []

    print_summary(results)

    total = sum(len(v) for v in results.values())
    sys.exit(0 if total >= 0 else 1)


if __name__ == '__main__':
    main()
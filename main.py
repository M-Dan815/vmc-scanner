# main.py
# ─────────────────────────────────────────────────────────────────────────────
# Entry point. Sets up logging and schedules scans per timeframe close.
# ─────────────────────────────────────────────────────────────────────────────

import logging
import logging.handlers
import sys
import os
from datetime import datetime, timezone

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron       import CronTrigger

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

    file_handler = logging.handlers.RotatingFileHandler(
        filename    = config.LOG_FILE,
        maxBytes    = config.LOG_MAX_BYTES,
        backupCount = config.LOG_BACKUP_COUNT,
        encoding    = 'utf-8'
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('apscheduler').setLevel(logging.WARNING)


# ─────────────────────────────────────────────────────────────────────────────
# JOB FACTORY
# ─────────────────────────────────────────────────────────────────────────────

def make_scan_job(scanner: VMCScanner, timeframe: str):
    tf_label = config.TIMEFRAME_LABELS.get(timeframe, timeframe)

    def job():
        logger = logging.getLogger('scheduler')
        logger.info(
            f"Cron triggered: {tf_label} scan "
            f"[{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}]"
        )
        try:
            scanner.scan_timeframe(timeframe)
        except Exception as exc:
            logger.error(
                f"Scheduled {tf_label} scan failed: {exc}",
                exc_info=True
            )

    job.__name__ = f"scan_{timeframe}"
    return job


# ─────────────────────────────────────────────────────────────────────────────
# STARTUP BANNER
# ─────────────────────────────────────────────────────────────────────────────

def print_banner(scanner: VMCScanner):
    logger = logging.getLogger('main')

    holdings_count = sum(1 for a in scanner.watchlist if a['group'] == 'holdings')
    watch_count    = sum(1 for a in scanner.watchlist if a['group'] == 'keep_an_eye')

    logger.info("=" * 58)
    logger.info("  VMC Cipher B + Divergences — Alert Scanner")
    logger.info("=" * 58)
    logger.info(f"  Active assets  : {len(scanner.watchlist)}")
    logger.info(f"    Holdings     : {holdings_count}")
    logger.info(f"    Keep an Eye  : {watch_count}")
    logger.info(f"  Timeframes     : {', '.join(config.TIMEFRAMES)}")
    logger.info(f"  Crypto enabled : {config.ENABLE_CRYPTO}")
    logger.info(f"  Stocks enabled : {config.ENABLE_STOCKS}")
    logger.info(f"  Data sources   : Binance.US + Coinbase")
    logger.info(f"  OS Level       : {config.OS_LEVEL} (Big Green below this)")
    logger.info(f"  Red Level      : {config.RED_LEVEL} (Big Red above this)")
    logger.info(f"  Alert target   : {config.GMAIL_RECIPIENT}")
    logger.info(f"  Log file       : {config.LOG_FILE}")
    logger.info("=" * 58)
    logger.info("  Scan schedule (UTC):")
    logger.info(f"    4-Hour  → HH:{config.SCAN_4H_MINUTE:02d} after each 4H close")
    logger.info(f"    Daily   → {config.SCAN_1D_HOUR:02d}:{config.SCAN_1D_MINUTE:02d} daily")
    logger.info(f"    Weekly  → Monday {config.SCAN_1W_HOUR:02d}:{config.SCAN_1W_MINUTE:02d}")
    logger.info(f"    Monthly → 1st of month {config.SCAN_1M_HOUR:02d}:{config.SCAN_1M_MINUTE:02d}")
    logger.info("=" * 58)
    logger.info("  Signal logic:")
    logger.info(f"    🟢 Big Green  → bullish crossover with WT1 < {config.OS_LEVEL}")
    logger.info(f"    🔴 Big Red    → bearish crossover with WT1 > {config.RED_LEVEL}")
    logger.info(f"    🟡 Yellow BUY → bullish crossover with WT1 between {config.OS_LEVEL} and {config.RED_LEVEL}")
    logger.info(f"    🟡 Yellow SELL→ bearish crossover with WT1 between {config.OS_LEVEL} and {config.RED_LEVEL}")
    logger.info("=" * 58)
    logger.info("  Scanner is live. Waiting for candle closes...")
    logger.info("  Press Ctrl+C to stop.")
    logger.info("=" * 58)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    setup_logging()
    logger = logging.getLogger('main')

    scanner = VMCScanner()
    print_banner(scanner)

    scheduler = BlockingScheduler(timezone='UTC')

    # 4-Hour
    scheduler.add_job(
        func    = make_scan_job(scanner, '4h'),
        trigger = CronTrigger(
            hour   = '0,4,8,12,16,20',
            minute = config.SCAN_4H_MINUTE
        ),
        id   = 'scan_4h',
        name = '4-Hour Scan',
        misfire_grace_time = 300,
    )

    # Daily
    scheduler.add_job(
        func    = make_scan_job(scanner, '1d'),
        trigger = CronTrigger(
            hour   = config.SCAN_1D_HOUR,
            minute = config.SCAN_1D_MINUTE
        ),
        id   = 'scan_1d',
        name = 'Daily Scan',
        misfire_grace_time = 600,
    )

    # Weekly
    scheduler.add_job(
        func    = make_scan_job(scanner, '1w'),
        trigger = CronTrigger(
            day_of_week = config.SCAN_1W_DOW,
            hour        = config.SCAN_1W_HOUR,
            minute      = config.SCAN_1W_MINUTE
        ),
        id   = 'scan_1w',
        name = 'Weekly Scan',
        misfire_grace_time = 1800,
    )

    # Monthly
    scheduler.add_job(
        func    = make_scan_job(scanner, '1M'),
        trigger = CronTrigger(
            day    = config.SCAN_1M_DAY,
            hour   = config.SCAN_1M_HOUR,
            minute = config.SCAN_1M_MINUTE
        ),
        id   = 'scan_1M',
        name = 'Monthly Scan',
        misfire_grace_time = 3600,
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scanner stopped by user (Ctrl+C).")
        scheduler.shutdown(wait=False)
        sys.exit(0)
    except Exception as exc:
        logger.critical(f"Scheduler crashed: {exc}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
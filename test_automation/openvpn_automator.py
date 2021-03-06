
import argparse
import logging
import glob
import os.path
import subprocess
import time

import openvpn


logger = logging.getLogger("vpn_loop")

LOG_FORMAT = (
    "%(asctime)s %(levelname)-7s %(name)-12s %(funcName)-14s %(message)s")

UP_DOWN_SCRIPT = "update-resolv-conf"

HOLD_FILE = "/tmp/VPN_HOLD"


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--logfile',
                        help="Logfile to log to")
    parser.add_argument('-p', '--openvpn_path', default='openvpn',
                        help="Path to OpenVPN")
    parser.add_argument('-c', '--crt_file',
                        help="Certificate file.")
    parser.add_argument('-a', '--auth_file',
                        help="File containing \"username\\npassword\"")
    parser.add_argument('-q', '--quiet', action='store_true',
                        help="Less verbose logging.")
    parser.add_argument(
        'vpn_name', help="Name of VPN.")
    parser.add_argument(
        'indir', help="Directory containing configuration files (.ovpn).")
    parser.add_argument(
        'script',
        help="Path to script to run on each. Passed {vpn} and {endpoint}.")
    parser.add_argument(
        'post_script', nargs='?',
        help="Path to script to run AFTER each endpoint. Same args as script.")
    return parser.parse_args()


def setup_logging(verbose, logfile=None):
    root_logger = logging.getLogger()
    formatter = logging.Formatter(LOG_FORMAT)
    streamhandler = logging.StreamHandler()
    streamhandler.setFormatter(formatter)
    root_logger.addHandler(streamhandler)

    if logfile:
        filehandler = logging.FileHandler(logfile)
        filehandler.setFormatter(formatter)
        root_logger.addHandler(filehandler)

    root_logger.setLevel(logging.INFO if verbose else logging.WARNING)


def main():
    args = get_args()

    setup_logging(not args.quiet, args.logfile)

    vpn_name = args.vpn_name.replace(" ", "_")

    crt_file = os.path.abspath(args.crt_file) if args.crt_file else None
    auth_file = os.path.abspath(args.auth_file) if args.auth_file else None

    config_path = os.path.dirname(args.crt_file) if args.crt_file else None

    script_path = os.path.abspath(args.script)
    postscript_path = os.path.abspath(
        args.post_script) if args.post_script else None

    up_down_script = os.path.abspath(
        os.path.join(os.path.dirname(__file__), UP_DOWN_SCRIPT))

    n_errors = 0
    n_endpoints = 0

    for config_file in sorted(glob.glob(os.path.join(args.indir, "*.ovpn"))):

        n_endpoints += 1

        while os.path.exists(HOLD_FILE):
            time.sleep(1)

        config_name = os.path.basename(config_file)[:-5].replace(" ", "_")
        config_file = os.path.abspath(config_file)

        vpn = openvpn.OpenVPN(timeout=60, auth_file=auth_file,
                              config_file=config_file, crt_file=crt_file,
                              path=args.openvpn_path, cwd=config_path,
                              up_down_script=up_down_script)
        logger.info("Processing config: %s", config_file)
        vpn.start()

        if not vpn.started:
            vpn.stop()
            logger.error("Failed to start VPN %s", config_file)
            continue

        # Do other stuff
        logger.info("Calling script.")
        result = subprocess.call([script_path, vpn_name, config_name])
        logger.info("Returned from script.")

        if result:
            logger.error("Result failed on endpoint %s with status %d",
                         config_name, result)
            logger.warning("Will not call postscript on %s %s",
                           vpn_name, config_name)
            n_errors += 1

        vpn.stop()
        logger.debug("VPN stopped!")

        if postscript_path and not result:
            logger.info("Calling post-script.")
            result = subprocess.call([postscript_path, vpn_name, config_name])
            logger.info("Returned from post-script.")

            if result:
                logger.error("Result failed on postscript call %s w/%d",
                             config_name, result)

    if n_errors:
        logger.error("Encountered errors in %d of %d endpoints.",
                     n_errors, n_endpoints)


if __name__ == "__main__":
    main()

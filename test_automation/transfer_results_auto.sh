#!/bin/bash

# This script transfers records generated by run_tests_auto.sh or similar.
# It is designed to be run by the openvpn automator OUTSIDE of a VPN session.
# It is NOT for direct human use.

usage() {
    if [[ "$@" ]]; then
        echo -e "ERROR: $@\n" >&2
    fi

    cat - <<EOF >&2
You should not be calling this script by hand.

It is designed to be called by scripts that iterate over multiple VPN endpoints.

(...but if you must know, the usage is: $0 VPN_NAME VPN_LOC_TAG )

EOF
    exit 1
}

NUM_ARGS=2

if [[ "$#" -ne $NUM_ARGS ]]; then
    usage "Invalid Arguments"
fi

if [[ $(whoami) != 'root' ]]; then
    echo "This script must run as root! (precede command with 'sudo')" >&2
    exit 1
fi

### determine the root directory -- hackish but works with OS X and bash.
pushd $(dirname $BASH_SOURCE)/.. > /dev/null
ROOT=$(pwd)
popd >/dev/null
###

# Still needed for log_checkpoint
source $ROOT/venv/bin/activate

# Functions for uploading results and retrieving API keys.
source $ROOT/includes/transfer_func.sh
# Additional helper functions for cleanly running tests.
source $ROOT/includes/helper_funcs.sh

DEFAULT_DIR=`pwd`

# collect information about the vpn service
VPN_NAME=$1
VPN_LOC_TAG=$2

# create a tag for labeling purposes
PATH_SAFE_VPN_NAME=$(echo "${VPN_NAME// /_}" | clean_str)
PATH_SAFE_VPN_LOC_TAG=$(echo "${VPN_LOC_TAG// /_}" | clean_str)
TAG=${PATH_SAFE_VPN_NAME}_${PATH_SAFE_VPN_LOC_TAG}

################################################################################

RESULTS_DIR=$DEFAULT_DIR/results/$TAG

log_checkpoint "auto_pre_transfer"

info "Waiting for internet to recover."
wait_until_connected
info "Transferring results"
transfer_file $TAG $RESULTS_DIR
rm -r $RESULTS_DIR
alert "TRANSER COMPLETE"
log_checkpoint "auto_done"

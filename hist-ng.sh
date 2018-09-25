#!/bin/bash

HIST_NG_PATH="/home/cipherboy/GitHub/cipherboy/hist-ng/hist-ng.py"

function hist_ng_save() {
    local last_hist="$HISTFILE"
    local temp_hist="$(mktemp)"
    local last_command=""

    export HISTFILE="$temp_hist"
    history -w
    last_command="$(tail -n 1 "$temp_hist")"
    python3 "$HIST_NG_PATH" save "$last_command"

    rm -rf $temp_hist
    export HISTFILE="$last_hist"
    history -a
    history -c
    history -r
}

export PROMPT_COMMAND="hist_ng_save; $PROMPT_COMMAND"

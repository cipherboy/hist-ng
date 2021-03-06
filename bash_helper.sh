#!/bin/bash

HIST_NG_PATH="/home/cipherboy/GitHub/cipherboy/hist-ng/hist_ng.py"

export HIST_NG_PROJECT="global"
export HIST_NG_SESSION="$(pwd)-$$-$RANDOM-$RANDOM-$RANDOM"

function hist_ng_save() {
    local last_hist="$HISTFILE"
    local temp_hist="$(mktemp)"
    local last_command=""

    export HISTFILE="$temp_hist"
    history -w
    last_command="$(tail -n 1 "$temp_hist")"
    python3 "$HIST_NG_PATH" cmd "$last_command"

    rm -rf $temp_hist
    export HISTFILE="$(python3 "$HIST_NG_PATH" session)"
    history -c
    history -r
}

function hist_ng_context() {
    export HIST_NG_PROJ="$1"
}

export PROMPT_COMMAND="hist_ng_save; $PROMPT_COMMAND"

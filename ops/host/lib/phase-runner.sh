#!/usr/bin/env bash
#
# Shared helpers for phase validation scripts.
# Provides timed checks and deterministic parallel check aggregation.

set -euo pipefail

phase_runner_record() {
  local line="$1"

  if declare -F record >/dev/null 2>&1; then
    record "${line}"
    return 0
  fi

  if [ -z "${EVIDENCE_FILE:-}" ]; then
    echo "ERROR: phase runner requires record() or EVIDENCE_FILE."
    return 1
  fi

  printf "%s\n" "${line}" >>"${EVIDENCE_FILE}"
}

phase_runner_require_log_file() {
  if [ -z "${LOG_FILE:-}" ]; then
    echo "ERROR: LOG_FILE must be set before using phase runner helpers."
    return 1
  fi
}

phase_runner_run_check_timed() {
  local name="$1"
  local cmd="$2"
  local started_at ended_at elapsed

  phase_runner_require_log_file

  phase_runner_record "### ${name}"
  phase_runner_record ""
  phase_runner_record '```bash'
  phase_runner_record "${cmd}"
  phase_runner_record '```'

  started_at="$(date +%s)"
  if eval "${cmd}" >>"${LOG_FILE}" 2>&1; then
    ended_at="$(date +%s)"
    elapsed=$((ended_at - started_at))
    phase_runner_record "- status: PASS"
    phase_runner_record "- duration_s: \`${elapsed}\`"
  else
    ended_at="$(date +%s)"
    elapsed=$((ended_at - started_at))
    phase_runner_record "- status: FAIL"
    phase_runner_record "- duration_s: \`${elapsed}\`"
    phase_runner_record "- log: \`${LOG_FILE}\`"
    return 1
  fi
  phase_runner_record ""
}

phase_runner_run_parallel_checks() {
  if [ "$#" -lt 4 ] || [ $(( $# % 2 )) -ne 0 ]; then
    echo "ERROR: run_parallel_checks expects <name cmd> pairs."
    return 1
  fi

  phase_runner_require_log_file

  local tmp_dir
  tmp_dir="$(mktemp -d "/tmp/phase-runner-parallel.${PHASE_ID:-phase}.XXXXXX")"

  local -a names cmds out_files status_files duration_files rc_files pids
  local idx=0
  local has_failure=0

  while [ "$#" -gt 0 ]; do
    names+=("$1")
    cmds+=("$2")
    shift 2
  done

  for idx in "${!names[@]}"; do
    out_files[idx]="${tmp_dir}/check-${idx}.out"
    status_files[idx]="${tmp_dir}/check-${idx}.status"
    duration_files[idx]="${tmp_dir}/check-${idx}.duration"
    rc_files[idx]="${tmp_dir}/check-${idx}.rc"

    (
      set +e
      local started_at ended_at elapsed rc
      started_at="$(date +%s)"
      eval "${cmds[idx]}" >"${out_files[idx]}" 2>&1
      rc=$?
      ended_at="$(date +%s)"
      elapsed=$((ended_at - started_at))

      if [ "${rc}" -eq 0 ]; then
        printf "PASS\n" >"${status_files[idx]}"
      else
        printf "FAIL\n" >"${status_files[idx]}"
      fi

      printf "%s\n" "${elapsed}" >"${duration_files[idx]}"
      printf "%s\n" "${rc}" >"${rc_files[idx]}"
    ) &
    pids[idx]=$!
  done

  for idx in "${!pids[@]}"; do
    wait "${pids[idx]}" || true
  done

  for idx in "${!names[@]}"; do
    local status duration rc
    status="FAIL"
    duration="0"
    rc="1"
    if [ -f "${status_files[idx]}" ]; then
      status="$(cat "${status_files[idx]}")"
    fi
    if [ -f "${duration_files[idx]}" ]; then
      duration="$(cat "${duration_files[idx]}")"
    fi
    if [ -f "${rc_files[idx]}" ]; then
      rc="$(cat "${rc_files[idx]}")"
    fi

    phase_runner_record "### ${names[idx]}"
    phase_runner_record ""
    phase_runner_record '```bash'
    phase_runner_record "${cmds[idx]}"
    phase_runner_record '```'
    phase_runner_record "- mode: parallel"

    if [ "${status}" = "PASS" ]; then
      phase_runner_record "- status: PASS"
      phase_runner_record "- duration_s: \`${duration}\`"
    else
      phase_runner_record "- status: FAIL"
      phase_runner_record "- duration_s: \`${duration}\`"
      phase_runner_record "- exit_code: \`${rc}\`"
      phase_runner_record "- log: \`${LOG_FILE}\`"
      has_failure=1
    fi
    phase_runner_record ""

    if [ -f "${out_files[idx]}" ]; then
      {
        echo ""
        echo "===== parallel check: ${names[idx]} ====="
        cat "${out_files[idx]}"
      } >>"${LOG_FILE}"
    fi
  done

  rm -rf "${tmp_dir}"

  if [ "${has_failure}" -ne 0 ]; then
    return 1
  fi
}

run_check_timed() {
  phase_runner_run_check_timed "$@"
}

run_parallel_checks() {
  phase_runner_run_parallel_checks "$@"
}

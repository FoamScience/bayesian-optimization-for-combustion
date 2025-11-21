#!/bin/bash
#
# Extract log-based metrics from OpenFOAM case
#
# Usage: get_metric.sh <case_dir> <metric_name>
#
# Available metrics:
#   continuity_error_local      - Latest local sum of continuity errors
#   continuity_error_global     - Latest global continuity error (absolute)
#   continuity_error_cumulative - Cumulative continuity error (absolute)
#   pressure_drop               - Static pressure drop: P_inlet - P_outlet (Pa)
#   pressure_loss_coefficient   - Normalized pressure drop: ΔP/P_inlet
#   yplus_max                   - Maximum y+ value on walls
#   yplus_avg                   - Average y+ value on walls
#
# Outputs only the scalar value, or "nan" if metric cannot be computed.
#

set -euo pipefail

# Check arguments
if [ $# -ne 2 ]; then
    echo "Usage: $0 <case_dir> <metric_name>" >&2
    echo "nan"
    exit 0
fi

CASE_DIR="$1"
METRIC="$2"
LOG_FILE="${CASE_DIR}/log.reactingFoam"

# Check if log file exists
if [ ! -f "$LOG_FILE" ]; then
    echo "nan"
    exit 0
fi

# Extract metric based on type
case "$METRIC" in
    continuity_error_local)
        # Extract latest local continuity error
        # Line format: "time step continuity errors : sum local = 1.0858e-07, global = ..."
        awk '/time step continuity errors/ {
            match($0, /sum local = ([0-9.eE+-]+)/, arr)
            if (arr[1]) value = arr[1]
        }
        END {
            if (value) print value
            else print "nan"
        }' "$LOG_FILE" 2>/dev/null || echo "nan"
        ;;

    continuity_error_global)
        # Extract latest global continuity error (absolute value)
        # Line format: "time step continuity errors : ... global = -6.275e-09, cumulative = ..."
        awk '/time step continuity errors/ {
            match($0, /global = ([0-9.eE+-]+)/, arr)
            if (arr[1]) value = arr[1]
        }
        END {
            if (value) {
                # Return absolute value
                if (value < 0) value = -value
                print value
            } else {
                print "nan"
            }
        }' "$LOG_FILE" 2>/dev/null || echo "nan"
        ;;

    continuity_error_cumulative)
        # Extract latest cumulative continuity error (absolute value)
        # Line format: "time step continuity errors : ... cumulative = 3.862e-05"
        awk '/time step continuity errors/ {
            match($0, /cumulative = ([0-9.eE+-]+)/, arr)
            if (arr[1]) value = arr[1]
        }
        END {
            if (value) {
                # Return absolute value
                if (value < 0) value = -value
                print value
            } else {
                print "nan"
            }
        }' "$LOG_FILE" 2>/dev/null || echo "nan"
        ;;

    pressure_drop)
        # Extract pressure drop from postProcessing files
        # Compute: ΔP = P_inlet - P_outlet (static pressure)
        # Note: Find the minimum common time between inlet and outlet files

        INLET_FILE="${CASE_DIR}/postProcessing/inletTotalPressure/0/surfaceFieldValue.dat"
        OUTLET_FILE="${CASE_DIR}/postProcessing/outletTotalPressure/0/surfaceFieldValue.dat"

        # Check if files exist
        if [ ! -f "$INLET_FILE" ] || [ ! -f "$OUTLET_FILE" ]; then
            echo "nan"
            exit 0
        fi

        # Get last time from both files and use the minimum
        t_inlet=$(awk '!/^#/ && NF >= 2 {t = $1} END {print t}' "$INLET_FILE")
        t_outlet=$(awk '!/^#/ && NF >= 2 {t = $1} END {print t}' "$OUTLET_FILE")

        # Find minimum time
        min_time=$(awk -v t1="$t_inlet" -v t2="$t_outlet" 'BEGIN {print (t1 < t2) ? t1 : t2}')

        # Extract pressures at the closest time <= min_time
        p_inlet=$(awk -v tmax="$min_time" '!/^#/ && NF >= 2 && $1 <= tmax {p = $2} END {if (p) print p; else print "nan"}' "$INLET_FILE")
        p_outlet=$(awk -v tmax="$min_time" '!/^#/ && NF >= 2 && $1 <= tmax {p = $2} END {if (p) print p; else print "nan"}' "$OUTLET_FILE")

        # Calculate pressure drop
        if [ "$p_inlet" != "nan" ] && [ "$p_outlet" != "nan" ]; then
            awk -v p_in="$p_inlet" -v p_out="$p_outlet" 'BEGIN {
                dp = p_in - p_out
                print dp
            }'
        else
            echo "nan"
        fi
        ;;

    pressure_loss_coefficient)
        # Extract pressure loss coefficient from postProcessing files
        # δ* = ΔP / P_inlet (normalized pressure drop)

        INLET_FILE="${CASE_DIR}/postProcessing/inletTotalPressure/0/surfaceFieldValue.dat"
        OUTLET_FILE="${CASE_DIR}/postProcessing/outletTotalPressure/0/surfaceFieldValue.dat"

        # Check if files exist
        if [ ! -f "$INLET_FILE" ] || [ ! -f "$OUTLET_FILE" ]; then
            echo "nan"
            exit 0
        fi

        # Get last time from both files and use the minimum
        t_inlet=$(awk '!/^#/ && NF >= 2 {t = $1} END {print t}' "$INLET_FILE")
        t_outlet=$(awk '!/^#/ && NF >= 2 {t = $1} END {print t}' "$OUTLET_FILE")

        # Find minimum time
        min_time=$(awk -v t1="$t_inlet" -v t2="$t_outlet" 'BEGIN {print (t1 < t2) ? t1 : t2}')

        # Extract pressures at the closest time <= min_time
        p_inlet=$(awk -v tmax="$min_time" '!/^#/ && NF >= 2 && $1 <= tmax {p = $2} END {if (p) print p; else print "nan"}' "$INLET_FILE")
        p_outlet=$(awk -v tmax="$min_time" '!/^#/ && NF >= 2 && $1 <= tmax {p = $2} END {if (p) print p; else print "nan"}' "$OUTLET_FILE")

        # Calculate coefficient
        if [ "$p_inlet" != "nan" ] && [ "$p_outlet" != "nan" ]; then
            awk -v p_in="$p_inlet" -v p_out="$p_outlet" 'BEGIN {
                if (p_in != 0) {
                    delta_star = (p_in - p_out) / p_in
                    print delta_star
                } else {
                    print "nan"
                }
            }'
        else
            echo "nan"
        fi
        ;;

    yplus_max)
        # Extract maximum y+ value from yPlus function object
        awk '
            /yPlus.*:/ {
                found = 1
                next
            }
            found && /max:/ {
                match($0, /max: ([0-9.eE+-]+)/, arr)
                if (arr[1]) value = arr[1]
                found = 0
            }
            END {
                if (value) print value
                else print "nan"
            }
        ' "$LOG_FILE" 2>/dev/null || echo "nan"
        ;;

    yplus_avg)
        # Extract average y+ value
        awk '
            /yPlus.*:/ {
                found = 1
                next
            }
            found && /average:/ {
                match($0, /average: ([0-9.eE+-]+)/, arr)
                if (arr[1]) value = arr[1]
                found = 0
            }
            END {
                if (value) print value
                else print "nan"
            }
        ' "$LOG_FILE" 2>/dev/null || echo "nan"
        ;;

    ch4_domain_average)
        OUTPUT=$(pvpython /tmp/data/scripts/compute_metric.py "$CASE_DIR" ch4_domain_average 2>/dev/null)
        if [ $? -ne 0 ] || [ -z "$OUTPUT" ]; then
            echo "nan"
        else
            echo "$OUTPUT"
        fi
        ;;

    pattern_factor)
        OUTPUT=$(pvpython /tmp/data/scripts/compute_metric.py "$CASE_DIR" pattern_factor 2>/dev/null)
        if [ $? -ne 0 ] || [ -z "$OUTPUT" ]; then
            echo "nan"
        else
            echo "$OUTPUT"
        fi
        ;;

    temperature_rise)
        OUTPUT=$(pvpython /tmp/data/scripts/compute_metric.py "$CASE_DIR" temperature_rise 2>/dev/null)
        if [ $? -ne 0 ] || [ -z "$OUTPUT" ]; then
            echo "nan"
        else
            echo "$OUTPUT"
        fi
        ;;

    *)
        # Unknown metric
        echo "nan"
        exit 0
        ;;
esac

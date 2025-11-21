#!/usr/bin/env bash

if ! command -v pvpython &> /dev/null; then
    echo "Install Paraview (at least 5.10)"
    exit 1
fi

if ! command -v uv &> /dev/null; then
    echo "Install uv from https://docs.astral.sh/uv/"
    exit 1
fi

if [ -z $WM_PROJECT ]; then
    echo "Source an OpenFOAM (ESI/OpenCFD) installation"
    exit 1
fi

set -e
mkdir /tmp/data/trials -p
mkdir artifacts -p
rm -rf /tmp/data/scripts
ln -s "$PWD/scripts" /tmp/data/scripts

echo "All good..."
echo "------------------------------------------------------------------"
echo "To start the optimization process:"
echo -e "   \033[1muvx foamBO --config MOO.yaml\033[0m"
echo "You can always browse the docs with:"
echo -e "   \033[1muvx foamBO --docs\033[0m"
echo "Check on the optimization with:"
echo -e "   \033[1muvx foamBO --visualize --config MOO.yaml ++store.read_from=json\033[0m"
echo "Or:"
echo -e "   \033[1muvx foamBO --analysis --config MOO.yaml ++store.read_from=json\033[0m"
echo "------------------------------------------------------------------"

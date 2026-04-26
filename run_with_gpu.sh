#!/bin/bash
export XAUTHORITY=/run/user/1002/gdm/Xauthority
export DISPLAY=:0
source ~/anaconda3/etc/profile.d/conda.sh
conda activate embench
python explore_alfred.py

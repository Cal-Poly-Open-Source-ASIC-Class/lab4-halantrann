printf "\
read_db "$(find runs/*/final/odb/* -type f -printf '%T@ %p\n' | sort -nr | head -1 | cut -d' ' -f2-)"
read_lib  $PDKPATH/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v60.lib
read_sdc  "$(find runs/*/final/sdc/* -type f -printf '%T@ %p\n' | sort -nr | head -1 | cut -d' ' -f2-)"
gui::show \n"
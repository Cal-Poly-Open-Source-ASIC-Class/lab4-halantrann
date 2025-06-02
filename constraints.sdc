puts "\[INFO\]: Creating Clocks"
create_clock [get_ports r_clk] -name r_clk -period 7
set_propagated_clock r_clk
create_clock [get_ports w_clk] -name w_clk -period 14
set_propagated_clock w_clk

set_clock_groups -asynchronous -group [get_clocks {r_clk w_clk}]

puts "\[INFO\]: Setting Max Delay"

set read_period     [get_property -object_type clock [get_clocks {r_clk}] period]
set write_period    [get_property -object_type clock [get_clocks {w_clk}] period]
set min_period      [expr {min(${read_period}, ${write_period})}]


set_max_delay -from [get_pins rgray*df*/CLK] -to [get_pins rgray_s2*df*/D] $min_period
set_max_delay -from [get_pins wgray*df*/CLK] -to [get_pins wgray_s2*df*/D] $min_period
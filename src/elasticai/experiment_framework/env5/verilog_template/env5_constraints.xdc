## Clock
set_property -dict { PACKAGE_PIN H11   IOSTANDARD LVCMOS33 } [get_ports { CLK_SYS }]; # IO_L13P_T2_MRCC_14
create_clock -add -name clk_100 -period 10 -waveform {0 5} [get_ports { CLK_SYS }];

## Status
set_property -dict { PACKAGE_PIN L12 IOSTANDARD LVCMOS33 } [get_ports { FPGA_BUSY }];

## Reset (active-low, asynchron von MCU GPIO13)
set_property -dict { PACKAGE_PIN M13 IOSTANDARD LVCMOS33 PULLDOWN true } [get_ports { RSTN_MCU }];
set_false_path -from [get_ports { RSTN_MCU }];

## SPI
set_property -dict { PACKAGE_PIN N11 IOSTANDARD LVCMOS33 } [get_ports { SPI_SCLK }];
set_property -dict { PACKAGE_PIN P12 IOSTANDARD LVCMOS33 } [get_ports { SPI_CSN }];
set_property -dict { PACKAGE_PIN P11 IOSTANDARD LVCMOS33 } [get_ports { SPI_MOSI }];
set_property -dict { PACKAGE_PIN M12 IOSTANDARD LVCMOS33 } [get_ports { SPI_MISO }];

## LEDs
set_property -dict { PACKAGE_PIN H12 IOSTANDARD LVCMOS33 } [get_ports { LEDS[0] }];
set_property -dict { PACKAGE_PIN J12 IOSTANDARD LVCMOS33 } [get_ports { LEDS[1] }];
set_property -dict { PACKAGE_PIN K12 IOSTANDARD LVCMOS33 } [get_ports { LEDS[2] }];
set_property -dict { PACKAGE_PIN J11 IOSTANDARD LVCMOS33 } [get_ports { LEDS[3] }];

## Configuration options, can be used for all designs
set_property BITSTREAM.CONFIG.CONFIGRATE 50 [current_design]
set_property BITSTREAM.CONFIG.SPI_BUSWIDTH 4 [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]
set_property CFGBVS VCCO [current_design]
set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
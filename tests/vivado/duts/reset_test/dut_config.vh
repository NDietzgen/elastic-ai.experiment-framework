//////////////////////////////////////////////////////////////////////////////////
// File Name:       dut_config.vh
// Description:     Auswahl des zu testenden Moduls (DUT).
//                  Anleitung und Liste der Klassen: README.md
//
// DUT_TYPE         "ROM", "RAM", "MULT", "MAC", "FILT", "DNN" oder "USER"
// DUT_BITWIDTH_IN  Bitbreite der Eingangsdaten (<= 16)
// DUT_MODULE       Modulname des DUT (optional, nicht bei "USER");
//                  auskommentiert = Standardname der Klasse
//////////////////////////////////////////////////////////////////////////////////

`ifndef DUT_CONFIG_VH
`define DUT_CONFIG_VH

`define DUT_TYPE        "USER"
`define DUT_BITWIDTH_IN 16
// `define DUT_MODULE   Mein_Modul

`endif

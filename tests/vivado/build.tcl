array set cfg $argv
foreach key {part top proj_name proj_dir src_dir src_xdc jobs} {
    if {![info exists cfg(-$key)]} { error "Fehlendes Argument: -$key" }
}

set part      $cfg(-part)
set top       $cfg(-top)
set proj_name $cfg(-proj_name)
set proj_dir  [file normalize $cfg(-proj_dir)]
set src_dir   [file normalize $cfg(-src_dir)]
set src_xdc   [file normalize $cfg(-src_xdc)]
set jobs      $cfg(-jobs)

# Alle Dateien eines Musters rekursiv einsammeln (Tcl-glob ist nicht rekursiv)
proc find_files {dir patterns} {
    set found {}
    foreach p $patterns {
        lappend found {*}[glob -nocomplain -directory $dir -types f $p]
    }
    foreach sub [glob -nocomplain -directory $dir -types d *] {
        lappend found {*}[find_files $sub $patterns]
    }
    return $found
}

set srcs [find_files $src_dir {*.v *.sv}]
if {[llength $srcs] == 0} { error "Keine .v/.sv-Dateien in $src_dir" }
if {![file exists $src_xdc]} { error "Datei nicht gefunden: $src_xdc" }

puts "Quelldateien: [llength $srcs]"
foreach f $srcs { puts "  $f" }

# ---- Projekt erstellen ----
create_project -force $proj_name $proj_dir/$proj_name -part $part
add_files -norecurse $srcs
add_files -fileset constrs_1 -norecurse $src_xdc
set_property top $top [current_fileset]
update_compile_order -fileset sources_1

# ---- Synthese ----
launch_runs synth_1 -jobs $jobs
wait_on_run synth_1
set status [get_property STATUS [get_runs synth_1]]
puts "Synthese-Status: $status"
if {![string match "*Complete*" $status]} { error "Synthese fehlgeschlagen: $status" }

# ---- Implementierung + Bitstream ----
launch_runs impl_1 -to_step write_bitstream -jobs $jobs
wait_on_run impl_1
set status [get_property STATUS [get_runs impl_1]]
puts "Implementierungsstatus: $status"
if {![string match "*Complete*" $status]} { error "Implementierung fehlgeschlagen: $status" }

close_project
puts "BUILD ERFOLGREICH ABGESCHLOSSEN"
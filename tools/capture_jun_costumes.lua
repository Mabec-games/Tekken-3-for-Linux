-- MAME 0.289, tektagt World TEG2/VER.C1, fresh NVRAM. No ROM data embedded.
-- Source-format audit: JUN_CAPTURE_OUTFIT=1,2,3 chooses Jun's original
-- model lookup 46,47,118 in her first selector position. This changes only
-- the in-memory preview lookup, never the ROM/NVRAM or the selected fighter.
local outfit=tonumber(os.getenv("JUN_CAPTURE_OUTFIT") or "1")
assert(outfit>=1 and outfit<=3)
local models={46,47,118}
local machine=manager.machine
local space=machine.devices[":maincpu"].spaces["program"]
local port=machine.ioport.ports[":JVS_PLAYER1"]
local frame=0
local function dump(name)
    local f=assert(io.open(name,"wb"))
    f:write(space:read_range(0,0x3fffff,8));f:close()
end
jun_import_capture=emu.add_machine_frame_notifier(function()
    frame=frame+1
    if frame>1800 then
        assert(space:read_u8(0x800111fd)==47 and space:read_u8(0x80011200)==118)
        space:write_u8(0x800111fc,models[outfit])
    end
    if frame==1800 then machine.ioport.ports[":JVS_COIN1"].fields["Coin 1"]:set_value(1) end
    if frame==1804 then machine.ioport.ports[":JVS_COIN1"].fields["Coin 1"]:set_value(0) end
    if frame==1860 then port.fields["1 Player Start"]:set_value(1) end
    if frame==1864 then port.fields["1 Player Start"]:set_value(0) end
    if frame==1962 then port.fields["P1 Up"]:set_value(1) end
    if frame==1966 then port.fields["P1 Up"]:set_value(0) end
    if frame>=1974 and frame<=2070 and (frame-1974)%12==0 then port.fields["P1 Right"]:set_value(1) end
    if frame>=1978 and frame<=2074 and (frame-1978)%12==0 then port.fields["P1 Right"]:set_value(0) end
    if frame==2130 then dump("jun-p"..outfit.."-select.bin");machine.video:snapshot();machine:exit() end
end)

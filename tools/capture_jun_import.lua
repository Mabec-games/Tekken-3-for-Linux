-- MAME 0.289, tektagt World TEG2/VER.C1, fresh NVRAM. No ROM data embedded.
-- Start from Xiaoyu, highlight Jun in the upper-right, then Jin below her.
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
    if frame==1800 then machine.ioport.ports[":JVS_COIN1"].fields["Coin 1"]:set_value(1) end
    if frame==1804 then machine.ioport.ports[":JVS_COIN1"].fields["Coin 1"]:set_value(0) end
    if frame==1860 then port.fields["1 Player Start"]:set_value(1) end
    if frame==1864 then port.fields["1 Player Start"]:set_value(0) end
    if frame==1962 then port.fields["P1 Up"]:set_value(1) end
    if frame==1966 then port.fields["P1 Up"]:set_value(0) end
    if frame>=1974 and frame<=2070 and (frame-1974)%12==0 then port.fields["P1 Right"]:set_value(1) end
    if frame>=1978 and frame<=2074 and (frame-1978)%12==0 then port.fields["P1 Right"]:set_value(0) end
    if frame==2130 then dump("jun-select-ram.bin") end
    if frame==2142 then port.fields["P1 Down"]:set_value(1) end
    if frame==2146 then port.fields["P1 Down"]:set_value(0) end
    if frame==2202 then dump("jin-select-ram.bin");machine:exit() end
end)

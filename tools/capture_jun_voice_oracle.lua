-- Run from workspace/jun-import with the local tektagt jun-fight state.
-- Request Jun's verified sound IDs through the original H8 driver. Capture
-- C352 registers when its execute-key-on register is written, after all
-- wave registers have been populated (the flags write happens too early).
local machine=manager.machine
local space=machine.devices[':sub'].spaces['program']
local out=assert(io.open('jun-voice-oracle.csv','w'))
out:write('tick,requested_id,voice,volume_front,frequency,flags,bank,start,end\n')
local tick,requested=0,0
jun_voice_tap=space:install_write_tap(0x280404,0x280405,'jun-voice-keyon',function()
 local base=0x280000+21*16
 if (space:read_u16(base+6)&0x4000)~=0 then
  out:write(string.format('%d,%d,21,%d,%d,%d,%d,%d,%d\n',tick,requested,
   space:read_u16(base),space:read_u16(base+4),space:read_u16(base+6),
   space:read_u16(base+8),space:read_u16(base+10),space:read_u16(base+12)))
 end
end)
jun_voice_frames=emu.add_machine_frame_notifier(function()
 tick=tick+1
 requested=0
 if tick>=60 and tick<=720 and (tick-60)%60==0 then
  requested=160+(tick-60)//60
  space:write_u16(0x080204,0x10)
  space:write_u16(0x080222,requested)
  space:write_u16(0x08012a,0x4101)
 end
 if tick==780 then out:close();machine:exit() end
end)

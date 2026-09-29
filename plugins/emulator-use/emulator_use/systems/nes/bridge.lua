-- File IPC: validated positional commands, no remotely evaluated Lua.
local root = assert(os.getenv('EMULATOR_USE_SESSION'))
local active, pending = nil, nil
local checkpoints = {}
local logical_frame = 0
local replay = false
local replay_length = 0
local buttons = {'A','B','select','start','up','down','left','right'}
local function input(names)
  if replay then return end -- Native FCEUX movie playback owns both ports.
  local state = {}
  for _, key in ipairs(buttons) do state[key] = false end
  for key in (names or ''):gmatch('[^,]+') do state[key] = true end
  joypad.set(1, state)
  local released = {}
  for _, key in ipairs(buttons) do released[key] = false end
  joypad.set(2, released)
end
local function json(value)
  local t = type(value)
  if t == 'nil' then return 'null' end
  if t == 'number' or t == 'boolean' then return tostring(value) end
  if t == 'string' then
    return '"' .. value:gsub('[%z\1-\31\\"]', function(c)
      return string.format('\\u%04x', string.byte(c))
    end) .. '"'
  end
  local out = {}
  if #value > 0 then
    for _, v in ipairs(value) do out[#out+1] = json(v) end
    return '[' .. table.concat(out, ',') .. ']'
  end
  for k,v in pairs(value) do out[#out+1] = json(tostring(k)) .. ':' .. json(v) end
  return '{' .. table.concat(out, ',') .. '}'
end
local function write(path, data)
  local f = assert(io.open(path .. '.tmp','wb')); f:write(data); f:close()
  assert(os.rename(path .. '.tmp',path))
end
local function regs()
  local r = {}
  for _, key in ipairs({'a','x','y','s','p','pc'}) do r[key] = memory.getregister(key) end
  return r
end
local function status()
  return {frame=logical_frame, emulator_frame=emu.framecount(), paused=emu.paused(),
    registers=regs(), rom=rom.getfilename(), rom_md5=rom.gethash('md5'), protocol=1,
    movie={enabled=replay, frame=logical_frame, length=replay_length,
      remaining=math.max(0,replay_length-logical_frame),
      mode=replay and (logical_frame>=replay_length and 'finished' or 'playback') or 'none'}}
end
local function unwatch()
  if active and active.watch then memory.registerwrite(active.watch, 1, nil) end
end
local function respond(id, value)
  value.id = id
  write(root .. '/response.json', json(value))
end
local function complete()
  unwatch()
  input('')
  emu.pause()
  local result=status()
  result.frames_advanced=active.total
  if active.watch then
    result.events=active.events
    result.event_count=active.count
    result.truncated=active.count > #active.events
    result.pc_context='CPU address only; mapper bank is not resolved'
  end
  pending={id=active.id,result=result}
  active=nil
end
emu.registerbefore(function()
  input(active and active.buttons or '')
end)
emu.registerafter(function()
  if active then
    logical_frame=logical_frame+1
    active.remaining=active.remaining-1
    if active.remaining <= 0 then complete() end
  else emu.pause() end
end)
local function handle(lines)
  local id,op=assert(lines[1]),assert(lines[2])
  if op=='status' then respond(id,status())
  elseif op=='movie' then
    assert(not replay and logical_frame==0 and next(checkpoints)==nil,'Fresh session required')
    assert(movie.play(root .. '/replay.fm2',true),'Could not load FM2 movie')
    movie.setreadonly(true)
    joypad.set(1,{}); joypad.set(2,{}) -- Relinquish any pending manual overrides.
    replay=true; replay_length=movie.length(); logical_frame=0
    emu.pause()
    respond(id,status())
  elseif op=='step' or op=='watch' then
    local n=assert(tonumber(lines[3])); assert(n>=1 and n<=600)
    if replay then
      assert((lines[4] or '')=='','Movie replay owns controller inputs')
      n=math.min(n,math.max(0,replay_length-logical_frame))
      if n==0 then
        local result=status(); result.frames_advanced=0
        result.events={}; result.event_count=0; result.truncated=false
        respond(id,result); return
      end
    end
    active={id=id,remaining=n,total=n,buttons=lines[4] or '',events={},count=0}
    if op=='watch' then
      active.watch=assert(tonumber(lines[5])); assert(active.watch>=0 and active.watch<2048)
      local limit=assert(tonumber(lines[6])); assert(limit>=1 and limit<=512)
      memory.registerwrite(active.watch,1,function(address,size,value)
        active.count=active.count+1
        if #active.events < limit then
          active.events[#active.events+1]={frame=logical_frame+1,address=address,
            size=size,value=value,registers=regs()}
        end
      end)
    end
    input(active.buttons); emu.unpause()
  elseif op=='ram' then
    local address,count=assert(tonumber(lines[3])),assert(tonumber(lines[4]))
    assert(address>=0 and count>=1 and count<=2048 and address+count<=2048)
    local bytes={}
    for i=0,count-1 do bytes[#bytes+1]=memory.readbyte(address+i) end
    respond(id,{frame=logical_frame,address=address,bytes=bytes})
  elseif op=='screenshot' then
    write(root .. '/' .. id .. '.gd',gui.gdscreenshot(true))
    respond(id,{frame=logical_frame,file=id .. '.gd'})
  elseif op=='save' then
    local key=assert(lines[3]); assert(key:match('^[%w_-]+$'))
    assert(not checkpoints[key], 'Checkpoint already exists')
    local state=savestate.create(root .. '/state-' .. key .. '.fcs')
    savestate.save(state); savestate.persist(state)
    checkpoints[key]={state=state,frame=logical_frame}
    respond(id,{checkpoint=key,frame=logical_frame,scope='this session'})
  elseif op=='load' then
    local cp=assert(checkpoints[lines[3]],'Unknown checkpoint')
    savestate.load(cp.state); logical_frame=cp.frame; input(''); emu.pause()
    respond(id,status())
  else error('Unknown operation') end
end
gui.register(function()
  if pending then respond(pending.id,pending.result); pending=nil end
  if active then return end
  local f=io.open(root .. '/request.txt','rb')
  if not f then return end
  local data=f:read('*a'); f:close(); os.remove(root .. '/request.txt')
  local lines={}
  for line in data:gmatch('(.-)\n') do lines[#lines+1]=line end
  local ok,err=pcall(handle,lines)
  if not ok then
    unwatch(); active=nil; input(''); emu.pause()
    respond(lines[1] or 'unknown',{error=tostring(err)})
  end
end)
emu.registerexit(function() unwatch(); input(''); emu.pause() end)
input(''); emu.pause()
write(root .. '/ready.json',json(status()))

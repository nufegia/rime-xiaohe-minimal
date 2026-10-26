-- SPDX-License-Identifier: GPL-3.0-or-later
local M = {}
local function reset(ctx)
  ctx:set_property('xh_pager_page', '0')
  ctx:set_property('xh_pager_signature', '')
  ctx:set_property('xh_pager_next', '0')
  ctx:set_property('xh_pager_count', '0')
  ctx:set_property('xh_pager_offset', '0')
end

function M.init(env)
  local ctx = env.engine.context
  reset(ctx)
  env.commit_connection = ctx.commit_notifier:connect(function(c) reset(c) end)
  env.update_connection = ctx.update_notifier:connect(function(c)
    if c.input == '' then reset(c) end
  end)
end

function M.func(key, env)
  if key:release() or key:ctrl() or key:alt() or key:super() then return 2 end
  local ctx = env.engine.context
  if ctx:get_option('ascii_mode') or not ctx:has_menu() then return 2 end
  local code = key.keycode
  local page = tonumber(ctx:get_property('xh_pager_page')) or 0
  local forward = code == 0xff56 or code == 61 or (code == 0xff09 and not key:shift())
  local backward = code == 0xff55 or code == 45 or code == 0xfe20
      or (code == 0xff09 and key:shift())
  if forward or backward then
    local target = page
    if forward and ctx:get_property('xh_pager_next') == '1' then target = page + 1 end
    if backward and page > 0 then target = page - 1 end
    if target ~= page then
      ctx:set_property('xh_pager_page', tostring(target))
      ctx:refresh_non_confirmed_composition()
    end
    return 1
  end
  -- The native selector uses the same 1..9,0 mapping. Consume out-of-range
  -- choices on the three-item first page and on a short final page.
  local choice
  if code >= 48 and code <= 57 then choice = (code - 49) % 10 end
  if code == 59 then choice = 1 end -- semicolon
  if code == 39 then choice = 2 end -- apostrophe
  if choice then
    local count = tonumber(ctx:get_property('xh_pager_count')) or 0
    if choice < count then ctx:select(choice) end
    return 1
  end
  return 2
end

function M.fini(env)
  if env.commit_connection then env.commit_connection:disconnect() end
  if env.update_connection then env.update_connection:disconnect() end
end

return M

-- SPDX-License-Identifier: GPL-3.0-or-later
-- The native menu remains one page; this filter supplies a logical 3/10 slice.
local M = {}
local function put(ctx, key, value)
  value = tostring(value)
  if ctx:get_property('xh_pager_' .. key) ~= value then
    ctx:set_property('xh_pager_' .. key, value)
  end
end

function M.func(input, env)
  local ctx = env.engine.context
  local comp = ctx.composition
  local seg = not comp:empty() and comp:back() or nil
  local signature = ctx.input .. ':' .. tostring(ctx.caret_pos) .. ':'
      .. tostring(seg and seg.start or 0) .. ':' .. tostring(seg and seg._end or 0)
  if ctx:get_property('xh_pager_signature') ~= signature then
    put(ctx, 'page', 0)
    put(ctx, 'signature', signature)
  end
  local page = tonumber(ctx:get_property('xh_pager_page')) or 0
  local offset = page == 0 and 0 or 3 + (page - 1) * 10
  local limit = page == 0 and 3 or 10
  local window, next_page = {}, false
  local index = 0
  -- Buffer a full logical page and one lookahead BEFORE yielding, so metadata
  -- is available even when the native menu stops requesting at ten candidates.
  for candidate in input:iter() do
    if index >= offset then
      if #window == limit then
        next_page = true
        break
      end
      window[#window + 1] = candidate
    end
    index = index + 1
  end
  -- select_keys belongs to this Schema instance, unlike shared ConfigData.
  -- All three native frontends use these characters as labels when no explicit
  -- alternative_select_labels exist. Spaces hide first-page digits; Lua handles
  -- the actual numeric selection independently. Never mutate shared label lists.
  local native_labels = env.engine.schema.config:get_bool('xiaohe_pager/native_labels')
  if native_labels then
    env.engine.schema.select_keys = page == 0 and string.rep(' ', 10) or '1234567890'
  end
  put(ctx, 'count', #window)
  put(ctx, 'next', next_page and 1 or 0)
  put(ctx, 'offset', offset)
  put(ctx, 'raw', ctx.input)
  for i, candidate in ipairs(window) do
    -- A nonempty zero-width comment also suppresses inherited completion hints
    -- on bundled Lua versions that retain comments for an empty shadow value.
    local comment = (native_labels or page == 0) and utf8.char(0x200B) or tostring(i % 10) .. ' '
    -- Keep the genuine candidate and committed text; digits are display-only.
    yield(ShadowCandidate(candidate, candidate.type, candidate.text, comment, false))
  end
end

return M

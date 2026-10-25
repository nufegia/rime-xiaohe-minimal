-- SPDX-License-Identifier: GPL-3.0-or-later
-- Fixed code-table entries stay in source order and never learn.
-- Smart candidates retain their Rime Phrase for sentence composition.
-- Automatic learning and user-frequency ranking are disabled in the schema.
local M = {}

function M.init(env)
  env.fixed = Component.Translator(env.engine, '', 'table_translator@fixed')
  env.custom = Component.Translator(env.engine, '', 'table_translator@custom')
  env.smart = Component.Translator(env.engine, '', 'script_translator@translator')
  env.simplify = Opencc('t2s.json')
end

function M.func(input, seg, env)
  local seen = {}
  local function emit(cand, smart)
    local text = smart and env.simplify:convert(cand.text) or cand.text
    if seen[text] then return end
    seen[text] = true
    if smart then
      yield(ShadowCandidate(cand, cand.type, text, '', true))
    else
      yield(cand)
    end
  end
  -- Once part of the composition is confirmed, only the remaining phonetic
  -- segment is translated. Do not inject whole-code fixed phrases into it.
  local whole = seg.start == 0 and input == env.engine.context.input
  local completions = {}
  local exact = false
  if whole then
    local custom = env.custom:query(input, seg)
    if custom then
      -- Expand the original LogInput templates at query time. All candidates
      -- in this query share one clock snapshot, including at midnight.
      local now
      local tokens = {
        {'#yyyy', '%Y'}, {'#MM', '%m'}, {'#dd', '%d'},
        {'#HH', '%H'}, {'#mm', '%M'},
      }
      for cand in custom:iter() do
        local template = cand.text:match('^@date:(.*)$')
        local text = template or cand.text
        if template then
          for _,token in ipairs(tokens) do
            if text:find(token[1], 1, true) then
              now = now or os.time()
              text = text:gsub(token[1], os.date(token[2], now))
            end
          end
        end
        if text ~= cand.text then
          -- Date candidates do not enter the phonetic learning dictionary.
          emit(Candidate('loginput_date', seg.start, seg._end, text, ''), false)
        else
          emit(cand, false)
        end
      end
    end
    if #input <= 4 and input:match('^[a-z]+$') then
      local fixed = env.fixed:query(input, seg)
      if fixed then
        for cand in fixed:iter() do
          if cand.type == 'completion' then
            completions[#completions + 1] = cand
          else
            exact = true
            emit(cand, false)
          end
        end
      end
    end
  end
  -- An empty three-key code slides down to its longer fixed codes.
  local slide_first = whole and #input == 3 and not exact
  if slide_first then
    for _,cand in ipairs(completions) do emit(cand, false) end
  end
  local smart = env.smart:query(input, seg)
  if smart then
    for cand in smart:iter() do emit(cand, true) end
  end
  if not slide_first then
    for _,cand in ipairs(completions) do emit(cand, false) end
  end
end

function M.fini(env)
  env.fixed, env.custom, env.smart, env.simplify = nil, nil, nil, nil
end

return M

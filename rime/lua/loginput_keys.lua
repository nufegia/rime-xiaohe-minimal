-- SPDX-License-Identifier: GPL-3.0-or-later
-- Match LogInput's "English punctuation after numbers" setting.
local M = {}
function M.init(env) env.after_number = false end
function M.func(key, env)
  if key:release() then return 2 end
  local ctx = env.engine.context
  if ctx:get_option('ascii_mode') or key:ctrl() or key:alt() or key:super() then
    env.after_number = false
    return 2
  end
  local code = key.keycode
  local idle = not ctx:is_composing()
  if idle and code >= 48 and code <= 57 then
    env.after_number = true
    return 2
  end
  if idle and env.after_number and (code == 44 or code == 46 or code == 33
      or code == 63 or code == 58 or code == 59) then
    env.engine:commit_text(string.char(code))
    env.after_number = false
    return 1
  end
  -- Modifier presses do not break the digit -> punctuation sequence.
  if code < 0xff00 then env.after_number = false end
  return 2
end
return M

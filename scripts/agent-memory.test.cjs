'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const test = require('node:test');

const SCRIPT = path.join(__dirname, 'agent-memory.cjs');

function createHarness() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'lockley-agent-memory-'));
  const memoryRoot = path.join(root, '.agent-memory');
  const env = {
    ...process.env,
    LOCKLEY_AGENT_MEMORY_REPO_ROOT: root,
    LOCKLEY_AGENT_MEMORY_ROOT: memoryRoot
  };

  function run(args, input = '') {
    const result = spawnSync(process.execPath, [SCRIPT, ...args], {
      env,
      input,
      encoding: 'utf8'
    });
    assert.equal(result.status, 0, result.stderr);
    return result.stdout;
  }

  function hook(agent, payload) {
    return run(['hook', agent], JSON.stringify(payload));
  }

  run(['init']);
  return { root, memoryRoot, run, hook };
}

test('captures Codex turns and returns startup context', t => {
  const harness = createHarness();
  t.after(() => fs.rmSync(harness.root, { recursive: true, force: true }));

  const startupOutput = harness.hook('codex', {
    session_id: 'session-one',
    cwd: harness.root,
    hook_event_name: 'SessionStart',
    source: 'startup',
    model: 'test-model'
  });
  const startup = JSON.parse(startupOutput);
  assert.match(startup.hookSpecificOutput.additionalContext, /Lockley local memory/);

  harness.hook('codex', {
    session_id: 'session-one',
    turn_id: 'turn-one',
    cwd: harness.root,
    hook_event_name: 'UserPromptSubmit',
    prompt: 'Investigate badge architecture.'
  });
  harness.hook('codex', {
    session_id: 'session-one',
    turn_id: 'turn-one',
    cwd: harness.root,
    hook_event_name: 'Stop',
    last_assistant_message: 'Badge awards come from event bosses.'
  });

  const sessionDirectory = path.join(harness.memoryRoot, 'session-logs', 'codex');
  const sessionFile = fs.readdirSync(sessionDirectory)
    .find(fileName => fileName.endsWith('_session-one.md'));
  assert.ok(sessionFile);
  const sessionLog = fs.readFileSync(path.join(sessionDirectory, sessionFile), 'utf8');
  assert.match(sessionLog, /Investigate badge architecture/);
  assert.match(sessionLog, /Badge awards come from event bosses/);
});

test('retrieves relevant history from another session', t => {
  const harness = createHarness();
  t.after(() => fs.rmSync(harness.root, { recursive: true, force: true }));

  harness.hook('codex', {
    session_id: 'old-session',
    turn_id: 'old-turn',
    cwd: harness.root,
    hook_event_name: 'UserPromptSubmit',
    prompt: 'How should normalized badge awards work?'
  });
  harness.hook('codex', {
    session_id: 'old-session',
    turn_id: 'old-turn',
    cwd: harness.root,
    hook_event_name: 'Stop',
    last_assistant_message: 'Use event_bosses badge_id and normalized pokemon_badges rows.'
  });

  const output = harness.hook('codex', {
    session_id: 'new-session',
    turn_id: 'new-turn',
    cwd: harness.root,
    hook_event_name: 'UserPromptSubmit',
    prompt: 'Review the badge awards architecture.'
  });
  const parsed = JSON.parse(output);
  assert.match(parsed.hookSpecificOutput.additionalContext, /event_bosses badge_id/);
});

test('redacts likely secrets and honors no-memory for the full turn', t => {
  const harness = createHarness();
  t.after(() => fs.rmSync(harness.root, { recursive: true, force: true }));

  harness.hook('claude', {
    session_id: 'privacy-session',
    cwd: harness.root,
    hook_event_name: 'UserPromptSubmit',
    prompt: 'api_key=sk-proj-abcdefghijklmnopqrstuvwxyz'
  });
  harness.hook('claude', {
    session_id: 'privacy-session',
    cwd: harness.root,
    hook_event_name: 'Stop',
    last_assistant_message: 'The key was received.'
  });
  harness.hook('claude', {
    session_id: 'privacy-session',
    cwd: harness.root,
    hook_event_name: 'UserPromptSubmit',
    prompt: '[no-memory] private design idea'
  });
  harness.hook('claude', {
    session_id: 'privacy-session',
    cwd: harness.root,
    hook_event_name: 'Stop',
    last_assistant_message: 'private design response'
  });

  const events = fs.readFileSync(
    path.join(harness.memoryRoot, 'state', 'events.jsonl'),
    'utf8'
  );
  assert.doesNotMatch(events, /sk-proj-/);
  assert.match(events, /REDACTED/);
  assert.doesNotMatch(events, /private design idea/);
  assert.doesNotMatch(events, /private design response/);
});

#!/usr/bin/env node
'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const DEFAULT_CONFIG = {
  version: 1,
  capture: {
    codex: true,
    claude: true,
    userPrompts: true,
    assistantResponses: true
  },
  retrieval: {
    enabled: true,
    startupMaxCharacters: 12000,
    relevantMaxCharacters: 6000,
    maxRelevantMatches: 5,
    recentConversationEntries: 8,
    maxIndexedEvents: 20000
  },
  privacy: {
    redactLikelySecrets: true,
    optOutMarkers: ['[no-memory]']
  }
};

const CURATED_TOP_LEVEL_FILES = [
  'CONTEXT.md',
  'project-principles.md',
  'known-issues.md',
  'glossary.md'
];

const STOP_WORDS = new Set([
  'about', 'after', 'again', 'also', 'another', 'because', 'before', 'being',
  'build', 'change', 'changes', 'code', 'could', 'does', 'from', 'great',
  'have', 'help', 'here', 'into', 'just', 'like', 'make', 'more', 'only',
  'other', 'please', 'should', 'some', 'system', 'than', 'that', 'their',
  'there', 'these', 'they', 'this', 'through', 'under', 'want', 'what',
  'when', 'where', 'which', 'will', 'with', 'would', 'your'
]);

function nowIso() {
  return new Date().toISOString();
}

function resolvePaths() {
  const repoRoot = path.resolve(
    process.env.LOCKLEY_AGENT_MEMORY_REPO_ROOT || path.join(__dirname, '..')
  );
  const memoryRoot = path.resolve(
    process.env.LOCKLEY_AGENT_MEMORY_ROOT || path.join(repoRoot, '.agent-memory')
  );

  return {
    repoRoot,
    memoryRoot,
    config: path.join(memoryRoot, 'config.json'),
    events: path.join(memoryRoot, 'state', 'events.jsonl'),
    sessions: path.join(memoryRoot, 'state', 'sessions.json'),
    errors: path.join(memoryRoot, 'state', 'hook-errors.log')
  };
}

function ensureDirectory(directory) {
  fs.mkdirSync(directory, { recursive: true });
}

function writeIfMissing(filePath, content) {
  if (fs.existsSync(filePath)) return;
  ensureDirectory(path.dirname(filePath));
  fs.writeFileSync(filePath, content, 'utf8');
}

function mergeObjects(base, override) {
  if (!override || typeof override !== 'object' || Array.isArray(override)) {
    return base;
  }

  const merged = { ...base };
  for (const [key, value] of Object.entries(override)) {
    if (
      value && typeof value === 'object' && !Array.isArray(value) &&
      base[key] && typeof base[key] === 'object' && !Array.isArray(base[key])
    ) {
      merged[key] = mergeObjects(base[key], value);
    } else {
      merged[key] = value;
    }
  }
  return merged;
}

function readJson(filePath, fallback) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch {
    return fallback;
  }
}

function writeJsonAtomic(filePath, value) {
  ensureDirectory(path.dirname(filePath));
  const temporaryPath = `${filePath}.${process.pid}.${Date.now()}.tmp`;
  fs.writeFileSync(temporaryPath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
  fs.renameSync(temporaryPath, filePath);
}

function initialize() {
  const paths = resolvePaths();
  const directories = [
    paths.memoryRoot,
    path.join(paths.memoryRoot, 'architecture-decisions'),
    path.join(paths.memoryRoot, 'features'),
    path.join(paths.memoryRoot, 'session-logs', 'codex'),
    path.join(paths.memoryRoot, 'session-logs', 'claude'),
    path.join(paths.memoryRoot, 'state')
  ];
  directories.forEach(ensureDirectory);

  writeIfMissing(paths.config, `${JSON.stringify(DEFAULT_CONFIG, null, 2)}\n`);
  writeIfMissing(paths.events, '');
  writeIfMissing(paths.sessions, '{\n  "version": 1,\n  "sessions": {}\n}\n');
  writeIfMissing(
    path.join(paths.memoryRoot, 'README.md'),
    '# Lockley Local Agent Memory\n\n' +
      'This directory is intentionally ignored by Git. Codex and Claude Code ' +
      'share it through project hooks. See `docs/agent-memory.md` for usage.\n'
  );
  writeIfMissing(
    path.join(paths.memoryRoot, 'CONTEXT.md'),
    '# Current Context\n\nAdd a concise description of the current system here.\n'
  );
  writeIfMissing(
    path.join(paths.memoryRoot, 'project-principles.md'),
    '# Project Principles\n\n- Verify memory against current code and data.\n'
  );
  writeIfMissing(
    path.join(paths.memoryRoot, 'known-issues.md'),
    '# Known Issues\n\nNo known issues have been recorded.\n'
  );
  writeIfMissing(
    path.join(paths.memoryRoot, 'glossary.md'),
    '# Glossary\n\nAdd Lockley-specific terms here.\n'
  );

  return paths;
}

function loadConfig(paths) {
  return mergeObjects(DEFAULT_CONFIG, readJson(paths.config, {}));
}

function redactSecrets(value) {
  let text = String(value || '');

  text = text.replace(
    /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/gi,
    '[REDACTED PRIVATE KEY]'
  );
  text = text.replace(/\bsk-[A-Za-z0-9_-]{12,}\b/g, '[REDACTED API KEY]');
  text = text.replace(/\bgh[pousr]_[A-Za-z0-9]{20,}\b/g, '[REDACTED GITHUB TOKEN]');
  text = text.replace(/\bxox[baprs]-[A-Za-z0-9-]{10,}\b/g, '[REDACTED SLACK TOKEN]');
  text = text.replace(
    /\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b/g,
    '[REDACTED JWT]'
  );
  text = text.replace(
    /(\bBearer\s+)[A-Za-z0-9._~+/=-]{10,}/gi,
    '$1[REDACTED]'
  );
  text = text.replace(
    /(\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?):\/\/[^:\s/@]+:)[^@\s]+@/gi,
    '$1[REDACTED]@'
  );
  text = text.replace(
    /(\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|secret|password|passwd)\b\s*[:=]\s*)(?:"[^"]*"|'[^']*'|[^\s,;]+)/gi,
    '$1[REDACTED]'
  );

  return text;
}

function prepareContent(value, config) {
  const content = String(value || '').trim();
  return config.privacy.redactLikelySecrets ? redactSecrets(content) : content;
}

function containsOptOut(prompt, config) {
  const normalized = String(prompt || '').toLowerCase();
  return config.privacy.optOutMarkers.some(marker =>
    normalized.includes(String(marker).toLowerCase())
  );
}

function safeSessionId(value) {
  const normalized = String(value || 'unknown-session')
    .replace(/[^A-Za-z0-9._-]/g, '_')
    .slice(0, 100);
  return normalized || 'unknown-session';
}

function loadSessionState(paths) {
  const state = readJson(paths.sessions, { version: 1, sessions: {} });
  if (!state.sessions || typeof state.sessions !== 'object') state.sessions = {};
  return state;
}

function sessionKey(agent, payload) {
  return `${agent}:${payload.session_id || 'unknown-session'}`;
}

function getOrCreateSession(paths, agent, payload) {
  const state = loadSessionState(paths);
  const key = sessionKey(agent, payload);
  const timestamp = nowIso();

  if (!state.sessions[key]) {
    const date = timestamp.slice(0, 10);
    const id = safeSessionId(payload.session_id);
    const relativePath = path.join('session-logs', agent, `${date}_${id}.md`);
    state.sessions[key] = {
      agent,
      sessionId: String(payload.session_id || 'unknown-session'),
      path: relativePath.replace(/\\/g, '/'),
      startedAt: timestamp,
      lastUpdatedAt: timestamp,
      model: payload.model || null,
      cwd: payload.cwd || null,
      privateTurnIds: [],
      suppressNextAssistant: false
    };

    const logPath = path.join(paths.memoryRoot, relativePath);
    writeIfMissing(
      logPath,
      `# ${agent === 'codex' ? 'Codex' : 'Claude Code'} session ${payload.session_id || 'unknown'}\n\n` +
        `- Started: ${timestamp}\n` +
        `- Model: ${payload.model || 'unknown'}\n` +
        `- Working directory: ${payload.cwd || 'unknown'}\n\n`
    );
  } else {
    state.sessions[key].lastUpdatedAt = timestamp;
    if (payload.model) state.sessions[key].model = payload.model;
    if (payload.cwd) state.sessions[key].cwd = payload.cwd;
  }

  writeJsonAtomic(paths.sessions, state);
  return { key, record: state.sessions[key], state };
}

function saveSessionState(paths, sessionData) {
  sessionData.record.lastUpdatedAt = nowIso();
  sessionData.state.sessions[sessionData.key] = sessionData.record;
  writeJsonAtomic(paths.sessions, sessionData.state);
}

function appendSessionText(paths, sessionData, text) {
  const logPath = path.join(paths.memoryRoot, sessionData.record.path);
  ensureDirectory(path.dirname(logPath));
  fs.appendFileSync(logPath, text, 'utf8');
}

function appendIndexedEvent(paths, event) {
  fs.appendFileSync(paths.events, `${JSON.stringify(event)}\n`, 'utf8');
}

function recordLifecycle(paths, agent, payload, label) {
  const sessionData = getOrCreateSession(paths, agent, payload);
  const timestamp = nowIso();
  appendSessionText(paths, sessionData, `## ${timestamp} ${label}\n\n`);

  if (label === 'Session ended') {
    sessionData.record.endedAt = timestamp;
    sessionData.record.endReason = payload.reason || 'other';
  }
  saveSessionState(paths, sessionData);
}

function markPrivateTurn(paths, agent, payload) {
  const sessionData = getOrCreateSession(paths, agent, payload);
  const turnId = payload.turn_id ? String(payload.turn_id) : null;
  if (turnId && !sessionData.record.privateTurnIds.includes(turnId)) {
    sessionData.record.privateTurnIds.push(turnId);
  }
  sessionData.record.suppressNextAssistant = true;
  appendSessionText(
    paths,
    sessionData,
    `## ${nowIso()} Capture skipped by [no-memory]\n\n`
  );
  saveSessionState(paths, sessionData);
}

function consumePrivateTurn(paths, agent, payload) {
  const sessionData = getOrCreateSession(paths, agent, payload);
  const turnId = payload.turn_id ? String(payload.turn_id) : null;
  const turnIndex = turnId ? sessionData.record.privateTurnIds.indexOf(turnId) : -1;
  const isPrivate = turnIndex >= 0 || sessionData.record.suppressNextAssistant;

  if (turnIndex >= 0) sessionData.record.privateTurnIds.splice(turnIndex, 1);
  if (isPrivate) sessionData.record.suppressNextAssistant = false;
  saveSessionState(paths, sessionData);
  return isPrivate;
}

function recordConversationEntry(paths, config, agent, payload, role, value) {
  const content = prepareContent(value, config);
  if (!content) return;

  const sessionData = getOrCreateSession(paths, agent, payload);
  const timestamp = nowIso();
  const heading = role === 'user' ? 'User' : 'Assistant';
  appendSessionText(
    paths,
    sessionData,
    `## ${timestamp} ${heading}\n\n${content}\n\n`
  );
  appendIndexedEvent(paths, {
    version: 1,
    timestamp,
    agent,
    sessionId: String(payload.session_id || 'unknown-session'),
    turnId: payload.turn_id ? String(payload.turn_id) : null,
    role,
    content,
    sessionPath: sessionData.record.path
  });
  saveSessionState(paths, sessionData);
}

function listMarkdownFiles(directory) {
  if (!fs.existsSync(directory)) return [];
  const files = [];
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...listMarkdownFiles(fullPath));
    if (entry.isFile() && entry.name.toLowerCase().endsWith('.md')) files.push(fullPath);
  }
  return files;
}

function readText(filePath) {
  try {
    return fs.readFileSync(filePath, 'utf8').trim();
  } catch {
    return '';
  }
}

function relativeMemoryPath(paths, filePath) {
  return path.relative(paths.memoryRoot, filePath).replace(/\\/g, '/');
}

function fitSections(header, sections, maxCharacters) {
  let output = header.trim();
  for (const section of sections) {
    const separator = '\n\n';
    const available = maxCharacters - output.length - separator.length;
    if (available <= 120) break;
    if (section.length <= available) {
      output += `${separator}${section}`;
      continue;
    }
    output += `${separator}${section.slice(0, available - 20).trimEnd()}\n[truncated]`;
    break;
  }
  return output.slice(0, maxCharacters);
}

function loadEvents(paths, maxEvents) {
  const text = readText(paths.events);
  if (!text) return [];
  return text
    .split(/\r?\n/)
    .filter(Boolean)
    .slice(-maxEvents)
    .map(line => {
      try {
        return JSON.parse(line);
      } catch {
        return null;
      }
    })
    .filter(Boolean);
}

function buildStartupContext(paths, config, currentSessionId) {
  const maxCharacters = Number(config.retrieval.startupMaxCharacters) || 12000;
  const sections = [];

  for (const fileName of CURATED_TOP_LEVEL_FILES) {
    const filePath = path.join(paths.memoryRoot, fileName);
    const content = prepareContent(readText(filePath), config);
    if (content) sections.push(`## ${fileName}\n${content}`);
  }

  const durableFiles = [
    ...listMarkdownFiles(path.join(paths.memoryRoot, 'architecture-decisions')),
    ...listMarkdownFiles(path.join(paths.memoryRoot, 'features'))
  ].sort((left, right) => {
    const leftTime = fs.statSync(left).mtimeMs;
    const rightTime = fs.statSync(right).mtimeMs;
    return rightTime - leftTime;
  });

  for (const filePath of durableFiles.slice(0, 20)) {
    const content = prepareContent(readText(filePath), config);
    if (content) sections.push(`## ${relativeMemoryPath(paths, filePath)}\n${content}`);
  }

  const recentCount = Number(config.retrieval.recentConversationEntries) || 8;
  const recentEvents = loadEvents(paths, config.retrieval.maxIndexedEvents)
    .filter(event => event.sessionId !== currentSessionId)
    .slice(-recentCount);
  if (recentEvents.length) {
    const excerpts = recentEvents.map(event => {
      const role = event.role === 'user' ? 'User' : 'Assistant';
      const content = prepareContent(event.content, config).slice(0, 1000);
      return `- ${event.timestamp} ${event.agent}/${role}: ${content}`;
    });
    sections.push(`## Recent conversation excerpts\n${excerpts.join('\n')}`);
  }

  return fitSections(
    'Lockley local memory is available below. Use it as fallible project recall, ' +
      'verify it against current code and data, and follow current user instructions first.',
    sections,
    maxCharacters
  );
}

function normalizeSearchText(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9_/-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function extractTerms(prompt) {
  const counts = new Map();
  for (const token of normalizeSearchText(prompt).split(' ')) {
    if (token.length < 4 || STOP_WORDS.has(token) || /^\d+$/.test(token)) continue;
    counts.set(token, (counts.get(token) || 0) + 1);
  }
  return [...counts.entries()]
    .sort((left, right) => right[1] - left[1] || right[0].length - left[0].length)
    .slice(0, 16)
    .map(([token]) => token);
}

function splitMarkdownIntoCandidates(paths, filePath, config) {
  const content = prepareContent(readText(filePath), config);
  if (!content) return [];
  const chunks = content.split(/(?=^#{1,3}\s+)/m).filter(Boolean);
  return chunks.map((chunk, index) => ({
    source: relativeMemoryPath(paths, filePath),
    content: chunk.trim(),
    timestamp: fs.statSync(filePath).mtime.toISOString(),
    weight: 1.5,
    id: `${filePath}:${index}`
  }));
}

function scoreCandidate(candidate, terms) {
  const normalized = normalizeSearchText(candidate.content);
  const normalizedSource = normalizeSearchText(candidate.source);
  let matchedTerms = 0;
  let score = 0;
  for (const term of terms) {
    const contentMatches = normalized.includes(term);
    const sourceMatches = normalizedSource.includes(term);
    if (!contentMatches && !sourceMatches) continue;
    matchedTerms += 1;
    if (contentMatches) score += term.length >= 8 ? 2 : 1;
    if (sourceMatches) score += 1;
  }
  if (matchedTerms >= 2) score += matchedTerms;
  return score * candidate.weight;
}

function buildRelevantContext(paths, config, prompt, currentSessionId) {
  if (!config.retrieval.enabled) return '';
  const terms = extractTerms(prompt);
  if (!terms.length) return '';

  const curatedFiles = [
    ...CURATED_TOP_LEVEL_FILES.map(fileName => path.join(paths.memoryRoot, fileName)),
    ...listMarkdownFiles(path.join(paths.memoryRoot, 'architecture-decisions')),
    ...listMarkdownFiles(path.join(paths.memoryRoot, 'features'))
  ].filter(filePath => fs.existsSync(filePath));

  const candidates = curatedFiles.flatMap(filePath =>
    splitMarkdownIntoCandidates(paths, filePath, config)
  );

  const events = loadEvents(paths, config.retrieval.maxIndexedEvents);
  const turnGroups = new Map();
  const openTurns = new Map();
  events.forEach((event, index) => {
    if (!event.content || event.sessionId === currentSessionId) return;

    const session = `${event.agent}:${event.sessionId}`;
    let turnKey;
    if (event.turnId) {
      turnKey = `${session}:${event.turnId}`;
    } else if (event.role === 'user' || !openTurns.has(session)) {
      turnKey = `${session}:sequence-${index}`;
      openTurns.set(session, turnKey);
    } else {
      turnKey = openTurns.get(session);
    }

    if (!turnGroups.has(turnKey)) {
      turnGroups.set(turnKey, {
        source: `${event.agent} session ${event.sessionId}`,
        timestamp: event.timestamp,
        entries: []
      });
    }
    const group = turnGroups.get(turnKey);
    group.timestamp = event.timestamp || group.timestamp;
    group.entries.push(event);
  });

  for (const [turnKey, group] of turnGroups) {
    const content = group.entries.map(event => {
      const role = event.role === 'user' ? 'User' : 'Assistant';
      return `${role}: ${prepareContent(event.content, config)}`;
    }).join('\n\n');
    candidates.push({
      source: group.source,
      content,
      timestamp: group.timestamp,
      weight: 1.1,
      id: `turn:${turnKey}`
    });
  }

  const seen = new Set();
  const ranked = candidates
    .map(candidate => ({ ...candidate, score: scoreCandidate(candidate, terms) }))
    .filter(candidate => candidate.score >= 2)
    .sort((left, right) =>
      right.score - left.score || String(right.timestamp).localeCompare(String(left.timestamp))
    )
    .filter(candidate => {
      const fingerprint = crypto.createHash('sha1').update(candidate.content).digest('hex');
      if (seen.has(fingerprint)) return false;
      seen.add(fingerprint);
      return true;
    })
    .slice(0, Number(config.retrieval.maxRelevantMatches) || 5);

  if (!ranked.length) return '';
  const sections = ranked.map(candidate =>
    `### ${candidate.source}\n${candidate.content.slice(0, 1400)}`
  );
  return fitSections(
    'Relevant prior Lockley memory follows. It may be stale; verify before relying on it.',
    sections,
    Number(config.retrieval.relevantMaxCharacters) || 6000
  );
}

function contextOutput(eventName, context) {
  if (!context) return '';
  return JSON.stringify({
    hookSpecificOutput: {
      hookEventName: eventName,
      additionalContext: context
    }
  });
}

function hooksCaptureAgent(config, agent) {
  return config.capture[agent] !== false;
}

function handleHook(agent, payload) {
  const paths = initialize();
  const config = loadConfig(paths);
  const eventName = payload.hook_event_name || payload.hookEventName;
  const currentSessionId = String(payload.session_id || 'unknown-session');
  const capturesAgent = hooksCaptureAgent(config, agent);

  if (eventName === 'SessionStart') {
    if (capturesAgent) recordLifecycle(paths, agent, payload, `Session started (${payload.source || 'startup'})`);
    const context = buildStartupContext(paths, config, currentSessionId);
    return contextOutput('SessionStart', context);
  }

  if (eventName === 'UserPromptSubmit') {
    if (containsOptOut(payload.prompt, config)) {
      if (capturesAgent) markPrivateTurn(paths, agent, payload);
      return '';
    }

    const relevantContext = buildRelevantContext(
      paths,
      config,
      payload.prompt,
      currentSessionId
    );
    if (capturesAgent && config.capture.userPrompts !== false) {
      recordConversationEntry(paths, config, agent, payload, 'user', payload.prompt);
    }
    return contextOutput('UserPromptSubmit', relevantContext);
  }

  if (eventName === 'Stop') {
    const privateTurn = capturesAgent ? consumePrivateTurn(paths, agent, payload) : false;
    if (
      capturesAgent && !privateTurn && config.capture.assistantResponses !== false
    ) {
      recordConversationEntry(
        paths,
        config,
        agent,
        payload,
        'assistant',
        payload.last_assistant_message
      );
    }
    return JSON.stringify({ continue: true });
  }

  if (eventName === 'SessionEnd') {
    if (capturesAgent) recordLifecycle(paths, agent, payload, 'Session ended');
    return '';
  }

  return '';
}

function appendHookError(error) {
  try {
    const paths = initialize();
    fs.appendFileSync(
      paths.errors,
      `${nowIso()} ${error && error.stack ? error.stack : String(error)}\n`,
      'utf8'
    );
  } catch {
    // Memory logging must never block the agent session.
  }
}

function printStatus(paths) {
  const config = loadConfig(paths);
  const state = loadSessionState(paths);
  const sessionValues = Object.values(state.sessions);
  const events = loadEvents(paths, Number.MAX_SAFE_INTEGER);
  const decisions = listMarkdownFiles(path.join(paths.memoryRoot, 'architecture-decisions'));
  const features = listMarkdownFiles(path.join(paths.memoryRoot, 'features'));
  const codexSessions = sessionValues.filter(session => session.agent === 'codex').length;
  const claudeSessions = sessionValues.filter(session => session.agent === 'claude').length;

  process.stdout.write(
    `Lockley agent memory\n` +
      `  Store: ${paths.memoryRoot}\n` +
      `  Capture: Codex ${config.capture.codex ? 'on' : 'off'}, Claude ${config.capture.claude ? 'on' : 'off'}\n` +
      `  Sessions: ${codexSessions} Codex, ${claudeSessions} Claude\n` +
      `  Conversation entries: ${events.length}\n` +
      `  Curated: ${decisions.length} decisions, ${features.length} feature notes\n`
  );
}

function readStdin() {
  return fs.readFileSync(0, 'utf8');
}

function usage() {
  process.stdout.write(
    'Usage:\n' +
      '  node scripts/agent-memory.cjs init\n' +
      '  node scripts/agent-memory.cjs status\n' +
      '  node scripts/agent-memory.cjs context\n' +
      '  node scripts/agent-memory.cjs search "topic"\n' +
      '  node scripts/agent-memory.cjs hook codex|claude\n'
  );
}

function main() {
  const [command = 'status', ...args] = process.argv.slice(2);

  if (command === 'hook') {
    const agent = args[0] === 'claude' ? 'claude' : 'codex';
    let payload = {};
    try {
      payload = JSON.parse(readStdin() || '{}');
      const output = handleHook(agent, payload);
      if (output) process.stdout.write(output);
    } catch (error) {
      appendHookError(error);
      if ((payload.hook_event_name || payload.hookEventName) === 'Stop') {
        process.stdout.write(JSON.stringify({ continue: true }));
      }
    }
    return;
  }

  const paths = initialize();
  const config = loadConfig(paths);

  if (command === 'init') {
    process.stdout.write(`Initialized ${paths.memoryRoot}\n`);
    return;
  }
  if (command === 'status') {
    printStatus(paths);
    return;
  }
  if (command === 'context') {
    process.stdout.write(`${buildStartupContext(paths, config, null)}\n`);
    return;
  }
  if (command === 'search') {
    const query = args.join(' ').trim();
    if (!query) throw new Error('Search requires a topic.');
    const result = buildRelevantContext(paths, config, query, null);
    process.stdout.write(`${result || 'No relevant memory found.'}\n`);
    return;
  }

  usage();
  process.exitCode = 1;
}

if (require.main === module) {
  try {
    main();
  } catch (error) {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  }
}

module.exports = {
  buildRelevantContext,
  buildStartupContext,
  containsOptOut,
  extractTerms,
  handleHook,
  initialize,
  redactSecrets,
  resolvePaths
};

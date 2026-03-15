#!/usr/bin/env node

/**
 * jerome7 — 7 minutes. Same session for everyone on earth. In your terminal.
 *
 * Usage:
 *   npx jerome7          → start today's session
 *   npx jerome7 --peek   → preview blocks without starting timer
 *   npx jerome7 --json   → output session as JSON for piping to other tools
 */

const https = require("https");
const readline = require("readline");

const API = "https://jerome7.com";
const ORANGE = "\x1b[38;2;232;93;4m";
const GREEN = "\x1b[38;2;63;185;80m";
const DIM = "\x1b[2m";
const BOLD = "\x1b[1m";
const WHITE = "\x1b[97m";
const RESET = "\x1b[0m";
const CLEAR_LINE = "\x1b[2K\r";

const PHASE_COLOR = {
  prime: "\x1b[38;2;88;166;255m",
  build: "\x1b[38;2;232;93;4m",
  move: "\x1b[38;2;63;185;80m",
  reset: "\x1b[38;2;210;168;255m",
};

function fetch(url) {
  return new Promise((resolve, reject) => {
    https.get(url, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => {
        try {
          resolve(JSON.parse(data));
        } catch {
          reject(new Error("Failed to parse response"));
        }
      });
    }).on("error", reject);
  });
}

function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

function printHeader() {
  console.log();
  console.log(`  ${ORANGE}${BOLD}JEROME7${RESET}`);
  console.log(`  ${DIM}7 minutes. same for everyone on earth.${RESET}`);
  console.log();
}

function printBlock(block, index, total) {
  const phase = block.phase || "build";
  const color = PHASE_COLOR[phase] || ORANGE;
  const num = `${index + 1}/${total}`;
  console.log();
  console.log(`  ${color}${BOLD}[${num}] ${block.name.toUpperCase()}${RESET}  ${DIM}${phase}${RESET}`);
  console.log(`  ${WHITE}${block.instruction}${RESET}`);
}

async function countdown(seconds) {
  const startTime = Date.now();
  const endTime = startTime + seconds * 1000;

  while (Date.now() < endTime) {
    const remaining = Math.ceil((endTime - Date.now()) / 1000);
    const elapsed = seconds - remaining;
    const barWidth = 30;
    const filled = Math.round((elapsed / seconds) * barWidth);
    const bar = "█".repeat(filled) + "░".repeat(barWidth - filled);

    process.stdout.write(
      `${CLEAR_LINE}  ${ORANGE}${bar}${RESET} ${WHITE}${formatTime(remaining)}${RESET}`
    );

    await sleep(100);
  }

  process.stdout.write(`${CLEAR_LINE}  ${GREEN}${"█".repeat(30)}${RESET} ${GREEN}✓ done${RESET}\n`);
}

async function runSession(session) {
  const blocks = session.blocks || [];
  const title = session.session_title || "the seven 7";

  console.log(`  ${ORANGE}${BOLD}${title.toUpperCase()}${RESET}`);
  console.log(`  ${DIM}${blocks.length} blocks · ${blocks.length * 60}s · starting now${RESET}`);

  for (let i = 0; i < blocks.length; i++) {
    const block = blocks[i];
    printBlock(block, i, blocks.length);
    await countdown(block.duration_seconds || 60);
  }

  console.log();
  console.log(`  ${GREEN}${BOLD}✓ SESSION COMPLETE${RESET}`);
  const closing = session.closing || "You showed up. That's the win.";
  console.log(`  ${DIM}${closing}${RESET}`);
  console.log();
  console.log(`  ${DIM}jerome7.com/timer · free forever · open source${RESET}`);
  console.log();
}

function peekSession(session) {
  const blocks = session.blocks || [];
  const title = session.session_title || "the seven 7";

  console.log(`  ${ORANGE}${BOLD}${title.toUpperCase()}${RESET}`);
  console.log();

  for (let i = 0; i < blocks.length; i++) {
    const block = blocks[i];
    const phase = block.phase || "build";
    const color = PHASE_COLOR[phase] || ORANGE;
    console.log(
      `  ${color}${(i + 1).toString().padStart(2)}.${RESET} ${WHITE}${block.name.padEnd(18)}${RESET}${DIM}${block.instruction}${RESET}`
    );
  }

  console.log();
  console.log(`  ${DIM}Run ${ORANGE}npx jerome7${RESET}${DIM} to start the timer${RESET}`);
  console.log();
}

function outputJson(session) {
  console.log(JSON.stringify(session, null, 2));
}

async function main() {
  const args = process.argv.slice(2);
  const peek = args.includes("--peek") || args.includes("-p");
  const json = args.includes("--json") || args.includes("-j");

  // For JSON output, skip the header and fetch directly
  if (json) {
    try {
      const session = await fetch(`${API}/daily`);
      outputJson(session);
    } catch (err) {
      console.error(JSON.stringify({ error: "Could not reach jerome7.com — check your connection." }));
      process.exit(1);
    }
    return;
  }

  printHeader();

  try {
    process.stdout.write(`  ${DIM}fetching today's session...${RESET}`);
    const session = await fetch(`${API}/daily`);
    process.stdout.write(`${CLEAR_LINE}`);

    if (peek) {
      peekSession(session);
    } else {
      // Wait for Enter to start
      console.log(`  ${DIM}Press ${WHITE}Enter${RESET}${DIM} to start · ${WHITE}Ctrl+C${RESET}${DIM} to quit${RESET}`);
      console.log();

      const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
      await new Promise((resolve) => {
        rl.question("", () => {
          rl.close();
          resolve();
        });
      });

      await runSession(session);
    }
  } catch (err) {
    process.stdout.write(`${CLEAR_LINE}`);
    console.log(`  ${DIM}Could not reach jerome7.com — check your connection.${RESET}`);
    console.log();
    process.exit(1);
  }
}

main();

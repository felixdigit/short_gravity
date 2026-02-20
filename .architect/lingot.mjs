import fs from 'fs';
import path from 'path';
import { spawnSync } from 'child_process';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const QUEUE_DIR = path.join(__dirname, 'queue');
const HISTORY_DIR = path.join(__dirname, 'history');
const ROOT_DIR = path.resolve(__dirname, '..');

// --- CONFIGURATION ---
const AI_CLI_CMD = 'claude'; 
// PATCH: Added YOLO mode flag to bypass interactive permission blocks
const AI_CLI_ARGS = ['--dangerously-skip-permissions', '-p'];

console.log("\n==================================================");
console.log("  NEXOD LINGOT ORCHESTRATOR (AUTONOMOUS v1.0.2)   ");
console.log("  Full Autonomy (YOLO Mode) Engaged.              ");
console.log("==================================================\n");

const mandates = fs.readdirSync(QUEUE_DIR).filter(f => f.endsWith('.md')).sort();

if (mandates.length === 0) {
    console.log("[!] Queue empty. The Cathedral rests at absolute zero.\n");
    process.exit(0);
}

for (const file of mandates) {
    const filePath = path.join(QUEUE_DIR, file);
    const content = fs.readFileSync(filePath, 'utf-8');
    
    const targetMatch = content.match(/TARGET:\s*(.+)/);
    if (!targetMatch) {
        console.error(`[X] Skipping ${file}: No 'TARGET: <path>' specified.`);
        continue;
    }
    
    const targetDir = targetMatch[1].trim();
    const absoluteTarget = path.resolve(ROOT_DIR, targetDir);

    console.log(`[+] ACQUIRED MANDATE: ${file}`);
    console.log(`[+] LOCKING TARGET ROOM: ${targetDir}`);

    const kernelPath = path.join(absoluteTarget, 'CLAUDE.md');
    let kernelContent = "No local CLAUDE.md found.";
    if (fs.existsSync(kernelPath)) {
        kernelContent = fs.readFileSync(kernelPath, 'utf-8');
        console.log(`[+] MICROKERNEL (CLAUDE.md) VERIFIED.`);
    }

    const payload = `STRICT DIRECTIVE FROM ORCHESTRATOR.
You are physically trapped in the directory: ${targetDir}.

LOCAL LAWS OF PHYSICS:
"""
${kernelContent}
"""

YOUR MANDATE:
"""
${content}
"""

CRITICAL EXECUTION RULES:
1. You are running in a HEADLESS, fully automated pipeline. There is NO human to reply to you.
2. DO NOT ask for permission. DO NOT explain what you are going to do. DO NOT converse.
3. IMMEDIATELY invoke your bash (pnpm) and file-writing tools to complete the mandate autonomously.`;

    console.log(`[+] WAKING AUTONOMOUS AGENT (${AI_CLI_CMD}) IN ${targetDir}...\n`);
    console.log(`------------------- AGENT STDOUT -------------------`);

    const worker = spawnSync(AI_CLI_CMD, [...AI_CLI_ARGS, payload], {
        cwd: absoluteTarget,
        stdio: 'inherit',
        shell: false 
    });

    console.log(`\n----------------------------------------------------`);

    if (worker.status !== 0) {
        console.log(`\n[X] AGENT FAILED OR WAS ABORTED (Exit Code: ${worker.status}). HALTING.`);
        process.exit(1);
    }

    console.log(`\n[+] AGENT FINISHED. ENGAGING CIRCUIT BREAKER (Type Check)...`);
    
    const tsc = spawnSync('npx', ['tsc', '--noEmit'], {
        cwd: absoluteTarget,
        stdio: 'inherit',
        shell: true
    });

    if (tsc.status === 0) {
        console.log(`\n[✓] CIRCUIT BREAKER PASSED. ZERO BLEED DETECTED.`);
        fs.renameSync(filePath, path.join(HISTORY_DIR, file));
        console.log(`[+] Mandate archived to history.\n`);
    } else {
        console.log(`\n[X] CIRCUIT BREAKER FAILED. STRUCTURAL COMPROMISE.`);
        console.log(`[!] Mandate left in queue. Assembly line halted.\n`);
        process.exit(1); 
    }
}

console.log("[+] QUEUE PROCESSED. RETURNING TO SLEEP.\n");

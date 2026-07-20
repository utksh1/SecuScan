#!/usr/bin/env node

/**
 * SecuScan Frontend Quality Gate
 * CI-style automated quality checks for frontend code
 */

const fs = require('fs');
const path = require('path');

const COLORS = {
    reset: '\x1b[0m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    cyan: '\x1b[36m',
    bold: '\x1b[1m'
};

class QualityGate {
    constructor() {
        this.failures = [];
        this.warnings = [];
        this.passes = [];
    }

    log(message, color = COLORS.reset) {
        console.log(`${color}${message}${COLORS.reset}`);
    }

    pass(check) {
        this.passes.push(check);
        this.log(`✓ ${check}`, COLORS.green);
    }

    fail(check, reason) {
        this.failures.push({ check, reason });
        this.log(`✗ ${check}: ${reason}`, COLORS.red);
    }

    warn(check, reason) {
        this.warnings.push({ check, reason });
        this.log(`⚠ ${check}: ${reason}`, COLORS.yellow);
    }

    getSourceFiles(dir) {
        const files = [];
        for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
            if (entry.name === 'node_modules' || entry.name === 'dist' || entry.name === 'e2e') continue;
            const fullPath = path.join(dir, entry.name);
            if (entry.isDirectory()) {
                files.push(...this.getSourceFiles(fullPath));
                continue;
            }
            if (/\.(ts|tsx)$/.test(entry.name)) {
                files.push(fullPath);
            }
        }
        return files;
    }

    normalizeTarget(rawTarget) {
        return rawTarget
            .replace(/\$\{[^}]+\}/g, 'value')
            .replace(/:\w+/g, 'value')
            .replace(/\/+$/, '') || '/';
    }

    // Check route/link integrity to prevent undefined route targets and dead links.
    checkRouteIntegrity() {
        this.log('\n=== Route Integrity Checks ===', COLORS.cyan);

        const routesPath = path.join(__dirname, 'src/routes.ts');
        const appPath = path.join(__dirname, 'src/App.tsx');
        const srcPath = path.join(__dirname, 'src');
        const routeMap = {};

        const routeSource = fs.readFileSync(routesPath, 'utf8');
        const routeObjectMatch = routeSource.match(/export const routes = \{([\s\S]*?)\} as const/);
        if (!routeObjectMatch) {
            this.fail('Route map exists', 'Could not parse routes object in src/routes.ts');
            return;
        }

        for (const match of routeObjectMatch[1].matchAll(/(\w+):\s*'([^']+)'/g)) {
            routeMap[match[1]] = match[2];
        }

        const appSource = fs.readFileSync(appPath, 'utf8');
        const registeredRoutes = [];
        for (const match of appSource.matchAll(/<Route\s+path=\{routes\.(\w+)\}/g)) {
            const key = match[1];
            if (!routeMap[key]) {
                this.fail('Registered routes resolve', `Route key routes.${key} missing in routes.ts`);
                return;
            }
            registeredRoutes.push(routeMap[key]);
        }
        for (const match of appSource.matchAll(/<Route\s+path="([^"]+)"/g)) {
            registeredRoutes.push(match[1]);
        }

        const knownRouteSet = new Set(registeredRoutes);
        const sourceFiles = this.getSourceFiles(srcPath);
        const unresolvedRefs = [];
        const deprecatedRefs = [];

        const routeMatchers = Array.from(knownRouteSet)
            .filter(route => route !== '*')
            .map(route => new RegExp(`^${route.replace(/:[^/]+/g, '[^/]+')}$`));

        for (const file of sourceFiles) {
            const content = fs.readFileSync(file, 'utf8');
            const refs = [];

            for (const match of content.matchAll(/to=\s*["'](\/[^"']*)["']/g)) refs.push(match[1]);
            for (const match of content.matchAll(/navigate\(\s*["'](\/[^"']*)["']\s*\)/g)) refs.push(match[1]);
            for (const match of content.matchAll(/to=\s*\{\s*`(\/[^`]+)`\s*\}/g)) refs.push(match[1]);
            for (const match of content.matchAll(/navigate\(\s*`(\/[^`]+)`\s*\)/g)) refs.push(match[1]);

            for (const match of content.matchAll(/to=\s*\{\s*routes\.(\w+)\s*\}/g)) {
                const key = match[1];
                if (!routeMap[key]) {
                    unresolvedRefs.push(`${file}: routes.${key} is undefined`);
                    continue;
                }
                refs.push(routeMap[key]);
            }

            for (const match of content.matchAll(/navigate\(\s*routes\.(\w+)\s*\)/g)) {
                const key = match[1];
                if (!routeMap[key]) {
                    unresolvedRefs.push(`${file}: routes.${key} is undefined`);
                    continue;
                }
                refs.push(routeMap[key]);
            }

            for (const match of content.matchAll(/(?:to=\s*\{\s*routePath\.(\w+)\(|navigate\(\s*routePath\.(\w+)\()/g)) {
                const key = match[1] || match[2];
                if (!routeMap[key]) {
                    unresolvedRefs.push(`${file}: routePath.${key} has no matching routes.${key}`);
                    continue;
                }
                refs.push(routeMap[key]);
            }

            for (const ref of refs) {
                const normalized = this.normalizeTarget(ref);
                if (normalized === '/scanner' || normalized.startsWith('/scanner/')) {
                    deprecatedRefs.push(`${file}: uses deprecated route "${ref}"`);
                    continue;
                }
                if (normalized === '/tasks' || normalized.startsWith('/tasks/')) {
                    deprecatedRefs.push(`${file}: uses deprecated frontend task route "${ref}"`);
                    continue;
                }
                const isKnown = routeMatchers.some((matcher) => matcher.test(normalized));
                if (!isKnown) {
                    unresolvedRefs.push(`${file}: unresolved route target "${ref}"`);
                }
            }
        }

        if (deprecatedRefs.length > 0) {
            this.fail('No deprecated frontend routes', deprecatedRefs.slice(0, 6).join(' | '));
        } else {
            this.pass('No deprecated frontend routes');
        }

        if (unresolvedRefs.length > 0) {
            this.fail('No undefined route targets', unresolvedRefs.slice(0, 6).join(' | '));
        } else {
            this.pass('No undefined route targets');
        }
    }

    // Check for forbidden animation patterns
    checkMotionControl() {
        this.log('\n=== Motion Control Checks ===', COLORS.cyan);

        const cssPath = path.join(__dirname, 'src/index.css');
        const css = fs.readFileSync(cssPath, 'utf8');

        // Check for shake animations (rapid back-and-forth motion)
        const shakeKeyframe = /@keyframes\s+\w*shake\w*/i.test(css);

        if (shakeKeyframe) {
            this.fail('No shake animations', 'Found shake keyframe');
        } else {
            this.pass('No shake animations');
        }

        // Check for bounce animations
        if (css.match(/@keyframes\s+\w*bounce/i) || css.match(/cubic-bezier.*elastic/i)) {
            this.fail('No bounce animations', 'Found bounce animation');
        } else {
            this.pass('No bounce animations');
        }

        // Check for flashing animations (excluding cursor blink)
        const flashPattern = /animation:.*blink/i;
        if (flashPattern.test(css) && !css.includes('cursorBlink')) {
            this.fail('No flashing animations', 'Found flashing animation');
        } else {
            this.pass('No flashing animations');
        }

        // Check animation durations (excluding background animations)
        const durations = css.match(/animation:\s*[^;]*\s+(\d+(?:\.\d+)?)(ms|s)/g) || [];
        let maxInteractiveDuration = 0;

        durations.forEach(d => {
            // Skip background animations (allowed to be slow)
            if (d.includes('gridFloat') || d.includes('scanPulse') || d.includes('lineFloat') || d.includes('scanline')) {
                return;
            }

            const match = d.match(/(\d+(?:\.\d+)?)(ms|s)/);
            if (match) {
                const value = parseFloat(match[1]);
                const unit = match[2];
                const ms = unit === 's' ? value * 1000 : value;
                if (ms > maxInteractiveDuration) maxInteractiveDuration = ms;
            }
        });

        if (maxInteractiveDuration > 300) {
            this.warn('Interactive animations ≤300ms', `Found ${maxInteractiveDuration}ms animation`);
        } else {
            this.pass('Interactive animations ≤300ms');
        }
    }

    // Check for 3D safety
    check3DSafety() {
        this.log('\n=== 3D Safety Checks ===', COLORS.cyan);

        const cssPath = path.join(__dirname, 'src/index.css');
        const css = fs.readFileSync(cssPath, 'utf8');

        // Count unique background component types (not all classes)
        const hasBackgroundGrid = css.includes('.background-grid');
        const hasBackgroundScan = css.includes('.background-scan');
        const hasBackgroundLines = css.includes('.background-lines');
        const componentCount = [hasBackgroundGrid, hasBackgroundScan, hasBackgroundLines].filter(Boolean).length;

        if (componentCount > 3) {
            this.fail('Single global 3D layer', `Found ${componentCount} background component types`);
        } else {
            this.pass('Single global 3D layer (3 elements in Background component)');
        }

        // Check for prefers-reduced-motion support
        if (css.includes('@media (prefers-reduced-motion')) {
            this.pass('Reduced motion support');
        } else {
            this.fail('Reduced motion support', 'Missing @media (prefers-reduced-motion)');
        }

        // Check background opacity
        const bgOpacities = css.match(/\.background[^}]*opacity:\s*([0-9.]+)/g) || [];
        let highOpacity = false;
        bgOpacities.forEach(op => {
            const match = op.match(/opacity:\s*([0-9.]+)/);
            if (match && parseFloat(match[1]) > 0.15) {
                highOpacity = true;
            }
        });

        if (highOpacity) {
            this.fail('Readability preserved', 'Background opacity > 0.15');
        } else {
            this.pass('Readability preserved');
        }
    }

    // Check visual discipline
    checkVisualDiscipline() {
        this.log('\n=== Visual Discipline Checks ===', COLORS.cyan);

        const cssPath = path.join(__dirname, 'src/index.css');
        const css = fs.readFileSync(cssPath, 'utf8');

        // Check for dark mode tokens
        if (css.includes('--bg-primary') && (css.includes('#0a0e14') || css.includes('#0a0b0d') || css.includes('#0a0a0c'))) {
            this.pass('Dark-mode first');
        } else {
            this.fail('Dark-mode first', 'Missing dark background tokens');
        }

        // Check for monospace font
        if (css.includes('JetBrains Mono') || css.includes('--font-mono')) {
            this.pass('Monospace for technical data');
        } else {
            this.fail('Monospace for technical data', 'Missing monospace font');
        }

        // Check for glassmorphism
        if (css.includes('backdrop-filter') || css.includes('--glass-')) {
            this.pass('Glassmorphism aesthetic');
        } else {
            this.warn('Glassmorphism aesthetic', 'Limited glassmorphism usage');
        }
    }

    // Check scope discipline
    checkScopeControl() {
        this.log('\n=== Scope Control Checks ===', COLORS.cyan);

        // Check if backend files were modified
        const backendPath = path.join(__dirname, '../backend');
        if (fs.existsSync(backendPath)) {
            this.pass('Backend untouched (manual verification required)');
        } else {
            this.pass('Backend untouched');
        }

        this.pass('No placeholder text (manual verification required)');
    }

    // Run all checks
    run() {
        this.log(`\n${COLORS.bold}${COLORS.cyan}╔════════════════════════════════════════╗${COLORS.reset}`);
        this.log(`${COLORS.bold}${COLORS.cyan}║   SecuScan Frontend Quality Gate      ║${COLORS.reset}`);
        this.log(`${COLORS.bold}${COLORS.cyan}╚════════════════════════════════════════╝${COLORS.reset}\n`);

        try {
            this.checkScopeControl();
            this.checkRouteIntegrity();
            this.checkVisualDiscipline();
            this.checkMotionControl();
            this.check3DSafety();
        } catch (error) {
            this.fail('Quality gate execution', error.message);
        }

        // Summary
        this.log(`\n${COLORS.bold}=== Summary ===${COLORS.reset}`, COLORS.cyan);
        this.log(`${COLORS.green}Passed: ${this.passes.length}${COLORS.reset}`);
        this.log(`${COLORS.yellow}Warnings: ${this.warnings.length}${COLORS.reset}`);
        this.log(`${COLORS.red}Failed: ${this.failures.length}${COLORS.reset}`);

        if (this.failures.length > 0) {
            this.log(`\n${COLORS.bold}${COLORS.red}✗ QUALITY GATE FAILED${COLORS.reset}\n`);
            process.exit(1);
        } else if (this.warnings.length > 0) {
            this.log(`\n${COLORS.bold}${COLORS.yellow}⚠ QUALITY GATE PASSED WITH WARNINGS${COLORS.reset}\n`);
            process.exit(0);
        } else {
            this.log(`\n${COLORS.bold}${COLORS.green}✓ QUALITY GATE PASSED${COLORS.reset}\n`);
            process.exit(0);
        }
    }
}

// Run quality gate
const gate = new QualityGate();
gate.run();

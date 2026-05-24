#!/usr/bin/env node
/**
 * fix_svg_vars.cjs — SVG 后处理修复器（工具无关）
 *
 * 解决 Cursor 内置 SVG 查看器的兼容问题：
 *
 * Fix 1 — CSS 变量替换（var(--xxx) → 实色值）
 *   Cursor 不完全支持 CSS var() 函数，自动提取 <svg style=""> 和 <style> 块中的
 *   变量定义，将全文 var(--xxx) / var(--xxx, fallback) 替换为实色值。
 *
 * Fix 2 — &lt;br/&gt; 多行拆分（→ <tspan>）
 *   某些 Mermaid 渲染器（如 pretty-mermaid）不识别 <br/> 换行语法，在 <text> 中
 *   输出字面的 &lt;br/&gt; 文本。此修复将含 &lt;br/&gt; 的 <text> 元素自动拆分
 *   为多行的 <tspan> 结构。
 *
 * 用法：
 *   node .cursor/tools/fix_svg_vars.cjs <svg文件1> [svg文件2 ...]
 *
 * 约束：
 *   - 直接覆写原文件
 *   - 不依赖外部包，纯 Node.js 内置模块
 *   - 工具无关：兼容 pretty-mermaid / mermaid-cli / d2 等任意生成器
 *
 * 附注：
 *   若未来 Cursor 原生支持 CSS var() 与 <text> 内嵌换行，本脚本自然废弃。
 */

const fs = require('fs');
const path = require('path');

// ===========================================================================
// Fix 1 — CSS 变量提取与替换
// ===========================================================================

function extractFromSvgStyle(svgContent) {
    const map = new Map();
    const m = svgContent.match(/<svg[^>]*\sstyle\s*=\s*"([^"]*)"/i);
    if (!m) return map;

    const decls = m[1].split(';');
    for (const d of decls) {
        const kv = d.trim();
        const colonIdx = kv.indexOf(':');
        if (colonIdx === -1) continue;
        const key = kv.slice(0, colonIdx).trim();
        const val = kv.slice(colonIdx + 1).trim();
        if (key.startsWith('--') && val) {
            map.set(key, val);
        }
    }
    return map;
}

function extractFromStyleBlock(svgContent) {
    const map = new Map();
    const styleM = svgContent.match(/<style[^>]*>([\s\S]*?)<\/style>/i);
    if (!styleM) return map;

    const css = styleM[1];
    const re = /(--[\w-]+)\s*:\s*([^;]+?)\s*(?:;|$)/g;
    let m;
    while ((m = re.exec(css)) !== null) {
        const key = m[1];
        const val = m[2].trim();
        if (val) map.set(key, val);
    }
    return map;
}

function buildVarMap(svgContent) {
    const m1 = extractFromSvgStyle(svgContent);
    const m2 = extractFromStyleBlock(svgContent);
    return new Map([...m1, ...m2]);
}

function replaceVar(text, varMap, fileName) {
    // var(--xxx, fallback)
    const m2 = text.match(/^var\(\s*(--[\w-]+)\s*,\s*([^)]+)\s*\)$/);
    if (m2) {
        const resolved = varMap.get(m2[1]);
        if (resolved) return resolved;
        console.warn(`  ⚠ ${fileName}: var(${m2[1]}) not found, using fallback: ${m2[2].trim()}`);
        return m2[2].trim();
    }
    // var(--xxx)
    const m1 = text.match(/^var\(\s*(--[\w-]+)\s*\)$/);
    if (m1) {
        const resolved = varMap.get(m1[1]);
        if (resolved) return resolved;
        console.warn(`  ⚠ ${fileName}: var(${m1[1]}) not found, keeping original`);
        return text;
    }
    console.warn(`  ⚠ ${fileName}: unrecognized var() syntax: ${text}`);
    return text;
}

function applyFixVars(svgContent, fileName) {
    const varMap = buildVarMap(svgContent);
    if (varMap.size === 0) {
        console.log(`  ${fileName}: Fix 1 (vars) — no CSS vars defined, skipped`);
        return { content: svgContent, count: 0 };
    }
    let total = 0;
    const after = svgContent.replace(/var\(\s*--[\w-]+(?:\s*,\s*[^)]+)?\s*\)/g, (match) => {
        const replaced = replaceVar(match, varMap, fileName);
        if (replaced !== match) total++;
        return replaced;
    });
    console.log(`  ${fileName}: Fix 1 (vars) — extracted ${varMap.size} CSS vars, ${total} var() calls resolved`);
    return { content: after, count: total };
}

// ===========================================================================
// Fix 2 — &lt;br/&gt;  →  <tspan> 多行拆分
// ===========================================================================

/**
 * 将单个 <text> 元素从单行拆为多行 <tspan> 结构。
 *
 * 示例输入：
 *   <text x="573.675" y="1338" text-anchor="middle" dy="0.35em" font-size="13" ...>
 *     &quot;第一行&lt;br/&gt;第二行&lt;br/&gt;第三行&quot;
 *   </text>
 *
 * 输出：
 *   <text text-anchor="middle" fill="#2e3440" font-size="13" font-weight="500" ...>
 *     <tspan x="573.675" dy="-14.3">第一行</tspan>
 *     <tspan x="573.675" dy="16.9">第二行</tspan>
 *     <tspan x="573.675" dy="16.9">第三行</tspan>
 *   </text>
 *
 * 注意：dy="0.35em" 在 <text> 上的含义被 <tspan> 接管；
 * 首行需要负偏移来补偿首次 dy。
 */
function splitBrText(fullMatch, attrs, body) {
    // 解码 &quot; &lt;br/&gt; 等实体
    let text = body
        .replace(/&quot;/g, '"')
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&amp;/g, '&');

    const lines = text.split(/<br\/>/g);
    if (lines.length <= 1) return fullMatch; // 无需拆分

    // 也处理 <br> 不带斜杠的情况
    const lines2 = text.split(/<br\s*\/?>/g);
    const finalLines = lines2.length > lines.length ? lines2 : lines;

    // 提取原始属性中的 x, font-size（用于行高计算）
    const xMatch = attrs.match(/x\s*=\s*"([^"]+)"/);
    const xVal = xMatch ? xMatch[1] : '0';

    const fsMatch = attrs.match(/font-size\s*=\s*"([^"]+)"/);
    const fontSize = fsMatch ? parseFloat(fsMatch[1]) : 13;

    // 保留除 x, dy（及 y 的显式定位）外的所有属性
    // y 保留用于 <text> 的基线定位，tspan 通过 dy 偏移
    const preservedAttrs = attrs
        .replace(/\s+x\s*=\s*"[^"]*"/, '')
        .replace(/\s+dy\s*=\s*"[^"]*"/, '')
        .trim();

    const yMatch = attrs.match(/y\s*=\s*"([^"]+)"/);
    const yVal = yMatch ? yMatch[1] : null;

    // 行高 ≈ font-size × 1.3
    const lineHeight = Math.round(fontSize * 1.3 * 10) / 10;

    // 构建 <tspan> 行
    // 首行 dy=0，依赖 <text> 上的 y；后续行 dy=lineHeight
    const tspans = finalLines.map((line, i) => {
        const trimmed = line.trim();
        if (!trimmed) return '';
        const dy = i === 0 ? 'dy="0"' : `dy="${lineHeight}"`;
        const escaped = trimmed
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
        return `<tspan x="${xVal}" ${dy}>${escaped}</tspan>`;
    }).filter(Boolean);

    if (tspans.length <= 1) return fullMatch;

    return `<text ${preservedAttrs}>\n${tspans.join('\n')}\n</text>`;
}

function applyFixBr(svgContent, fileName) {
    // 匹配含 &lt;br/&gt; 或 &lt;br&gt; 的 <text> 元素
    // 使用非贪婪匹配 body 内容
    const re = /<text\b([^>]*)>([\s\S]*?)<\/text>/g;
    let total = 0;
    const after = svgContent.replace(re, (full, attrs, body) => {
        if (body.includes('&lt;br/&gt;') || body.includes('&lt;br&gt;')) {
            total++;
            return splitBrText(full, attrs, body);
        }
        return full;
    });
    if (total > 0) {
        console.log(`  ${fileName}: Fix 2 (br) — ${total} text elements split into multi-line`);
    } else {
        console.log(`  ${fileName}: Fix 2 (br) — no &lt;br/&gt; found, skipped`);
    }
    return { content: after, count: total };
}

// ===========================================================================
// Main
// ===========================================================================

const files = process.argv.slice(2);
if (files.length === 0) {
    console.error('Usage: node fix_svg_vars.cjs <svg-file1> [svg-file2 ...]');
    process.exit(1);
}

for (const filePath of files) {
    const absPath = path.resolve(filePath);
    const name = path.basename(absPath);
    if (!fs.existsSync(absPath)) {
        console.error(`Skipping (not found): ${absPath}`);
        continue;
    }
    console.log(`\n${name}:`);
    const before = fs.readFileSync(absPath, 'utf-8');

    // Fix 1: CSS 变量替换
    const r1 = applyFixVars(before, name);
    let after = r1.content;

    // Fix 2: <br/> → <tspan> 多行拆分
    const r2 = applyFixBr(after, name);
    after = r2.content;

    if (r1.count > 0 || r2.count > 0) {
        fs.writeFileSync(absPath, after, 'utf-8');
        console.log(`  → written (${r1.count} var + ${r2.count} br fixes)`);
    } else {
        console.log(`  → no changes, skipped`);
    }
}
console.log('\nDone.');

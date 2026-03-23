import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import p1 from './chief_complaints_part1.mjs';
import p2 from './chief_complaints_part2.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, '..');
const out = path.join(root, 'static', 'data', 'chief_complaints.json');
fs.mkdirSync(path.dirname(out), { recursive: true });
const merged = [...p1, ...p2];
fs.writeFileSync(out, JSON.stringify(merged), 'utf-8');
console.log('Wrote', out, '(' + merged.length + ' categories)');

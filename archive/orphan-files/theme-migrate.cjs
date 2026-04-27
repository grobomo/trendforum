const fs = require('fs');
const path = require('path');

const dir = path.join(__dirname, '..', 'src', 'client', 'components');
const files = fs.readdirSync(dir).filter(f => f.endsWith('.tsx'));

// Also process LoginForm which uses bg-page
const replacements = [
  ['bg-[#1a1a2e]', 'bg-page'],
  ['bg-[#16162a]', 'bg-input'],
  ['bg-[#1e1e3a]', 'bg-card'],
  ['border-[#2a2a4a]', 'border-border'],
  ['border-[#3a3a5a]', 'border-border-hover'],
  ['hover:border-[#3a3a5a]', 'hover:border-border-hover'],
  ['hover:border-[#D5232F]', 'hover:border-accent'],
  ['focus:border-[#D5232F]', 'focus:border-accent'],
  ['text-[#e0e0e0]', 'text-text'],
  ['text-[#aaaacc]', 'text-muted'],
  ['text-[#8888aa]', 'text-muted'],
  ['text-[#666688]', 'text-dim'],
  ['text-[#D5232F]', 'text-accent'],
  ['bg-[#D5232F]', 'bg-accent'],
  ['hover:bg-red-700', 'hover:bg-accent-hover'],
  ['bg-[#2a2a4a]', 'bg-border'],
  ['hover:bg-[#2a2a4a]/50', 'hover:bg-border/50'],
  ['hover:bg-[#3a3a5a]', 'hover:bg-border-hover'],
  ['placeholder-[#666688]', 'placeholder-dim'],
  ['hover:text-white', 'hover:text-text'],
];

let total = 0;
for (const f of files) {
  const fpath = path.join(dir, f);
  let content = fs.readFileSync(fpath, 'utf-8');
  let count = 0;
  for (const [from, to] of replacements) {
    while (content.includes(from)) {
      content = content.replace(from, to);
      count++;
    }
  }
  if (count > 0) {
    fs.writeFileSync(fpath, content);
    console.log(f + ': ' + count + ' replacements');
    total += count;
  }
}
console.log('Total: ' + total + ' replacements across ' + files.length + ' files');

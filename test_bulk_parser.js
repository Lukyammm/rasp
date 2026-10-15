function parseBulk(raw) {
    const parsed = [];
    const rawLines = raw.split(/\r?\n/).map(l => l.trim()).filter(Boolean);

    if (rawLines.length === 1 && rawLines[0].includes(',') && !rawLines[0].match(/,\s*\d+/)) {
        const words = rawLines[0].split(',').map(w => w.trim()).filter(Boolean);
        words.forEach(w => parsed.push({ text: w, weight: 20 }));
    } else {
        rawLines.forEach(rawLine => {
            let line = rawLine.replace(/^[•\-\*\s]+/, '').trim();
            if (!line) return;
            if (/^(posi[cç][aã]o|rank|#|termo|palavra|word|termo\t|palavra\t)/i.test(line)) return;
            if (line.includes('\t')) {
                const parts = line.split('\t').map(p => p.trim()).filter(Boolean);
                if (parts.length >= 2) {
                    if (/^\d+$/.test(parts[0]) && parts.length >= 3 && !/^\d+$/.test(parts[1])) {
                        const word = parts[1].replace(/^[•\-\*\s]+/, '');
                        const weight = parseInt(parts[2].replace(/[^\d]/g, ''), 10) || 15;
                        parsed.push({ text: word, weight: Math.max(1, weight) });
                        return;
                    }
                    if (!/^\d+$/.test(parts[0])) {
                        const word = parts[0].replace(/^[•\-\*\s]+/, '');
                        const weight = parseInt(parts[1].replace(/[^\d]/g, ''), 10) || 15;
                        parsed.push({ text: word, weight: Math.max(1, weight) });
                        return;
                    }
                }
            }
            if (line.includes(',')) {
                const csvParts = line.split(',').map(p => p.trim()).filter(Boolean);
                if (csvParts.length === 2 && /^\d+$/.test(csvParts[1])) {
                    parsed.push({ text: csvParts[0], weight: Math.max(1, parseInt(csvParts[1], 10)) });
                    return;
                }
                if (csvParts.length >= 3 && /^\d+$/.test(csvParts[0]) && /^\d+$/.test(csvParts[2])) {
                    parsed.push({ text: csvParts[1], weight: Math.max(1, parseInt(csvParts[2], 10)) });
                    return;
                }
            }
            if (line.includes(';')) {
                const scParts = line.split(';').map(p => p.trim()).filter(Boolean);
                if (scParts.length >= 2 && /^\d+$/.test(scParts[1])) {
                    parsed.push({ text: scParts[0], weight: Math.max(1, parseInt(scParts[1], 10)) });
                    return;
                }
            }
            const match = line.match(/^(.+?)(?:\s*[:=]\s*|\s+)(\d+)(?:\s*%)?$/);
            if (match) {
                const text = match[1].replace(/^["']|["']$/g, '').trim();
                const weight = Math.max(1, parseInt(match[2], 10));
                parsed.push({ text, weight });
                return;
            }
            const parenMatch = line.match(/^(.+?)\s*\(\s*(\d+)\s*\)$/);
            if (parenMatch) {
                parsed.push({ text: parenMatch[1].trim(), weight: Math.max(1, parseInt(parenMatch[2], 10)) });
                return;
            }
            const cleaned = line.replace(/^[•\-\*\d+\.\s]+/, '').trim();
            if (cleaned) parsed.push({ text: cleaned, weight: 15 });
        });
    }
    return parsed;
}

const tests = [
    'Fortaleza, 85\nInovação, 64',
    'Posição\tTermo\tFrequência\tParticipação\n1\tFortaleza\t85\t35%\n2\tInovação\t64\t25%',
    'Fortaleza; 85\nInovação; 64',
    'Fortaleza, Inovação, Saúde, Comunidade',
    '🎉 Fortaleza 2026: 100\n🚀 Inovação: 80',
    'Fortaleza (85)\nInovação (64)',
    '- Fortaleza: 85\n- Inovação: 64'
];

tests.forEach((t, i) => {
    console.log(`Test ${i+1}:`, parseBulk(t));
});

const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

const inputDir = path.join(__dirname, '../docs/images');
const outputDir = inputDir;

const files = [
    'tiktok.svg',
    'ChatGPT_logo.svg',
    'Logo_Benz.svg',
    '宝马.svg',
    '特斯拉.svg',
    '星巴克.svg',
    '麦当劳-01.svg',
    '耐克.svg'
];

files.forEach(file => {
    const inputPath = path.join(inputDir, file);
    const outputPath = path.join(outputDir, file.replace('.svg', '.png'));

    if (fs.existsSync(inputPath)) {
        sharp(inputPath)
            .resize(256) // Resize to reasonable size
            .png()
            .toFile(outputPath)
            .then(info => { console.log(`Converted ${file} to PNG`); })
            .catch(err => { console.error(`Error converting ${file}:`, err); });
    } else {
        console.warn(`File not found: ${inputPath}`);
    }
});

const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

const inputDir = path.join(__dirname, '../resources/logos');
const outputDir = inputDir;

const files = [
    'tiktok.svg',
    'ChatGPT_logo.svg',
    'Logo_Benz.svg',
    'bmw.svg',
    'tesla.svg',
    'starbucks.svg',
    'mcdonalds.svg',
    'nike.svg'
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

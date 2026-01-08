const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

const inputDir = path.join(__dirname, '../docs/images');
const outputDir = inputDir;

// Read all files in directory
fs.readdir(inputDir, (err, files) => {
    if (err) {
        console.error('Could not list the directory.', err);
        process.exit(1);
    }

    files.forEach(file => {
        if (path.extname(file).toLowerCase() === '.svg') {
            const inputPath = path.join(inputDir, file);
            // Replace extension carefully
            const outputName = path.basename(file, path.extname(file)) + '.png';
            const outputPath = path.join(outputDir, outputName);

            // Always convert to ensure we have the latest version
            sharp(inputPath)
                .resize({ width: 256, height: 256, fit: 'contain', background: { r: 0, g: 0, b: 0, alpha: 0 } })
                .png()
                .toFile(outputPath)
                .then(info => { console.log(`Converted ${file} to ${outputName}`); })
                .catch(err => { console.error(`Error converting ${file}:`, err); });
        }
    });
});

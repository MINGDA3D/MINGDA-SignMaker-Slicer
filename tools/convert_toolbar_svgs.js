const sharp = require('sharp');
const path = require('path');
const fs = require('fs');

const imagesDir = path.join(__dirname, '..', 'docs', 'images');

// 需要转换的工具栏 SVG 图标
const svgFiles = [
    'move.svg',
    'rotate.svg',
    'scale.svg',
    'mirror_x.svg',
    'mirror_y.svg',
    'split_objects_dark.svg',
    'arrange.svg'
];

async function convertSvgToPng(svgFile) {
    const svgPath = path.join(imagesDir, svgFile);
    const pngFile = svgFile.replace('.svg', '.png');
    const pngPath = path.join(imagesDir, pngFile);
    
    if (!fs.existsSync(svgPath)) {
        console.log(`跳过: ${svgFile} 不存在`);
        return;
    }
    
    try {
        await sharp(svgPath)
            .resize(64, 64)  // 生成较大的尺寸，方便缩放
            .png()
            .toFile(pngPath);
        console.log(`转换成功: ${svgFile} -> ${pngFile}`);
    } catch (err) {
        console.error(`转换失败 ${svgFile}:`, err.message);
    }
}

async function main() {
    console.log('开始转换 SVG 图标为 PNG...\n');
    
    for (const svgFile of svgFiles) {
        await convertSvgToPng(svgFile);
    }
    
    console.log('\n转换完成!');
}

main();

#! /usr/bin/env node
/*
 * svg2png CLI
 *
 * Copyright (c) 2012 lucor
 * Copyright (c) 2013 Ryan Parman <http://ryanparman.com>
 */

"use strict";

var fs = require('fs'),
	path = require('path'),
	util  = require('util'),
	argv = require('optimist').argv,
	svg2png = require("./svg2png");

var help = [
	"usage: svg2png input[.svg] [options]",
	"",
	"Converts SVG images into PNG images, optionally resizing them and crushing them.",
	"",
	"Pass a directory to scan for *.svg files, or pass an individual *.svg file to convert.",
	"The output filename will be the same as the input unless a scale factor or width is used,",
	"in which case that value will be appended to the end of the filename.",
	"",
	"options:",
	// "  -c, --crush   Pass the resulting PNG file through pngcrush and optipng.",
	"  -s, --scale   Scale the height and width by this (float) factor.",
	"                The default value is 1.0. Takes priority over --width.",
	"  -w, --width   Resize the PNG to a specific width, scaling the height automatically.",
	"                The default value is the width of the source SVG.",
	"  -q, --quiet   Be quiet, dammit!",
	"  -h, --help    You're staring at it.",
	""
].join('\n');

if (argv.h || argv.help || argv._.length === 0) {
	return util.puts(help);
}

var workPath = argv._[0];

if (fs.existsSync(workPath)) {
	var scale = ((argv.s || argv.scale) || 'w' + (argv.w || argv.width) || 1.0);

	if (fs.statSync(workPath).isFile()) {
		if (path.extname(workPath, '.svg') === '.svg') {
			var src = workPath;
			var fn = path.basename(workPath, '.svg');
			var dest = workPath.split(path.sep);
			dest.pop();
			dest.push(fn);
			dest = dest.join(path.sep);
			if (argv.s || argv.scale) {
				dest += '-s' + (argv.s || argv.scale);
			}
			else if (argv.w || argv.width) {
				dest += '-w' + (argv.w || argv.width);
			}
			dest += '.png';
			svg2png(src, dest, scale, function(err) {
				if (err) {
					console.error('An error occurred converting %s in %s: %s', src, dest, err);
				}
				else {
					console.info('%s has been converted in %s', src, dest);

					// if (argv.c || argv.crush) {
					// 	try {
					// 		console.log('Starting: ' + fs.statSync(dest).size);

					// 		var reader = fs.createReadStream(dest);
					// 		var writer = fs.createWriteStream(dest + '_');
					// 		var crusher = new OptiPng(['-o7']);

					// 		var evtr = reader.pipe(crusher).pipe(writer);
					// 		evtr.on('close', function() {
					// 			fs.unlink(dest, function() {
					// 				fs.rename(dest + '_', dest, function() {
					// 					console.log('Ending:   ' + fs.statSync(dest).size);
					// 				});
					// 			});
					// 		});
					// 	}
					// 	catch (e) {
					// 		console.error('An error occurred while crushing the PNG: %s', e);
					// 	}
					// }
				}
			})
		}
		else {
			console.info('Not an SVG file: %s', file)
		}
	}
	else if (fs.statSync(workPath).isDirectory()) {
		fs.readdir(workPath, function(err, files) {
			files.forEach(function(file) {
				if (path.extname(file, '.svg') === '.svg') {
					var src = path.join(workPath, file);
					var dest = path.join(workPath, path.basename(file, '.svg'));
					if (argv.s || argv.scale) {
						dest += '-s' + (argv.s || argv.scale);
					}
					else if (argv.w || argv.width) {
						dest += '-w' + (argv.w || argv.width);
					}
					dest += '.png';
					svg2png(src, dest, scale, function(err) {
						if (err) {
							console.error('An error occurred converting %s in %s: %s', src, dest, err)
						}
						else {
							console.info('%s has been converted in %s', src, dest);

							if (argv.c || argv.crush) {
								try {
									fs.createReadStream(dest).pipe(new PngCrush(['-res', 300, '-rle'])).pipe(fs.createWriteStream(dest));
								}
								catch (e) {
									console.error('An error occurred while using pngcrush: %s', e);
								}

								try {
									fs.createReadStream(dest).pipe(new OptiPng(['-o7'])).pipe(fs.createWriteStream(dest));
								}
								catch (e) {
									console.error('An error occurred while using optipng: %s', e);
								}

								console.info('%s has been crushed.', dest);
							}
						}
					})
				}
				else {
					if (!argv.q && !argv.quiet) {
						console.info('Skipped non-SVG file: %s', file)
					}
				}
			})
		})
	}
}
else {
	console.error('Invalid input: %s', workPath)
}

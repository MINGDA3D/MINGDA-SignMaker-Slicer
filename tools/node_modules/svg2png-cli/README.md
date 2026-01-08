# svg2png-cli

**svg2png-cli** is a simple CLI wrapper for [svg2png](https://github.com/domenic/svg2png)
by Domenic Denicola. Forked from earlier work on the CLI wrapper by
[Luca Corbo](http://lucor.github.com).


## Installation
It's built on [Node.js](http://nodejs.org) and can be found in [npm](https://npmjs.org/package/svg2png-cli).

	# Local installation
	npm install svg2png-cli

	# Global installation
	sudo npm install -g svg2png-cli


## Usage
Calling `svg2png` with no parameters, or with `-h` or `--help`, you can see the help screen.

	usage: svg2png input[.svg] [options]

	Converts SVG images into PNG images, optionally resizing them and crushing them.

	Pass a directory to scan for *.svg files, or pass an individual *.svg file to convert.
	The output filename will be the same as the input unless a scale factor or width is used,
	in which case that value will be appended to the end of the filename.

	options:
	  -s, --scale   Scale the height and width by this (float) factor.
	                The default value is 1.0. Takes priority over --width.
	  -w, --width   Resize the PNG to a specific width, scaling the height automatically.
	                The default value is the width of the source SVG.
	  -q, --quiet   Be quiet, dammit!
	  -h, --help    You're staring at it.

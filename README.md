# python-pdfimgextract

A fast parallel PDF image extractor written in Python.

## Features

- parallel extraction
- atomic file writes
- duplicate image removal
- clean CLI interface
- progress bar
- safe interruption handling

## Installation

pip install -r requirements.txt

## Usage

python ./pdfimgextract.py [INPUT_PDF] [OUTPUT_DIR] [NUMBER_OF_PROCESSES]

Or use the optional flags:

--input | -i  
--output | -o  
--parallelism | -p  

The default number of parallel processes is **8** if not specified.
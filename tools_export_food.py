"""Portable, dependency-free Excel 100g sheet reader for project retraining.

Uses only Python's standard-library ZIP/XML parsers, so Windows users can export
'Food Ready 100g' source without requiring any special Excel automation package.
Note: only stored cell values are read; formulas are not recalculated.
"""

import csv
import posixpath
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / 'data' / 'food_dataset_original.xlsx'
OUTPUT = ROOT / 'data' / 'food_100g.csv'
SHEET_NAME = 'ML Ready 100g'
MAIN = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
OFFICE_REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PACKAGE_REL = 'http://schemas.openxmlformats.org/package/2006/relationships'
CELL_RE = re.compile(r'^([A-Z]+)')


def col_number(letters):
    pos = 0
    for ch in letters:
        pos = pos * 26 + (ord(ch) - ord('A') + 1)
    return pos - 1


def extract_rows(workbook_file):
    with zipfile.ZipFile(workbook_file) as workbook:
        root = ET.fromstring(workbook.read('xl/workbook.xml'))
        sheet_id = None
        for node in root.findall(f'.//{{{MAIN}}}sheet'):
            if node.get('name') == SHEET_NAME:
                sheet_id = node.get(f'{{{OFFICE_REL}}}id')
                break
        if sheet_id is None:
            raise ValueError('Missing Excel worksheet: ' + SHEET_NAME)
        rel_root = ET.fromstring(workbook.read('xl/_rels/workbook.xml.rels'))
        target = None
        for node in rel_root.findall(f'{{{PACKAGE_REL}}}Relationship'):
            if node.get('Id') == sheet_id:
                target = node.get('Target')
                break
        if not target:
            raise ValueError('Could not locate worksheet XML')
        worksheet = target.lstrip('/') if target.startswith('/') else posixpath.normpath('xl/' + target)
        ss = []
        if 'xl/sharedStrings.xml' in workbook.namelist():
            ss_root = ET.fromstring(workbook.read('xl/sharedStrings.xml'))
            for item in ss_root.findall(f'{{{MAIN}}}si'):
                ss.append(''.join(t.text or '' for t in item.iter(f'{{{MAIN}}}t')))
        sheet = ET.fromstring(workbook.read(worksheet))
        values = []
        for row in sheet.findall(f'.//{{{MAIN}}}sheetData/{{{MAIN}}}row'):
            record = [None] * 10
            for cell in row.findall(f'{{{MAIN}}}c'):
                match = CELL_RE.match(cell.attrib.get('r', ''))
                if not match:
                    continue
                index = col_number(match.group(1))
                if index < 0 or index >= 10:
                    continue
                v = cell.find(f'{{{MAIN}}}v')
                cell_type = cell.get('t', '')
                if cell_type == 'inlineStr':
                    ins = cell.find(f'{{{MAIN}}}is')
                    value = ''.join(t.text or '' for t in ins.iter(f'{{{MAIN}}}t')) if ins is not None else ''
                elif v is None:
                    value = None
                elif cell_type == 's':
                    value = ss[int(v.text)]
                elif cell_type in ('str', 'e'):
                    value = v.text
                elif cell_type == 'b':
                    value = int(v.text or 0)
                else:
                    numeric = float(v.text)
                    value = int(numeric) if numeric.is_integer() else numeric
                record[index] = value
            if any(item is not None for item in record):
                values.append(record)
        return values


def main():
    values = extract_rows(INPUT)
    if not values or values[0][1] != 'Food Name' or values[0][9] != 'Score':
        raise ValueError('Excel worksheet columns have changed unexpectedly')
    rows = [r for r in values[1:] if r[1] is not None]
    if len(rows) != 718:
        print('NOTICE: dataset row count is now', len(rows), '(original dataset had 718).')
    with OUTPUT.open('w', encoding='utf-8-sig', newline='') as dest:
        writer = csv.writer(dest)
        writer.writerows([values[0]] + rows)
    print(f'Exported {len(rows)} foods from original workbook to: {OUTPUT}')


if __name__ == '__main__':
    main()

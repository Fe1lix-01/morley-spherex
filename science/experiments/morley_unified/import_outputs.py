#!/usr/bin/env python3
"""Copia solamente los productos outputs/ del ZIP original, sin Windows .venv.

Uso: python import_outputs.py ~/Downloads/MORLEY_PIPELINE_UNIFICADO.zip
No sobreescribe archivos existentes. El repositorio ignora estos productos.
"""
from __future__ import annotations
import argparse
import shutil
import stat
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

DEST = Path(__file__).resolve().parent / 'outputs'


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('zip_original', type=Path)
    args = parser.parse_args()
    if not args.zip_original.is_file():
        parser.error(f'No existe: {args.zip_original}')
    files, copied, skipped, nbytes = 0, 0, 0, 0
    with ZipFile(args.zip_original) as archive:
        for item in archive.infolist():
            if item.is_dir():
                continue
            raw = PurePosixPath(item.filename)
            parts = raw.parts
            if '..' in parts or '/outputs/' not in f'/{item.filename}':
                continue
            if not all(part not in ('', '.', '..') for part in parts):
                continue
            # Aceptar únicamente el árbol de productos del proyecto original.
            expected = ('MORLEY_PIPELINE_UNIFICADO','MORLEY_PIPELINE_UNIFICADO','outputs')
            if tuple(parts[:3]) != expected or len(parts) <= 3:
                continue
            if stat.S_IFMT(item.external_attr >> 16) == stat.S_IFLNK:
                continue
            rel = Path(*parts[3:])
            dest = DEST / rel
            files += 1
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                with dest.open('xb') as f, archive.open(item) as stream:
                    shutil.copyfileobj(stream, f)
            except FileExistsError:
                skipped += 1
                continue
            copied += 1
            nbytes += item.file_size
    print(f'Productos detectados: {files} | copiados: {copied} | existentes no sobreescritos: {skipped}')
    print(f'Tamaño copiado: {nbytes/1_000_000:.2f} MB')
    print(f'Destino: {DEST}')
    print('NOTA: los outputs se ignoran en Git. No significa que las detecciones sean científicamente validadas.')


if __name__ == '__main__':
    main()

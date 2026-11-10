#!/bin/sh
# Cek sisa data contoh sebelum README dipublikasikan.
# Pemakaian: sh scripts/cek-placeholder.sh [berkas ...]   (bawaan: README.md + assets/*.svg)
# Keluar dengan kode 1 jika masih ada placeholder, 0 jika bersih.

if [ "$#" -gt 0 ]; then
  set -- "$@"
else
  set -- README.md assets/header-light.svg assets/header-dark.svg
fi

hasil=$(grep -nF -e '‹' -e '›' -e 'GANTI' -e 'example.com' "$@" 2>/dev/null)

if [ -n "$hasil" ]; then
  printf '%s\n\n' "$hasil"
  echo "Masih ada placeholder (‹ ›, GANTI, example.com). Ganti atau hapus dulu." >&2
  exit 1
fi

echo "Bersih: tidak ada placeholder tersisa."

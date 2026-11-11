# Varian galaxy

README profil bertema langit malam (midnight, cyan, amber). Tiga gambar SVG, masing-masing dalam varian **dark** dan **light**, dibuat oleh renderer orisinal dari data akun GitHub. Sisanya Markdown biasa.

| Bagian | Sumber data | Berkas |
| :-- | :-- | :-- |
| Hero: nama, peran, tagline, spiral galaksi dengan label proyek | `galaxy.config.json` (+ bintang repo bila live) | `assets/hero-{dark,light}.svg` |
| Projects in orbit | `projects` di config | blok `projects` di `README.md` |
| A year of building: konstelasi | kalender kontribusi 12 bulan | `assets/constellation-{dark,light}.svg` |
| Growing over time: pohon sakura atau pine | kalender kontribusi + total bintang | `assets/tree-{dark,light}.svg` |
| Beyond the code, Let's connect | `beyond`, `connect` di config | blok `beyond`, `connect` |

Blok `hero`, `constellation`, dan `tree` di `README.md` juga diisi renderer (tag gambar), jadi nama berkas dan teks alternatifnya selalu sinkron dengan tema yang dipilih.

Varian dasar (terminal) tetap ada di `template/` dan tidak berubah.

## Data demo dan data live

| | `--demo` | `--live` |
| :-- | :-- | :-- |
| Sumber | generator deterministik di `render.py` | `api.github.com` |
| Jaringan / token | tidak perlu | perlu `GITHUB_TOKEN` |
| Penanda di hasil | lencana **DEMO DATA** di tiap SVG, catatan di README, footer `DESIGN CONCEPT · EXAMPLE CONTENT` | tidak ada |
| Jumlah bintang repo di daftar proyek | tidak ditampilkan | ditampilkan |

Semua gambar yang ada di repo kit dibuat dengan `--demo`. Angkanya bukan statistik siapa pun. Mode live menolak berjalan selama config masih memuat `YOUR NAME`, `YOUR-USERNAME`, atau `example.com`, dan tidak pernah jatuh diam-diam ke data demo.

## Pemasangan

Syarat: Python 3.8+ (hanya pustaka standar) dan repositori profil publik bernama sama persis dengan username GitHub-mu.

1. Salin isi folder `galaxy/` (termasuk `.github/`) ke akar repositori profil:

   ```sh
   cp -R dev-readme-kit/galaxy/. USERNAME/
   ```

2. Edit `galaxy.config.json`: `username`, `identity`, `projects`, `beyond`, `connect`, `tree.style`. Ubah `data.mode` menjadi `"live"`.
3. Cek sisa data contoh (tanpa jaringan):

   ```sh
   python3 scripts/render.py --check
   ```

4. Ubah teks yang tidak dibuat renderer langsung di `README.md`: judul bagian dan keterangan pohon. Jangan hapus penanda `<!-- galaxy:nama:start -->` dan `<!-- galaxy:nama:end -->`; isi di antaranya ditimpa setiap render.
5. Commit dan push. Buka tab **Actions**, pilih `update-galaxy`, lalu **Run workflow** untuk render pertama dengan data nyata. Setelah itu workflow berjalan harian pukul 03:17 UTC.

Pratinjau lokal dengan data demo tidak butuh token:

```sh
python3 scripts/render.py --demo --all-trees   # juga menulis tree-{sakura,pine}-{dark,light}.svg
```

Pratinjau lokal dengan data nyata: `GITHUB_TOKEN=... python3 scripts/render.py --live`. Token fine-grained tanpa izin tambahan cukup untuk data publik. Jangan menulis token ke berkas.

## Konfigurasi

| Kunci | Isi |
| :-- | :-- |
| `username` | username GitHub. Di Actions ditimpa `github.repository_owner` lewat env `GALAXY_USER`. |
| `identity.name` / `role` / `tagline` | teks hero. Nama panjang dipecah dua baris otomatis. |
| `projects[]` | maksimal 6. `title` dan `description` untuk daftar, `label` (opsional, bawaan `title`) untuk spiral, `repo` (`pemilik/nama`) untuk tautan dan bintang, `url` (opsional) menggantikan tautan repo. |
| `beyond[]` | butir di bagian *Beyond the code*. |
| `connect[]` | pasangan `label` dan `url`. URL hanya `http(s)://` atau `mailto:`. |
| `tree.style` | `"sakura"` atau `"pine"`. |
| `appearance` | `"auto"` (bawaan), `"dark"`, atau `"light"`. Lihat bagian Tema. Flag `--theme` menang. |
| `data.mode` | `"demo"` atau `"live"` untuk jalan tanpa flag. Flag `--demo` / `--live` menang. |
| `data.demo_end_date` | tanggal akhir jendela demo, supaya keluaran demo tetap sama. |

Semua teks dibersihkan dan di-escape sebelum masuk ke SVG atau Markdown.

## Tema terang dan gelap

Setiap gambar punya dua berkas yang digambar terpisah, bukan satu gambar yang dibalik warnanya:

| | dark | light |
| :-- | :-- | :-- |
| Latar | gradasi midnight `#142058` → `#040A1C` | gradasi putih `#FFFFFF` → `#DCE7FA` dengan garis tepi `#C5D3EC`, agar kartu terbaca di halaman putih |
| Bintang | putih kebiruan, cyan, amber | tinta indigo `#1F2F66`, cyan `#0B7FA8`, amber `#E08A00`, pink `#DB3F7C` (dipertegas, dengan opasitas minimum lebih tinggi) |
| Pohon | batang indigo, kelopak cyan ke pink di langit gelap | batang ungu tua, tanah lilac, matahari pucat sebagai ganti bulan, tingkat pine teal tua dengan lampu pucat |
| Komposisi | sama persis | sama persis |

Kontras teks (WCAG, dihitung terhadap ujung-ujung gradasi): teks utama ≥ 13,6:1, teks redup ≥ 5,8:1 (light) dan ≥ 7,2:1 (dark), teks peran cyan ≥ 5,7:1 (light) dan ≥ 9,1:1 (dark).

### Memilih mode lewat `appearance`

| Nilai | Yang dirender | Tag di README |
| :-- | :-- | :-- |
| `"auto"` | kedua tema | `<picture>` dengan `<source media="(prefers-color-scheme: dark)">` lalu `<img>` light sebagai cadangan |
| `"dark"` | hanya `*-dark.svg` | `![alt](assets/x-dark.svg)` |
| `"light"` | hanya `*-light.svg` | `![alt](assets/x-light.svg)` |

Contoh `<picture>` yang ditulis renderer ke README (pada `auto`):

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/hero-dark.svg">
  <img src="assets/hero-light.svg" alt="...">
</picture>
```

Pada `auto`, GitHub memilih berkas sesuai tema yang aktif bagi pengunjung (mengikuti sistem bila tema GitHub diatur "Sync with system"). Berganti mode tidak menghapus berkas tema lain; hapus sendiri yang tidak dipakai.

Preview lokal memilih varian dengan aturan yang sama: `preview-galaxy-light.html` memuat `*-light.svg` dan `preview-galaxy-dark.html` memuat `*-dark.svg`.

## Ukuran teks

GitHub menampilkan README selebar kolom sekitar 830–890 px, sehingga gambar `viewBox` 1000 px diperkecil ±0,85–0,89×. Ukuran teks di SVG sudah dihitung untuk itu; tabel berikut memakai skala 0,888 (kolom 888 px):

| Teks | Di SVG | Tampil ±px |
| :-- | :-- | :-- |
| Label proyek di spiral | 17 | 15,1 |
| Peran (miring) | hingga 30, mengecil untuk teks panjang | hingga 26,6 |
| Tagline (bio) | 21 | 18,6 |
| Bulan, legenda, hari | 16 / 15 / 15 | 14,2 / 13,3 / 13,3 |
| Statistik konstelasi | 17 | 15,1 |
| Lencana DEMO, caption demo | 15 | 13,3 |

Di layar ponsel (±343 px) seluruh gambar mengecil ±0,34×, jadi teks kecil menjadi sulit dibaca. Itu batas dari memakai gambar tunggal; nama dan daftar proyek tetap tersedia sebagai teks Markdown, dan teks alternatif memuat nama, peran, dan tagline.

## Pemetaan data

Jendela data adalah 365 hari terakhir (live: hari ini UTC dan 364 hari sebelumnya).

### Konstelasi

- Satu hari = satu titik. Kolom mengikuti minggu kalender GitHub (mulai Minggu), baris mengikuti hari dalam minggu, dengan geser kecil yang deterministik.
- Hari tanpa kontribusi: titik redup kecil. Hari aktif: bintang.
- Ukuran dan warna mengikuti kuartil hari aktif: level 1–2 cyan kecil, level 3 putih, level 4 bintang empat sudut amber.
- Garis menghubungkan dua hari aktif berurutan yang berjarak paling jauh 4 hari. Celah lebih lebar memutus konstelasi.
- Sumbu bawah: label bulan nyata dalam jendela (rolling, bukan Jan–Des).

### Hero

- Spiral digambar dari titik acak deterministik (seed dari username); bintang tidak mewakili data apa pun.
- Setiap proyek menjadi penanda di salah satu dari dua lengan utama, bergantian per proyek. Ukuran penanda naik dengan log jumlah bintang repo (live saja).

### Pohon

Jendela dibagi 12 irisan sama rata (±30 hari), irisan terlama di dasar, terbaru di pucuk. `m` = total kontribusi irisan, `a` = jumlah hari aktif irisan, `T` = total kontribusi, `S` = total bintang repo publik non-fork milik akun (maksimal 100 repo).

| Elemen | Sakura | Pine |
| :-- | :-- | :-- |
| Tinggi | batang `170 + 130·g` | batang dan 12 tingkat memakai tinggi yang sama |
| `g` | `log10(1+T) / log10(3001)`, dibatasi 0–1 | sama |
| Satu irisan menjadi | satu cabang, makin tinggi makin baru | satu tingkat, makin tinggi makin baru |
| Panjang / lebar | cabang `55 + 150·√(m/maks)` (30 bila `m=0`), mengecil ke atas | tingkat `46 + 150·√(m/maks)`, menyempit ke atas |
| Ranting / hiasan | `2 + round(2·a/maks a)` ranting per cabang | `min(22, a)` lampu per tingkat |
| Bunga atau lampu | `min(60, 2·a + round(6·m/maks))` bunga, warna cyan (lama) ke pink (baru) | warna lampu cyan ke pink menurut irisan |
| Lentera / ornamen amber | `min(12, round(2.5·log10(1+S)))` | jumlah sama |
| Puncak | — | bintang `10 + 8·min(1, log10(1+S)/4)`, amber bila `S>0` |
| Tanah | `min(45, round(total hari aktif / 8))` kelopak atau cahaya jatuh | sama |

Demo memakai `S = 87`, jadi menghasilkan 5 lentera.

## Data, privasi, dan izin

- Satu kueri GraphQL dan paling banyak beberapa panggilan REST ke `api.github.com`. Tidak ada layanan lain.
- Yang dibaca: kalender kontribusi, bintang repo publik. Tidak ada kode, isu, atau repo privat yang dibaca atau dikirim.
- Kontribusi privat hanya ikut terhitung bila akunmu mengaktifkan *Include private contributions on my profile* dan token boleh melihatnya. Dengan `GITHUB_TOKEN` bawaan Actions, anggap hanya data publik yang terhitung.
- Workflow hanya meminta `contents: write` untuk commit hasil render. Tidak ada secret yang dibuat atau ditulis di berkas. `GITHUB_TOKEN` disuntik Actions per-run.
- Satu-satunya action pihak ketiga adalah `actions/checkout`. Untuk keamanan lebih, kunci ke SHA commit rilis yang sudah kamu periksa.
- Bila repo mengatur *Workflow permissions* menjadi baca saja pada tingkat organisasi atau repo, ubah di Settings → Actions → General.
- GitHub bisa menonaktifkan workflow terjadwal setelah 60 hari tanpa aktivitas repo. Aktifkan lagi dari tab Actions bila itu terjadi.

## Kompatibilitas render GitHub

- Gambar: `<picture>` (mode `auto`) atau Markdown `![alt](assets/x-dark.svg)` (mode satu tema). SVG dimuat lewat `<img>`, jadi tanpa skrip, tanpa font atau gambar eksternal, tanpa `foreignObject`. Hanya CSS internal untuk kedipan bintang, dan dimatikan bila pengguna meminta *reduced motion*. Judul, daftar proyek, minat, dan kontak tetap Markdown.
- Teks: font sistem (`system-ui`, Georgia untuk peran). Lebar teks bergantung pada font di perangkat pembaca; renderer memberi ruang cadangan.
- Tema: tiap gambar punya latar sendiri bersudut membulat, dan varian light memakai garis tepi tipis supaya kartunya terlihat di halaman putih.
- Aksesibilitas: tiap SVG punya `<title>` dan `<desc>`; README memuat teks alternatif dan daftar proyek sebagai teks biasa.
- Ukuran per tema: hero ±101 KB, constellation ±37 KB, tree sakura ±51 KB, tree pine ±18 KB.

## Preview

`preview/preview-galaxy-light.html` (halaman putih, aset `*-light.svg`) dan `preview/preview-galaxy-dark.html` (halaman gelap, aset `*-dark.svg`) merender `galaxy/README.md` dengan CSS gaya GitHub, ditambah bagian "hanya di preview" yang menampilkan kedua opsi pohon berdampingan. Bangun ulang:

```sh
npm i --no-save marked@12 github-markdown-css@5        # di folder sementara
PREVIEW_DEPS=/folder/sementara node scripts/buat-preview.mjs
```

### Preview animasi untuk README repo kit

`docs/previews/galaxy-animated-{dark,light}.svg` menggabungkan hero, konstelasi, dan pohon dalam satu gambar dengan data demo. Dibuat dengan:

```sh
python3 galaxy/scripts/render.py --preview-svg docs/previews
python3 scripts/cek-animasi.py        # verifikasi statis, kode keluar 0 bila lolos
```

Gerakan (semuanya CSS di dalam SVG, tanpa JavaScript dan tanpa SMIL):

| Efek | Cara kerja |
| :-- | :-- |
| Kelip bintang | ±26% bintang hero dan bintang konstelasi tingkat 3–4 memakai `tw` (opasitas 0,2 ↔ 1, periode 3,3–7,2 s) dengan jeda acak per bintang |
| Orbit | tiga cincin tipis di bidang galaksi yang sudah dimiringkan, satu titik per cincin, periode 18 s, 29 s (berlawanan arah), dan 44 s |
| Piringan menggoyang | seluruh bintang piringan berputar ±3,5° bolak-balik dalam 28 s, simpangan terjauh ±14 unit |
| Denyut | halo penanda proyek dan lentera amber berdenyut pelan (4,6 s) |

Penanda proyek dan kotak labelnya sengaja diam supaya tetap terbaca, sehingga piringan hanya bergoyang pelan, bukan berputar penuh. Semua animasi berada di dalam `@media (prefers-reduced-motion: no-preference)`; pengguna yang meminta gerak minimal melihat gambar diam yang sama dengan aset statis. Posisi bintang piringan identik dengan `hero-*.svg` yang sudah disetujui (diperiksa oleh `cek-animasi.py`), dan aset statis di `galaxy/assets/` tidak diubah.

`cek-animasi.py` memeriksa: XML valid, tanpa skrip, SMIL, atau URL eksternal; animasi hanya di dalam blok *reduced-motion*; setiap `@keyframes` dan kelas terdefinisi; id unik dan rujukan terpenuhi; tata letak bintang sama dengan aset statis; serta simpangan gerak terburuk tetap di dalam kanvas. Pemeriksaan ini tidak menggantikan melihat animasinya langsung di browser.

Preview HTML dibangun tanpa browser dan tidak menggantikan pengecekan di GitHub sungguhan. Tangkapan layarnya (`docs/previews/preview-galaxy-light.png` dan `docs/previews/preview-galaxy-dark.png`) diambil dari kedua HTML ini dan disertakan di README akar.

## Batasan yang belum diverifikasi

- Tampilan visual belum dilihat langsung; aset divalidasi sebagai XML, dicek batas koordinat, kontras, ukuran font, dan determinismenya. Rendering teks bergantung pada font sistem pembaca.
- Alur Actions dan akses `GITHUB_TOKEN` ke kalender kontribusi belum dijalankan di GitHub. Uji dengan **Run workflow** sebelum mengandalkan jadwal harian.
- Daftar bintang dibatasi 100 repo pertama.

## Kredit dan lisensi

Kode renderer dan semua aset di `galaxy/` ditulis dari nol dan berlisensi [MIT](../LICENSE). Konsepnya terinspirasi oleh proyek berikut. Tidak ada kode atau aset yang disalin.

| Proyek | Lisensi | Gagasan |
| :-- | :-- | :-- |
| [vinimlo/galaxy-profile](https://github.com/vinimlo/galaxy-profile) | GPL-3.0 | profil sebagai galaksi SVG. Kodenya sengaja tidak dibaca atau disalin agar varian ini tetap MIT. |
| [m3hrab/github-constellation](https://github.com/m3hrab/github-constellation) | MIT | riwayat kontribusi sebagai peta bintang |
| [egorthinks/git-bonsai](https://github.com/egorthinks/git-bonsai) | MIT | pohon yang tumbuh dari aktivitas commit |

Preview HTML menyematkan `github-markdown-css` (MIT, © Sindre Sorhus) hanya untuk tampilan preview.

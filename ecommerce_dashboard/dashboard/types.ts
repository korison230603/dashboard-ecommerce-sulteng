
export interface RingkasanUmum {
  total_pedagang: number;
  total_valid: number;
  total_tidak_valid: number;
  total_lokasi: number;
  total_kategori: number;
}

export interface AlasanTidakValid {
  alasan: string;
  jumlah: number;
}

export interface SebaranLokasi {
  lokasi: string;
  jumlah: number;
}

export interface SebaranKategori {
  kategori: string;
  jumlah: number;
}

export interface KonsentrasiPedagang {
  lokasi: string;
  kepadatan: number;
}

export interface PedagangPerLokasi {
  lokasi: string;
  jumlah: number;
  valid: number;
  tidak_valid: number;
}

export interface DiversifikasiKategori {
  lokasi: string;
  index_diversifikasi: number;
}

export interface PedagangRaw {
  id: number;
  nama: string;
  lokasi: string;
  kategori: string;
  is_valid: boolean;
  alasan_tidak_valid?: string;
  created_at: string;
}

export interface DashboardData {
  ringkasan_umum: RingkasanUmum;
  alasan_tidak_valid: AlasanTidakValid[];
  sebaran_lokasi: SebaranLokasi[];
  sebaran_kategori: SebaranKategori[];
  konsentrasi_pedagang: KonsentrasiPedagang[];
  pedagang_per_lokasi: PedagangPerLokasi[];
  diversifikasi_kategori: DiversifikasiKategori[];
  persentase_validitas: number;
  pedagang_per_lokasi_all: PedagangRaw[];
}
